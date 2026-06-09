#!/usr/bin/env node
/**
 * browser-test.js
 *
 * Puppeteer-based browser automation for testing WebWorks Reverb output.
 * Loads Reverb in headless Chrome, monitors console errors, inspects components,
 * and returns structured test results as JSON.
 *
 * PRIMARY pass/fail signal: the `preload` class is REMOVED from
 * <body id="connect_body">. Reverb's connect.js removes it only in its
 * page_load_complete handler, which fires when the FIRST content page actually
 * renders inside page_iframe. So preload-removed == fully loaded; preload-still-
 * present == stuck on the spinner / broken. `Parcels.loaded_all` and "no console
 * errors" are NOT reliable — connect.js catches exceptions internally, so a
 * broken load can still report loaded_all === true (or fail silently). Those are
 * kept only as secondary diagnostics.
 *
 * Usage:
 *   node browser-test.js <chrome-path> <entry-url> [format-settings-json] [--vanilla]
 *
 * Arguments:
 *   chrome-path           - Path to Chrome/Chromium executable
 *   entry-url             - file:// URL to Reverb entry point (the output index.html)
 *   format-settings-json  - Optional JSON string with FormatSettings
 *
 * Flags:
 *   --vanilla        - No-bypass mode: launch Chrome WITHOUT
 *                      --disable-web-security / --allow-file-access-from-files so
 *                      the test sees exactly what a user gets double-clicking the
 *                      file from disk. The default (bypass) mode masks
 *                      vanilla-file:// breakage. Also settable via VANILLA=1.
 *
 * Output:
 *   JSON with test results including the primary preload signal, secondary
 *   diagnostics, errors, warnings, and component analysis
 *
 * Environment Variables:
 *   TIMEOUT          - Page load timeout in milliseconds (default: 30000)
 *   DEBUG            - Enable verbose logging (1 or 0, default: 0)
 *   SCREENSHOT_PATH  - Optional path to save screenshot
 *   VANILLA          - Set to 1 for no-bypass mode (same as --vanilla)
 */

const puppeteer = require('puppeteer-core');

// Configuration
const TIMEOUT = parseInt(process.env.TIMEOUT || '30000', 10);
const DEBUG = process.env.DEBUG === '1';
const SCREENSHOT_PATH = process.env.SCREENSHOT_PATH || null;

// Exit codes
const EXIT_SUCCESS = 0;
const EXIT_ERROR = 1;

/**
 * Logger utility
 */
const logger = {
  debug: (...args) => {
    if (DEBUG) console.error('[DEBUG]', ...args);
  },
  info: (...args) => console.error('[INFO]', ...args),
  warn: (...args) => console.error('[WARN]', ...args),
  error: (...args) => console.error('[ERROR]', ...args),
};

/**
 * Parse command-line arguments
 */
function parseArguments() {
  const raw = process.argv.slice(2);

  // Separate flags (--foo) from positional arguments so the flag can appear anywhere.
  const flags = raw.filter((a) => a.startsWith('--'));
  const positional = raw.filter((a) => !a.startsWith('--'));
  const vanilla = flags.includes('--vanilla') || process.env.VANILLA === '1';

  if (positional.length < 2) {
    console.error('Usage: browser-test.js <chrome-path> <entry-url> [format-settings-json] [--vanilla]');
    process.exit(EXIT_ERROR);
  }

  const chromePath = positional[0];
  const entryUrl = positional[1];
  const formatSettingsJson = positional[2] || '{}';

  let formatSettings = {};
  try {
    formatSettings = JSON.parse(formatSettingsJson);
  } catch (error) {
    logger.error('Failed to parse format-settings-json:', error.message);
    process.exit(EXIT_ERROR);
  }

  return { chromePath, entryUrl, formatSettings, vanilla };
}

/**
 * Test result accumulator
 */
