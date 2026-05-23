# Humanizer (vendored)

This plugin packages the [`blader/humanizer`](https://github.com/blader/humanizer) skill as a first-party plugin in `webworks-agent-skills`.

The skill itself lives at `skills/humanizer/`. Its `LICENSE`, `README.md`, and `SKILL.md` are vendored unchanged from upstream. Sync metadata, the rationale for vendoring, and the manual port process are recorded in [`skills/humanizer/UPSTREAM.md`](skills/humanizer/UPSTREAM.md).

## Why this is vendored, not a submodule

The upstream skill targets general-purpose, human-audience humanization. We need the same skill to behave differently when the input is itself a skill file or other agent-readable content. Owning the copy in-tree lets that divergence land as normal PRs against this repo, keeps the plugin lifecycle simple for contributors (no submodule init), and forces deliberate manual ports of upstream changes rather than accidental sync regressions.

The trade-off: upstream improvements have to be pulled in by hand. The `UPSTREAM.md` file tracks the last sync commit and the port process.

## What is planned to diverge

- **Skill-file auto-detection.** When the input is a skill file or other agent-readable reference, apply a different rule set automatically.
- **Dual-audience rule profiles.** Each rule will be tagged as helpful, neutral, or harmful for the agent-readable audience, and the skill will select a profile based on the detected audience.

Neither change is in scope for the upstream repo. They are tracked in follow-up issues.

## License and attribution

Upstream is MIT-licensed. The `LICENSE` file at `skills/humanizer/LICENSE` is preserved unchanged. The Wikipedia "Signs of AI writing" citation and WikiProject AI Cleanup credit are preserved in `skills/humanizer/SKILL.md`.
