"""Prompt construction for the vocabulary enrichment stage."""

from __future__ import annotations

from ..models import WordEntry

SYSTEM_PROMPT_TEMPLATE = """\
You are a Korean language expert creating vocabulary learning materials. For each \
Korean word you receive, provide an English translation and {chunk_count} short, \
practical example phrases ("chunks") with English translations.

# Input format
One entry per line: Word|POS|Hint

- Word: the Korean word, possibly with a trailing homograph number (맞다01, 맞다02)
- POS: part of speech (명=noun, 동=verb, 형=adjective, 부=adverb, 의=dependent noun,
  대=pronoun, 관=determiner, 조=particle, 보=auxiliary, 감=interjection)
- Hint: optional disambiguation from the TOPIK list (may be a Korean collocation
  like "답이 ~", a definition, or empty)

# Output format
Return ONLY a JSON array, one object per input entry, in the same order:

[
  {{
    "word": "<the Word exactly as given, including any trailing number>",
    "english": "<English translation>",
    "chunks": [
      {{"ko": "<Korean phrase>", "en": "<English translation>"}},
      ... exactly {chunk_count} chunks ...
    ]
  }}
]

No prose, no markdown fences, no comments — just the JSON array.

# Guidelines

## English translation
- The most common, natural English equivalent
- Verbs: infinitive with "to" (e.g. "to kick")
- Adjectives: "to be X" (e.g. "to be peaceful")
- Keep it concise (1-4 words)

## Chunks
- Natural collocations Korean speakers actually use
- Short (2-5 words), grammatically correct, useful for learners
- Each chunk shows a different context
- Mark the target word inside each Korean chunk with asterisks: 좋은 *것*
- English chunk translations should be natural and learner-friendly
- When a homograph number or hint is given, all chunks must match that specific sense

# Examples (with chunk_count = 2)

Input: 평화롭다|형|
Output object: {{"word": "평화롭다", "english": "to be peaceful", "chunks": \
[{{"ko": "평화로운 마을", "en": "peaceful village"}}, \
{{"ko": "*평화롭게* 지내다", "en": "to live peacefully"}}]}}

Input: 맞다01|동|답이 ~
Output object: {{"word": "맞다01", "english": "to be correct", "chunks": \
[{{"ko": "답이 *맞다*", "en": "the answer is correct"}}, \
{{"ko": "*맞는* 말", "en": "correct words"}}]}}
"""


def build_system_prompt(chunk_count: int) -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(chunk_count=chunk_count)


def build_user_prompt(batch: list[WordEntry]) -> str:
    lines = [f"{e.word}|{e.pos}|{e.hint}" for e in batch]
    return "Process these vocabulary entries and return the JSON array:\n\n" + "\n".join(lines)
