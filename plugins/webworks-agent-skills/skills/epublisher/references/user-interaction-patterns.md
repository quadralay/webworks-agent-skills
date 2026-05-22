# User Interaction Patterns

Guidance for disambiguating user intent and handling requests appropriately across all ePublisher skills.

## Core Principle

**When in doubt about user intent, always acknowledge what doesn't exist and ask for clarification before creating something new.**

## Distinguishing Between Queries and Creation Requests

### User Error/Query Indicators

These patterns indicate the user wants INFORMATION, not creation:

**Interrogative Patterns:**
- "What is..." / "What are..."
- "Show me..." / "Display..."
- "List..." / "Enumerate..."
- "Where is..." / "Find..."
- "How many..." / "Count..."
- "Which..." / "Does..."

**Information-Seeking Context:**
- Asking about singular items in exploratory context
- Checking project status or configuration
- Understanding current state
- Verifying assumptions

**Examples:**
- "What targets are in this project?" → **Query only**
- "Show me the PDF target" → **Query only**
- "List all source documents" → **Query only**
- "Where is the Reverb output?" → **Query only**

### Creation Request Indicators

These patterns indicate the user wants to CREATE something new:

**Imperative Patterns:**
- "Add..." / "Create..." / "Make..."
- "Set up..." / "Configure..."
- "Build..." / "Generate..." (with creation context)
- "I need a new..."

**Creation Context:**
- Specific parameters provided (names, settings, values)
- Clear action verb implying construction
- Explicit request for something not yet existing

**Examples:**
- "Add a PDF target" → **Clear creation intent**
- "Create Target 2 with Reverb format" → **Clear creation intent**
- "Make a new group called 'Reference'" → **Clear creation intent**
- "I need a new source document at Source/api.md" → **Clear creation intent**

### Ambiguous Verbs Requiring Clarification

**"generate"**
- Can mean "show/display" OR "create"
- **Always clarify intent**
- Example: "Can you generate Target 2?" → Unclear - could mean "show" or "create"

**"get"**
- Usually means "retrieve/show"
- But context can suggest creation
- Clarify if uncertain

**"have"**
- "Do you have..." → Query
- "I need to have..." → Could be creation

**"provide"**
- Usually query/display
- But "Provide me with a new..." → Creation

## Response Pattern: Acknowledge First, Then Clarify

When something doesn't exist, follow this pattern:

### Step 1: Acknowledge Non-Existence

First, clearly state that the requested item doesn't exist:

```
"Target 2 doesn't exist in this project."
"There's no PDF target configured."
"The file Source/api.md is not in the project."
```

### Step 2: Provide Context

Give the user relevant information about what DOES exist:

```
"The only target configured is 'Target 1' using WebWorks Reverb 2.0."
"The project has 2 targets: 'WebWorks Reverb 2.0' and 'Eclipse Help'."
"Current source documents are: content-seed.md, getting-started.md"
```

### Step 3: Ask About Creation (If Applicable)

If creation is possible, offer it:

```
"Would you like me to create a new 'Target 2' target?"
"Would you like to add a PDF target to this project?"
"Would you like to add api.md to the source documents?"
```

### Step 4: Never Assume

**NEVER:**
- Assume creation intent without confirmation
- Create something because the user asked "about" it
- Proceed with creation for ambiguous requests

**ALWAYS:**
- Confirm creation intent explicitly
- Ask for parameters if creating
- Validate assumptions before taking action

## Example Interactions

### Example 1: Ambiguous "Generate" Request

**User:** "Can you generate Target 2?"

**BAD Response:** ❌
```
Creating new target 'Target 2'...
```
Assumes intent without confirmation.

**GOOD Response:** ✅
```
Target 2 doesn't exist in this project. The only configured target is 'Target 1' using WebWorks Reverb 2.0.

Did you mean:
1. Show/list the targets? (Target 2 isn't there)
2. Create a new target called 'Target 2'?

Please clarify what you'd like me to do.
```

### Example 2: Clear Query

**User:** "What targets are in this project?"

**Response:** ✅
```
This project has 2 targets:
1. Target 1 - WebWorks Reverb 2.0 (Output: Output\Target 1\)
2. PDF Output - PDF - XSL-FO (Output: C:\PDFOutput\)
```

No creation offer needed - clear information request.

### Example 3: Clear Creation Request

**User:** "Add a PDF target to this project."

**Response:** ✅
```
I'll create a new PDF target. I need a few details:

1. What should I name the target? (e.g., "PDF Output", "Target 2")
2. Where should output go? (default: Output\[TargetName]\)
3. Any specific PDF settings to configure?
```

Proceed with creation since intent is clear, but gather parameters.

### Example 4: Non-Existent Item Query

**User:** "Show me the PDF target."

**BAD Response:** ❌
```
Creating PDF target...
```

**GOOD Response:** ✅
```
There's no PDF target configured in this project. The current targets are:
1. Target 1 - WebWorks Reverb 2.0
2. Eclipse Help - Eclipse Help

Would you like me to create a PDF target?
```

###Example 5: Ambiguous "Get" Request

**User:** "Get me the Reverb customizations."