class TestResults {
  constructor() {
    this.errors = [];
    this.warnings = [];
    this.infos = [];
    // PRIMARY signal: preload removed from body#connect_body (first page rendered).
    this.preloadCleared = false;
    // SECONDARY diagnostic: Parcels.loaded_all (unreliable — see file header). null = unknown.
    this.parcelsLoadedAll = null;
    // Raw read of the primary signal and supporting state, for debugging failures.
    this.diagnostics = {};
    this.vanillaMode = false;
    this.loadTime = 0;
    this.components = {};
    this.formatSettingsMismatches = [];
  }

  addError(message, details = null) {
    this.errors.push({ message, details, timestamp: new Date().toISOString() });
  }

  addWarning(message, details = null) {
    this.warnings.push({ message, details, timestamp: new Date().toISOString() });
  }

  addInfo(message, details = null) {
    this.infos.push({ message, details, timestamp: new Date().toISOString() });
  }

  toJSON() {
    return {
      // PRIMARY pass/fail: the preload class was removed from body#connect_body.
      success: this.preloadCleared,
      preloadCleared: this.preloadCleared,
      // Backward-compatible alias of the primary signal (was Parcels-based).
      reverbLoaded: this.preloadCleared,
      vanillaMode: this.vanillaMode,
      loadTime: this.loadTime,
      // SECONDARY diagnostic only — do NOT gate on this (connect.js catches exceptions).
      parcelsLoadedAll: this.parcelsLoadedAll,
      diagnostics: this.diagnostics,
      errors: this.errors,
      warnings: this.warnings,
      infos: this.infos,
      components: this.components,
      formatSettingsMismatches: this.formatSettingsMismatches,
      errorCount: this.errors.length,
      warningCount: this.warnings.length,
    };
  }
}

/**
 * Launch browser and create page
 *
 * @param {string}  chromePath  Path to the Chrome/Chromium executable.
 * @param {boolean} vanilla     When true, omit the web-security bypass flags so
 *                              the runtime is exercised exactly as a user double-
 *                              clicking the file from disk would see it. When
 *                              false (default), the bypass flags are added — they
 *                              let the parent read cross-origin iframe DOM and so
 *                              can MASK vanilla-file:// breakage.
 */
async function launchBrowser(chromePath, vanilla) {
  logger.debug('Launching browser:', chromePath, vanilla ? '(vanilla / no-bypass)' : '(bypass)');

  // Harness/sandbox flags — unrelated to web-origin behavior, kept in both modes.
  const args = [
    '--no-sandbox',
    '--disable-setuid-sandbox',
    '--disable-dev-shm-usage',
  ];

  if (!vanilla) {
    // Bypass flags: convenient for headless testing but they relax file:// origin
    // rules, so a build that is broken for real users can still appear to load.
    args.push('--disable-web-security');
    args.push('--allow-file-access-from-files');
  }

  const browser = await puppeteer.launch({
    executablePath: chromePath,
    headless: true,
    args,
  });

  logger.debug('Browser launched successfully');
  return browser;
}

/**
 * Setup console monitoring
 */
function setupConsoleMonitoring(page, results) {
  page.on('console', (msg) => {
    const type = msg.type();
    const text = msg.text();

    logger.debug(`Console [${type}]:`, text);

    if (type === 'error') {
      results.addError(`Console error: ${text}`);
    } else if (type === 'warning') {
      results.addWarning(`Console warning: ${text}`);
    }
  });

  page.on('pageerror', (error) => {
    logger.debug('Page error:', error.message);
    results.addError(`Page error: ${error.message}`, { stack: error.stack });
  });

  page.on('requestfailed', (request) => {
    const url = request.url();
    const failure = request.failure();
    logger.debug('Request failed:', url, failure);
    results.addError(`Failed to load resource: ${url}`, { reason: failure ? failure.errorText : 'Unknown' });
  });
}

/**
 * Predicate (runs in the page) for the PRIMARY load signal: the entry shell is
 * body#connect_body and the `preload` class has been removed from it. connect.js
 * removes preload only after the first content page renders, so this is the one
 * reliable "fully loaded" signal.
 */
