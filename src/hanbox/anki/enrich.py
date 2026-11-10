"""Stage 1 — enrich word entries with translations and example chunks via an LLM."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from .checkpoint import append_enriched, load_enriched
from .llm import LLMClient, LLMError
from .llm.prompts import build_system_prompt, build_user_prompt
from .models import Chunk, EnrichedWord, WordEntry

logger = logging.getLogger(__name__)

_JSON_FENCE = re.compile(r"^```(?:json)?\s*|\s*```$", re.MULTILINE)


def parse_response(
    text: str, batch: list[WordEntry], chunk_count: int
) -> tuple[list[EnrichedWord], list[WordEntry]]:
    """Match the model's JSON array back to the batch entries.

    Matching is by the echoed `word` field rather than position, so partial or
    reordered responses degrade gracefully. Duplicate words within a batch
    (homographs sharing a surface form) are assigned in order of appearance.
    Returns (successes, entries that could not be matched or were malformed).
    """
    cleaned = _JSON_FENCE.sub("", text.strip())
    start, end = cleaned.find("["), cleaned.rfind("]")
    if start == -1 or end <= start:
        logger.warning("Response contained no JSON array.")
        return [], list(batch)
    try:
        items = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse response JSON: %s", exc)
        return [], list(batch)
    if not isinstance(items, list):
        return [], list(batch)

    word_to_entries: dict[str, list[WordEntry]] = {}
    for entry in batch:
        word_to_entries.setdefault(entry.word, []).append(entry)

    successes: list[EnrichedWord] = []
    matched: set[int] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        word = str(item.get("word", "")).strip()
        english = str(item.get("english", "")).strip()
        raw_chunks = item.get("chunks", [])
        chunks = [
            Chunk(korean=str(c.get("ko", "")).strip(), english=str(c.get("en", "")).strip())
            for c in raw_chunks
            if isinstance(c, dict) and str(c.get("ko", "")).strip()
        ][:chunk_count]
        if not english or not chunks:
            logger.warning("Incomplete result for %r — will retry.", word)
            continue

        entry = next(
            (e for e in word_to_entries.get(word, []) if e.index not in matched),
            None,
        )
        if entry is None:
            logger.warning("Unmatched word in response: %r", word)
            continue
        matched.add(entry.index)
        successes.append(EnrichedWord(entry=entry, english=english, chunks=chunks))

    failed = [e for e in batch if e.index not in matched]
    return successes, failed


def _run_batch(
    llm: LLMClient,
    batch: list[WordEntry],
    system: str,
    chunk_count: int,
    retries: int = 3,
) -> tuple[list[EnrichedWord], list[WordEntry]]:
    """Call the LLM for one batch, retrying transport-level failures."""
    for attempt in range(1, retries + 1):
        try:
            response = llm.generate(system, build_user_prompt(batch))
            return parse_response(response, batch, chunk_count)
        except LLMError as exc:
            logger.warning("Attempt %d/%d failed: %s", attempt, retries, exc)
            if attempt < retries:
                time.sleep(2**attempt)
    return [], list(batch)


def enrich_words(
    llm: LLMClient,
    entries: list[WordEntry],
    checkpoint_path: Path,
    batch_size: int = 25,
    chunk_count: int = 3,
) -> dict[int, EnrichedWord]:
    """Enrich all entries, resuming from and appending to the checkpoint.

    Returns every enriched record (previously checkpointed + new).
    """
    done = load_enriched(checkpoint_path)
    pending = [e for e in entries if e.index not in done]
    logger.info("Enriching %d words (%d already checkpointed).", len(pending), len(done))
    if not pending:
        return done

    system = build_system_prompt(chunk_count)
    failed: list[WordEntry] = []

    total_batches = (len(pending) + batch_size - 1) // batch_size
    for batch_num, i in enumerate(range(0, len(pending), batch_size), start=1):
        batch = pending[i : i + batch_size]
        logger.info(
            "Batch %d/%d (%s ... %s)",
            batch_num,
            total_batches,
            batch[0].display_word,
            batch[-1].display_word,
        )
        successes, batch_failed = _run_batch(llm, batch, system, chunk_count)
        if successes:
            append_enriched(checkpoint_path, successes)
            done.update({r.entry.index: r for r in successes})
        failed.extend(batch_failed)

    # One consolidated retry pass for stragglers, in smaller batches.
    if failed:
        logger.info("Retrying %d failed entries.", len(failed))
        still_failed: list[WordEntry] = []
        retry_size = max(1, batch_size // 2)
        for i in range(0, len(failed), retry_size):
            batch = failed[i : i + retry_size]
            successes, batch_failed = _run_batch(llm, batch, system, chunk_count)
            if successes:
                append_enriched(checkpoint_path, successes)
                done.update({r.entry.index: r for r in successes})
            still_failed.extend(batch_failed)
        if still_failed:
            logger.error(
                "%d entries could not be enriched: %s",
                len(still_failed),
                ", ".join(e.word for e in still_failed[:20]),
            )

    logger.info("Enrichment complete: %d/%d words.", len(done), len(entries))
    return done