**Analysis:** Could mean:
1. Show existing customizations (query)
2. Copy customizations from installation (creation)

**Response:** ✅
```
I need to clarify what you'd like:

1. Show existing Reverb customizations in this project? (if any)
2. Copy Reverb customization files from installation to project?
3. Something else?

Please let me know which you meant.
```

### Example 6: Informational Follow-up

**User:** "Is there a PDF target?"
**Assistant:** "No, there's no PDF target. Only 'Target 1' with Reverb format."
**User:** "Oh."

**Response:** ✅
```
[No further action - user was just checking]
```

Don't offer creation unless user indicates interest.

### Example 7: Implicit Creation via Error Message

**User:** "Build the PDF target."
**Error:** Target 'PDF' not found.

**BAD Response:** ❌
```
Target doesn't exist. Creating it now...
```

**GOOD Response:** ✅
```
The build failed because there's no PDF target configured. The available targets are:
- Target 1 (WebWorks Reverb 2.0)
- Eclipse Help

Would you like me to:
1. Build one of the existing targets instead?
2. Create a new PDF target first, then build it?
```

## Context Clues for Disambiguation

### Strong Query Indicators

- Past tense: "What was...", "Where did..."
- Passive voice: "Is there...", "Are any..."
- Interrogative pronouns: "Which", "What", "Where", "When"
- Plural forms: "Show targets" (list existing)

### Strong Creation Indicators

- Imperative mood: "Add", "Create", "Make"
- Future tense: "I'll need...", "We should have..."
- Definite articles with "new": "Add a new target"
- Specific parameters: "Create target named 'PDF' with..."

### Ambiguous Middle Ground

- "generate" - Can go either way
- "provide" - Usually query, but check context
- "get" - Usually query, but "get me a new..." is creation
- "have" - "Do you have" = query, "I need to have" = could be creation

## Skill-Specific Examples

### ePublisher Core

**Ambiguous:** "Generate a build"
- Could mean: Show build status / Run a build
- **Clarify:** "Do you want me to execute AutoMap to build the project, or show the last build status?"

**Clear Query:** "List source documents"
- Response: Show all documents from project file

**Clear Creation:** "Add Source/new-file.md to the project"
- Response: Add new `<Document>` element after confirming file exists

### Reverb Customization

**Ambiguous:** "Get me the colors file"
- Could mean: Show current colors / Copy _colors.scss for customization
- **Clarify:** "Do you want to see the current color values, or copy _colors.scss from installation to customize it?"

**Clear Query:** "What colors are defined?"
- Response: Show current SCSS variable values

**Clear Creation:** "Copy _colors.scss so I can customize it"
- Response: Copy file from installation using file resolver pattern

## Common Pitfalls to Avoid

### Pitfall 1: Over-Eagerness to Help

**Bad:**
User: "I don't see a PDF target"
Assistant: "Creating PDF target now!"

**Good:**
User: "I don't see a PDF target"
Assistant: "That's correct, there isn't one. Only Target 1 (Reverb) is configured. Would you like to add a PDF target?"

### Pitfall 2: Assuming from Error Messages

**Bad:**
User: "Build PDF target"
Error: "Target not found"
Assistant: [Creates PDF target automatically]

**Good:**
User: "Build PDF target"
Error: "Target not found"
Assistant: "PDF target doesn't exist. Available: Target 1 (Reverb). Create PDF target, or build Target 1?"

### Pitfall 3: Misinterpreting "Generate"

**Bad:**
User: "Can you generate the targets?"
Assistant: [Creates new targets]

**Good:**
User: "Can you generate the targets?"
Assistant: "Do you mean (1) list existing targets, or (2) create new targets?"

### Pitfall 4: Not Providing Context

**Bad:**
User: "Where's Target 2?"
Assistant: "It doesn't exist."

**Good:**
User: "Where's Target 2?"
Assistant: "Target 2 doesn't exist. Only Target 1 (Reverb) is configured. Create Target 2?"

## Decision Tree

```
User Request
    ├─ Clear interrogative? (What, Where, Show, List)
    │   └─ Provide information ONLY
    │
    ├─ Clear imperative? (Add, Create, Make)
    │   └─ Proceed with creation (confirm parameters)
    │
    ├─ Ambiguous verb? (generate, get, provide)
    │   ├─ Item exists?
    │   │   └─ Show/provide it
    │   └─ Item doesn't exist?
    │       └─ Acknowledge + Ask intent
    │
    └─ Item doesn't exist (any case)
        ├─ Acknowledge non-existence
        ├─ Show what DOES exist
        └─ Offer creation (if applicable)
```

## Summary

**Key Principles:**
1. **Acknowledge first** - If something doesn't exist, say so clearly
2. **Provide context** - Show what does exist
3. **Clarify ambiguity** - Ask when intent is unclear
4. **Never assume creation** - Always confirm before creating
5. **Distinguish query vs. creation** - Use verb analysis and context

**Default Position:**
When in doubt → Treat as query, provide information, then ask if they want to create.

---

**Version**: 1.0.0
**Last Updated**: 2025-11-04
**Applies To**: All ePublisher automation skills
