# Reverb 2.0 Landmark Lookup-Table Artifacts

Pre-built lookup-table artifacts emitted by `scripts/resolve-landmarks.py dump`. See `../landmark-lookup-table.md` for the schema contract.

## Filename convention

```
<product>-<version>-<language>.json
```

For example, `epublisher-designer-2026.1-en.json` for the ePublisher Designer 2026.1 English help mirror.

## Current artifacts

| File | Source | Notes |
|---|---|---|
| `tests-fixtures-stand-in.json` | `skills/reverb2/tests/fixtures/` multi-chunk fixtures | Verification stand-in. Not for runtime consumption — purely a reproducible artifact the verifier can re-emit and diff against. |

A real ePublisher Designer 2026.1 Help (en) artifact will ship in a follow-up commit once generated from the production help output.

## Regeneration

Each artifact is reproducible (modulo `source.captured_at`) from its named source:

```bash
python ../../scripts/resolve-landmarks.py dump \
    --from <source-chunks-dir> \
    --out <product>-<version>-<language>.json \
    --source-label "<semantic source name>"
```

Always pass `--source-label`. The default `source.path` is the absolute path of `--from`, which embeds a developer-local filesystem string that would defeat the determinism contract across machines.

The verifier (`tests/verify-landmark-resolver.py`) re-emits each committed artifact and asserts byte-equivalence (modulo `captured_at`) when the underlying source is reachable. Set `REVERB_HELP_MIRROR=<chunks-dir>` to point at an installed help mirror for the freshness check; the verifier `SKIP`s the check cleanly when the source is unavailable.