function preloadClearedInPage() {
  var body = document.body;
  return !!body && body.id === 'connect_body' && !body.classList.contains('preload');
}

/**
 * Read the primary load signal and supporting diagnostics from the page, on both
 * the pass and fail paths, and set results.preloadCleared accordingly. This is
 * the single source of truth for the pass/fail decision.
 */
async function capturePrimarySignal(page, results) {
  try {
    const signal = await page.evaluate(() => {
      var body = document.body;
      var parcels = (typeof Parcels !== 'undefined' && Parcels !== null) ? Parcels : null;
      var connect = (typeof Connect !== 'undefined' && Connect !== null) ? Connect : null;
      return {
        bodyId: body ? body.id : null,
        hasPreloadClass: body ? body.classList.contains('preload') : null,
        parcelsDefined: parcels !== null,
        parcelsLoadedAll: parcels ? (parcels.loaded_all === true) : null,
        firstPageLoaded: connect ? (connect.first_page_loaded === true) : null,
        readyState: document.readyState,
      };
    });

    results.diagnostics = signal;
    results.parcelsLoadedAll = signal.parcelsLoadedAll;

    if (signal.bodyId !== 'connect_body') {
      // Not the Reverb shell — the preload signal does not apply, so we cannot
      // confirm a successful load. Fail safe rather than risk a false pass.
      results.preloadCleared = false;
      results.addWarning(
        "Entry page is not a Reverb shell (body#connect_body not found) -- the 'preload' " +
          'load signal cannot be evaluated. Verify the entry URL points at the Reverb ' +
          "output's index.html.",
        { bodyId: signal.bodyId }
      );
    } else {
      results.preloadCleared = signal.hasPreloadClass === false;
    }
  } catch (error) {
    results.preloadCleared = false;
    results.addError('Failed to read primary load signal (preload class on body#connect_body)', {
      error: error.message,
    });
  }
}

/**
 * Load Reverb output and wait for the primary load signal (preload cleared).
 */
async function loadReverbOutput(page, entryUrl, results) {
  logger.info('Loading Reverb output:', entryUrl);

  const startTime = Date.now();

  // Navigate. Use 'domcontentloaded' (not 'networkidle2') because in vanilla
  // file:// mode blocked cross-origin requests may never let the network go idle;
  // the preload signal below — not network quiescence — is the real completion gate.
  try {
    await page.goto(entryUrl, {
      waitUntil: 'domcontentloaded',
      timeout: TIMEOUT,
    });
  } catch (error) {
    results.loadTime = Date.now() - startTime;
    if (error.name === 'TimeoutError') {
      results.addError('Timeout navigating to entry URL', {
        timeout: TIMEOUT,
        entryUrl,
        suggestion: 'Try increasing TIMEOUT environment variable',
      });
    } else {
      results.addError('Failed to navigate to entry URL', { error: error.message, entryUrl });
    }
    await capturePrimarySignal(page, results);
    return;
  }

  logger.debug('Page loaded, waiting for preload to clear (first content page render)...');

  // PRIMARY wait: spinner clears == preload removed from body#connect_body.
  try {
    await page.waitForFunction(preloadClearedInPage, { timeout: TIMEOUT });
    logger.info('preload cleared -- Reverb fully loaded');
  } catch (error) {
    if (error.name === 'TimeoutError') {
      results.addError(
        "Reverb never finished loading: 'preload' class still present on body#connect_body " +
          '(spinner never cleared -- the first content page did not render). This is the broken-' +
          'load case that Parcels.loaded_all and "no console errors" can miss.',
        { timeout: TIMEOUT, vanillaMode: results.vanillaMode }
      );
    } else {
      results.addError('Error while waiting for preload signal', { error: error.message });
    }
  }

  results.loadTime = Date.now() - startTime;

  // Read the final state (sets preloadCleared) regardless of pass/fail.
  await capturePrimarySignal(page, results);

  if (results.preloadCleared) {
    logger.info(`Reverb loaded successfully in ${results.loadTime}ms`);
  } else {
    logger.warn(`Reverb did not fully load (preload not cleared) after ${results.loadTime}ms`);
  }
}

