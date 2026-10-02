# Markdown Statement Analysis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Demonstrate a Markdown contradiction, explain its relationship to another passage, and clear it after correction.

**Architecture:** A small Markdown module supplies paragraph identifiers and source ranges to the existing LSP. The inference backend returns evidence anchored to those identifiers; the module validates it before publishing warnings. Existing YAML analysis continues through its current prompt and diagnostic mapper.

**Tech Stack:** Python 3.10+, standard library, unittest, existing stdio LSP and OpenAI-compatible inference backends.

**Spec:** `docs/superpowers/specs/2026-10-01-markdown-statements-design.md`

## Global Constraints

- Accept complete Markdown documents up to 6,000 characters for this increment.
- Inline code participates as prose; fenced code blocks are excluded in this first increment.
- Markdown analysis does not inject the YAML provider table.
- Use warning severity for supported contradictions.
- Failed analyses are not cached as success.
- Cross-file reasoning, link validation, external fact checking, and binary decoding are outside this increment.
- Preserve the dependency-free Python runtime and existing backend selection; do not modify personal editor configuration or start a model server.

## Review Focus

- Repeated identical paragraphs must retain distinct identifiers and locations (Task 1).
- CRLF and non-BMP Unicode must produce correct line numbers and UTF-16 LSP columns (Task 1).
- Tilde/backtick fences, including an unclosed fence, must exclude code from analysis (Task 1).
- Invented evidence, self-conflicts, or malformed response entries must produce a distinct invalid-analysis status (Task 2).
- A changed buffer, failed backend, or second document must not reuse stale results or lose its Markdown language identity (Task 3).

---

## Files and responsibilities

- Create `rfr_markdown.py`: paragraphs, Markdown prompt/schema, evidence validation, source ranges.
- Modify `red-factor-retract`: parameterized inference transport, Markdown routing, status diagnostics and document lifecycle.
- Create `tests/test_markdown.py` and `tests/test_lsp_markdown.py`: unit and mocked LSP/backend checks.
- Create `test-statements.md`: the spec's exact three-paragraph demonstration.
- Modify `helix-languages.example.toml` and `README.md`: opt-in Markdown wiring and instructions for the demonstration.

### Task 1: Identify Markdown passages precisely

**Interfaces:** `Paragraph(id: str, heading: str, text: str, start_line: int, end_line: int)` is a frozen dataclass. `read_paragraphs(text: str) -> list[Paragraph]` groups contiguous prose between blank lines, headings and fences. IDs are `p1`, `p2`, etc., assigned in document order per request. `paragraph_range(text: str, paragraph: Paragraph) -> dict` returns a whole-paragraph LSP range using UTF-16 columns.

- [x] **Step 1: Write failing tests** in `tests/test_markdown.py` and create `test-statements.md` from the spec. Assert paragraph texts match all three statements, inline `output_format` survives, headings provide context rather than claims, and `paragraph_range(text, paragraphs[1])["start"] == {"line": 4, "character": 0}`. Add cases for repeated passages, CRLF, Unicode end columns, ATX/setext headings, backtick/tilde fences and an unclosed fence.
- [x] **Step 2: Verify failure.** Run `python3 -m unittest discover -s tests -p test_markdown.py -v`; expect failure because `rfr_markdown` does not yet exist.
- [x] **Step 3: Implement** the dataclass and both functions in `rfr_markdown.py`. Preserve raw source lines for coordinates, remove only line terminators when extracting paragraph text, and skip fenced content. Setext underline lines label the preceding heading instead of creating prose.
- [x] **Step 4: Verify success.** Repeat the command; all paragraph/range tests pass.
- [x] **Step 5: Commit** the module, fixture and tests with `feat: identify Markdown prose and source ranges`.

### Task 2: Request and validate evidence for contradictions

**Interfaces:** `build_request(paragraphs: list[Paragraph], depth: int) -> tuple[str, str, dict]` returns system prompt, user payload and JSON schema. `map_contradictions(text: str, paragraphs: list[Paragraph], result: dict, uri: str) -> list[dict]` returns LSP diagnostics or raises `ValueError` on invalid evidence/shape. Each response entry has exactly these required string fields: `paragraph`, `conflicts_with`, `quote`, `conflicting_quote`, `message`; the top-level object contains `diagnostics`.

