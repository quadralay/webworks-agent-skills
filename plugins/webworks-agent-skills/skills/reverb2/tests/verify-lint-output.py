#!/usr/bin/env python3
"""
verify-lint-output.py

Standalone verifier for lint-output.py. Runs every test scenario and prints
PASS/FAIL lines. Exits 0 only when every scenario passes.

Usage:
    python verify-lint-output.py

Two layers:
  - Internal-function tests import lint-output.py as a module and exercise the
    pure parsing/classification helpers directly.
  - CLI contract tests copy the committed `tests/fixtures/lint-output/good`
    tree to a tempdir, mutate one file to inject a single defect, and assert the
    linter's exit code and findings. No network access is required.
"""

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

THIS_DIR = Path(__file__).resolve().parent
SKILL_DIR = THIS_DIR.parent
SCRIPT_PATH = SKILL_DIR / 'scripts' / 'lint-output.py'
GOOD_FIXTURE = THIS_DIR / 'fixtures' / 'lint-output' / 'good'


def _load_linter_module():
    """Import lint-output.py despite the dash in its filename."""
    spec = importlib.util.spec_from_file_location('lint_output', SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


linter = _load_linter_module()

# Reuse the script's palette so PASS/FAIL output stays in sync.
RED = linter.RED
GREEN = linter.GREEN
YELLOW = linter.YELLOW
NC = linter.NC

_results: list[tuple[str, bool, str]] = []


def check(name: str, condition: bool, detail: str = '') -> None:
    _results.append((name, bool(condition), detail))
    if condition:
        print(f"{GREEN}PASS:{NC} {name}")
    else:
        print(f"{RED}FAIL:{NC} {name}" + (f" — {detail}" if detail else ''))


def run_cli(*cli_args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *cli_args],
        capture_output=True,
        text=True,
    )


class CopyOfGood:
    """Context manager: a throwaway copy of the good fixture in a tempdir."""

    def __enter__(self) -> Path:
        self._tmp = Path(tempfile.mkdtemp(prefix='lint-output-'))
        self.root = self._tmp / 'out'
        shutil.copytree(GOOD_FIXTURE, self.root)
        return self.root

    def __exit__(self, *exc) -> None:
        shutil.rmtree(self._tmp, ignore_errors=True)


def _read(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding='utf-8', newline='\n')


def _findings(proc: subprocess.CompletedProcess) -> list[dict]:
    """Parse the --json report's findings list from a CLI run."""
    return json.loads(proc.stdout)['findings']


def _checks_present(findings: list[dict], check_name: str) -> list[dict]:
    return [f for f in findings if f['check'] == check_name]


# ---------------------------------------------------------------------------
# Internal-function tests
# ---------------------------------------------------------------------------

def test_self_closed_flags_non_void() -> None:
    findings = linter.find_self_closed('<div/><span/><a/>')
    tags = sorted(t for _, _, t, _ in findings)
    check("find_self_closed flags non-void <div>/<span>/<a>", tags == ['a', 'div', 'span'], str(tags))


def test_self_closed_ignores_void() -> None:
    findings = linter.find_self_closed('<meta charset="utf-8"/><br/><link href="x"/><img src="y"/>')
    check("find_self_closed ignores void elements", findings == [], str(findings))


def test_self_closed_flags_script() -> None:
    findings = linter.find_self_closed('<head><script src="a.js"/></head>')
    tags = [t for _, _, t, _ in findings]
    check("find_self_closed flags self-closed <script> (Trac #2792)", tags == ['script'], str(tags))


def test_self_closed_skips_cdata_script_body() -> None:
    # A literal "<div/>" inside a real <script> body is CDATA text, not a tag.
    findings = linter.find_self_closed('<script>var s = "<div/>";</script><p>ok</p>')
    check("find_self_closed ignores <div/> inside script CDATA", findings == [], str(findings))


def test_self_closed_exempts_foreign_content() -> None:
    findings = linter.find_self_closed('<svg viewBox="0 0 1 1"><path d="M0 0"/><rect/></svg>')
    check("find_self_closed exempts <svg> foreign content", findings == [], str(findings))


def test_self_closed_after_foreign_closes() -> None:
    # Once </svg> closes, a self-closed <div/> in HTML context is flagged again.
    findings = linter.find_self_closed('<svg><path d="x"/></svg><div/>')
    tags = [t for _, _, t, _ in findings]
    check("find_self_closed resumes flagging after </svg>", tags == ['div'], str(tags))


def test_parse_manifest_good() -> None:
    entries = linter.parse_manifest(_read(GOOD_FIXTURE / 'index.html'))
    ok = (
        len(entries) == 2
        and entries[0].gid_anchor == 'gid-alpha' and entries[0].href == 'Alpha.html'
        and entries[0].gid_li == 'gid-alpha' and entries[0].name == 'Alpha'
        and entries[1].gid_anchor == 'gid-bravo' and entries[1].href == 'Bravo.html'
    )
    check("parse_manifest extracts both parcels with gid/href/name", ok,
          f"got {[(e.name, e.gid_anchor, e.href) for e in entries]}")


