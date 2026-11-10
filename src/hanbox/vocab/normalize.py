"""Homograph-number normalisation shared by the vocabulary lists.

The TOPIK list numbers homographs (`하다01`, `수2`). Kimchi and Yonsei lists
mostly don't. TOPIK's numbering is treated as the source of truth: an
unnumbered word in another list maps to the *lowest* number TOPIK uses for
that base form.
"""

from __future__ import annotations

import re
from collections import defaultdict

_NUMBERED = re.compile(r"^(.*?)(\d+)$")


def parse_word_number(word: str) -> tuple[str, int | None]:
    """Split a word into (base, homograph number).

    >>> parse_word_number("하다")
    ('하다', None)
    >>> parse_word_number("하다01")
    ('하다', 1)
    """
    m = _NUMBERED.match(word)
    if not m:
        return word, None
    base, digits = m.groups()
    num = int(digits)
    if num == 0:
        return word, None
    return base, num


def topik_numbering(topik_words: list[str]) -> dict[str, set[int]]:
    """Collect the homograph numbers TOPIK uses for each base form."""
    base_to_nums: dict[str, set[int]] = defaultdict(set)
    for word in topik_words:
        base, num = parse_word_number(word)
        if num is not None:
            base_to_nums[base].add(num)
    return base_to_nums


def build_normalization_map(topik_words: list[str], other_words: list[str]) -> dict[str, str]:
    """Map every raw word (TOPIK and others) to its normalised form."""
    base_to_nums = topik_numbering(topik_words)
    mapping: dict[str, str] = {}

    for word in topik_words:
        base, num = parse_word_number(word)
        if base in base_to_nums:
            mapping[word] = f"{base}{num if num is not None else min(base_to_nums[base])}"
        else:
            mapping[word] = word

    for word in other_words:
        if word in mapping:
            continue
        base, num = parse_word_number(word)
        if base in base_to_nums:
            mapping[word] = f"{base}{num or min(base_to_nums[base])}"
        else:
            mapping[word] = word
    return mapping
