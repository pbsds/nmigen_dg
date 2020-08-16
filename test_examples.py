#!/usr/bin/env python3
from concurrent.futures import ThreadPoolExecutor
import glob
import re
import subprocess
import sys

# Compare generated designs after stripping comments

def strip_src_verilog(source):
    comment1_re = re.compile(r'^\s*\(\*.*\*\)$').match
    comment2_re = re.compile(r'^\s*\/\*.*\*\/$$').match
    linefilter = lambda line: not comment1_re(line) and not comment2_re(line)

    def linestripper(line: str):
        if "(*" in line and "*)" in line:
            return line.split("(*", 1)[0] + line.split("*)", 1)[1]
        return line

    return "\n".join(
        linestripper(line)
        for line in source.splitlines()
        if linefilter(line)
    )

def strip_src_ilang(source):
    return "\n".join(
        line
        for line in source.splitlines()
        if not line.strip().startswith("attribute \\src ")
    )

def main():
    batches = []
    with ThreadPoolExecutor() as e:
        for pyscript in sorted(glob.glob("examples/*.py")):
            dgscript = pyscript[:-2] + "dg"
            batches.append((
                pyscript,
                dgscript,
                e.submit(subprocess.run, ["python",             pyscript, "generate", "-t", "il"], capture_output=True),
                e.submit(subprocess.run, ["python", "-m", "dg", dgscript, "generate", "-t", "il"], capture_output=True),
            ))

    col_width = max(len(pyscript) for pyscript, *_ in batches)

    for pyscript, dgscript, e1, e2 in batches:
        res1, res2 = e1.result(), e2.result()
        error = (res1.returncode, res1.returncode) != (0, 0)
        ilang1 = res1.stdout.decode()
        ilang2 = res2.stdout.decode()

        name = pyscript[:-2] + "{py,dg}"

        stripped_result1 = strip_src_ilang(ilang1) # strip_src_verilog(ilang1)
        stripped_result2 = strip_src_ilang(ilang2) # strip_src_verilog(ilang2)

        n_wrong_src_attrs = sum( # assumes ilang
            "nmigen_dg/dsl.dg" in line
            for line in ilang2.splitlines()
            if line.strip().startswith("attribute \\src ")
        )

        print(
            name.ljust(col_width+5),
            ":",
            str(not error and stripped_result1 == stripped_result2).ljust(5),
            str(n_wrong_src_attrs if n_wrong_src_attrs else "-").rjust(5)
        )

        if "-s" in sys.argv[1:]: continue
        for i, (line1, line2) in enumerate(zip(*map(str.splitlines, [stripped_result1, stripped_result2]))):
            if line1 != line2:
                print("\t", str(i).rjust(3),"-", line1)
                print("\t", str(i).rjust(3),"+", line2)

if __name__ == "__main__":
    main()
