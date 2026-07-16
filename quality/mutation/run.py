"""Dependency-free mutation smoke test for critical reservation/checkout branches."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

MUTATIONS = [
    (
        "accept_duplicate_seats",
        "reservation.py",
        "if not seat_ids or len(set(seat_ids)) != len(seat_ids):",
        "if not seat_ids and len(set(seat_ids)) != len(seat_ids):",
    ),
    (
        "remove_active_seat_uniqueness",
        "reservation.py",
        "CREATE UNIQUE INDEX IF NOT EXISTS one_active_owner_per_event_seat",
        "CREATE INDEX IF NOT EXISTS one_active_owner_per_event_seat",
    ),
    (
        "allow_confirmation_at_expiry",
        "reservation.py",
        'datetime.fromisoformat(row["expires_at"]) <= current',
        'datetime.fromisoformat(row["expires_at"]) < current',
    ),
    (
        "invert_payment_success",
        "checkout.py",
        "if attempt.status is PaymentResult.SUCCEEDED:",
        "if attempt.status is PaymentResult.FAILED:",
    ),
    (
        "skip_payment_failure_compensation",
        "checkout.py",
        "elif attempt.status is PaymentResult.FAILED:",
        "elif False:",
    ),
    (
        "disable_ticket_deduplication",
        "checkout.py",
        "if reservation_id in self.tickets:",
        "if False:",
    ),
]


def run_tests(source: Path) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(source)
    return subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests")],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )


def main() -> int:
    results = []
    with tempfile.TemporaryDirectory() as temporary:
        work = Path(temporary)
        for name, filename, original, replacement in MUTATIONS:
            shutil.rmtree(work / "src", ignore_errors=True)
            shutil.copytree(ROOT / "src", work / "src")
            target = work / "src" / "ticketplus" / filename
            content = target.read_text()
            if content.count(original) != 1:
                raise RuntimeError(f"mutation target changed for {name}")
            target.write_text(content.replace(original, replacement))
            completed = run_tests(work / "src")
            killed = completed.returncode != 0
            results.append({"mutation": name, "killed": killed})
            print(f"{'KILLED' if killed else 'SURVIVED'}: {name}")

    killed_count = sum(result["killed"] for result in results)
    score = round(100 * killed_count / len(results), 2)
    report = {"mutations": results, "killed": killed_count, "total": len(results), "score": score}
    report_path = ROOT / "reports" / "mutation"
    report_path.mkdir(parents=True, exist_ok=True)
    (report_path / "summary.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"Mutation score: {score}% ({killed_count}/{len(results)})")
    return 0 if killed_count == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())

