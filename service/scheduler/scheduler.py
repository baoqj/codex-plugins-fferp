from __future__ import annotations

import argparse
import time

from scripts.common.logging import append_jsonl


def run_daily_jobs() -> None:
    append_jsonl(
        "action_log.jsonl",
        {
            "actor": "fferp-scheduler",
            "action": "daily_jobs_placeholder",
            "note": "Wire report generation, payment imports, and receivables checks here.",
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run scheduled FFERP background jobs.")
    parser.add_argument("--loop", action="store_true")
    parser.add_argument("--interval", type=float, default=86400)
    args = parser.parse_args()
    while True:
        run_daily_jobs()
        if not args.loop:
            break
        time.sleep(args.interval)
