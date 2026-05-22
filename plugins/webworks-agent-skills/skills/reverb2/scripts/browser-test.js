#!/usr/bin/env node
/**
 * browser-test.js
 *
 * Puppeteer-based browser automation for testing WebWorks Reverb output.
 * Loads Reverb in headless Chrome, monitors console errors, inspects components,
 * and returns structured test results as JSON.
 *
 * Usage:
 *   node browser-test.js <chrome-path> <entry-url> [format-settings-json]
 *
 * Arguments:
 *   chrome-path           - Path to Chrome/Chromium executable
 *   entry-url             - file:// URL to Reverb entry point
 *   format-settings-json  - Optional JSON string with FormatSettings
 *
 * Output:
 *   JSON with test results including errors, warnings, and component analysis
 *
 * Environment Variables:
 *   TIMEOUT          - Page load timeout in milliseconds (default: 30000)
 *   DEBUG            - Enable verbose logging (1 or 0, default: 0)
 *   SCREENSHOT_PATH  - Optional path to save screenshot
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
  const args = process.argv.slice(2);

  if (args.length < 2) {
    console.error('Usage: browser-test.js <chrome-path> <entry-url> [format-settings-json]');
    process.exit(EXIT_ERROR);
  }

  const chromePath = args[0];
  const entryUrl = args[1];
  const formatSettingsJson = args[2] || '{}';

  let formatSettings = {};
  try {
    formatSettings = JSON.parse(formatSettingsJson);
  } catch (error) {
    logger.error('Failed to parse format-settings-json:', error.message);
    process.exit(EXIT_ERROR);
  }

  return { chromePath, entryUrl, formatSettings };
}

/**
 * Test result accumulator
 */
class TestResults {
  constructor() {
    this.errors = [];
    this.warnings = [];
    this.infos = [];
    this.reverbLoaded = false;
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
      success: this.errors.length === 0,
      reverbLoaded: this.reverbLoaded,
      loadTime: this.loadTime,
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
 */
async function launchBrowser(chromePath) {
  logger.debug('Launching browser:', chromePath);

  const browser = await puppeteer.launch({
    executablePath: chromePath,
    headless: true,
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-web-security', // Allow file:// access
      '--allow-file-access-from-files',
    ],
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
 * Load Reverb output and wait for initialization
 */
async function loadReverbOutput(page, entryUrl, results) {
  logger.info('Loading Reverb output:', entryUrl);

  const startTime = Date.now();

  try {
    await page.goto(entryUrl, {
      waitUntil: 'networkidle2',
      timeout: TIMEOUT,
    });

    logger.debug('Page loaded, waiting for Reverb runtime...');

    // Wait for Reverb runtime to initialize (Parcels.loaded_all === true)
    await page.waitForFunction(
      () => (typeof Parcels !== 'undefined' && Parcels.loaded_all === true) || document.readyState === 'complete',
      { timeout: TIMEOUT }
    );

    const endTime = Date.now();
    results.loadTime = endTime - startTime;
    results.reverbLoaded = true;

    logger.info(`Reverb loaded successfully in ${results.loadTime}ms`);
  } catch (error) {
    const endTime = Date.now();
    results.loadTime = endTime - startTime;

    if (error.name === 'TimeoutError') {
      results.addError('Timeout waiting for Reverb to load', {
        timeout: TIMEOUT,
        suggestion: 'Try increasing TIMEOUT environment variable',
      });
    } else {
      results.addError('Failed to load Reverb output', { error: error.message });
    }
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

  const { components } = results;

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
  const { chromePath, entryUrl, formatSettings } = parseArguments();
  const results = new TestResults();

  let browser = null;

  try {
    // Launch browser
    browser = await launchBrowser(chromePath);
    const page = await browser.newPage();

    // Setup monitoring
    setupConsoleMonitoring(page, results);

    // Load Reverb output
    await loadReverbOutput(page, entryUrl, results);

    if (results.reverbLoaded) {
      // Analyze components
      await analyzeComponents(page, results);

      // Validate FormatSettings
      await validateFormatSettings(page, formatSettings, results);

      // Capture screenshot if requested
      await captureScreenshot(page, SCREENSHOT_PATH);
    }
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

  // Exit with appropriate code
  process.exit(results.errors.length === 0 ? EXIT_SUCCESS : EXIT_ERROR);
}

// Run tests
runTests().catch((error) => {
  console.error(JSON.stringify({
    success: false,
    errors: [{ message: 'Fatal error', details: error.message, stack: error.stack }],
  }, null, 2));
  process.exit(EXIT_ERROR);
});
