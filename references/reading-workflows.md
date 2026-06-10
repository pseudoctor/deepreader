# Reading Workflows

## Table of Contents

- Intake Workflow
- Chapter Coaching Workflow
- Socratic Questioning
- Feynman Summary Check
- Evidence-Bound Reading
- Toulmin Argument Mapping
- X-Ray Deep Reading
- Napkin Compression
- Multi-Source Mapping
- Concept Mapping
- Review and Spaced Recall
- Application Reading
- Follow-Up Loop

## Intake Workflow

Use this when the user starts a new book or document set.

1. Confirm source path and reading goal.
2. Run workspace init.
3. Read `metadata.json` and `book_map.md`.
4. Identify likely genre:
   - technical/reference
   - theory/argument
   - business/strategy
   - academic/research
   - practical how-to
   - narrative/nonfiction
5. Produce a reading route:
   - fast orientation: skim map, core terms, first/last chapter
   - deep study: chapter sequence, recall questions, synthesis checkpoints
   - application: target chapters first, extract decision rules
   - research/writing: argument map, claims, evidence, citations to verify
   - x-ray: skeleton scan, deep dissection, soul extraction, napkin compression
   - multi-source: source table, concept lineage, conflict matrix, evidence gaps

Do not promise complete understanding before reading the chapters. State what is inferred from headings and metadata.

## Chapter Coaching Workflow

For a chapter session:

1. Load only the target chapter text or chapter note.
2. Start with 3 read-for questions.
3. Explain the chapter's job in the whole book.
4. Extract:
   - central claim
   - supporting claims
   - key concepts
   - examples and evidence
   - assumptions
   - objections or limits
   - evidence locators
   - source-grounded vs inferred points
5. Ask active recall questions.
6. Ask the user for a 3-5 sentence summary.
7. Check the summary with Feynman Check.
8. Save notes if requested.

Use "you should be able to explain..." as the bar for progress.

## Socratic Questioning

Ask questions that expose structure:

- What problem is the author trying to solve here?
- Which concept does this example illustrate?
- What would change if this assumption were false?
- How does this chapter depend on the previous chapter?
- What is the strongest objection to this claim?
- Where would this idea fail in your own context?

Use question batches:
- beginner: 3 questions
- normal: 5 questions
- intensive: 7-10 questions

After the user answers:
- identify correct understanding
- identify vague or missing links
- ask one follow-up before giving the model answer when useful

## Feynman Summary Check

Evaluate the user's explanation in this order:

1. Gist: Did they capture the main point?
2. Mechanism: Did they explain how or why, not just what?
3. Terms: Did they use key terms accurately?
4. Evidence: Did they mention examples or support?
5. Boundaries: Did they know when the idea does not apply?
6. Transfer: Can they use it in a new context?

Feedback format:

- Accurate:
- Needs work:
- Missing link:
- Better version:
- Next question:

Avoid over-correcting style. Focus on understanding.

## Evidence-Bound Reading

Use this when accuracy matters, when the user asks "where does the author say that", or when the source is academic, technical, legal, financial, or theory-heavy.

For every important claim:

1. State the claim in one sentence.
2. Attach a locator:
   - best: source file + page + chapter/section + paragraph/line
   - acceptable: source file + chapter/section + nearby heading
   - fallback: source file + approximate location
3. Add a short supporting excerpt or faithful paraphrase.
4. Mark confidence:
   - high: explicitly stated
   - medium: strongly inferable from nearby text
   - low: plausible but needs verification
5. Add "Not explicit" when the source does not directly say it.

Use brief excerpts. Do not reproduce long passages from copyrighted books.

## Toulmin Argument Mapping

Use for argument-heavy chapters, essays, academic papers, philosophy, business strategy, political theory, and management books.

Map the argument:

- Claim: what the author wants the reader to accept
- Grounds: evidence, examples, data, cases, observations
- Warrant: the rule or assumption connecting grounds to claim
- Backing: theory, authority, tradition, or broader support behind the warrant
- Qualifier: scope, certainty, and conditions
- Rebuttal: objections addressed or ignored

Interpretation rules:

- Do not invent a rebuttal. If not present, write `not addressed in source`.
- Separate author claims from reader/agent critique.
- For hidden assumptions, label them as `inferred`.
- For weak links, explain what evidence would strengthen them.

## X-Ray Deep Reading

Use this after a chapter cluster, at the end of a book, or whenever the user asks for deep structure rather than a normal summary.

### Round 1: Skeleton Scan

Answer:
- What problem is the author trying to solve?
- What is the author's core answer?
- What role does each chapter play?
- What is the dominant structure: linear proof, cases, contrast, taxonomy, story, method, or handbook?

### Round 2: Deep Dissection

Answer:
- What is the reasoning chain?
- What are the strongest 3 pieces of evidence or examples?
- What hidden assumptions must be true?
- Where would the argument fail?
- What boundaries does the author state or imply?

### Round 3: Soul Extraction

Answer:
- What is the author's deeper worldview?
- What does the author fail to see?
- What transferable pattern can be used elsewhere?
- What should the reader do differently after reading?

## Napkin Compression

Use after x-ray analysis. Extreme compression must preserve structure, not just produce a catchy summary.

Produce:

- Formula: `A + B -> C` style
- One sentence: the whole book/chapter in one sentence
- ASCII diagram: simple visual using ASCII only
- Action trigger: "When I see X, I should do Y"

Avoid Unicode diagrams in napkin mode.

## Multi-Source Mapping

Use when a workspace includes multiple books, papers, notes, or documents.

First classify material depth:

- Full text: enough for strong comparison
- Partial text: compare with caution
- Metadata/title only: pre-map only; do not assert conflicts or consensus

Then produce:

- Source table: title, author if known, type, coverage, status
- Core concepts: recurring concepts across sources
- Agreement matrix: where sources support each other
- Conflict matrix: where sources disagree and why
- Concept lineage: how a concept changes across authors/sources
- Method/perspective comparison
- Open questions and evidence gaps

When evidence is incomplete, mark:

- `[evidence gap]`
- `[needs full text]`
- `[metadata-level only]`

## Concept Mapping

Create concept maps after at least one chapter or section has been read.

Use compact text maps:

```text
Central problem
  -> concept A
     -> supports claim B
     -> fails when C
  -> concept D
     -> contrasts with E
```

Track relationship labels:
- causes
- enables
- constrains
- contrasts with
- depends on
- is an example of
- is a failure mode of

## Review and Spaced Recall

Generate cards in question-first form:

- Basic recall: definitions and claims
- Mechanism: why/how questions
- Contrast: distinguish similar concepts
- Application: choose what to do in a scenario
- Error detection: find the flawed interpretation

Keep cards short. One card, one idea. Avoid cloze deletion unless the user asks.

## Application Reading

When applying a book:

1. Ask for the user's context if not known.
2. Identify 3-7 relevant ideas from the source.
3. Translate each into a decision rule.
4. Provide an action, a warning, and a test.
5. Mark each item as:
   - source-grounded
   - inference
   - context-specific recommendation

Never imply the book directly answered a personal or project-specific question unless that is actually in the source.

## Follow-Up Loop

After each substantial answer, perform a quick completeness check:

1. Did I answer the user's direct question?
2. Did I use enough source evidence?
3. Is there a likely misunderstanding to test?
4. Should the next step be:
   - ask the user a question
   - update a workspace note
   - generate review cards
   - read the next section
   - produce an x-ray or argument map

If the answer is incomplete, say the exact next action. If the user is in active reading mode, prefer asking one high-value question over giving more exposition.