/**
 * Analyze Reverb components in DOM
 */
async function analyzeComponents(page, results) {
  logger.debug('Analyzing Reverb components...');

  try {
    results.components = await page.evaluate(() => {
      const components = {};

      // Toolbar - Check for child nodes (element exists even when disabled)
      const toolbarDiv = document.getElementById('toolbar_div');
      const toolbarPresent = toolbarDiv !== null && toolbarDiv.childNodes.length > 0;
      components.toolbar = {
        present: toolbarPresent,
        logo: null,
        searchPresent: false,
      };

      if (toolbarPresent) {
        const logo = document.getElementById('ww_skin_toolbar_logo');
        if (logo) {
          components.toolbar.logo = logo.src || 'present';
        }
        components.toolbar.searchPresent = document.querySelector('.ww_skin_search_form') !== null;
      }

      // Header - Check for child nodes (element exists even when disabled)
      const headerDiv = document.getElementById('header_div');
      const headerPresent = headerDiv !== null && headerDiv.childNodes.length > 0;
      components.header = {
        present: headerPresent,
        logo: null,
      };

      if (headerPresent) {
        const logo = document.getElementById('ww_skin_header_logo');
        if (logo) {
          components.header.logo = logo.src || 'present';
        }
      }

      // Footer - Dual-mode detection (end-of-layout or end-of-page)
      const footerDiv = document.getElementById('footer_div');
      const hasEndOfLayoutFooter = footerDiv && footerDiv.childNodes.length > 0;
      const hasEndOfPageFooter = document.getElementById('ww_skin_footer') !== null;
      const footerPresent = hasEndOfLayoutFooter || hasEndOfPageFooter;

      components.footer = {
        present: footerPresent,
        type: hasEndOfLayoutFooter ? 'end-of-layout' : (hasEndOfPageFooter ? 'end-of-page' : 'none'),
        logo: null,
      };

      if (footerPresent) {
        const logo = document.getElementById('ww_skin_footer_logo');
        if (logo) {
          components.footer.logo = logo.src || 'present';
        }
      }

      // TOC - Check for child nodes (element exists even when disabled)
      const tocDiv = document.getElementById('toc');
      const tocPresent = tocDiv !== null && tocDiv.childNodes.length > 0;
      components.toc = {
        present: tocPresent,
        expanded: false,
        itemCount: 0,
      };

      if (tocPresent) {
        components.toc.expanded = tocDiv.classList.contains('expanded') || tocDiv.style.display !== 'none';
        components.toc.itemCount = tocDiv.querySelectorAll('.ww_skin_toc_entry').length;
      }

      // Content Area (Reverb uses iframe for content)
      const pageDiv = document.getElementById('page_div');
      const pageIframe = document.getElementById('page_iframe');
      components.content = {
        present: pageDiv !== null,
        hasIframe: pageIframe !== null,
        iframeSrc: pageIframe ? pageIframe.src : null,
      };

      return components;
    });

    logger.debug('Component analysis complete:', results.components);
  } catch (error) {
    results.addError('Failed to analyze components', { error: error.message });
  }
}

/**
 * Validate FormatSettings against DOM
 */
