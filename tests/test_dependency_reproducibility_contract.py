from pathlib import Path
import re


PROJECT_ROOT = Path(__file__).resolve().parents[1]

REQUIREMENT_NAME = re.compile(
    r"^([A-Za-z0-9_.-]+)(?:\[[^\]]+\])?"
)


def _direct_requirement_names(
    path: Path,
) -> set[str]:
    names: set[str] = set()

    for raw_line in path.read_text(
        encoding="utf-8"
    ).splitlines():
        line = raw_line.strip()
        if (
            not line
            or line.startswith("#")
            or line.startswith("-r ")
        ):
            continue

        match = REQUIREMENT_NAME.match(
            line
        )
        if match is None:
            raise AssertionError(
                f"Unrecognized requirement line in {path.name}: {line}"
            )

        names.add(
            match.group(1).lower().replace(
                "_",
                "-",
            )
        )

    return names


def test_python_reproducibility_baseline_is_minor_family() -> None:
    assert (
        PROJECT_ROOT / ".python-version"
    ).read_text(
        encoding="utf-8"
    ).strip() == "3.13"


def test_compiler_toolchain_is_exact_pinned() -> None:
    lines = [
        line.strip()
        for line in (
            PROJECT_ROOT / "requirements-compiler.txt"
        ).read_text(
            encoding="utf-8"
        ).splitlines()
        if line.strip()
        and not line.strip().startswith("#")
    ]

    assert lines == [
        "pip==26.1.2",
        "pip-tools==7.6.0",
    ]


def test_runtime_and_dev_sources_cover_legacy_direct_dependencies() -> None:
    legacy = _direct_requirement_names(
        PROJECT_ROOT / "requirements.txt"
    )
    runtime = _direct_requirement_names(
        PROJECT_ROOT / "requirements.in"
    )
    dev = _direct_requirement_names(
        PROJECT_ROOT / "requirements-dev.in"
    )

    assert runtime <= legacy
    assert dev <= legacy
    assert runtime | dev == legacy


def test_runtime_source_does_not_contain_test_or_formatting_tools() -> None:
    runtime = _direct_requirement_names(
        PROJECT_ROOT / "requirements.in"
    )

    assert runtime.isdisjoint(
        {
            "pytest",
            "black",
            "flake8",
            "pip-tools",
        }
    )


def test_dev_source_includes_runtime_manifest() -> None:
    text = (
        PROJECT_ROOT / "requirements-dev.in"
    ).read_text(
        encoding="utf-8"
    )

    assert "-r requirements.in" in text


def test_compile_script_requires_python_313_family_and_hashes() -> None:
    text = (
        PROJECT_ROOT
        / "scripts"
        / "compile_requirements.ps1"
    ).read_text(
        encoding="utf-8"
    )

    assert '$ExpectedPythonMajorMinor = "3.13"' in text
    assert "requirements-compiler.txt" in text
    assert text.count("--generate-hashes") == 2
    assert "requirements.lock" in text
    assert "requirements-dev.lock" in text
