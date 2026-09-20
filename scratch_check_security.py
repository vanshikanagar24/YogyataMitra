import os
import re

ROOT = r"D:\YogyataMitra\backend\app"
raw_sql_findings = []

for dirpath, _, filenames in os.walk(ROOT):
    for f in filenames:
        if f.endswith(".py"):
            p = os.path.join(dirpath, f)
            with open(p, "r", encoding="utf-8") as file:
                lines = file.readlines()
                for i, line in enumerate(lines, 1):
                    if "execute(" in line:
                        if 'f"' in line or "f'" in line or "%" in line or ".format(" in line:
                            raw_sql_findings.append((p, i, line.strip()))

print(f"Raw SQL string interpolation findings: {len(raw_sql_findings)}")
for p, i, l in raw_sql_findings:
    print(f"  {p}:{i} -> {l}")
