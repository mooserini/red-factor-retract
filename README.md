# Red Factor Retract

Semantic relationship highlighter for YAML and Markdown. Analyze a configuration
or document and see related conflicts beside the affected values or statements.
Analysis runs on opening, saving, or using the depth command; proposed-edit
simulation is a future direction.

Built for [Helix](https://helix-editor.com) as a stdio LSP (stdlib-only Python,
no deps), backed by [OpenRouter's Free Models Router](https://openrouter.ai)
(`openrouter/free`) with a local `llama-server` fallback.

## How it works

```
Helix (yaml/markdown) → red-factor-retract (stdio) → openrouter/free (primary)
                                              → local llama-server (fallback)
                                             → textDocument/publishDiagnostics
```

- **Minimal inference vs DeepLeaf:** `` ` `` toggles depth 1 ↔ 2 (normal ↔ full
  relational chew). `~` stays as your case toggle.
- **YAML impact:** diagnostics carry a model-supplied impact score and severity;
  numeric thresholds are used when severity is absent. Low-impact results are suppressed.
- **Markdown statements:** warnings connect contradictory passages and quote
  evidence from both. Possibilities and recommendations are distinguished from
  facts. This checks consistency within a document, rather than external truth.
- **Privacy:** matching single-line `api_key`/`token`/`password` and similar
  keys are masked to `[REDACTED]`. This pattern filter does not cover every secret:
  prefixed keys, list entries, multiline values, and prose may remain visible to
  hosted models. Use `RFR_BACKEND=local` for private documents. The OpenRouter
  authentication key comes from `OPENROUTER_API_KEY` env or macOS keychain.

## Quick start

1. `brew install helix`
2. Copy `helix-languages.example.toml` → `~/.config/helix/languages.toml`
   (fix the `command` path to point at your checkout)
3. Copy `helix-config.example.toml` snippet → `~/.config/helix/config.toml`
4. `security add-generic-password -a "$USER" -s "OPENROUTER_API_KEY" -w "sk-or-..."`
5. `hx test-hermes.yaml`, `:w`, watch `ogg` light up red.

Offline fallback: `./start-llama-8222.sh` (reuses model files in place,
zero extra disk), `RFR_BACKEND=local`.

## Small Markdown demonstration

Run `./demo-markdown` for the small example with temporary Helix configuration
and a scratch copy of the fixture. It uses this checkout and leaves your personal
editor configuration alone. Edits to the scratch copy are discarded on exit.

Use the Markdown block in `helix-languages.example.toml` with the server command
pointing to this checkout, then open `hx test-statements.md`.

The fixture says the renderer accepts MP3/WAV, instructs you to select OGG, and
mentions that OGG might be supported in the future. The intended result is a
warning on the OGG instruction, citing the MP3/WAV restriction. The future
possibility should remain unflagged. Change the instruction to MP3 and save with
`:w`; the warning should clear after analysis. Backtick requests a different
analysis depth and also refreshes the feedback. Model judgments may vary; quoted
evidence confirms where the claims came from, not whether the reasoning is right.

This first increment accepts complete Markdown documents up to **6,000 characters**.
Larger documents receive an informational diagnostic rather than being silently
truncated. Backend failures and invalid evidence have their own informational
diagnostic, so they cannot be mistaken for a successful check with no conflicts.
Passages are grouped under headings; inline code participates and fenced code
examples are excluded. Warning ranges cover whole passages, with related
information pointing to the other statement. Depth 2 uses contextual reasoning
for Markdown; it does not inject the YAML provider table.

YAML retains its original first-6,000-character prompt limit and key lookup behavior.

Run the offline tests with `python3 -m unittest discover -s tests -v`.

## Files

| file | what |
|---|---|
| `red-factor-retract` | the LSP and inference transport (executable Python, stdlib only) |
| `rfr_markdown.py` | Markdown passages, evidence validation, and source ranges |
| `providers.json` | curated provider constraints (xai/elevenlabs/openai) |
| `helix-languages.example.toml` | Helix LSP wiring |
| `helix-config.example.toml` | backtick depth-toggle keymap |
| `test-hermes.yaml` | Hermes TTS fixture (xai + ogg conflict) |
| `test-statements.md` | tiny Markdown contradiction-and-correction fixture |
| `demo-markdown` | isolated Helix launcher for the small Markdown example |
| `start-llama-8222.sh` | local fallback server |
| `red-factor-retract-spec.md` | full design spec with diagrams |
| `exports/` | provenance (session export) |

## Env

| var | default | notes |
|---|---|---|
| `RFR_BACKEND` | `auto` | `auto` = hosted first, local fallback |
| `RFR_OPENROUTER_MODEL` | `openrouter/free` | free router, filters for structured-output support |
| `RFR_LLM_URL` | `http://127.0.0.1:8222/...` | local fallback |
| `RFR_DEPTH` | `1` | hotkey toggles 1 ↔ 2 |
