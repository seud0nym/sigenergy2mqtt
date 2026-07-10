#!/usr/bin/env python3
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

min_version = (3, 11)  # SNYK CODE CWE-611 :  XXE and DDOS vulnerabilities in xml.etree.ElementTree.parse mitigated by ensuring min Python 3.11
if sys.version_info < min_version:
    raise Exception(f"Python {min_version[0]}.{min_version[1]} or higher is required!")

# 1. Define the coverage file destination
coverage_file = "coverage.xml"

# 2. Run pytest to generate the coverage.xml file
print("Running pytest and generating coverage report...")
try:
    # Adjust "--cov=." to a specific directory (e.g., "--cov=src") if needed.
    # check=False allows the script to continue even if some tests fail,
    # as long as the coverage file is still generated.
    subprocess.run(["pytest", "-n", "auto", "--cov=sigenergy2mqtt", f"--cov-report=xml:{coverage_file}"], check=False)
except FileNotFoundError:
    print("Error: 'pytest' is not installed or not found in your PATH.", file=sys.stderr)
    sys.exit(1)

# 3. Ensure the coverage file actually exists before parsing
if not os.path.exists(coverage_file):
    print(f"Error: Coverage file '{coverage_file}' was not found. Did pytest run successfully?", file=sys.stderr)
    sys.exit(1)

# 4. Parse and analyze the coverage file
print("Analysing coverage results...")
tree = ET.parse(coverage_file)  # SNYK CODE CWE-611: Mitigated because script execution is limited to Python 3.11+
root = tree.getroot()

files = []
for cls in root.findall(".//class"):
    name = cls.get("filename")
    line_rate = float(cls.get("line-rate", 0))
    lines = cls.findall("lines/line")
    total = len(lines)
    covered = sum(1 for line in lines if int(line.get("hits", 0)) > 0)
    missing = total - covered
    missing_lines = [line.get("number") for line in lines if int(line.get("hits", 0)) == 0]
    files.append((line_rate, name, total, covered, missing, missing_lines))

files.sort(key=lambda x: (x[0], -x[4]))

print(f"\n{'File':<60} {'Rate':>6} {'Total':>6} {'Missing':>8}")
print("-" * 85)
for rate, name, total, covered, missing, missing_lines in files:
    if rate < 1.0:
        print(f"{name:<60} {rate:>6.1%} {total:>6} {missing:>8}  lines: {','.join(missing_lines[:20])}")
