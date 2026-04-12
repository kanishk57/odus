#!/usr/bin/env python3
import os
import shutil
import subprocess
import argparse
from pathlib import Path

DEMO_DIR = Path.home() / "odus_demo_git"

def run_cmd(cmd, cwd=None):
    return subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)

def setup_error():
    """Sets up a broken Git repository with a merge conflict for the demo."""
    if DEMO_DIR.exists():
        shutil.rmtree(DEMO_DIR)
    
    DEMO_DIR.mkdir()
    print(f"[Demo] Creating demo environment in {DEMO_DIR}...")

    # 1. Initialize repo
    run_cmd("git init", cwd=DEMO_DIR)
    run_cmd("git config user.email 'demo@odus.ai'", cwd=DEMO_DIR)
    run_cmd("git config user.name 'Odus Demo'", cwd=DEMO_DIR)

    # 2. Initial commit
    app_file = DEMO_DIR / "app.py"
    app_file.write_text("print('Base version')\n")
    run_cmd("git add app.py && git commit -m 'Initial commit'", cwd=DEMO_DIR)

    # 3. Branch A
    run_cmd("git checkout -b feature-a", cwd=DEMO_DIR)
    app_file.write_text("print('Feature A version')\n")
    run_cmd("git add app.py && git commit -m 'Add feature A'", cwd=DEMO_DIR)

    # 4. Branch B (from main)
    run_cmd("git checkout main", cwd=DEMO_DIR)
    run_cmd("git checkout -b feature-b", cwd=DEMO_DIR)
    app_file.write_text("print('Feature B version')\n")
    run_cmd("git add app.py && git commit -m 'Add feature B'", cwd=DEMO_DIR)

    # 5. Trigger conflict
    print("[Demo] Triggering a merge conflict...")
    run_cmd("git merge feature-a", cwd=DEMO_DIR)

    print("\n" + "="*60)
    print("DEMO READY: MOCK ERROR STATE CREATED")
    print("="*60)
    print(f"Directory: {DEMO_DIR}")
    print("Status: MERGE CONFLICT in app.py")
    print("\nTerminal Output for Odus to read:")
    print("-" * 20)
    result = run_cmd("git status", cwd=DEMO_DIR)
    print(result.stdout)
    print("-" * 20)
    print("\n[Action] Now open a terminal in this directory and let Odus see the conflict!")

def reset():
    """Cleans up the demo environment."""
    if DEMO_DIR.exists():
        print(f"[Demo] Cleaning up {DEMO_DIR}...")
        shutil.rmtree(DEMO_DIR)
        print("[Demo] Cleanup complete.")
    else:
        print("[Demo] Nothing to clean up.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Odus Demo Error State Generator")
    parser.add_argument("--reset", action="store_true", help="Fix the broken state and cleanup.")
    args = parser.parse_args()

    if args.reset:
        reset()
    else:
        setup_error()
