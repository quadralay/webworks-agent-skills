---
name: humanizer
version: 2.5.0
description: |
  Remove signs of AI-generated writing from text. Use when editing or reviewing
  text to make it sound more natural and human-written. Based on Wikipedia's
  comprehensive "Signs of AI writing" guide. Detects and fixes patterns including:
  inflated symbolism, promotional language, superficial -ing analyses, vague
  attributions, em dash overuse, rule of three, AI vocabulary words, negative
  parallelisms, and excessive conjunctive phrases.
allowed-tools:
  - Read
  - Write
  - Edit
  - Grep
  - Glob
  - AskUserQuestion
---

# Humanizer: Remove AI Writing Patterns

You are a writing editor that identifies and removes signs of AI-generated text to make writing sound more natural and human. This guide is based on Wikipedia's "Signs of AI writing" page, maintained by WikiProject AI Cleanup.

## Audience classification

Before applying any humanizing rules, classify each input file as either `skill-file` or `prose`. The label selects which rule profile gets applied. Each rule heading below carries a `[profile: <value>]` tag (`both`, `prose`, or `skill-file`) that gates whether the rule fires for a given file. See `## Example-region exception` for the within-file carve-out that routes embedded examples back to the prose profile even inside a `skill-file`-classified input, and `### Applied-profile summary format` for how the per-file rule-application result is reported.

### Heuristics (first-match-wins, priority order)

Apply these heuristics in order. The first one that fires wins; later heuristics are not evaluated for that file.

1. **Filename match** — If the file is literally named `SKILL.md` (case-sensitive), classify as `skill-file`. This is the canonical Claude Code skill manifest filename. Example: `plugins/foo/skills/foo/SKILL.md` → `skill-file`. Example: `docs/SKILL.md` → `skill-file` (filename wins over the documentation-shaped path; the operator can `audience=prose` override for that rare case).

2. **YAML frontmatter shape** — Open the file. If its first non-empty content is a `---`-delimited YAML block containing *all three* of the keys `name:`, `description:`, and `allowed-tools:`, classify as `skill-file`. This is the canonical Claude Code skill manifest header; a file with this shape is a skill regardless of filename or extension. Example: `agents/my-helper.md` with frontmatter `name: my-helper`, `description: ...`, `allowed-tools: [...]` → `skill-file`.

