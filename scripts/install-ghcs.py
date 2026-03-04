#!/usr/bin/env python3
import os
import json
import subprocess

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(script_dir, "..", "ghc-versions.json")
    with open(json_path, 'r') as f:
        ghc_versions = json.load(f)
    for version in ghc_versions:
        subprocess.check_call(["ghcup", "install", "ghc", version])

if __name__ == "__main__":
    main()
