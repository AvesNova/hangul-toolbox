"""Configuration: built-in defaults, optional TOML config file, resolution.

Setting precedence (highest wins):

    CLI flags  >  config file (hanbox.toml)  >  environment  >  defaults

Credentials are environment-only (a local `.env` is loaded automatically and
gitignored) — they never appear in the config file or on the command line.
The environment layer covers the standard variables only: ANTHROPIC_API_KEY,
OPENAI_API_KEY and OPENAI_BASE_URL.
"""

from __future__ import annotations

import logging
import tomllib
from pathlib import Path
from typing import Any

from .tts import DEFAULT_VOICES

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_FILE = Path("hanbox.toml")

DEFAULTS: dict[str, Any] = {
    "input": Path("data/topik_words.csv"),
    "output_dir": Path("output"),
    "levels": "",
    "limit": None,
    "chunks": 3,
    "llm_provider": "anthropic",
    "llm_model": None,
    "llm_base_url": None,
    "batch_size": 25,
    "tts_provider": "qwen",
    "tts_model": None,
    "tts_base_url": None,
    "voices": ",".join(DEFAULT_VOICES),
    "deck_name": "TOPIK Vocabulary",
}

# Maps (config file section, key) to the flat setting name used internally,
# which matches the corresponding CLI flag.
_FILE_KEYS: dict[tuple[str, str], str] = {
    ("pipeline", "input"): "input",
    ("pipeline", "output_dir"): "output_dir",
    ("pipeline", "levels"): "levels",
    ("pipeline", "limit"): "limit",
    ("pipeline", "chunks"): "chunks",
    ("llm", "provider"): "llm_provider",
    ("llm", "model"): "llm_model",
    ("llm", "base_url"): "llm_base_url",
    ("llm", "batch_size"): "batch_size",
    ("tts", "provider"): "tts_provider",
    ("tts", "model"): "tts_model",
    ("tts", "base_url"): "tts_base_url",
    ("tts", "voices"): "voices",
    ("export", "deck_name"): "deck_name",
}


def load_config_file(path: Path) -> dict[str, Any]:
    """Read a TOML config file into a flat settings dict.

    Missing file returns {}. Unknown sections/keys are warned about rather
    than rejected, so a config written for a newer version degrades gracefully.
    """
    if not path.exists():
        return {}
    data = tomllib.loads(path.read_text(encoding="utf-8"))

    flat: dict[str, Any] = {}
    for section, table in data.items():
        if not isinstance(table, dict):
            logger.warning("Config: ignoring top-level key %r.", section)
            continue
        for key, value in table.items():
            name = _FILE_KEYS.get((section, key))
            if name is None:
                logger.warning("Config: ignoring unknown key [%s] %s.", section, key)
                continue
            flat[name] = value

    # TOML-friendly list forms are normalized to the CLI's comma strings.
    for key in ("levels", "voices"):
        if isinstance(flat.get(key), list):
            flat[key] = ",".join(str(v) for v in flat[key])
    logger.info("Loaded config from %s.", path)
    return flat


def resolve(cli_args: dict[str, Any], file_config: dict[str, Any]) -> dict[str, Any]:
    """Merge the layers into the final settings dict.

    `cli_args` values of None mean "not given on the command line" and are
    skipped, letting the config file or the default show through.
    """
    settings = dict(DEFAULTS)
    settings.update({k: v for k, v in file_config.items() if k in DEFAULTS})
    settings.update({k: v for k, v in cli_args.items() if k in DEFAULTS and v is not None})
    for key in ("input", "output_dir"):
        settings[key] = Path(settings[key])
    if not settings["limit"]:  # 0 in a config file means "no limit"
        settings["limit"] = None
    return settings
