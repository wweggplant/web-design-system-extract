#!/usr/bin/env python3
"""
Setup script for Design System Reverse Engineer.
Installs Playwright and required dependencies.
"""

import subprocess
import sys


def run_command(cmd, description):
    """Run a command and report status."""
    print(f"\n📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed")
        if e.stderr:
            print(e.stderr)
        return False


def main():
    print("🚀 Setting up Design System Reverse Engineer...")

    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ required")
        sys.exit(1)

    # Install playwright
    if not run_command(
        f"{sys.executable} -m pip install playwright",
        "Installing Playwright"
    ):
        sys.exit(1)

    # Install chromium browser
    if not run_command(
        f"{sys.executable} -m playwright install chromium",
        "Installing Chromium browser"
    ):
        sys.exit(1)

    print("\n✅ Setup complete! You can now run:")
    print("   python scripts/collect.py <url> --output ./artifacts")


if __name__ == "__main__":
    main()
