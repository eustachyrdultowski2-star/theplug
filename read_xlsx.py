#!/usr/bin/env python3
"""Minimal .xlsx reader (stdlib only) — xlsx is just a zip of XML."""
import zipfile, re, sys, json
from xml.etree import ElementTree as ET

NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def col_index(ref):
    letters = re.match(r"([A-Z]+)", ref).group(1)
    n = 0
    for ch in letters:
        n = n * 26 + (ord(ch) - 64)
    return n - 1


def read(path):
    z = zipfile.ZipFile(path)

    shared = []
    if "xl/sharedStrings.xml" in z.namelist():
        root = ET.fromstring(z.read("xl/sharedStrings.xml"))
        for si in root.findall(f"{NS}si"):
            shared.append("".join(t.text or "" for t in si.iter(f"{NS}t")))

    # map sheet name -> file
    wb = ET.fromstring(z.read("xl/workbook.xml"))
    names = [s.get("name") for s in wb.iter(f"{NS}sheet")]

    sheets = {}
    sheet_files = sorted(n for n in z.namelist() if re.match(r"xl/worksheets/sheet\d+\.xml$", n))
    for i, sf in enumerate(sheet_files):
        root = ET.fromstring(z.read(sf))
        rows = []
        for row in root.iter(f"{NS}row"):
            cells = {}
            for c in row.findall(f"{NS}c"):
                ref, ctype = c.get("r"), c.get("t")
                v = c.find(f"{NS}v")
                isel = c.find(f"{NS}is")
                if ctype == "s" and v is not None:
                    val = shared[int(v.text)]
                elif isel is not None:
                    val = "".join(t.text or "" for t in isel.iter(f"{NS}t"))
                elif v is not None:
                    val = v.text
                else:
                    continue
                cells[col_index(ref)] = (val or "").strip()
            if cells:
                width = max(cells) + 1
                rows.append([cells.get(i, "") for i in range(width)])
        sheets[names[i] if i < len(names) else f"sheet{i+1}"] = rows
    return sheets


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    data = read(sys.argv[1])
    for name, rows in data.items():
        print(f"=== SHEET: {name}  ({len(rows)} rows) ===")
        for r in rows[:6]:
            print("  ", r[:8])
        print()
