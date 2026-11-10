from pathlib import Path

from hanbox.anki.config import DEFAULTS, load_config_file, resolve

SAMPLE_TOML = """\
[pipeline]
levels = ["A", "B"]
limit = 100

[llm]
provider = "openai"
model = "qwen3:32b"
base_url = "http://localhost:11434/v1"

[tts]
voices = ["alloy", "nova"]

[export]
deck_name = "My Deck"

[unknown_section]
foo = 1
"""


def _write(tmp_path: Path) -> Path:
    path = tmp_path / "hanbox.toml"
    path.write_text(SAMPLE_TOML, encoding="utf-8")
    return path


def test_load_config_file_flattens_and_normalizes(tmp_path):
    cfg = load_config_file(_write(tmp_path))
    assert cfg["llm_provider"] == "openai"
    assert cfg["llm_model"] == "qwen3:32b"
    assert cfg["llm_base_url"] == "http://localhost:11434/v1"
    assert cfg["levels"] == "A,B"  # TOML list -> comma string
    assert cfg["voices"] == "alloy,nova"
    assert cfg["deck_name"] == "My Deck"
    assert "foo" not in cfg  # unknown keys ignored, not fatal


def test_load_missing_config_file_is_empty(tmp_path):
    assert load_config_file(tmp_path / "nope.toml") == {}


def test_resolve_precedence_cli_over_file_over_default(tmp_path):
    file_cfg = load_config_file(_write(tmp_path))
    cli = {k: None for k in DEFAULTS}
    cli["llm_model"] = "claude-sonnet-5-5"  # explicit flag

    settings = resolve(cli, file_cfg)
    assert settings["llm_model"] == "claude-sonnet-5-5"  # CLI wins
    assert settings["llm_provider"] == "openai"  # file wins over default
    assert settings["batch_size"] == DEFAULTS["batch_size"]  # default survives
    assert settings["limit"] == 100


def test_resolve_coerces_types():
    settings = resolve({"input": "other.csv"}, {})
    assert isinstance(settings["input"], Path)
    assert isinstance(settings["output_dir"], Path)


def test_resolve_zero_limit_means_no_limit():
    assert resolve({}, {"limit": 0})["limit"] is None