async function validateFormatSettings(page, formatSettings, results) {
  if (!formatSettings || Object.keys(formatSettings).length === 0) {
    logger.debug('No FormatSettings provided, skipping validation');
    return;
  }

  logger.debug('Validating FormatSettings against DOM...');

  // Default each sub-object so validation is null-safe even when component
  // analysis did not populate results.components (e.g. a failed/stuck load).
  const components = results.components || {};
  components.toolbar = components.toolbar || {};
  components.header = components.header || {};
  components.footer = components.footer || {};
  components.toc = components.toc || {};

  // Validate toolbar-generate
  if (formatSettings['toolbar-generate'] === 'false' && components.toolbar.present) {
    results.formatSettingsMismatches.push('toolbar-generate=false but toolbar exists in DOM');
  } else if (formatSettings['toolbar-generate'] === 'true' && !components.toolbar.present) {
    results.formatSettingsMismatches.push('toolbar-generate=true but toolbar missing from DOM');
  }

  // Validate header-generate
  if (formatSettings['header-generate'] === 'false' && components.header.present) {
    results.formatSettingsMismatches.push('header-generate=false but header exists in DOM');
  } else if (formatSettings['header-generate'] === 'true' && !components.header.present) {
    results.formatSettingsMismatches.push('header-generate=true but header missing from DOM');
  }

  // Validate footer-generate
  if (formatSettings['footer-generate'] === 'false' && components.footer.present) {
    results.formatSettingsMismatches.push('footer-generate=false but footer exists in DOM');
  } else if (formatSettings['footer-generate'] === 'true' && !components.footer.present) {
    results.formatSettingsMismatches.push('footer-generate=true but footer missing from DOM');
  }

  // Validate toc-generate
  if (formatSettings['toc-generate'] === 'false' && components.toc.present) {
    results.formatSettingsMismatches.push('toc-generate=false but TOC exists in DOM');
  } else if (formatSettings['toc-generate'] === 'true' && !components.toc.present) {
    results.formatSettingsMismatches.push('toc-generate=true but TOC missing from DOM');
  }

  // Validate toc-initial-state
  if (formatSettings['toc-initial-state'] === 'expanded' && components.toc.present && !components.toc.expanded) {
    results.formatSettingsMismatches.push('toc-initial-state=expanded but TOC is collapsed');
  } else if (formatSettings['toc-initial-state'] === 'collapsed' && components.toc.present && components.toc.expanded) {
    results.formatSettingsMismatches.push('toc-initial-state=collapsed but TOC is expanded');
  }

  logger.debug('FormatSettings validation complete. Mismatches:', results.formatSettingsMismatches.length);
}

/**
 * Capture screenshot if requested
 */
async function captureScreenshot(page, screenshotPath) {
  if (!screenshotPath) return;

  logger.info('Capturing screenshot:', screenshotPath);

  try {
    await page.screenshot({
      path: screenshotPath,
      fullPage: true,
    });
    logger.info('Screenshot saved successfully');
  } catch (error) {
    logger.error('Failed to capture screenshot:', error.message);
  }
}

/**
 * Main test execution
 */
async function runTests() {
  const { chromePath, entryUrl, formatSettings, vanilla } = parseArguments();
  const results = new TestResults();
  results.vanillaMode = vanilla;

  let browser = null;

  try {
    // Launch browser
    browser = await launchBrowser(chromePath, vanilla);
    const page = await browser.newPage();

    // Setup monitoring
    setupConsoleMonitoring(page, results);

    // Load Reverb output (sets the primary preload signal)
    await loadReverbOutput(page, entryUrl, results);

    // Secondary diagnostics — run regardless of pass/fail so a failing report
    // still shows what rendered (and the screenshot captures the stuck spinner).
    await analyzeComponents(page, results);
    await validateFormatSettings(page, formatSettings, results);
    await captureScreenshot(page, SCREENSHOT_PATH);
  } catch (error) {
    results.addError('Unexpected error during test execution', { error: error.message, stack: error.stack });
  } finally {
    if (browser) {
      await browser.close();
      logger.debug('Browser closed');
    }
  }

  // Output results as JSON
  console.log(JSON.stringify(results.toJSON(), null, 2));

  // Exit code follows the PRIMARY signal (preload cleared), not console errors.
  process.exit(results.preloadCleared ? EXIT_SUCCESS : EXIT_ERROR);
}

// Run tests
runTests().catch((error) => {
  console.error(JSON.stringify({
    success: false,
    errors: [{ message: 'Fatal error', details: error.message, stack: error.stack }],
  }, null, 2));
  process.exit(EXIT_ERROR);
});
