"""
Failure-path tests for atomic analysis export persistence.
"""

from pathlib import Path

import pytest

from investment_terminal.exporters.analysis_exporter import (
    AnalysisExporter,
)
from tests.test_analysis_exporter import (
    create_package,
)


def test_save_json_preserves_existing_file_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "analysis.json"
    original = '{"state":"previous"}'
    output_path.write_text(
        original,
        encoding="utf-8",
    )

    def fail_replace(
        source: object,
        destination: object,
    ) -> None:
        raise OSError(
            "replace failed"
        )

    monkeypatch.setattr(
        "investment_terminal.utils.atomic_write.os.replace",
        fail_replace,
    )

    with pytest.raises(
        OSError,
        match="replace failed",
    ):
        AnalysisExporter().save_json(
            package=create_package(),
            output_path=output_path,
        )

    assert output_path.read_text(
        encoding="utf-8"
    ) == original
    assert list(
        tmp_path.glob(
            ".analysis.json.*.tmp"
        )
    ) == []
