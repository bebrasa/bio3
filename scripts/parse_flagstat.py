#!/usr/bin/env python3
"""Parse samtools flagstat output and extract mapped reads percentage."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


MAPPED_PATTERN = re.compile(
    r"^\s*(\d+)\s+\+\s+\d+\s+mapped\s+\(([\d.]+)%",
    re.MULTILINE,
)


def parse_mapped_percent(flagstat_text: str) -> float:
    match = MAPPED_PATTERN.search(flagstat_text)
    if not match:
        raise ValueError("Could not find mapped reads percentage in flagstat output")
    return float(match.group(2))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Extract % mapped reads from samtools flagstat output"
    )
    parser.add_argument(
        "flagstat_file",
        type=Path,
        help="Path to samtools flagstat output file",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=90.0,
        help="Mapping quality threshold in percent (default: 90)",
    )
    args = parser.parse_args()

    text = args.flagstat_file.read_text()
    percent = parse_mapped_percent(text)
    status = "OK" if percent > args.threshold else "not OK"

    print(f"Mapped reads: {percent:.2f}%")
    print(f"Threshold: {args.threshold:.2f}%")
    print(status)

    return 0 if status == "OK" else 1


if __name__ == "__main__":
    sys.exit(main())
