import pytest

from hanbox.cli import build_parser


@pytest.mark.parametrize("group", ["anki", "vocab", "freq", "similar"])
def test_every_group_is_registered(group):
    with pytest.raises(SystemExit) as exc:
        build_parser().parse_args([group, "--help"])
    assert exc.value.code == 0


def test_requires_a_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])
