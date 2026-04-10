"""
demo/run_demo.py — CLI runner for all ARGUS demo cases.

Usage:
    python demo/run_demo.py --case pump_and_dump
    python demo/run_demo.py --case spoofing
    python demo/run_demo.py --case circular_trading
    python demo/run_demo.py --case all
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import traceback

# ── Auto-redirect to venv Python if torch_geometric is not available ──────────
def _ensure_venv():
    """Re-exec with the project's venv Python when core packages are missing."""
    try:
        import torch_geometric  # noqa: F401
        return  # already in correct env
    except ImportError:
        pass

    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    venv_python = os.path.join(root, ".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = os.path.join(root, ".venv", "bin", "python")  # Linux/macOS

    if not os.path.exists(venv_python):
        print("[ARGUS] ERROR: .venv not found. Activate it first or run:")
        print("  .venv\\Scripts\\pip install -r requirements.txt")
        sys.exit(1)

    if os.path.abspath(sys.executable) != os.path.abspath(venv_python):
        # Force UTF-8 so box-drawing chars don't crash on Windows cp1252 terminals
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        result = subprocess.run(
            [venv_python, "-W", "ignore"] + sys.argv,
            stdin=sys.stdin,
            stdout=sys.stdout,
            stderr=sys.stderr,
            env=env,
        )
        sys.exit(result.returncode)

_ensure_venv()


# ── Only reached when running inside the correct venv ─────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    parser = argparse.ArgumentParser(
        description="ARGUS Demo — Run synthetic market manipulation detection cases"
    )
    parser.add_argument(
        "--case",
        choices=["pump_and_dump", "spoofing", "circular_trading", "social_manipulation", "all"],
        required=True,
        help="Which demo case to run",
    )
    args = parser.parse_args()

    if args.case in ("pump_and_dump", "all"):
        try:
            from demo.real_cases.case_pump_dump import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in pump_and_dump:")
            traceback.print_exc()

    if args.case in ("spoofing", "all"):
        try:
            from demo.real_cases.case_spoofing import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in spoofing:")
            traceback.print_exc()

    if args.case in ("circular_trading", "all"):
        try:
            from demo.real_cases.case_circular_trading import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in circular_trading:")
            traceback.print_exc()

    if args.case in ("social_manipulation", "all"):
        try:
            from demo.real_cases.case_social_manipulation import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in social_manipulation:")
            traceback.print_exc()


if __name__ == "__main__":
    main()
