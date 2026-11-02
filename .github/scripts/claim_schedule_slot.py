"""Keep GitHub's hourly schedule as a retry path without producing hourly batches."""

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path


STATE_PATH = Path("workflow_schedule_state.json")
MIN_PRODUCTION_GAP = timedelta(hours=2)


def write_output(should_run: bool, reason: str, pairs_to_run: int) -> None:
    output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as output_file:
            output_file.write(f"should_run={'true' if should_run else 'false'}\n")
            output_file.write(f"reason={reason}\n")
            output_file.write(f"pairs_to_run={pairs_to_run}\n")


def read_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def main() -> int:
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    now = datetime.now(timezone.utc)
    state = read_state()
    pairs_to_run = 2
    previous_status = str(state.get("last_run_status", "")).lower()
    if previous_status in {"partial", "failure", "running"}:
        try:
            remaining_videos = max(1, min(4, int(state.get("target_unfilled_videos", 4))))
            pairs_to_run = max(1, min(2, (remaining_videos + 1) // 2))
        except (TypeError, ValueError):
            pairs_to_run = 2
    else:
        state["target_unfilled_videos"] = 4

    if event_name == "schedule":
        previous_status = str(state.get("last_run_status", "")).lower()
        previous_start = str(state.get("last_started_at_utc", "")).strip()
        if previous_status in {"running", "success"} and previous_start:
            try:
                previous_dt = datetime.fromisoformat(previous_start.replace("Z", "+00:00"))
                if previous_dt.tzinfo is None:
                    previous_dt = previous_dt.replace(tzinfo=timezone.utc)
                elapsed = now - previous_dt.astimezone(timezone.utc)
                if elapsed < MIN_PRODUCTION_GAP:
                    minutes_left = max(0, int((MIN_PRODUCTION_GAP - elapsed).total_seconds() // 60))
                    reason = f"last production slot is {previous_status}; {minutes_left} minutes remain"
                    write_output(False, reason, pairs_to_run)
                    print(f"Scheduled safety tick skipped: {reason}.", flush=True)
                    return 0
            except (TypeError, ValueError):
                print("Production slot timestamp was invalid; allowing this run to recover.", flush=True)

    state["last_started_at_utc"] = now.isoformat()
    state["last_run_status"] = "running"
    state["last_run_id"] = run_id
    state["last_event"] = event_name
    STATE_PATH.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    write_output(True, "production slot claimed", pairs_to_run)
    print(f"Production slot claimed for run {run_id} at {now.isoformat()}.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
