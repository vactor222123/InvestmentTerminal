"""Locally verify one private research export against its redacted report."""

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

from investment_terminal.operations.instrument_research_verification import (
    verify_instrument_research_export,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private-export", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--report-sha256", required=True)
    parser.add_argument("--symbol", required=True)
    options = parser.parse_args(argv)
    try:
        if re.fullmatch(r"[0-9a-f]{64}", options.report_sha256) is None:
            raise ValueError("Report checksum is invalid")
        if (not options.private_export.is_absolute()
                or not options.report.is_absolute()
                or not options.private_export.is_file()
                or not options.report.is_file()
                or options.private_export.resolve().is_relative_to(
                    options.report.parent.resolve()
                )):
            raise ValueError("Research evidence paths are invalid")
        report_bytes = options.report.read_bytes()
        if sha256(report_bytes).hexdigest() != options.report_sha256:
            raise ValueError("Report bytes changed")
        private_bytes = options.private_export.read_bytes()
        if len(report_bytes) > 1_000_000 or len(private_bytes) > 8_000_000:
            raise ValueError("Research evidence exceeds the byte bound")
        report = _strict_json(report_bytes)
        private = _strict_json(private_bytes)
        verify_instrument_research_export(
            private, report, expected_symbol=options.symbol,
        )
    except (OSError, UnicodeError, ValueError, TypeError, OverflowError):
        print("Research evidence verification failed; do not share private data",
              file=sys.stderr)
        return 1
    print("VERIFIED: private export and redacted report match the selected symbol")
    print(f"REPORT_SHA256: {options.report_sha256}")
    print(f"PRIVATE_SHA256: {sha256(private_bytes).hexdigest()}")
    print("DO NOT SEND: private export without explicit per-artifact approval")
    return 0


def _strict_json(raw):
    def reject_constant(_value):
        raise ValueError("Non-finite JSON value")

    def unique_object(pairs):
        value = {}
        for key, item in pairs:
            if key in value:
                raise ValueError("Duplicate JSON key")
            value[key] = item
        return value

    return json.loads(raw, parse_constant=reject_constant,
                      object_pairs_hook=unique_object)


if __name__ == "__main__":
    raise SystemExit(main())