def test_gid_anchor_split() -> None:
    mk = linter.ParcelEntry
    ok = (
        mk(None, None, 'Alpha:gid-alpha', 'Alpha.html').gid_anchor == 'gid-alpha'
        and mk(None, None, ':gid-x', 'x.html').gid_anchor is None
        and mk(None, None, 'nocolon', 'x.html').gid_anchor is None
        and mk(None, None, None, None).gid_anchor is None
    )
    check("ParcelEntry.gid_anchor mirrors id.split(':')[1]", ok)


def test_classify_gid_id() -> None:
    c = linter.classify_gid_id
    ok = (
        c('id:gid-a') == 'gid-a'
        and c('toc:gid-a') == 'gid-a'
        and c('data:gid-a') == 'gid-a'
        and c('page:gid-a:first') == 'gid-a'
        and c('page:gid-a:last') == 'gid-a'
        and c('breadcrumbs:gid-a') is None       # excluded prefix
        and c('breadcrumbs:p9aXbYcZ') is None     # page-keyed, not a GroupID
        and c('connect_body') is None
    )
    check("classify_gid_id maps id/toc/data/page, excludes breadcrumbs", ok)


def test_extract_parcel_gids() -> None:
    body_gid, gids = linter.extract_parcel_gids(_read(GOOD_FIXTURE / 'Alpha.html'))
    ok = body_gid == 'gid-alpha' and gids == {'gid-alpha'}
    check("extract_parcel_gids returns body GID, ignores page-keyed breadcrumbs", ok,
          f"body={body_gid} gids={sorted(gids)}")


def test_extract_local_assets() -> None:
    refs = linter.extract_local_assets(_read(GOOD_FIXTURE / 'index.html'))
    paths = sorted(p for _, p in refs)
    ok = paths == ['css/base.css', 'scripts/common.js', 'scripts/connect.js']
    check("extract_local_assets strips ?v=, drops remote cdn refs", ok, str(paths))


def test_expected_chunk_suffixes() -> None:
    suffixes = linter.expected_chunk_suffixes(GOOD_FIXTURE)
    ok = sorted(suffixes) == ['_ix.html', '_lx.js', '_sx.js']
    check("expected_chunk_suffixes reads all three from the fixture connect.js", ok, str(suffixes))


# ---------------------------------------------------------------------------
# CLI contract tests
# ---------------------------------------------------------------------------

def test_cli_good_clean() -> None:
    proc = run_cli(str(GOOD_FIXTURE), '--no-color')
    check("CLI: good fixture exits 0", proc.returncode == 0, proc.stdout + proc.stderr)
    check("CLI: good fixture reports OK", 'OK' in proc.stdout, proc.stdout)


def test_cli_good_json() -> None:
    proc = run_cli(str(GOOD_FIXTURE), '--json')
    data = json.loads(proc.stdout)
    ok = data['success'] is True and data['findings'] == [] and data['summary']['errors'] == 0
    check("CLI: good fixture --json has success=true, no findings", ok, proc.stdout)


def test_cli_self_closed() -> None:
    with CopyOfGood() as root:
        idx = root / 'index.html'
        text = _read(idx).replace(
            'src="scripts/connect.js?v=abc123"></script>',
            'src="scripts/connect.js?v=abc123"/>',
        )
        _write(idx, text)
        proc = run_cli(str(root), '--json')
        sc = _checks_present(_findings(proc), 'self-closed-element')
        ok = proc.returncode == 1 and any(f['file'] == 'index.html' and 'script' in f['snippet'] for f in sc)
        check("CLI: self-closed <script/> flagged on index.html, exit 1", ok,
              f"rc={proc.returncode} findings={sc}")


def test_cli_groupid_total_mismatch() -> None:
    with CopyOfGood() as root:
        alpha = root / 'Alpha.html'
        _write(alpha, _read(alpha).replace('gid-alpha', 'gid-wrong'))
        proc = run_cli(str(root), '--json')
        gm = _checks_present(_findings(proc), 'manifest-parcel-groupid')
        ok = (
            proc.returncode == 1
            and any(f['file'] == 'Alpha.html' and 'gid-wrong' in f['message']
                    and 'gid-alpha' in f['message'] for f in gm)
        )
        check("CLI: whole-parcel GroupID mismatch flagged, exit 1", ok,
              f"rc={proc.returncode} findings={gm}")


def test_cli_li_anchor_mismatch() -> None:
    with CopyOfGood() as root:
        idx = root / 'index.html'
        # Desync the wrapping <li group:GID> from its anchor's GID.
        _write(idx, _read(idx).replace('id="group:gid-alpha"', 'id="group:gid-zzz"'))
        proc = run_cli(str(root), '--json')
        gm = _checks_present(_findings(proc), 'manifest-parcel-groupid')
        ok = (
            proc.returncode == 1
            and any(f['file'] == 'index.html' and 'gid-zzz' in f['message'] for f in gm)
        )
        check("CLI: manifest <li> vs anchor GroupID desync flagged, exit 1", ok,
              f"rc={proc.returncode} findings={gm}")


