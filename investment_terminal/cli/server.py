"""
Production server CLI entrypoint.

The current inbound rate limiter is process-local. Therefore the production CLI
intentionally permits exactly one Uvicorn worker until a shared/distributed
admission backend exists.
"""

import argparse

import uvicorn


APP_FACTORY = "investment_terminal.server.production:create_app"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the Investment Terminal grounded AI API server.",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind host. Default: 127.0.0.1",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Bind port. Default: 8000",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help=(
            "Worker process count. Must be 1 while inbound rate limiting "
            "uses process-local state."
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=(
            "critical",
            "error",
            "warning",
            "info",
            "debug",
            "trace",
        ),
        default="info",
        help="Uvicorn log level. Default: info",
    )
    return parser


def main(
    argv: list[str] | None = None,
) -> int:
    args = build_parser().parse_args(
        argv
    )

    if not 1 <= args.port <= 65535:
        raise SystemExit(
            "--port must be between 1 and 65535"
        )
    if args.workers != 1:
        raise SystemExit(
            "--workers must be 1 while inbound rate limiting "
            "uses process-local state"
        )
    if not isinstance(
        args.host,
        str,
    ) or not args.host.strip():
        raise SystemExit(
            "--host must not be empty"
        )

    uvicorn.run(
        APP_FACTORY,
        factory=True,
        host=args.host.strip(),
        port=args.port,
        workers=args.workers,
        log_level=args.log_level,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(
        main()
    )