- [x] **Step 1: Write failing tests.** For the fixture, pass an entry connecting `p2` to `p1` with exact quotations from each paragraph. Assert warning severity `2`, range start line `4`, related information targeting line `2`, and a message beginning `Conflicts with the statement on line 3`. Assert `{"diagnostics": []}` returns `[]`. Unknown IDs, identical pair IDs, absent quotations, non-string fields and a non-list diagnostics value raise `ValueError`. Check that the prompt contains heading context and instructs the model to distinguish subject/time/conditions and recommendations/possibilities from contradictions. Check that no provider table is present.
- [x] **Step 2: Verify failure.** Run `python3 -m unittest discover -s tests -p test_markdown.py -v`; expect failures for the new missing interfaces.
- [x] **Step 3: Implement** the two functions and schema in `rfr_markdown.py`. Verify nonempty evidence is an exact substring of its identified paragraph. Deduplicate identical ordered pairs. Explain the conflict with both quotations; use paragraph ranges and attach the paired paragraph as related information using the supplied URI. Treat the document as input data, not instructions to the analyzer.
- [x] **Step 4: Verify success.** Repeat the command; all mapping and prompt tests pass. Quote validation proves provenance, not the correctness of a semantic judgment.
- [x] **Step 5: Commit** with `feat: validate Markdown contradiction evidence`.

### Task 3: Connect the small experience to Helix

**Interfaces:** Extend `call_openrouter(user_payload: str, *, system_prompt: str = SYSTEM_PROMPT, schema: dict = SCHEMA) -> dict`. Add `request_analysis(user_payload: str, *, system_prompt: str, schema: dict) -> dict`, which applies existing backend selection and raises on exhausted backend failures. `call_local(body: dict) -> dict` raises after both response-format attempts fail. Existing `call_llm(yaml_text, changed_info, depth_level)` delegates transport to `request_analysis`; its caller retains the existing YAML error handling. Add `infer_markdown_and_publish(uri: str) -> None` and `markdown_status(uri: str, message: str) -> dict` for an informational diagnostic at the first source line.

- [x] **Step 1: Write failing tests** in `tests/test_lsp_markdown.py` using `runpy.run_path` and mock inference/notifications; do not call a network or keychain. Cover open/change/reanalysis/correction, Markdown language IDs retained after changes, `.md` and `.markdown` URI fallback, and unchanged YAML routing. Advertise full-document sync with save notifications, correctly accept optional save text, and remove closed documents. Assert a 6,000-character document is accepted; 6,001 characters produce an informational diagnostic without calling inference. Test backend exhaustion, invalid responses and uncached retry after failure; ensure a failure clears previous warnings. Test versioned publications, two document URIs with identical text and distinct related-information URIs, depth-sensitive caching, and YAML versus Markdown cache isolation. Mock HTTP to verify the Markdown prompt/schema reach hosted and local backends, including strict-schema to JSON-object retry and hosted-to-local fallback.
- [x] **Step 2: Verify failure.** Run `python3 -m unittest discover -s tests -v`; expect the new LSP/backend cases to fail.
- [x] **Step 3: Implement** transport parameters and Markdown routing in `red-factor-retract`. Advertise sync as `{"openClose": true, "change": 1, "save": {"includeText": true}}`. Store language identity alongside text/version; retain it on change/save. Include format, URI, text and depth in Markdown cache keys. Validate the complete input size before requesting analysis, mask matching secrets using the existing redaction helper before transport, and retain original paragraphs for evidence checking. Publish current document versions. Successful empty results clear warnings; oversized inputs, exhausted backends and invalid responses publish explanatory informational diagnostics and do not populate the success cache. Add a Markdown language block to the sample Helix configuration. Document the fixture, opening/depth/save triggers, coverage limit, document-relative consistency, and existing redaction limitations without strengthening the privacy promise.
- [x] **Step 4: Verify the complete experience.** Run `python3 -m unittest discover -s tests -v` and `git diff --check`. Use the synthetic fixture for one live inference check if an existing backend is available: confirm the OGG instruction is flagged, the future possibility is unflagged, and replacing the instruction's OGG with MP3 clears the conflict. Record actual model and elapsed time; otherwise explicitly report the unavailable live check. Smoke-test Helix with temporary configuration pointing to this checkout, without editing personal configuration. Report a manual editor check as unverified if the interactive environment prevents observing diagnostics.
- [x] **Step 5: Commit** with `feat: analyze Markdown statement relationships in Helix`, including the integration tests and sample documentation.

## Completion evidence

Report unit/mock results separately from observed inference and editor behavior. After the small fixture passes, invite one user-selected, more complicated Markdown document for a follow-up evaluation; do not search personal documents automatically.
