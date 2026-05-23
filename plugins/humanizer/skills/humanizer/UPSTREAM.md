# Upstream

This skill is a vendored copy of [`blader/humanizer`](https://github.com/blader/humanizer). It was previously wired as a Git submodule and is now an in-tree copy maintained as a first-party plugin of `webworks-agent-skills`.

## Sync metadata

- **Source**: `https://github.com/blader/humanizer`
- **Last sync commit**: `12881abf6671c4ab62eceeb56f911b752f9fd6d2`
- **Vendored on**: 2026-05-22
- **License**: MIT (see `LICENSE`, preserved unchanged from upstream)
- **Attribution**: Wikipedia "Signs of AI writing" citation and WikiProject AI Cleanup credit preserved in `SKILL.md`

## Reason for divergence

The upstream skill targets general-purpose human-audience humanization. We need behavior tailored to skill files and other agent-readable content, where rules that target promotional language and anthropomorphization are usually helpful but rules that target length, active/passive shape, and rhythm variation actively damage precision and specification-grade wording.

Planned divergence:

- Skill-file auto-detection so the skill applies a different rule set when the input is itself a skill file or other agent-readable content.
- Dual-audience rule profiles so each rule can be opted in or out per audience (human-facing prose vs. agent-readable reference).

Both pieces are out of scope for the upstream repo and specific to the WebWorks plugin ecosystem.

## Process for future manual ports

We do not track upstream automatically. When a notable upstream change appears (a new AI pattern from WikiProject AI Cleanup, a meaningful rewrite of an existing rule), pull it in by hand:

1. Compare `git log <last-sync-sha>..HEAD` on the upstream repo against this directory.
2. For each candidate change, evaluate it against the WebWorks profile criteria. Rules that target vagueness, filler, promotional language, or anthropomorphization usually port cleanly. Rules that target sentence length, parallelism, or rhythm need an audience-profile decision before they port.
3. Apply ported changes here as a normal PR. Update **Last sync commit** above to the new upstream SHA. Note any rules that were deliberately not ported and why.
4. If upstream renames or restructures the skill, prefer keeping local file layout stable and reconcile content rule-by-rule rather than mirroring the rename.
