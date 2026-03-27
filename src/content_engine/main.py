from __future__ import annotations

import argparse
from pathlib import Path
import sys

from content_engine.config import Settings
from content_engine.security import format_findings, scan_repository


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate viral short-form video packages.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Generate one batch of videos.")
    run_parser.add_argument("--niche", default=None)
    run_parser.add_argument("--limit", type=int, default=1)
    run_parser.add_argument("--ab-hooks", type=int, default=2)

    batch_parser = subparsers.add_parser("batch", help="Generate multiple videos in one run.")
    batch_parser.add_argument("--niche", default=None)
    batch_parser.add_argument("--count", type=int, default=5)
    batch_parser.add_argument("--ab-hooks", type=int, default=2)

    schedule_parser = subparsers.add_parser("schedule", help="Run on a repeating interval.")
    schedule_parser.add_argument("--niche", default=None)
    schedule_parser.add_argument("--count", type=int, default=3)
    schedule_parser.add_argument("--interval-minutes", type=int, default=180)
    schedule_parser.add_argument("--ab-hooks", type=int, default=2)

    web_parser = subparsers.add_parser("web", help="Run the website and API.")
    web_parser.add_argument("--host", default=None)
    web_parser.add_argument("--port", type=int, default=None)

    subparsers.add_parser("security-check", help="Scan the repository for likely leaked secrets.")

    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "security-check":
        findings = scan_repository(Path.cwd())
        print(format_findings(findings))
        if findings:
            raise SystemExit(1)
        return

    if args.command == "web":
        import uvicorn
        from content_engine.web.app import create_app

        settings = Settings.from_env()
        uvicorn.run(
            create_app(settings),
            host=args.host or settings.web_host,
            port=args.port or settings.web_port,
        )
        return

    from content_engine.pipeline.orchestrator import ContentEngine

    settings = Settings.from_env()
    engine = ContentEngine(settings)
    niche = args.niche or settings.default_niche

    if args.command == "run":
        engine.run_once(niche=niche, limit=args.limit, ab_hooks=args.ab_hooks)
        return
    if args.command == "batch":
        engine.run_once(niche=niche, limit=args.count, ab_hooks=args.ab_hooks)
        return
    if args.command == "schedule":
        engine.run_schedule(
            niche=niche,
            count=args.count,
            interval_minutes=args.interval_minutes,
            ab_hooks=args.ab_hooks,
        )
        return
    raise SystemExit(f"Unsupported command: {args.command}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)
