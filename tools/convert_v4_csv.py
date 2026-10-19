#!/usr/bin/env python3
"""Convert a COmanage Registry v4 Org Identity Source CSV (as used by the v4 training kit)
into the FileSource "CSV v3" format that Registry PE 5.x expects.

    python3 tools/convert_v4_csv.py IN.csv OUT.csv [--uid]

What it does
  * header: v4 model names -> v5 table names, e.g. Name.given.official -> names.given.official,
    Identifier.identifier.eppn+login -> identifiers.identifier.eppn ("+login" is not allowed in v3;
    give people login identifiers with a Pipeline flange or an Identifier Assignment instead)
  * drops the empty trailing column the v4 files carry
  * --uid adds identifiers.identifier.uid = given.family (lowercase), for Identifier/UID matching
  * checks: first column is SORID, SORIDs and uids unique, no "<" or ">" anywhere
  * writes UTF-8 without a BOM, LF line endings, minimal quoting
Only synthetic (fictional) people belong in workshop files.
"""
import csv
import re
import sys

MODEL_MAP = {
    "Name": "names",
    "Identifier": "identifiers",
    "EmailAddress": "email_addresses",
    "TelephoneNumber": "telephone_numbers",
    "Address": "addresses",
    "Url": "urls",
}


def convert_label(label: str) -> str:
    if label == "SORID":
        return label
    parts = label.split(".")
    if len(parts) != 3 or parts[0] not in MODEL_MAP:
        raise SystemExit(f"don't know how to convert header label {label!r}")
    model, field, typ = parts
    typ = typ.split("+", 1)[0]
    return f"{MODEL_MAP[model]}.{field}.{typ}"


def make_uid(given: str, family: str) -> str:
    uid = f"{given}.{family}".lower()
    return re.sub(r"[^a-z0-9.-]", "", uid)


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    add_uid = "--uid" in sys.argv[1:]
    if len(args) != 2:
        raise SystemExit(__doc__)
    src, dst = args
    with open(src, newline="", encoding="utf-8-sig") as fh:
        rows = [r for r in csv.reader(fh) if any(c.strip() for c in r)]
    header, body = rows[0], rows[1:]
    while header and header[-1] == "":
        header.pop()
    width = len(header)
    for r in body:
        extra = r[width:]
        if any(c.strip() for c in extra):
            raise SystemExit(f"row has more columns than the header: {r}")
        del r[width:]
    new_header = [convert_label(h) for h in header]
    if new_header[0] != "SORID":
        raise SystemExit("the first column must be SORID")
    if add_uid:
        gi = new_header.index("names.given.official")
        fi = new_header.index("names.family.official")
        new_header.append("identifiers.identifier.uid")
        for r in body:
            r.append(make_uid(r[gi], r[fi]))
    for col in range(len(new_header)):
        if col == 0 or new_header[col] == "identifiers.identifier.uid":
            values = [r[col] for r in body]
            dupes = {v for v in values if values.count(v) > 1}
            if dupes:
                raise SystemExit(f"duplicate {new_header[col]} values: {sorted(dupes)}")
    for r in [new_header] + body:
        if any("<" in c or ">" in c for c in r):
            raise SystemExit(f"'<' or '>' is not allowed: {r}")
    with open(dst, "w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(new_header)
        writer.writerows(body)
    print(f"{dst}: {len(body)} rows, columns: {', '.join(new_header)}")


if __name__ == "__main__":
    main()
