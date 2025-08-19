#!/usr/bin/env python3

import subprocess
import argparse
from x22_fleet.Library.BaseLogger import BaseLogger

def main():
    parser = argparse.ArgumentParser(description="Run a sequence of pytest tests multiple times.")
    parser.add_argument(
        "--count", type=int, default=100, help="Number of times to repeat the entire test sequence (default: 10)"
    )
    parser.add_argument(
        "test_file", type=str,
        nargs='?',  # Allows the test_file to be optional
        default="x22_testing/x22_fleet/Testing/Test_Recording.py",
        help="Path to the pytest test file to run (default: Test_Recording.py)"
    )
    
    args = parser.parse_args()
    
    logger = BaseLogger(log_file_path="Runtests.log", log_to_console=True).get_logger()
    for i in range(args.count):
        print(f"Run {i + 1} of {args.count}")
        cmd = [
            "pytest",
            "-v",
            "-s",
            "--log-cli-level=INFO",
            f"--junitxml=report-{i + 1}.xml",
            f"--html=report-{i + 1}.html",
            args.test_file,
        ]
        logger.info(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd)
        if result.returncode != 0:
            logger.error(f"Test run {i + 1} failed. Stopping further execution.")
            exit(result.returncode)  # Propagate the pytest exit code

if __name__ == "__main__":
    main()
