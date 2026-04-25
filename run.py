#!/usr/bin/env python3
"""Legacy CLI entry point — kept so existing docs (`python run.py ...`)
keep working. The actual CLI logic lives in `harness/cli.py`. After
`pip install -e .`, prefer the `rp-bench` console script.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from harness.cli import main

if __name__ == "__main__":
    sys.exit(main())
