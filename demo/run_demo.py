"""
demo/run_demo.py — CLI runner for all SENTINEL demo cases.
PS-402: Detection of Digital Threats & Malicious Content

Usage:
    python demo/run_demo.py --case coordinated_botnet
    python demo/run_demo.py --case fake_news_campaign
    python demo/run_demo.py --case phishing_campaign
    python demo/run_demo.py --case platform_abuse
    python demo/run_demo.py --case all

Legacy cases (still functional):
    python demo/run_demo.py --case pump_and_dump
    python demo/run_demo.py --case spoofing
    python demo/run_demo.py --case circular_trading
    python demo/run_demo.py --case social_manipulation
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
        print("[SENTINEL] ERROR: .venv not found. Activate it first or run:")
        print("  .venv\\Scripts\\pip install -r requirements.txt")
        sys.exit(1)

    if os.path.abspath(sys.executable) != os.path.abspath(venv_python):
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
        description="SENTINEL Demo — Run PS-402 digital threat detection cases"
    )
    parser.add_argument(
        "--case",
        choices=[
            # PS-402 cases
            "coordinated_botnet", "fake_news_campaign",
            "phishing_campaign", "platform_abuse",
            # Legacy aliases (still functional)
            "pump_and_dump", "spoofing", "circular_trading", "social_manipulation",
            "all",
        ],
        required=True,
        help="Which demo case to run",
    )
    args = parser.parse_args()

    # ── PS-402 Cases ──────────────────────────────────────────────────────────

    if args.case in ("coordinated_botnet", "all"):
        try:
            from demo.real_cases.case_coordinated_botnet import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in coordinated_botnet:")
            traceback.print_exc()

    if args.case in ("fake_news_campaign", "all"):
        try:
            from demo.real_cases.case_fake_news_campaign import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in fake_news_campaign:")
            traceback.print_exc()

    if args.case in ("phishing_campaign", "all"):
        try:
            from demo.real_cases.case_phishing_campaign import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in phishing_campaign:")
            traceback.print_exc()

    if args.case in ("platform_abuse", "all"):
        try:
            from demo.real_cases.case_platform_abuse import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in platform_abuse:")
            traceback.print_exc()

    # ── Legacy Cases (backward compat) ────────────────────────────────────────

    if args.case == "pump_and_dump":
        try:
            from demo.real_cases.case_pump_dump import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in pump_and_dump:")
            traceback.print_exc()

    if args.case == "spoofing":
        try:
            from demo.real_cases.case_spoofing import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in spoofing:")
            traceback.print_exc()

    if args.case == "circular_trading":
        try:
            from demo.real_cases.case_circular_trading import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in circular_trading:")
            traceback.print_exc()

    if args.case == "social_manipulation":
        try:
            from demo.real_cases.case_social_manipulation import print_verdict
            print_verdict()
        except Exception:
            print("ERROR in social_manipulation:")
            traceback.print_exc()


if __name__ == "__main__":
    main()
