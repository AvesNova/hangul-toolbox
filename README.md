# hangul-toolbox

[![CI](https://github.com/AvesNova/hangul-toolbox/actions/workflows/ci.yml/badge.svg)](https://github.com/AvesNova/hangul-toolbox/actions/workflows/ci.yml)

A command-line toolbox (`hanbox`) for building Korean vocabulary data: merging
word lists from different sources, scraping frequency rankings, finding
look-alike words, and generating Anki decks with LLM-written example phrases
and text-to-speech audio.

```console
$ hanbox --help
  anki      TOPIK word list -> LLM example phrases -> TTS audio -> Anki deck
  vocab     Merge word lists (Kimchi/TOPIK/Yonsei) and clean Yonsei index files
  freq      Scrape a frequency list and attach ranks to vocab files
  similar   Find word pairs that differ by a single jamo (e.g. 소년/소녀)
```

## Install

Requires Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/AvesNova/hangul-toolbox && cd hangul-toolbox
uv sync                  # core
uv sync --extra scrape   # + Selenium, for `hanbox freq scrape`
uv sync --extra qwen     # + local Qwen3-TTS (CUDA GPU), for `hanbox anki`
uv run hanbox --help
```

## Tools

### `hanbox anki` — TOPIK words → Anki deck

An LLM writes a translation and example phrases for each word, a TTS engine
voices them, and the result is exported as a ready-to-import `.apkg`. Every
stage is resumable (checkpointed enrichment, content-addressed audio) and the
LLM and TTS backends are pluggable (Anthropic, any OpenAI-compatible endpoint,
local Qwen3-TTS). Full guide: [docs/anki.md](docs/anki.md).

```bash
hanbox anki run --limit 10
```

### `hanbox vocab` — merge and clean word lists

`merge` interleaves a frequency list (Kimchi), the TOPIK list and the Yonsei
textbook list into one master list, unifying homograph numbering (`하다01`,
`하다1`, `하다`) using TOPIK as the source of truth. `yonsei` cleans OCR'd
textbook index files into a lemma list (noise filtering, manual lemma fixes,
suspected non-lemma report).

```bash
hanbox vocab merge --output output/master_words.csv
hanbox vocab yonsei --raw-dir path/to/raw
```

### `hanbox similar` — minimal-pair finder

Finds words that differ by exactly one jamo in one syllable (소년/소녀,
자라다/바라다), ranked so pairs of common words come first. Optionally restricts to
the words in your own Anki deck. Words are bucketed by "word with one
position wildcarded", so the search is O(n·L) rather than comparing every pair.

```bash
hanbox similar --known output/topik_anki.tsv
```

### `hanbox freq` — frequency ranks

`scrape` collects a ranked word list with per-meaning details via Selenium;
`add` attaches a `Frequency` column to any vocab CSV.

```bash
hanbox freq scrape --pages 5 --delay 1.0
hanbox freq add my_vocab.csv --ranks data/external/frequency_scrape.csv --word-column Korean
```

## Data

See [DATA.md](DATA.md) for what ships in `data/`, where it came from, and what
is intentionally left out.

## Development

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check .
```

```
src/hanbox/
├── cli.py        # top-level `hanbox`; each tool registers its own subcommand group
├── anki/         # enrich → audio → export pipeline (+ llm/ and tts/ backends)
├── vocab/        # normalize.py, merge.py, yonsei.py
├── freq/         # rank.py, scrape.py
└── similar/      # pairs.py
```

## History

This project grew out of personal Korean-study scripts written from November
2025 onward: a frequency-list scraper, TOPIK and textbook word-list cleaning,
and a TOPIK-to-Anki pipeline. In November 2026 they were consolidated into this
single package with one `hanbox` CLI and tests. The earlier work lived in a
scratch repository with unstructured history, so this repository starts fresh
from the consolidated code.

## AI assistance

This project was built with the assistance of AI tools.

## License

MIT
