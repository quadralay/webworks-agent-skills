---
title: "feat: Implement MDPP009 orphaned comment tag validation"
type: feat
status: completed
date: 2026-03-01
---

# Implement MDPP009 Orphaned Comment Tag Validation

## Overview

The markdown-plus-plus skill documents an MDPP009 validation code ("Orphaned comment tag") in the syntax-reference.md validation table, but the validation script (`validate-mdpp.py`) does not yet implement it. A prior session completed all documentation updates (attachment rules in syntax-reference.md, common mistakes in SKILL.md and best-practices.md, MDPP009 in the validation table). This plan covers implementing the check in the script and adding test coverage.

## Problem Statement / Motivation

Markdown++ comment tags (styles, aliases, markers, multiline) must be attached to the content element they apply to — no blank line between the tag and the element. A blank line silently breaks the association, causing the tag to pass through as a plain HTML comment with no effect. This is a common authoring mistake that produces no error, just unexpected output. Authors need tooling to catch it.

## Proposed Solution

Add MDPP009 detection logic to `validate_file()` in `validate-mdpp.py`, plus shared code-fence tracking infrastructure that benefits all existing checks. Create a dedicated test file exercising both positive (should warn) and negative (should not warn) scenarios.

## Technical Considerations

### Architecture

The implementation integrates into the existing single-pass, line-by-line validation loop in `validate_file()`. Key additions:

1. **Code fence tracking** (shared infrastructure) — a boolean `in_code_fence` flag toggled on ``` / ~~~ lines. All existing checks (MDPP001-008) benefit from this; they currently have no awareness of code fences and can produce false positives on syntax shown in code examples.

2. **MDPP009 check** — after the main loop, a second pass identifies non-exempt MDPP comment tags and verifies attachment via lookahead.

### Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Inline vs. block tags | Skip orphan check if tag is not the only non-whitespace on the line | Inline tags attach to content on the same line; checking "next line" would produce false positives |
| Consecutive separate tags | Flag as orphaned — author should use combined syntax | Combined tags (`<!-- style:X ; #alias ; marker:Y="Z" -->`) are the standard; separate tags on consecutive lines are not valid attachment and should warn |
| Code fence tracking | Shared `in_code_fence` flag for all checks | Minimal cost (one boolean toggle), fixes latent false-positive bug in MDPP001-008 |
| Content element definition | Any non-blank line that is not an MDPP comment tag is a valid content element | Catch-all avoids false positives; overly specific patterns risk missing valid Markdown constructs |
| Multiline strictness | General content check (same as other tags) | Multiline-before-non-table is a valid concern but belongs in a separate, stricter check (future MDPP010) |
| Mixed exempt/non-exempt combined tags | If any non-exempt command present, check for attachment | `<!-- condition:web ; style:Heading -->` contains a style — the style needs attachment |
| Severity | Warning | Orphaned tags are harmless (pass through) but indicate likely authoring error |

### Implementation Approach

#### Phase 1: Code Fence Tracking (shared infrastructure)

Add to `validate_file()` at the top of the main loop:

```python
# validate-mdpp.py — inside validate_file(), before existing loop
CODE_FENCE_PATTERN = re.compile(r'^\s{0,3}(`{3,}|~{3,})')

in_code_fence = False
for line_num, line in enumerate(lines, start=1):
    if CODE_FENCE_PATTERN.match(line):
        in_code_fence = not in_code_fence
    if in_code_fence:
        continue
    # ... existing checks ...
```

**Note:** The simple toggle does not handle nested/mismatched fences, but this matches CommonMark behavior for typical documents.

#### Phase 2: MDPP009 Detection

A helper function + second pass after the main loop:

```python
# validate-mdpp.py

# Regex matching any non-exempt MDPP comment tag
MDPP_TAG_PATTERN = re.compile(
    r'<!--\s*(?:style:|#[a-zA-Z0-9_-]+|markers?:|multiline)'
)

def _is_mdpp_tag_line(line: str) -> bool:
    """True if line's only non-whitespace content is an MDPP comment tag."""
    stripped = line.strip()
    if not stripped.startswith('<!--'):
        return False
    return bool(MDPP_TAG_PATTERN.match(stripped))

def _has_non_exempt_command(line: str) -> bool:
    """True if the comment tag contains style, alias, marker, or multiline."""
    return bool(MDPP_TAG_PATTERN.search(line))

def _is_content_line(line: str) -> bool:
    """True if line is a non-blank, non-MDPP-tag content element."""
    stripped = line.strip()
    if not stripped:
        return False
    # Any non-blank line that is not an MDPP comment tag counts as content
    if stripped.startswith('<!--') and MDPP_TAG_PATTERN.match(stripped):
        return False
    return True
