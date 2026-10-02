#!/bin/zsh
# Your own llama-server on :8222. Reuses OpenWhispr's model files in place — zero extra disk.
# 8221 = OpenWhispr's, 8222 = yours. 8080 left alone for your web space.
MODEL="/Users/thomaskenny/.cache/openwhispr/models/gemma-4-26B_q4_0-it.gguf"
DRAFT="/Users/thomaskenny/.cache/openwhispr/models/mtp-gemma-4-26B-A4B-it.gguf"
LOG="/Users/thomaskenny/Documents/Default Project/llama-8222.log"
exec /opt/homebrew/bin/llama-server \
  --model "$MODEL" \
  --host 127.0.0.1 --port 8222 \
  --threads 4 --ctx-size 16384 --jinja \
  --n-gpu-layers 99 \
  --model-draft "$DRAFT" --spec-type draft-mtp --spec-draft-n-max 3 >>"$LOG" 2>&1
