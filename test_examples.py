#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor
import glob
import re
import subprocess
import sys

# or perhaps just ask yosys to ommit the cruft?
comment1_re = re.compile(r'^\s*\(\*.*\*\)$').match
comment2_re = re.compile(r'^\s*\/\*.*\*\/$$').match
linefilter = lambda line: not comment1_re(line) and not comment2_re(line)

def linestripper(line: str):
    if "(*" in line and "*)" in line:
        return line.split("(*", 1)[0] + line.split("*)", 1)[1]
    return line


with ThreadPoolExecutor() as e:
    batches = []
    for pyscript in sorted(glob.glob("examples/*.py")):
        dgscript = pyscript[:-2] + "dg"
        batches.append((
            pyscript,
            dgscript,
            e.submit(subprocess.run, ["python",             pyscript, "generate", "-t", "v"], capture_output=True),
            e.submit(subprocess.run, ["python", "-m", "dg", dgscript, "generate", "-t", "v"], capture_output=True),
        ))

col_width = max(len(pyscript) for pyscript, *_ in batches)

for pyscript, dgscript, e1, e2 in batches:
    error = (e1.result().returncode, e1.result().returncode) != (0, 0)
    result1 = "\n".join(linestripper(line)
        for line in e1.result().stdout.decode().splitlines()
        if linefilter(line))
    result2 = "\n".join(linestripper(line)
        for line in e2.result().stdout.decode().splitlines()
        if linefilter(line))

    print((pyscript[:-2] + "{py,dg}").ljust(col_width+5), ":", not error and result1 == result2)

    if "-s" in sys.argv[1:]: continue
    for i, (line1, line2) in enumerate(zip(*map(str.splitlines, [result1, result2]))):
        if line1 != line2:
            print("\t", str(i).rjust(3),"-", line1)
            print("\t", str(i).rjust(3),"+", line2)
