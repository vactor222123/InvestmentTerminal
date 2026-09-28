"""Static guards for the user-executed private operational handoff."""

import ast
from pathlib import Path
import re


HANDOFF = (
    Path(__file__).resolve().parents[1]
    / "docs" / "PHASE_7_TEN_YEAR_SPAN_HANDOFF.md"
)


def test_powershell_block_is_ascii_and_has_exact_read_only_boundary():
    document = HANDOFF.read_text(encoding="utf-8")
    block = document.split("```powershell\n", 1)[1].split("\n```", 1)[0]
    assert block.isascii()
    assert 'git rev-parse HEAD' in block
    assert '650a85b09390da8914515b3725b391be85da8fc1' in block
    assert '--history-start "2016-09-23T00:00:00+00:00"' in block
    assert 'python -m investment_terminal.cli.weekly_stored_coverage' in block
    assert 'SEND: $Report' in block and 'DO NOT SEND: $Database' in block
    assert not re.search(r"\$\w+\.\d", block)
    assert 'weekly_candle_refresh `' not in block


def test_embedded_python_validation_has_valid_syntax_and_read_only_sqlite():
    document = HANDOFF.read_text(encoding="utf-8")
    code = document.split("$ValidationCode = @'\n", 1)[1].split("\n'@", 1)[0]
    ast.parse(code)
    assert '"?mode=ro"' in code
    assert 'PRAGMA query_only = ON' in code
    assert 'PRAGMA integrity_check' in code