def test_cli_missing_deploy_file() -> None:
    with CopyOfGood() as root:
        os.remove(root / 'Alpha_lx.js')
        proc = run_cli(str(root), '--json')
        du = _checks_present(_findings(proc), 'parcel-deploy-unit')
        ok = proc.returncode == 1 and any(f['file'] == 'Alpha_lx.js' for f in du)
        check("CLI: missing _lx.js deploy-unit file flagged, exit 1", ok,
              f"rc={proc.returncode} findings={du}")


def test_cli_older_build_omits_lx_chunk() -> None:
    # An older build whose connect.js does not fetch _lx.js legitimately ships no
    # <Name>_lx.js. Removing the chunk AND its connect.js reference must NOT be
    # flagged (regression guard: real pre-landmark builds were false-positived).
    with CopyOfGood() as root:
        os.remove(root / 'Alpha_lx.js')
        os.remove(root / 'Bravo_lx.js')
        connect = root / 'scripts' / 'connect.js'
        text = _read(connect)
        text = '\n'.join(line for line in text.splitlines() if '_lx.js' not in line) + '\n'
        _write(connect, text)
        proc = run_cli(str(root), '--json')
        du = _checks_present(_findings(proc), 'parcel-deploy-unit')
        ok = proc.returncode == 0 and du == []
        check("CLI: older build (connect.js omits _lx.js) is not flagged for missing _lx.js",
              ok, f"rc={proc.returncode} findings={du}")


def test_cli_missing_content_dir() -> None:
    with CopyOfGood() as root:
        shutil.rmtree(root / 'Alpha')
        proc = run_cli(str(root), '--json')
        du = _checks_present(_findings(proc), 'parcel-deploy-unit')
        ok = proc.returncode == 1 and any(f['file'] == 'Alpha/' for f in du)
        check("CLI: missing parcel content directory flagged, exit 1", ok,
              f"rc={proc.returncode} findings={du}")


def test_cli_missing_asset_warns() -> None:
    with CopyOfGood() as root:
        os.remove(root / 'scripts' / 'common.js')
        proc = run_cli(str(root), '--json')
        data = json.loads(proc.stdout)
        ri = _checks_present(data['findings'], 'reference-integrity')
        ok = (
            proc.returncode == 0  # warnings alone do not fail
            and data['success'] is True
            and any(f['file'] == 'scripts/common.js' and f['severity'] == 'warn' for f in ri)
        )
        check("CLI: missing local asset warns, exit 0 (non-strict)", ok,
              f"rc={proc.returncode} findings={ri}")

        proc_strict = run_cli(str(root), '--json', '--strict')
        ok_strict = proc_strict.returncode == 1 and json.loads(proc_strict.stdout)['success'] is False
        check("CLI: --strict turns the warning into exit 1", ok_strict,
              f"rc={proc_strict.returncode}")


def test_cli_missing_index() -> None:
    tmp = Path(tempfile.mkdtemp(prefix='lint-output-empty-'))
    try:
        proc = run_cli(str(tmp), '--json')
        findings = _findings(proc)
        ok = proc.returncode == 1 and any('index.html' in (f.get('file') or '') for f in findings)
        check("CLI: missing index.html flagged, exit 1", ok, f"rc={proc.returncode} findings={findings}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_cli_not_a_directory() -> None:
    proc = run_cli(str(THIS_DIR / 'does-not-exist-xyz'), '--no-color')
    check("CLI: non-existent output dir exits 2", proc.returncode == 2, f"rc={proc.returncode}")


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

def main() -> int:
    tests = [
        test_self_closed_flags_non_void,
        test_self_closed_ignores_void,
        test_self_closed_flags_script,
        test_self_closed_skips_cdata_script_body,
        test_self_closed_exempts_foreign_content,
        test_self_closed_after_foreign_closes,
        test_parse_manifest_good,
        test_gid_anchor_split,
        test_classify_gid_id,
        test_extract_parcel_gids,
        test_extract_local_assets,
        test_expected_chunk_suffixes,
        test_cli_good_clean,
        test_cli_good_json,
        test_cli_self_closed,
        test_cli_groupid_total_mismatch,
        test_cli_li_anchor_mismatch,
        test_cli_missing_deploy_file,
        test_cli_older_build_omits_lx_chunk,
        test_cli_missing_content_dir,
        test_cli_missing_asset_warns,
        test_cli_missing_index,
        test_cli_not_a_directory,
    ]
    print(f"Running {len(tests)} lint-output test scenarios\n")
    for test in tests:
        try:
            test()
        except Exception as e:  # noqa: BLE001 — a crashing test is a failed test
            check(test.__name__, False, f"raised {type(e).__name__}: {e}")

    passed = sum(1 for _, ok, _ in _results if ok)
    total = len(_results)
    print()
    if passed == total:
        print(f"{GREEN}All {total} checks passed{NC}")
        return 0
    print(f"{RED}{total - passed} of {total} checks failed{NC}")
    return 1


if __name__ == '__main__':
    sys.exit(main())
