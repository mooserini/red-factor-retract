# Red Factor Retract

Semantic blast-radius highlighter for YAML. Edit one key, see the downstream
relational impact as red → green — *before* you type.

Built for [Helix](https://helix-editor.com) as a stdio LSP (stdlib-only Python,
no deps), backed by [OpenRouter's Free Models Router](https://openrouter.ai)
(`openrouter/free`) with a local `llama-server` fallback.

## How it works

```
Helix (yaml) → red-factor-retract (stdio) → openrouter/free (primary)
                                              → local llama-server (fallback)
                                             → textDocument/publishDiagnostics
```

- **Minimal inference vs DeepLeaf:** `` ` `` toggles depth 1 ↔ 2 (normal ↔ full
  relational chew). `~` stays as your case toggle.
- **Impact → severity:** 0.8–1.0 error (red), 0.5–0.8 warning (yellow),
  0.2–0.5 info, below hint/suppressed.
- **Secrets never leave the box:** `api_key`/`token`/`password` values are
  redacted to `[REDACTED]` before any hosted call. Key comes from
  `OPENROUTER_API_KEY` env or macOS keychain — never from files.

## Quick start

1. `brew install helix`
2. Copy `helix-languages.example.toml` → `~/.config/helix/languages.toml`
   (fix the `command` path to point at your checkout)
3. Copy `helix-config.example.toml` snippet → `~/.config/helix/config.toml`
4. `security add-generic-password -a "$USER" -s "OPENROUTER_API_KEY" -w "sk-or-..."`
5. `hx test-hermes.yaml`, `:w`, watch `ogg` light up red.

Offline fallback: `./start-llama-8222.sh` (reuses model files in place,
zero extra disk), `RFR_BACKEND=local`.

## Files

| file | what |
|---|---|
| `red-factor-retract` | the LSP (executable Python, stdlib only) |
| `providers.json` | curated provider constraints (xai/elevenlabs/openai) |
| `helix-languages.example.toml` | Helix LSP wiring |
| `helix-config.example.toml` | backtick depth-toggle keymap |
| `test-hermes.yaml` | Hermes TTS fixture (xai + ogg conflict) |
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
