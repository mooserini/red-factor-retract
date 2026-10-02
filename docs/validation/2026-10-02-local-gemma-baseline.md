# Local Gemma baseline: 2026-10-02

Tested the unchanged Markdown implementation at commit `a5e7229` against the
user-provided local endpoint `http://localhost:1234/v1`. The model-list endpoint
and every completion reported `google/gemma-4-e4b`. The downloaded model was
labeled Gemma 4 E4B Instruct; quantization and server internals were not inspected.

## Controlled comparison

Used the same synthetic `test-statements.md` fixture and its correction from
`to OGG` to `to MP3`. Depth was 1, temperature 0, streaming disabled, and the
production timeout remained 20 seconds. Each request went through the existing
local backend without application caching or hosted fallback. No personal
documents or global configuration were used or changed.

The expected conflict is one warning on the instruction at line 5, citing the
restriction at line 3. The corrected document should have no warnings. The future
possibility at line 7 should remain unflagged.

| Trial | Input | Time | Outcome |
|---|---|---|---|
| 1 | conflict | 3.192 s | Rejected: invalid passage IDs |
| 1 | corrected | 1.626 s | Rejected: invalid passage IDs |
| 2 | conflict | 1.721 s | Rejected: invalid passage IDs |
| 2 | corrected | 1.615 s | Rejected: invalid passage IDs |
| 3 | conflict | 1.794 s | Rejected: invalid passage IDs |
| 3 | corrected | 1.734 s | Rejected: invalid passage IDs |

All six requests completed using `json_schema` on the first transport attempt;
none timed out or used JSON-object fallback. Zero of six responses passed the
evidence validator, which reported `contradiction requires two distinct known
passages`. A captured conflict response used the heading
`Example output configuration` in both identifier fields instead of supplied
IDs such as `p2` and `p1`. It also put the restriction in the first quote rather
than following the instruction-first orientation. These timings measure rejected
responses, not successful editor resolution.

## Transport isolation

Two additional diagnostic requests kept the model, prompt, input, temperature,
and timeout unchanged, but omitted `response_format`. The conflict and corrected
inputs took 2.075 s and 2.077 s respectively. Both again used the heading as both
passage IDs and added an unexpected top-level `depth` field. The corrected MP3
case still contained a diagnostic, with the explanation “The formats mentioned
are related but the specific details differ.”

This reproduces the identifier problem without schema enforcement. It does not
isolate model weights from prompt interpretation, model packaging, or server
behavior. The observed responses do not establish that this model is unsuitable
for other tasks, and six runs are not a general accuracy or latency benchmark.

## Development implication

The fixed local model makes the current contract failure reproducible. Keep this
baseline separate from later prompt or schema changes. The strict validator
prevented invalid evidence from becoming editor warnings; the existing failure
path reports an informational analysis status rather than a clean conclusion.

A subsequent small experiment can tighten the permitted passage identifiers and
make the expected contradiction/correction distinction explicit, then rerun both
cases against this same model. No implementation or server settings were changed
in this evaluation.
