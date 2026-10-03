"""Profile-backed, single-instrument factual research export."""

import argparse
from datetime import datetime, timedelta
from pathlib import Path
import re
import sys

from investment_terminal.cli.instrument_research_export import main as export_main
from investment_terminal.cli.weekly_run import _profile


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--projection", required=True, type=Path)
    parser.add_argument("--projection-sha256", required=True)
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--history-start", required=True)
    parser.add_argument("--end", required=True)
    parser.add_argument("--private-output", required=True, type=Path)
    parser.add_argument("--report-output", required=True, type=Path)
    options = parser.parse_args(argv)
    try:
        profile, paths = _profile(options.profile)
        end = datetime.fromisoformat(options.end)
        if (end.utcoffset() != timedelta(0)
                or end.hour != 0 or end.minute != 0
                or end.second != 0 or end.microsecond != 0):
            raise ValueError("End must be UTC midnight")
        if re.fullmatch(r"[0-9a-f]{64}", options.projection_sha256) is None:
            raise ValueError("Projection checksum is invalid")
        projection = options.projection.resolve()
        private = options.private_output.resolve()
        report = options.report_output.resolve()
        if (not options.projection.is_absolute()
                or not options.private_output.is_absolute()
                or not options.report_output.is_absolute()
                or not projection.is_file()
                or private.parent != projection.parent
                or report.parent != paths["report_directory"]
                or projection.is_relative_to(paths["report_directory"])):
            raise ValueError("Private and report paths are invalid")
        checkpoint = (paths["weekly_checkpoint_directory"]
                      / f"weekly_candle_refresh_{end.date().isoformat()}.json")
        result = export_main([
            "--manifest", str(paths["manifest"]),
            "--manifest-checksum", profile["manifest_checksum"],
            "--source-checkpoint-directory", str(paths["source_checkpoint_directory"]),
            "--weekly-checkpoint", str(checkpoint),
            "--projection", str(projection),
            "--projection-sha256", options.projection_sha256,
            "--database", str(paths["database"]),
            "--symbol", options.symbol,
            "--history-start", options.history_start,
            "--end", options.end,
            "--private-output", str(private),
            "--report-output", str(report),
        ])
    except (Exception, SystemExit):
        print("Research run preflight failed; inspect private inputs locally",
              file=sys.stderr)
        return 1
    if report.is_file():
        print(f"SEND: {report}")
    print("DO NOT SEND: private profile, projection, export, checkpoints, database")
    return result


if __name__ == "__main__":
    raise SystemExit(main())
