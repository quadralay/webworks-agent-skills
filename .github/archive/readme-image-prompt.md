# README Image Generation Prompt

Use this prompt with Gemini (Nano Banana Pro) to generate the hero image for the README.

**Value proposition to convey:** Claude Code with these skills can audit Markdown++ documents, identify syntax issues (indentation, list structure, style comments), automatically fix them, publish with AutoMap, and verify fixes via HTML diff comparison—turning hours of manual work into minutes.

---

## Prompt

```
<work_surface>
A polished UI mockup showing an AI coding assistant terminal performing documentation quality assurance. The terminal shows an iterative fix-and-verify workflow: analyzing Markdown++ syntax, applying automated fixes, publishing with ePublisher AutoMap, and comparing HTML output via diff. Style: modern tech product screenshot suitable for a GitHub README hero image.
</work_surface>

<layout>
Wide aspect ratio (16:9). Dark themed interface.
Left side (60%): Windows Terminal window with conversation.
Right side (40%): Preview panel showing documentation output.
Subtle gradient background behind the windows.
</layout>

<components>
Terminal window:
- Windows 11 style window chrome with rounded corners
- Minimize/maximize/close buttons on the right (─ □ ✕)
- Tab bar showing "Claude Code" with PowerShell-style icon
- Dark charcoal background (#0c0c0c)
- User input line: "Fix the Markdown++ syntax issues and verify"
- AI response block showing:
  - "Invoking markdown-plus-plus skill..."
  - "Found 396 issues: substeps, indentation, styles"
  - "Fixing letter lists → numbered (a→1, b→2)..."
  - "Publishing baseline with AutoMap..."
  - "Running HTML diff comparison..."
  - Green checkmark with "Verified: 243 elements fixed"

Preview panel:
- Split view showing diff comparison
- Left: "baseline" label with red highlighted lines
- Right: "modified" label with green highlighted lines
- Code showing class="ProcedureSubStep1_Item" change
- Professional documentation styling visible behind

Visual accents:
- Purple glow or highlight on AI response area
- Green accent on success states
- Soft drop shadows on windows
</components>

<constraints>
- No real logos or trademarked brand imagery
- Text must be legible but can be slightly stylized
- Professional, minimal aesthetic—no clutter
- Colors: dark grays (#1a1a2e), purples (#7c3aed), greens (#22c55e)
- Windows Terminal uses #0c0c0c background with #cccccc text
- Suitable for light and dark GitHub themes
</constraints>
```

---

## Output

- **File:** `images/readme-main.png`
- **Recommended:** Compress with TinyPNG or Squoosh before committing

## Reference

Prompt structure based on: https://www.radicalcuriosity.xyz/p/how-to-create-an-effective-prompt
