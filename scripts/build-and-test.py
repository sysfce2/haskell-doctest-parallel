#!/usr/bin/env python3
"""
Build the project with multiple GHC versions in parallel.
Each build runs in a temporary directory with a copy of the git-tracked files.
"""
import json
import subprocess
import tempfile
import shutil
import os
import sys
import threading
from pathlib import Path
from multiprocessing import Pool

# ANSI color codes
BOLD_GREEN = "\033[1;32m"
BOLD_RED = "\033[1;31m"
CYAN = "\033[36m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"
GREEN = "\033[32m"
RED = "\033[31m"
WHITE = "\033[37m"
BRIGHT_CYAN = "\033[96m"
BRIGHT_YELLOW = "\033[93m"
BRIGHT_MAGENTA = "\033[95m"
RESET = "\033[0m"

# Load GHC versions from JSON file
def load_ghc_versions():
    """Load GHC versions from ghc-versions.json."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "..", "ghc-versions.json")
    with open(json_path, 'r') as f:
        return json.load(f)

GHC_VERSIONS = load_ghc_versions()

# Colors for each GHC version prefix
GHC_COLORS = [CYAN, YELLOW, MAGENTA, BLUE, GREEN, RED, WHITE, BRIGHT_CYAN, BRIGHT_YELLOW, BRIGHT_MAGENTA]

# Steps to run for each GHC version
STEPS = [
    {
        "name": "build",
        "command": lambda ghc_version: ["cabal", "build", "all", "-w", f"ghc-{ghc_version}"],
    },
    {
        "name": "test",
        "command": lambda ghc_version: ["cabal", "run", "doctests", "-w", f"ghc-{ghc_version}", "-j8"],
    },
    {
        "name": "test",
        "command": lambda ghc_version: ["cabal", "run", "spectests", "-w", f"ghc-{ghc_version}", "-j8"],
    },
]

# Lock for thread-safe printing
print_lock = threading.Lock()


def get_git_files(repo_path):
    """Get list of files tracked by git."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_path,
        capture_output=True,
        text=True,
        check=True
    )
    return [f for f in result.stdout.strip().split('\n') if f]


def copy_repo_to_temp(repo_path, temp_dir):
    """Copy all git-tracked files to temporary directory."""
    files = get_git_files(repo_path)
    for file in files:
        src = os.path.join(repo_path, file)
        dst = os.path.join(temp_dir, file)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)


def stream_output(pipe, prefix, color):
    """Stream output from a pipe with a colored prefix."""
    for line in iter(pipe.readline, ''):
        if line:
            with print_lock:
                print(f"{color}[{prefix}]{RESET} {line}", end='', flush=True)


def build_with_ghc(ghc_version, repo_path, color):
    """Build the project with a specific GHC version."""
    prefix = f"GHC {ghc_version}"

    with tempfile.TemporaryDirectory() as temp_dir:
        # Copy repository to temp directory
        copy_repo_to_temp(repo_path, temp_dir)

        step_results = []

        # Run each step in sequence
        for step in STEPS:
            step_name = step["name"]
            command = step["command"](ghc_version)

            with print_lock:
                print(f"{color}[{prefix}]{RESET} Running {step_name}")

            # Run the step
            process = subprocess.Popen(
                command,
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Stream output
            stream_output(process.stdout, prefix, color)

            # Wait for process to complete
            returncode = process.wait()

            if returncode == 0:
                with print_lock:
                    print(f"{BOLD_GREEN}✓ {prefix}: {step_name.capitalize()} successful{RESET}")
                step_results.append(True)
            else:
                with print_lock:
                    print(f"{BOLD_RED}✗ {prefix}: {step_name.capitalize()} failed{RESET}")
                step_results.append(False)
                # Stop running further steps if one fails
                break

        # Return results: all steps must succeed for overall success
        all_success = len(step_results) == len(STEPS) and all(step_results)
        return ghc_version, step_results


def main():
    repo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")

    print(f"Building with GHC versions: {', '.join(GHC_VERSIONS)}")
    print(f"Repository: {repo_path}\n")

    # Run builds in parallel
    args = [
        (ghc_version, repo_path, GHC_COLORS[i % len(GHC_COLORS)])
        for i, ghc_version in enumerate(GHC_VERSIONS)
    ]

    with Pool() as pool:
        results = pool.starmap(build_with_ghc, args)

    # Print summary
    print("\n=== Build Summary ===")
    for ghc_version, step_results in results:
        if len(step_results) == len(STEPS) and all(step_results):
            status = f"{BOLD_GREEN}✓ ALL STEPS PASSED{RESET}"
        else:
            # Show which steps passed/failed
            step_statuses = []
            for i, step in enumerate(STEPS):
                if i < len(step_results):
                    if step_results[i]:
                        step_statuses.append(f"{BOLD_GREEN}✓ {step['name'].upper()}{RESET}")
                    else:
                        step_statuses.append(f"{BOLD_RED}✗ {step['name'].upper()}{RESET}")
                else:
                    step_statuses.append(f"{YELLOW}○ {step['name'].upper()} (skipped){RESET}")
            status = " ".join(step_statuses)
        print(f"GHC {ghc_version}: {status}")


if __name__ == "__main__":
    main()
