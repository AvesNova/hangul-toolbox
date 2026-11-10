# `hanbox anki` — TOPIK word list to Anki deck

A three-stage pipeline:

1. **enrich** — an LLM generates an English translation and short example
   phrases ("chunks") for every word
2. **audio** — a TTS engine synthesizes audio for every Korean chunk
3. **export** — writes a tab-separated import file, a media folder, and a
   ready-to-import `.apkg` deck

Every stage is resumable: enrichment checkpoints to `output/enriched.jsonl`
as it goes, and audio files are content-addressed so nothing is synthesized
twice. Interrupt the pipeline at any point and rerun the same command.

## Setup

```bash
uv sync                 # core pipeline (Anthropic LLM + remote TTS)
uv sync --extra qwen    # additionally: local Qwen3-TTS (needs a CUDA GPU)
```

## Configuration

Settings resolve in this order (highest wins):

```
CLI flags  >  config file (hanbox.toml)  >  environment  >  built-in defaults
```

**Credentials are environment-only** — they never go in the config file or on
the command line. Copy the template and fill in what you use; `.env` is
gitignored and loaded automatically:

```bash
cp .env.example .env
```

| Backend | Variable |
|---|---|
| Anthropic | `ANTHROPIC_API_KEY` (or an `ant auth login` profile) |
| OpenAI-compatible LLM/TTS | `OPENAI_API_KEY` (omit for local servers) |
| OpenAI-compatible endpoint | `OPENAI_BASE_URL` (e.g. `http://localhost:11434/v1`) |

**Non-secret defaults** (provider, model, voices, levels, ...) can live in a
`hanbox.toml` next to where you run the command — copy
[hanbox.example.toml](../hanbox.example.toml) to get started, or pass
`--config path/to/file.toml`.

## Usage

Full run with the defaults (Claude for phrases, local Qwen3-TTS for audio):

```bash
uv run hanbox anki run
```

Try it on 10 words first:

```bash
uv run hanbox anki run --limit 10
```

Run stages individually:

```bash
uv run hanbox anki enrich --levels A,B --batch-size 25
uv run hanbox anki audio
uv run hanbox anki export --deck-name "TOPIK A+B"
```

### Swapping providers

The LLM and TTS backends are pluggable. Anything speaking the OpenAI API
shape works — OpenAI itself, OpenRouter, Groq, Ollama, LM Studio, vLLM for
text; OpenAI TTS, Kokoro-FastAPI, openedai-speech for audio:

```bash
# Ollama for phrases, OpenAI TTS for audio
uv run hanbox anki run \
    --llm-provider openai --llm-base-url http://localhost:11434/v1 --llm-model qwen3:32b \
    --tts-provider openai --tts-model tts-1 --voices alloy,nova,echo
```

The Anthropic backend caches the system prompt, so repeated batches only pay
for the word list itself.

## Output

```
output/
├── enriched.jsonl    # checkpoint — one enriched word per line
├── media/            # topik_<hash>.wav|mp3 audio files
├── topik_anki.tsv    # tab-separated Anki import file
└── topik_anki.apkg   # double-click to import into Anki
```

### Importing

**Easiest:** open `topik_anki.apkg` in Anki. Notes carry stable GUIDs, so
re-importing an updated deck updates existing cards instead of duplicating
them.

**Manual (TSV):** copy the contents of `output/media/` into your Anki
[collection.media](https://docs.ankiweb.net/files.html) folder, then import
`topik_anki.tsv` (File → Import, fields separated by tabs). Columns:

| # | Field | Notes |
|---|---|---|
| 1 | Word_Korean | homograph suffix stripped (것01 → 것) |
| 2 | Word_English | |
| 3 | Chunks_Korean | pipe-separated; target word marked with `*asterisks*` |
| 4 | Chunks_English | pipe-separated, same count |
| 5 | Chunks_Audio | pipe-separated `[sound:...]` tags, same count |

The bundled note type ("Korean Chunk Randomizer") shows the word plus one
randomly chosen chunk on the front and reveals the translations and audio on
the back.

## Extending

To add a backend, implement the protocol in `llm/base.py` or `tts/base.py`
and register it in the package's `create_llm` / `create_tts` factory.
