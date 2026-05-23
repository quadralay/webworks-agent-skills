# WebWorks Agent Skills

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Claude Code](https://img.shields.io/badge/Claude-Code-purple)](https://claude.ai/code)

AI agent skills for WebWorks ePublisher and Markdown++ authoring.

![Claude Code publishing an ePublisher project](images/readme-main.png)

## Install

In Claude Code:

```
/plugin marketplace add quadralay/webworks-agent-skills
/plugin install webworks-agent-skills@webworks-agent-skills
```

> **Migrating from `webworks-claude-skills`?** This repo was renamed in 3.0.0. Uninstall the old plugin (`/plugin uninstall webworks-claude-skills`) before installing the new one. Any skill invocations or permission entries in your `.claude/settings.local.json` referencing `webworks-claude-skills:*` must be updated to `webworks-agent-skills:*`.

All skills activate automatically based on your project context.

## Skills

| Skill | What It Does |
|-------|--------------|
| **epublisher** | ePublisher project knowledge, file resolver hierarchy, customization patterns |
| **markdown-integration** | ePublisher integration patterns for Markdown++ sources (variable resolution, style mapping to Stationery, per-target conditions) |
| **automap** | Automated publishing with AutoMap CLI |
| **reverb** | Reverb 2.0 output testing, CSH analysis, SCSS theming |
| **humanizer** | Remove signs of AI-generated writing from text (vendored from [blader/humanizer](https://github.com/blader/humanizer); see [UPSTREAM.md](plugins/humanizer/skills/humanizer/UPSTREAM.md) for divergence notes) |

For Markdown++ **format syntax**, validation, and authoring best practices, install the companion plugin [`quadralay/markdown-plus-plus`](https://github.com/quadralay/markdown-plus-plus). The `markdown-integration` skill in this plugin defers to it for format-level concerns and focuses on the ePublisher integration layer.

## Example Workflows

**Publishing:**
```
You: "Publish the project with all targets"
Claude: Detects AutoMap, runs publish, reports results
```

**Testing:**
```
You: "Test the Reverb output for JavaScript errors"
Claude: Launches browser, checks console, reports issues
```

**Markdown++ integration:**
```
You: "Why does $product_name; render as literal text in the PDF target?"
Claude: Walks the variable resolution hierarchy (Stationery → project → target → job file)
        and identifies which level is missing the value
```

**Theming:**
```
You: "Change the primary color to #2563eb"
Claude: Guides you through SCSS variable overrides with proper cascade mappings
```

## Requirements

| Skill | Platform | Requirements |
|-------|----------|--------------|
| epublisher | Windows | ePublisher 2024.1+ |
| markdown-integration | Windows | ePublisher 2024.1+ (paired with `quadralay/markdown-plus-plus` for format syntax) |
| automap | Windows | ePublisher + AutoMap |
| reverb | Windows | ePublisher + browser |
| humanizer | Any | Claude Code or Claude Desktop |

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE).

---

🛠️ Built for [WebWorks ePublisher](https://www.webworks.com) | 🤖 Powered by [Claude Code](https://claude.ai/code)
