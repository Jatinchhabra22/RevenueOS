#!/usr/bin/env python3
"""Print (or run) the commands that restore the seeded demo book."""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / "artifacts" / "workflows"

COMMANDS = [
    [sys.executable, str(ROOT / "scripts" / "generate_synthetic_data.py"), "--seed", "42", "--customers", "3000"],
    [sys.executable, str(ROOT / "scripts" / "train_models.py"), "--data-dir", "data/demo", "--seed", "42"],
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset the synthetic demo dataset and models")
    parser.add_argument("--execute", action="store_true", help="Run the regenerate + train commands")
    parser.add_argument(
        "--clear-workflows",
        action="store_true",
        help="Delete artifacts/workflows so EVT_000861 can be executed again under cooldown policy",
    )
    args = parser.parse_args()

    print("Demo reset commands:")
    for command in COMMANDS:
        print(" ", " ".join(command))
    print("  rm -rf artifacts/workflows   # optional; simulated runs now count toward guardrails")
    print()
    print("Then:")
    print("  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000")
    print("  cd frontend && npm run dev")
    print("  cd backend && source .venv/bin/activate && pytest")

    if args.clear_workflows or args.execute:
        if WORKFLOWS.exists():
            shutil.rmtree(WORKFLOWS)
            print(f"Cleared {WORKFLOWS}")

    if not args.execute:
        return
    for command in COMMANDS:
        subprocess.run(command, cwd=ROOT, check=True)


if __name__ == "__main__":
    main()
