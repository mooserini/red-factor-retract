# Mercury Decide: synthetic Markdown evaluation

On 2026-10-02, selected `inception/mercury-decide:free` explicitly through
`POST https://openrouter.ai/api/alpha/decisions`. Used the existing OpenRouter
credential in memory; no credential was printed or saved. All six responses
reported `inception/mercury-decide-20260930` from Inception. This pins the selected
model rather than using `openrouter/free`; the requested free alias is not a
guarantee that the provider will retain that version forever.

## Inputs and checks

Used only the same synthetic `test-statements.md` fixture and its correction
from `to OGG` to `to MP3`. No personal documents were sent. Each document served
as the state for two fixed typed yes/no questions (`noul`): whether the instruction
violates the current restriction, and whether the future possibility contradicts
it. The criteria explicitly distinguish current restrictions from future
possibilities. Application code owns question IDs; the model need not generate
paragraph identifiers, quotations, or explanations.

Validated the two answer keys, answer types, and numeric probabilities in [0, 1].
Used 0.5 only as a preselected evaluation boundary, not a production threshold.
The expected decisions are conflict=true/future=false for OGG, and both=false
after the MP3 correction. Exact questions, fixture, and responses are preserved
in [the synthetic results JSON](2026-10-02-mercury-decide-results.json).

| Trial | Input | P(instruction conflict) | P(future conflict) | Time |
|---|---|---|---|---|
| 1 | conflict | 0.99995167 | 0.00035697 | 0.610 s |
| 1 | corrected | 0.00012339 | 0.00037998 | 0.368 s |
| 2 | conflict | 0.99996880 | 0.00085590 | 0.261 s |
| 2 | corrected | 0.00012339 | 0.00037998 | 0.367 s |
| 3 | conflict | 0.99996679 | 0.00085590 | 0.280 s |
| 3 | corrected | 0.00005476 | 0.00017953 | 0.432 s |

All 12 judgments across six requests matched the expectations. Every response
reported cost zero. No application result cache, automatic retry, alternate
model, or hosted/local fallback was used. Provider-side caching was not measured.
These are client round-trip timings for a tiny fixture, not an editor latency
benchmark or an independent evaluation of probability calibration.

## Scaffold control and interpretation

Prepared a local Gemma Boolean control using the same state, questions, and
criteria, with a two-Boolean output schema instead of the previous passage-ID
and quotation generation. The local server on port 1234 refused all connection
attempts; no Gemma judgments were obtained. These transport failures are not
model-quality failures.

The Mercury result supports testing a typed decision backend next. It does not
establish whether its tuning or the simpler scaffold caused the improvement:
both the model and output task differ from the earlier Gemma experiment. Repeated
runs of two documents also do not establish general accuracy. The future-specific
question directly states the modality distinction, which is part of the scaffold.

This was an isolated API evaluation. The Helix LSP, backend defaults, personal
configuration, and server settings were not changed. Integrating typed decisions
will require mapping them to source ranges and safe explanations in application
code, and a small labeled set covering negation, conditions, and time changes.

API reference: https://openrouter.ai/docs/api/api-reference/alphadecisions/submit-a-decisions-request
