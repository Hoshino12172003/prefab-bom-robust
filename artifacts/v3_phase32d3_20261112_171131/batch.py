"""Execute and retain output of independent fixed-policy experiment jobs."""

import argparse
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def job(spec):
    runner, mode, policy = spec.split(":")
    command = [sys.executable, "-B", str(HERE / f"{runner}.py"), mode, policy]
    path = HERE / f"{runner}_{mode}_{policy}.txt"
    with path.open("w", encoding="utf-8") as stream:
        code = subprocess.run(command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT).returncode
    path.with_suffix(".exit").write_text(str(code)+"\n", encoding="utf-8")
    print(spec, "exit", code, flush=True)
    return code


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("jobs", nargs="+")
    args = parser.parse_args()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        codes = list(pool.map(job, args.jobs))
    sys.exit(int(any(codes)))
