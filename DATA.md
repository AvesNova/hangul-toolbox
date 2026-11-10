# Data sources

What ships in `data/`, where it came from, and what deliberately doesn't.

| File | What it is | Source / status |
|---|---|---|
| `topik_words.csv` | ~6,000 TOPIK vocabulary words with part of speech, gloss and level (A/B/C) | The public TOPIK vocabulary list. **TODO: confirm and record the exact upstream source.** |
| `yonsei_words.csv` | Word + textbook-volume tag (`1-1.csv` … `3-2.csv`) | Headwords from the index of the Yonsei Korean textbook series, lemmatised by `hanbox vocab yonsei`. Words only; no book text. |
| `yonsei_word_fixes.csv` | Manual lemma corrections (`바람이` → `바람`) | Hand-written. |
| `master_words.csv` | The merged master list: Kimchi rank + TOPIK level + Yonsei volume, plus an English gloss and two example phrases per word | A snapshot: produced by `hanbox vocab merge`, then enriched with an LLM and hand-edited. The glosses and phrases are LLM-generated. |

## Not included (on purpose)

- **Scans or text of the Yonsei books** — copyrighted. Only the derived word list above is shipped.
- **Kimchi Reader frequency data** — `hanbox vocab merge` expects it at
  `data/external/kimchi_words.csv` (`Rank|Word`). Produce it yourself with
  `hanbox freq scrape` (see the site's terms first) or supply any frequency list.
- **The National Institute of Korean Language Basic Dictionary dump** — large
  (>1 GB) and downloadable from the publisher. No code in this repo reads it.
- **Audio, generated decks, API keys** — regenerate with `hanbox anki`.
