# First Markdown increment: validation

Implemented the approved statement-analysis design in the isolated Codex
worktree. The small example connects a current format restriction to an
incompatible instruction, while leaving a future possibility unflagged.

## Automated checks

`python3 -m unittest discover -s tests -v`: 37 tests pass.
`git diff --check`: passes.

Checks cover passage boundaries, repeated text, ATX/setext headings, fenced
examples including quote/list containers, CRLF and UTF-16 positions; evidence/schema validation; document/depth
caching; correction and clearing; failure/coverage diagnostics; both inference
backends and fallback payloads; YAML routing; and real subprocess stdio framing,
Unicode, shutdown, and closed input pipes. Mocked inference checks exercise the
server's behavior, rather than measuring model judgment quality.

The editor-disconnection regression was observed failing before its fix, as was
the shutdown-null response check. Both pass after the fix. The fallback schema
contract, passage identity under redaction, and Unicode status range checks also
went from failing to passing before completion.

## Observed model behavior

Used only the synthetic `test-statements.md` fixture through the existing
OpenRouter credential; no personal documents were sent.

An initial live attempt exposed incompatible response fields. Adding the explicit
Markdown schema to the system prompt supplied the contract even on JSON-object
fallback, while retaining strict source-evidence validation.

The subsequent standalone checks passed:

| Input | Selected model | Observed time | Result |
|---|---|---|---|
| OGG instruction conflicts with MP3/WAV restriction | `cohere/north-mini-code:free` | 7.44 s | One warning on the instruction, citing the restriction |
| Instruction corrected to MP3 | `google/gemma-4-26b-a4b-it:free` | 0.79 s | No conflicts |

These are individual observations, not a latency or accuracy benchmark. A live
local-model check was unavailable because the configured server on port 8222
was not running; local transport was checked with controlled HTTP responses.

## Observed editor behavior

Helix 25.07.1 used temporary configuration pointing to this checkout. Its terminal
rendered a yellow warning and underline on line 5; navigating to the diagnostic
displayed the explanation and quotations. The future possibility was unflagged.
The instruction was changed to MP3 inside the editor and saved. The LSP then
published an empty diagnostics array at the new document version.

Both editor requests selected `nvidia/nemotron-3-ultra-550b-a55b:free`: the first
took 31.00 s and the corrected check took 5.26 s. Exiting after completion
returned successfully. No personal editor configuration was changed.

## Review decisions and remaining limits

- Final review was an author self-review because the user explicitly deferred
  subagents. This lacks an independent reviewer.
- Added `demo-markdown` so the example can be opened without installing global
  configuration. It uses a scratch copy; edits are discarded when it exits.
- Deferred minor: inference remains synchronous. Quitting during an outstanding
  request can hit Helix's shutdown timeout; background inference/cancellation
  belongs in a subsequent increment. Ordinary idle shutdown and input-pipe EOF
  are verified.
- This is a small prose reader, not a complete Markdown parser. Common fenced
  examples inside quote/list containers are excluded and tested; complex markup
  still requires a follow-up evaluation.
- Markdown accepts complete documents up to 6,000 characters. The larger-file
  check explicitly reports missing coverage. YAML retains its original partial
  prompt limit and naive key mapping.
- Evidence validation confirms quotation provenance, not factual truth or the
  correctness of every model judgment. Pattern-based secret masking remains
  incomplete; the README describes its limits and local-only mode.

Next evaluation: one user-selected Markdown document with more complicated prose,
after inspecting its size and choosing an appropriate backend for its contents.