```

The second pass iterates lines (respecting code fence state), identifies non-exempt MDPP tag lines, and checks whether the immediately next line is a content element:

```python
# After the existing main loop, before the unclosed-conditions check
in_code_fence = False
for line_num, line in enumerate(lines, start=1):
    if CODE_FENCE_PATTERN.match(line):
        in_code_fence = not in_code_fence
    if in_code_fence:
        continue
    if not _is_mdpp_tag_line(line):
        continue
    if not _has_non_exempt_command(line):
        continue

    # Check if the very next line is a content element (no blank line, no other tag)
    next_line_idx = line_num  # 0-based index of next line (line_num is 1-based current)
    if next_line_idx >= len(lines) or not _is_content_line(lines[next_line_idx]):
        issues.append(ValidationIssue(
            type=Severity.WARNING.value,
            code="MDPP009",
            message="Orphaned comment tag (not attached to element)",
            file=filepath,
            line=line_num,
            context=line.strip()[:60],
            suggestion="Remove the blank line between this tag and the element it applies to, or combine with an adjacent tag using semicolons"
        ))
```

**Key behavior:** The next line must be a content element — not a blank line, not another MDPP tag, not EOF. If authors need multiple commands on one element, they should use the combined syntax (`<!-- style:X ; #alias ; marker:Y="Z" -->`).

#### Phase 3: Test File

Create `tests/sample-orphaned-tags.md` with sections covering:

**Should trigger MDPP009 (positive cases):**
1. Style tag with blank line before content
2. Alias tag with blank lines on both sides
3. Marker tag between heading and paragraph (blank line above content)
4. Combined tag (`style + alias + marker`) orphaned by blank line
5. Tag at end of file with no following content
6. Tag followed by only blank lines to EOF
7. Multiple orphaned tags in sequence (each should warn independently)
8. Separate tags on consecutive lines above content (top tag is orphaned — should use combined syntax)

**Should NOT trigger MDPP009 (negative cases):**
9. Style tag directly above heading (valid attachment)
10. Alias tag directly above paragraph (valid attachment)
11. Marker at file start directly above Title paragraph
12. Combined tag (`style + alias + marker`) directly above element (single tag, valid)
13. Condition open/close tags (exempt — wraps content)
14. Include directive (exempt — standalone)
15. Inline style tag on same line as content
16. `<!-- multiline -->` directly above table header row
17. Combined tag with condition + style above content (has non-exempt, is attached)
18. Tag inside a fenced code block (ignored entirely)
19. Regular HTML comment (not an MDPP pattern — ignored)

### Performance Implications

- The second pass adds O(n) line iteration. For typical MDPP documents (<500 lines), this is negligible.
- No new external dependencies; stays stdlib-only.

### Security Considerations

None — this is a read-only validation check on local files.

## Acceptance Criteria

- [x] `validate-mdpp.py` implements code fence tracking (`in_code_fence` flag) shared by all checks
- [x] `validate-mdpp.py` implements MDPP009 detection — next line must be a content element (no lookahead through consecutive tags)
- [x] Inline tags (not sole content on their line) are skipped for orphan checking
- [x] Exempt types (conditions, includes) do not trigger MDPP009
- [x] Combined tags with any non-exempt command are checked
- [x] `tests/sample-orphaned-tags.md` covers all 19 test scenarios listed above
- [x] Running validator against `sample-basic.md` produces 0 MDPP009 warnings
- [x] Running validator against `sample-full.md` produces 0 MDPP009 warnings
- [x] Running validator against `sample-orphaned-tags.md` produces warnings for exactly the positive cases (scenarios 1-8)
- [x] `--json` output includes MDPP009 warnings in the `warnings` array
- [x] `--strict` mode promotes MDPP009 warnings to errors

## Dependencies & Risks

- **Uncommitted documentation changes**: The prior session left attachment rule documentation as uncommitted changes in SKILL.md, syntax-reference.md, and best-practices.md. These should be committed together with the script changes in one PR.
- **Code fence tracking scope creep**: Adding `in_code_fence` changes behavior for existing checks (MDPP001-008) by suppressing false positives inside code fences. This is a bug fix, not a behavior change, but warrants running existing test files to confirm no regressions.
- **Consecutive separate tags**: Authors may have existing documents with separate tags on consecutive lines (e.g., a style tag then an alias tag). Under this validation, the top tag will be flagged as orphaned with a suggestion to combine using semicolons. This is intentional — combined syntax is the standard.

## Success Metrics

- Validator catches all orphaned tags in the test file with zero false positives
- Existing test files (`sample-basic.md`, `sample-full.md`, `sample-duplicate-aliases.md`) produce identical results before and after the change (except suppression of any false positives that were inside code fences)

## Sources & References

- Prior session plan: `plugins/webworks-claude-skills/plans/mdpp-attachment-rules-validation.md`
- Validation script: `plugins/webworks-claude-skills/skills/markdown-plus-plus/scripts/validate-mdpp.py`
- Attachment rules table: `plugins/webworks-claude-skills/skills/markdown-plus-plus/references/syntax-reference.md:15-23`
- MDPP009 validation code: `plugins/webworks-claude-skills/skills/markdown-plus-plus/references/syntax-reference.md:720`
- Common Mistake #7: `plugins/webworks-claude-skills/skills/markdown-plus-plus/references/best-practices.md:417-438`
- Test files: `plugins/webworks-claude-skills/skills/markdown-plus-plus/tests/sample-*.md`