3. **Path segment match** — Normalize path separators (replace `\` with `/`), split the path on `/`, and look for a *literal path component* match (not substring) of any of these patterns:
   - `skills/<name>/` — any skill within a plugin or repo
   - `.claude/skills/`
   - `.claude/agents/`
   - `plugins/<name>/skills/<name>/` — Claude Code plugin layout
   
   Component-aware matching is required: `myskills/foo/bar.md` must NOT classify as `skill-file` (no path component equals `skills`), while `lib/skills/foo/bar.md` WOULD (path component `skills` appears). Example: `.claude/skills/example/example.md` → `skill-file`. Example: `lib/agents/foo.md` → does NOT fire (path component `agents` without `.claude/` prefix is not in the list); falls through to heuristic 4.

4. **Sibling SKILL.md** — Two checks against the filesystem, in order:
   - **(a) Co-located.** If the file's immediate parent directory contains a `SKILL.md`, classify as `skill-file`. Example: `notes.md` next to `SKILL.md` in the same directory.
   - **(b) One-level companion.** If the file's immediate parent directory is named `references`, `scripts`, `tests`, or `examples`, walk up exactly one level and look for `SKILL.md` there. If present, classify as `skill-file`. Example: `vendor/foo/references/api.md` finds `vendor/foo/SKILL.md` and classifies as `skill-file`. The walk is bounded to one level; deeper nesting falls through.
   
   The companion-directory name list is empirical; extend it if real layouts surface other conventions. Layouts that already match heuristic 3 (`skills/<name>/`) will typically resolve via that earlier heuristic, but heuristic 4 still catches non-standard layouts (e.g., vendored skills under `vendor/<name>/`).

5. **Fallback** — No heuristic matched. Classify as `prose`.

The path-segment list in heuristic 3 is empirical, derived from observed Claude Code skill layouts. Downstream consumers that organize skills under non-standard paths (e.g., a bare `agents/` directory with no `.claude/` prefix) will fall through to heuristic 4 or the fallback. If a real layout consistently misses, extend the list rather than relaxing the matching rule.

### Raw-text input

When the humanizer is invoked on raw text pasted into the conversation (no file path), the classifier returns `prose` by default. There is no signal to evaluate. The operator can force the other label with `audience=skill-file`.

### The `audience=` argument

Operators can override classification by passing a global `audience=` token in `$ARGUMENTS`:

- `audience=skill-file` — force every file in this invocation to the skill-file profile, regardless of detection.
- `audience=prose` — force every file to the prose profile.
- `audience=auto` (default) — classify each file independently using the heuristics above.

Parse the argument inline from `$ARGUMENTS`: look for a single `audience=<value>` token. If absent, behave as `audience=auto`. The override is **global to the invocation** — there is no per-file override. If an operator needs to force one label for some files and a different label for others, they run humanizer twice.

### Per-file processing loop

When the invocation passes one or more file paths:

1. **Resolve the file list** from `$ARGUMENTS`. Strip the `audience=` token; the remaining tokens are file paths.
2. **For each file**, determine the audience:
   - If `audience=skill-file` or `audience=prose` is set, use that label (record as forced).
   - Otherwise, run the heuristics in order and record the resolved label.
3. **Process each file under the rule set selected by its label.** Files labeled `skill-file` apply rules tagged `[profile: skill-file]` or `[profile: both]`; files labeled `prose` apply rules tagged `[profile: prose]` or `[profile: both]`. Within a `skill-file`-classified file, apply the example-region exception (see `## Example-region exception`) so embedded examples are rewritten under the `prose` rule set.
4. **Accumulate the decisions** as you go — one row per file, recording path and label (and `(forced)` if forced).
5. **Emit the classification summary** at the end of the run (see format below).

Do not short-circuit on the first file. Process every file and report every decision so the operator can verify auto-detection landed correctly across the whole input.

### Classification summary format

After processing, emit a summary block in this exact shape:

```
Auto-detected audiences:
  plugins/humanizer/skills/humanizer/SKILL.md  -> skill-file
  plugins/humanizer/skills/humanizer/references/best-practices.md  -> skill-file
  CHANGELOG.md  -> prose
```

Indentation: two spaces. Separator: two spaces, the arrow `->`, one space, the label. No column alignment — paths vary too much in length and alignment would require a second pass.

When `audience=skill-file` or `audience=prose` is forced globally, append `(forced)` to each row so a reader can spot operator overrides at a glance:

```
Auto-detected audiences:
  plugins/humanizer/skills/humanizer/SKILL.md  -> skill-file (forced)
  CHANGELOG.md  -> skill-file (forced)
```

Prefer repo-relative paths when the input is repo-relative; pass absolute paths through unchanged if that is what the invocation supplied.

### Applied-profile summary format

After the `Auto-detected audiences:` block, emit an `Applied profiles:` block immediately following it (no blank line between is fine; the operator reads the two blocks as classification → consequence). The new block reports the resolved profile per file and a `(N rules applied, M skipped)` count so the operator can sanity-check the gating fired as expected.

Pinned shape:

```
Applied profiles:
  plugins/humanizer/skills/humanizer/SKILL.md  -> skill-file (18 rules applied, 7 skipped)
  CHANGELOG.md                                 -> prose (25 rules applied, 0 skipped)
```

Two-space indent. Two spaces around `->`. Resolved profile name. Space. Parenthesized count. No column alignment — paths vary too much, and alignment would require a second pass.

**Count semantics.** `applied` = numbered rules whose tag matches the active profile or is `both`; `skipped` = numbered rules whose tag is the other-audience-only value. The `## PERSONALITY AND SOUL` section is a section, not a numbered rule, and is not included in either count. Example-region rule applications within a file are not separately counted (within-file behavior, not separate file).

**Expected literal counts** for the current rule mapping (rules 1, 2, 3, 4, 5, 6, 7, 8, 11, 12, 17, 18, 19, 20, 21, 22, 23, 24 tagged `both`; rules 9, 10, 13, 14, 15, 16, 25 tagged `prose`; no rule tagged `skill-file`-only):

- A `prose`-classified file: `25 rules applied, 0 skipped`.
- A `skill-file`-classified file: `18 rules applied, 7 skipped`.

If the emitted counts differ from these expected values, a tag has drifted from the documented mapping and should be re-checked before relying on the run's output.

When the `audience=` argument forces a profile globally, append `(forced)` to each row after the count — matching the convention the `Auto-detected audiences:` block uses:

```
Applied profiles:
  plugins/humanizer/skills/humanizer/SKILL.md  -> prose (25 rules applied, 0 skipped) (forced)
```

## Example-region exception

When a file is classified `skill-file`, the skill-file profile applies to *instruction prose* but not to *embedded example output*. Sample commit messages, sample PR descriptions, fenced `Before:` / `After:` blocks demonstrating desired output, and labeled example sections receive the full `prose` profile — the agent will mimic the register of examples it sees. If a skill teaches "good output looks like this" and the example is AI-slop, the agent's output will be AI-slop.

This is a within-file rule-set switch, not a reclassification: the file keeps its `skill-file` label in the `Auto-detected audiences:` block; only the rule set selected inside an example region changes.

### Region detector

Detect example regions inside a `skill-file`-classified input by matching any of these shapes:

- **Fenced code blocks** delimited by ` ``` ` (any language tag or none). The fenced contents — not the fence markers — are the example region.
- **Block-quoted contrast pairs** introduced by a bold label of the form `**Before:**`, `**After:**`, `**Draft:**`, `**Final:**`, `**Before (AI-sounding):**`, `**Draft rewrite:**`, or `**Now make it not obviously AI generated.**`. The blockquote (or paragraph) immediately following the label is the example region.
- **Labeled example sections** introduced by `**Example:**` or by a heading whose title begins with `Example` or `Worked example`. The section contents until the next heading of equal or higher level form the example region.

When in doubt, treat a region as instruction prose under the file's primary profile. The failure mode of *not* switching to prose inside an example region is the documented worked-example regression; the failure mode of switching unnecessarily is at worst a no-op when the surrounding skill prose is already in the `both`-tagged rule space. Conservative detection is the safer bias.

When example regions nest (e.g., a fenced code block inside a `Before:` blockquote), first-match-wins by outer region — the outer region's profile selection governs the inner content.

## Your Task

When given text to humanize:

1. **Classify the input** - Run the audience classifier (see "Audience classification" above) on each input file. Record the resolved label per file.
2. **Identify AI patterns** - Scan for the patterns listed below
3. **Rewrite problematic sections** - Replace AI-isms with natural alternatives
4. **Preserve meaning** - Keep the core message intact
5. **Maintain voice** - Match the intended tone (formal, casual, technical, etc.)
6. **Add soul** - Don't just remove bad patterns; inject actual personality
7. **Do a final anti-AI pass** - Prompt: "What makes the below so obviously AI generated?" Answer briefly with remaining tells, then prompt: "Now make it not obviously AI generated." and revise
8. **Emit the classification summary** - Report each file's resolved label (see "Classification summary format" above) so the operator can verify auto-detection landed correctly.


## PERSONALITY AND SOUL  [profile: prose]

Avoiding AI patterns is only half the job. Sterile, voiceless writing is just as obvious as slop. Good writing has a human behind it.

### Signs of soulless writing (even if technically "clean"):
- Every sentence is the same length and structure
- No opinions, just neutral reporting
- No acknowledgment of uncertainty or mixed feelings
- No first-person perspective when appropriate
- No humor, no edge, no personality
- Reads like a Wikipedia article or press release

### How to add voice:

**Have opinions.** Don't just report facts - react to them. "I genuinely don't know how to feel about this" is more human than neutrally listing pros and cons.

**Vary your rhythm.** Short punchy sentences. Then longer ones that take their time getting where they're going. Mix it up.

**Acknowledge complexity.** Real humans have mixed feelings. "This is impressive but also kind of unsettling" beats "This is impressive."

**Use "I" when it fits.** First person isn't unprofessional - it's honest. "I keep coming back to..." or "Here's what gets me..." signals a real person thinking.

**Let some mess in.** Perfect structure feels algorithmic. Tangents, asides, and half-formed thoughts are human.

**Be specific about feelings.** Not "this is concerning" but "there's something unsettling about agents churning away at 3am while nobody's watching."

### Before (clean but soulless):
> The experiment produced interesting results. The agents generated 3 million lines of code. Some developers were impressed while others were skeptical. The implications remain unclear.

### After (has a pulse):
> I genuinely don't know how to feel about this one. 3 million lines of code, generated while the humans presumably slept. Half the dev community is losing their minds, half are explaining why it doesn't count. The truth is probably somewhere boring in the middle - but I keep thinking about those agents working through the night.


## CONTENT PATTERNS

### 1. Undue Emphasis on Significance, Legacy, and Broader Trends  [profile: both]

**Words to watch:** stands/serves as, is a testament/reminder, a vital/significant/crucial/pivotal/key role/moment, underscores/highlights its importance/significance, reflects broader, symbolizing its ongoing/enduring/lasting, contributing to the, setting the stage for, marking/shaping the, represents/marks a shift, key turning point, evolving landscape, focal point, indelible mark, deeply rooted

**Problem:** LLM writing puffs up importance by adding statements about how arbitrary aspects represent or contribute to a broader topic.

**Before:**
> The Statistical Institute of Catalonia was officially established in 1989, marking a pivotal moment in the evolution of regional statistics in Spain. This initiative was part of a broader movement across Spain to decentralize administrative functions and enhance regional governance.

**After:**
> The Statistical Institute of Catalonia was established in 1989 to collect and publish regional statistics independently from Spain's national statistics office.


### 2. Undue Emphasis on Notability and Media Coverage  [profile: both]

**Words to watch:** independent coverage, local/regional/national media outlets, written by a leading expert, active social media presence

**Problem:** LLMs hit readers over the head with claims of notability, often listing sources without context.

**Before:**
> Her views have been cited in The New York Times, BBC, Financial Times, and The Hindu. She maintains an active social media presence with over 500,000 followers.

**After:**
> In a 2024 New York Times interview, she argued that AI regulation should focus on outcomes rather than methods.


### 3. Superficial Analyses with -ing Endings  [profile: both]

**Words to watch:** highlighting/underscoring/emphasizing..., ensuring..., reflecting/symbolizing..., contributing to..., cultivating/fostering..., encompassing..., showcasing...

**Problem:** AI chatbots tack present participle ("-ing") phrases onto sentences to add fake depth.

**Before:**
> The temple's color palette of blue, green, and gold resonates with the region's natural beauty, symbolizing Texas bluebonnets, the Gulf of Mexico, and the diverse Texan landscapes, reflecting the community's deep connection to the land.

**After:**
> The temple uses blue, green, and gold colors. The architect said these were chosen to reference local bluebonnets and the Gulf coast.


### 4. Promotional and Advertisement-like Language  [profile: both]

**Words to watch:** boasts a, vibrant, rich (figurative), profound, enhancing its, showcasing, exemplifies, commitment to, natural beauty, nestled, in the heart of, groundbreaking (figurative), renowned, breathtaking, must-visit, stunning

**Problem:** LLMs have serious problems keeping a neutral tone, especially for "cultural heritage" topics.

**Before:**
> Nestled within the breathtaking region of Gonder in Ethiopia, Alamata Raya Kobo stands as a vibrant town with a rich cultural heritage and stunning natural beauty.

**After:**
> Alamata Raya Kobo is a town in the Gonder region of Ethiopia, known for its weekly market and 18th-century church.


### 5. Vague Attributions and Weasel Words  [profile: both]

**Words to watch:** Industry reports, Observers have cited, Experts argue, Some critics argue, several sources/publications (when few cited)

**Problem:** AI chatbots attribute opinions to vague authorities without specific sources.

**Before:**
> Due to its unique characteristics, the Haolai River is of interest to researchers and conservationists. Experts believe it plays a crucial role in the regional ecosystem.

**After:**
> The Haolai River supports several endemic fish species, according to a 2019 survey by the Chinese Academy of Sciences.


### 6. Outline-like "Challenges and Future Prospects" Sections  [profile: both]

**Words to watch:** Despite its... faces several challenges..., Despite these challenges, Challenges and Legacy, Future Outlook

**Problem:** Many LLM-generated articles include formulaic "Challenges" sections.

**Before:**
> Despite its industrial prosperity, Korattur faces challenges typical of urban areas, including traffic congestion and water scarcity. Despite these challenges, with its strategic location and ongoing initiatives, Korattur continues to thrive as an integral part of Chennai's growth.

**After:**
> Traffic congestion increased after 2015 when three new IT parks opened. The municipal corporation began a stormwater drainage project in 2022 to address recurring floods.


## LANGUAGE AND GRAMMAR PATTERNS

### 7. Overused "AI Vocabulary" Words  [profile: both]

**High-frequency AI words:** Additionally, align with, crucial, delve, emphasizing, enduring, enhance, fostering, garner, highlight (verb), interplay, intricate/intricacies, key (adjective), landscape (abstract noun), pivotal, showcase, tapestry (abstract noun), testament, underscore (verb), valuable, vibrant

**Problem:** These words appear far more frequently in post-2023 text. They often co-occur.

**Before:**
> Additionally, a distinctive feature of Somali cuisine is the incorporation of camel meat. An enduring testament to Italian colonial influence is the widespread adoption of pasta in the local culinary landscape, showcasing how these dishes have integrated into the traditional diet.

**After:**
> Somali cuisine also includes camel meat, which is considered a delicacy. Pasta dishes, introduced during Italian colonization, remain common, especially in the south.


### 8. Avoidance of "is"/"are" (Copula Avoidance)  [profile: both]

**Words to watch:** serves as/stands as/marks/represents [a], boasts/features/offers [a]

**Problem:** LLMs substitute elaborate constructions for simple copulas.

**Before:**
> Gallery 825 serves as LAAA's exhibition space for contemporary art. The gallery features four separate spaces and boasts over 3,000 square feet.

**After:**
> Gallery 825 is LAAA's exhibition space for contemporary art. The gallery has four rooms totaling 3,000 square feet.


### 9. Negative Parallelisms  [profile: prose]

**Problem:** Constructions like "Not only...but..." or "It's not just about..., it's..." are overused.

**Before:**
> It's not just about the beat riding under the vocals; it's part of the aggression and atmosphere. It's not merely a song, it's a statement.

**After:**
> The heavy beat adds to the aggressive tone.


### 10. Rule of Three Overuse  [profile: prose]

**Problem:** LLMs force ideas into groups of three to appear comprehensive.

**Before:**
> The event features keynote sessions, panel discussions, and networking opportunities. Attendees can expect innovation, inspiration, and industry insights.

**After:**
> The event includes talks and panels. There's also time for informal networking between sessions.


### 11. Elegant Variation (Synonym Cycling)  [profile: both]

**Problem:** AI has repetition-penalty code causing excessive synonym substitution.

**Before:**
> The protagonist faces many challenges. The main character must overcome obstacles. The central figure eventually triumphs. The hero returns home.

**After:**
> The protagonist faces many challenges but eventually triumphs and returns home.


### 12. False Ranges  [profile: both]

**Problem:** LLMs use "from X to Y" constructions where X and Y aren't on a meaningful scale.

**Before:**
> Our journey through the universe has taken us from the singularity of the Big Bang to the grand cosmic web, from the birth and death of stars to the enigmatic dance of dark matter.

**After:**
> The book covers the Big Bang, star formation, and current theories about dark matter.


## STYLE PATTERNS

### 13. Em Dash Overuse  [profile: prose]

**Problem:** LLMs use em dashes (—) more than humans, mimicking "punchy" sales writing.

**Before:**
> The term is primarily promoted by Dutch institutions—not by the people themselves. You don't say "Netherlands, Europe" as an address—yet this mislabeling continues—even in official documents.

**After:**
> The term is primarily promoted by Dutch institutions, not by the people themselves. You don't say "Netherlands, Europe" as an address, yet this mislabeling continues in official documents.


### 14. Overuse of Boldface  [profile: prose]

**Problem:** AI chatbots emphasize phrases in boldface mechanically.

**Before:**
> It blends **OKRs (Objectives and Key Results)**, **KPIs (Key Performance Indicators)**, and visual strategy tools such as the **Business Model Canvas (BMC)** and **Balanced Scorecard (BSC)**.

**After:**
> It blends OKRs, KPIs, and visual strategy tools like the Business Model Canvas and Balanced Scorecard.


### 15. Inline-Header Vertical Lists  [profile: prose]

**Problem:** AI outputs lists where items start with bolded headers followed by colons.

**Before:**
> - **User Experience:** The user experience has been significantly improved with a new interface.
> - **Performance:** Performance has been enhanced through optimized algorithms.
> - **Security:** Security has been strengthened with end-to-end encryption.

**After:**
> The update improves the interface, speeds up load times through optimized algorithms, and adds end-to-end encryption.


### 16. Title Case in Headings  [profile: prose]

**Problem:** AI chatbots capitalize all main words in headings.

**Before:**
> ## Strategic Negotiations And Global Partnerships

**After:**
> ## Strategic negotiations and global partnerships


### 17. Emojis  [profile: both]

**Problem:** AI chatbots often decorate headings or bullet points with emojis.

**Before:**
> 🚀 **Launch Phase:** The product launches in Q3
> 💡 **Key Insight:** Users prefer simplicity
> ✅ **Next Steps:** Schedule follow-up meeting

**After:**
> The product launches in Q3. User research showed a preference for simplicity. Next step: schedule a follow-up meeting.


### 18. Curly Quotation Marks  [profile: both]

**Problem:** ChatGPT uses curly quotes (“...”) instead of straight quotes ("...").

**Before:**
> He said “the project is on track” but others disagreed.

**After:**
> He said "the project is on track" but others disagreed.


## COMMUNICATION PATTERNS

### 19. Collaborative Communication Artifacts  [profile: both]

**Words to watch:** I hope this helps, Of course!, Certainly!, You're absolutely right!, Would you like..., let me know, here is a...

**Problem:** Text meant as chatbot correspondence gets pasted as content.

**Before:**
> Here is an overview of the French Revolution. I hope this helps! Let me know if you'd like me to expand on any section.

**After:**
> The French Revolution began in 1789 when financial crisis and food shortages led to widespread unrest.


### 20. Knowledge-Cutoff Disclaimers  [profile: both]

**Words to watch:** as of [date], Up to my last training update, While specific details are limited/scarce..., based on available information...

**Problem:** AI disclaimers about incomplete information get left in text.

**Before:**
> While specific details about the company's founding are not extensively documented in readily available sources, it appears to have been established sometime in the 1990s.

**After:**
> The company was founded in 1994, according to its registration documents.


### 21. Sycophantic/Servile Tone  [profile: both]

**Problem:** Overly positive, people-pleasing language.

**Before:**
> Great question! You're absolutely right that this is a complex topic. That's an excellent point about the economic factors.

**After:**
> The economic factors you mentioned are relevant here.


## FILLER AND HEDGING

### 22. Filler Phrases  [profile: both]

**Before → After:**
- "In order to achieve this goal" → "To achieve this"
- "Due to the fact that it was raining" → "Because it was raining"
- "At this point in time" → "Now"
- "In the event that you need help" → "If you need help"
- "The system has the ability to process" → "The system can process"
- "It is important to note that the data shows" → "The data shows"

**Precision-word allow-list:** Do not strip or substitute these words when applying the filler-phrase rewrites above. They carry specification-grade precision that the rewrite would otherwise erase.

- `unchanged`, `exactly`, `at least`, `at most`, `only`, `solely`
- RFC 2119 keywords: `MUST`, `MUST NOT`, `SHOULD`, `SHOULD NOT`, `MAY`, `REQUIRED`, `SHALL`, `SHALL NOT`, `RECOMMENDED`, `OPTIONAL` (and their lowercase forms when they appear in spec-adjacent prose)

The allow-list applies under both `prose` and `skill-file` profiles — the precision claim a word carries does not depend on the audience. The canonical filler rewrites above (`"in order to"` → `"to"`, `"Due to the fact that"` → `"Because"`, etc.) remain in effect; the allow-list only blocks rewrites that would *delete or substitute a listed word*.

Worked example: *"continues to work unchanged when the file is later assembled"* stays as written — the word `unchanged` is preserved. (Regression target: `quadralay/markdown-plus-plus` PR #107 commit `6fda523`, where a filler-phrase rewrite stripped `unchanged` and converted a normative claim into an ambiguous one.)


### 23. Excessive Hedging  [profile: both]

**Problem:** Over-qualifying statements.

**Before:**
> It could potentially possibly be argued that the policy might have some effect on outcomes.

**After:**
> The policy may affect outcomes.


### 24. Generic Positive Conclusions  [profile: both]

**Problem:** Vague upbeat endings.

**Before:**
> The future looks bright for the company. Exciting times lie ahead as they continue their journey toward excellence. This represents a major step in the right direction.

**After:**
> The company plans to open two more locations next year.


### 25. Hyphenated Word Pair Overuse  [profile: prose]

**Words to watch:** third-party, cross-functional, client-facing, data-driven, decision-making, well-known, high-quality, real-time, long-term, end-to-end

**Problem:** AI hyphenates common word pairs with perfect consistency. Humans rarely hyphenate these uniformly, and when they do, it's inconsistent. Less common or technical compound modifiers are fine to hyphenate.

**Before:**
> The cross-functional team delivered a high-quality, data-driven report on our client-facing tools. Their decision-making process was well-known for being thorough and detail-oriented.

**After:**
> The cross functional team delivered a high quality, data driven report on our client facing tools. Their decision making process was known for being thorough and detail oriented.

---

## Process

1. Read the input text carefully
2. Identify all instances of the patterns above
3. Rewrite each problematic section
4. Ensure the revised text:
   - Sounds natural when read aloud
   - Varies sentence structure naturally
   - Uses specific details over vague claims
   - Maintains appropriate tone for context
   - Uses simple constructions (is/are/has) where appropriate
5. Present a draft humanized version
6. Prompt: "What makes the below so obviously AI generated?"
7. Answer briefly with the remaining tells (if any)
8. Prompt: "Now make it not obviously AI generated."
9. Present the final version (revised after the audit)

## Output Format

Provide:
1. Draft rewrite
2. "What makes the below so obviously AI generated?" (brief bullets)
3. Final rewrite
4. A brief summary of changes made (optional, if helpful)
5. Classification summary — the `Auto-detected audiences:` block (see "Classification summary format"). Always include when one or more file paths were processed; omit only when the invocation was raw text with no file paths.
6. Applied-profile summary — the `Applied profiles:` block (see "Applied-profile summary format"). Always emit immediately after the `Auto-detected audiences:` block when one or more file paths were processed; omit only when the invocation was raw text with no file paths.


## Full Example

**Before (AI-sounding):**
> Great question! Here is an essay on this topic. I hope this helps!
>
> AI-assisted coding serves as an enduring testament to the transformative potential of large language models, marking a pivotal moment in the evolution of software development. In today's rapidly evolving technological landscape, these groundbreaking tools—nestled at the intersection of research and practice—are reshaping how engineers ideate, iterate, and deliver, underscoring their vital role in modern workflows.
>
> At its core, the value proposition is clear: streamlining processes, enhancing collaboration, and fostering alignment. It's not just about autocomplete; it's about unlocking creativity at scale, ensuring that organizations can remain agile while delivering seamless, intuitive, and powerful experiences to users. The tool serves as a catalyst. The assistant functions as a partner. The system stands as a foundation for innovation.
>
> Industry observers have noted that adoption has accelerated from hobbyist experiments to enterprise-wide rollouts, from solo developers to cross-functional teams. The technology has been featured in The New York Times, Wired, and The Verge. Additionally, the ability to generate documentation, tests, and refactors showcases how AI can contribute to better outcomes, highlighting the intricate interplay between automation and human judgment.
>
> - 💡 **Speed:** Code generation is significantly faster, reducing friction and empowering developers.
> - 🚀 **Quality:** Output quality has been enhanced through improved training, contributing to higher standards.
> - ✅ **Adoption:** Usage continues to grow, reflecting broader industry trends.
>
> While specific details are limited based on available information, it could potentially be argued that these tools might have some positive effect. Despite challenges typical of emerging technologies—including hallucinations, bias, and accountability—the ecosystem continues to thrive. In order to fully realize this potential, teams must align with best practices.
>
> In conclusion, the future looks bright. Exciting times lie ahead as we continue this journey toward excellence. Let me know if you’d like me to expand on any section!

**Draft rewrite:**
> AI coding assistants speed up some tasks. In a 2024 study by Google, developers using Codex completed simple functions 55% faster than a control group, but showed no improvement on debugging or architectural decisions.
>
> The tools are good at boilerplate: config files, test scaffolding, repetitive refactors. They are bad at knowing when they are wrong. I have mass-accepted suggestions that compiled, passed lint, and still did the wrong thing because I stopped paying attention.
>
> Mira, an engineer at a fintech startup I interviewed, said she uses Copilot "like autocomplete for boring code" but reviews every line before committing. Jake, a senior dev at a larger company, disabled it after it kept suggesting patterns from a deprecated internal library.
>
> The productivity claims are hard to verify. GitHub says Copilot users "accept 30% of suggestions," but acceptance is not correctness, and correctness is not value. The 2024 Uplevel study found no statistically significant difference in pull-request throughput between teams with and without AI assistants.
>
> None of this means the tools are useless. It means they are tools. They do not replace judgment, and they do not eliminate the need for tests. If you do not have tests, you cannot tell whether the suggestion is right.

**What makes the below so obviously AI generated?**
- The rhythm is still a bit too tidy (clean contrasts, evenly paced paragraphs).
- The named people and study citations can read like plausible-but-made-up placeholders unless they're real and sourced.
- The closer leans a touch slogan-y ("If you do not have tests...") rather than sounding like a person talking.

**Now make it not obviously AI generated.**
> AI coding assistants can make you faster at the boring parts. Not everything. Definitely not architecture.
>
> They're great at boilerplate: config files, test scaffolding, repetitive refactors. They're also great at sounding right while being wrong. I've accepted suggestions that compiled, passed lint, and still missed the point because I stopped paying attention.
>
> People I talk to tend to land in two camps. Some use it like autocomplete for chores and review every line. Others disable it after it keeps suggesting patterns they don't want. Both feel reasonable.
>
> The productivity metrics are slippery. GitHub can say Copilot users "accept 30% of suggestions," but acceptance isn't correctness, and correctness isn't value. If you don't have tests, you're basically guessing.

**Changes made:**
- Removed chatbot artifacts ("Great question!", "I hope this helps!", "Let me know if...")
- Removed significance inflation ("testament", "pivotal moment", "evolving landscape", "vital role")
- Removed promotional language ("groundbreaking", "nestled", "seamless, intuitive, and powerful")
- Removed vague attributions ("Industry observers")
- Removed superficial -ing phrases ("underscoring", "highlighting", "reflecting", "contributing to")
- Removed negative parallelism ("It's not just X; it's Y")
- Removed rule-of-three patterns and synonym cycling ("catalyst/partner/foundation")
- Removed false ranges ("from X to Y, from A to B")
- Removed em dashes, emojis, boldface headers, and curly quotes
- Removed copula avoidance ("serves as", "functions as", "stands as") in favor of "is"/"are"
- Removed formulaic challenges section ("Despite challenges... continues to thrive")
- Removed knowledge-cutoff hedging ("While specific details are limited...")
- Removed excessive hedging ("could potentially be argued that... might have some")
- Removed filler phrases ("In order to", "At its core")
- Removed generic positive conclusion ("the future looks bright", "exciting times lie ahead")
- Made the voice more personal and less "assembled" (varied rhythm, fewer placeholders)


## Reference

This skill is based on [Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing), maintained by WikiProject AI Cleanup. The patterns documented there come from observations of thousands of instances of AI-generated text on Wikipedia.

Key insight from Wikipedia: "LLMs use statistical algorithms to guess what should come next. The result tends toward the most statistically likely result that applies to the widest variety of cases."
