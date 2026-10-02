# First Markdown increment: relationships between statements

## Purpose

Extend Red Factor Retract to readable files through small, observable examples.
The user selected YAML, Markdown, and TOML as the starting formats, and chose
relationships between statements as Markdown's first behavior. This increment
adds one Markdown experience to the existing editor and inference flow. TOML
remains a subsequent increment.

Success means opening a short document, seeing a contradiction highlighted with
an explanation connecting both statements, correcting it, and seeing the warning
clear after reanalysis.

## Demonstration

```markdown
# Example output configuration

The renderer accepts only MP3 and WAV output.

For this renderer, set `output_format` to OGG.

OGG support might be added in a future version.
```

The current OGG instruction contradicts the stated accepted formats. Both
statements should be identified, with a warning on the instruction and an
explanation citing the restriction. Changing OGG to MP3 in that instruction
resolves the conflict. The future possibility remains compatible with both
versions and must not be reported as a contradiction.

Here, true versus false means consistent versus contradictory relative to the
document's explicit claims. A quiet document does not establish factual truth.
Recommendations, possibilities, different time periods, and different subjects
must not be treated as contradictions merely because their wording differs.

## Small implementation boundary

Keep the existing stdio LSP, backend selection, and open/depth-command analysis
flow. The Markdown reader groups prose paragraphs under their headings and
assigns stable identifiers for each analysis request, with exact source ranges.
Inline code participates as prose; fenced code blocks are excluded in this first
increment. Other file types continue through the existing YAML behavior.

The Markdown prompt uses the document as its source of facts. The model returns
conflicting paragraph identifiers, a brief explanation, and quoted evidence from
each paragraph. Markdown analysis does not inject the YAML provider table.
The server verifies identifiers and evidence against the input before publishing
diagnostics; the model does not supply editor coordinates. Cross-file reasoning,
link validation, external fact checking, and binary decoding are outside this
increment.

Use warning severity for supported contradictions. Do not represent a model's
impact score as a probability that a statement is false. Diagnostics should say
"Conflicts with the statement on line ..." and include the relevant evidence.

## Coverage and failure behavior

Accept complete Markdown documents up to 6,000 characters for this increment.
An oversized document receives an informational diagnostic explaining that it
was not analyzed, rather than silently analyzing a prefix. Backend failure or
an invalid response clears previous relational diagnostics and produces a
distinct informational diagnostic; failed analyses are not cached as success.
Successful analyses with no contradictions clear prior diagnostics.

## Verification

Use deterministic mocked responses to check evidence validation, exact ranges,
contradiction publication, clearing after correction, and coverage/failure
messages. Use the three-paragraph fixture for a separate model-quality check:
the present-tense instruction should be flagged, and the future possibility
should remain unflagged. A manual Helix check verifies that the result is visible
and understandable. Record observed latency without claiming a general speed
benchmark. Model-quality checks and editor checks remain separate from unit
tests so a passing mock cannot be mistaken for a verified inference experience.
