"""Data backend for the DTSC Internship Atlas dashboard.

Two modes:
  --generate-sample   write a synthetic internship_records.csv (one row per
                      internship, with noise) so the pipeline runs end to end
                      before real data exists.
  --input FILE        aggregate a real (or synthetic) CSV of internship
                      records into state_data.json, in the exact shape the
                      dashboard's recordFor() expects per state.

Example:
    python internship_backend.py --generate-sample
    python internship_backend.py --input internship_records.csv --output state_data.json

With no --input/--output, files are read from and written to this script's
folder, so it works from any working directory.
"""

import argparse
import csv
import json
import os
import random
from collections import Counter
from datetime import datetime, timezone

import pandas as pd

# Same catalog as the dashboard's FIELDS object: (company, hq_state, logo_slug, monogram)
FIELDS = {
    "tech": {
        "label": "Technology & Software",
        "roles": ["Software Engineering Intern", "Data Science Intern", "Product Management Intern", "Cloud/DevOps Intern"],
        "companies": [
            ("Google", "CA", "google", None), ("Microsoft", "WA", "microsoft", None), ("Amazon", "WA", "amazon", None),
            ("Apple", "CA", "apple", None), ("Meta", "CA", "meta", None), ("Micron Technology", "ID", None, "MU"),
            ("Adobe", "CA", "adobe", None), ("Salesforce", "CA", "salesforce", None),
            ("Dell Technologies", "TX", "dell", None), ("Qualcomm", "CA", "qualcomm", None),
        ],
    },
    "finance": {
        "label": "Finance & Business Services",
        "roles": ["Investment Banking Intern", "Financial Analyst Intern", "Business Operations Intern", "Risk Management Intern"],
        "companies": [
            ("JPMorgan Chase", "NY", "chase", None), ("Goldman Sachs", "NY", "goldmansachs", None),
            ("Morgan Stanley", "NY", None, "MS"), ("Citadel", "IL", None, "CTD"), ("CME Group", "IL", None, "CME"),
            ("H&R Block", "MO", None, "HRB"), ("Edward Jones", "MO", None, "EJ"), ("Travelers", "CT", None, "TRV"),
            ("Capital One", "VA", None, "COF"),
        ],
    },
    "health": {
        "label": "Healthcare & Life Sciences",
        "roles": ["Clinical Research Intern", "Biotech R&D Intern", "Health Informatics Intern", "Pharmaceutical Sciences Intern"],
        "companies": [
            ("Johnson & Johnson", "NJ", None, "J&J"), ("Pfizer", "NY", None, "PFE"), ("Merck", "NJ", "merck", None),
            ("Mayo Clinic", "MN", None, "MC"), ("Medtronic", "MN", None, "MDT"), ("UPMC", "PA", None, "UPMC"),
            ("Epic Systems", "WI", None, "EPIC"), ("Moderna", "MA", None, "MRNA"), ("Biogen", "MA", None, "BIIB"),
            ("CVS Health", "RI", None, "CVS"),
        ],
    },
    "eng": {
        "label": "Engineering & Manufacturing",
        "roles": ["Mechanical Engineering Intern", "Manufacturing Engineering Intern", "Industrial Design Intern", "Quality Engineering Intern"],
        "companies": [
            ("General Motors", "MI", "generalmotors", None), ("Ford Motor Company", "MI", "ford", None),
            ("Honda North America", "OH", "honda", None), ("Toyota Motor North America", "TX", "toyota", None),
            ("BMW Manufacturing", "SC", "bmw", None), ("Caterpillar", "IL", "caterpillar", None),
            ("Cummins", "IN", None, "CMI"), ("Lockheed Martin", "MD", None, "LMT"),
        ],
    },
    "market": {
        "label": "Marketing, Media & Communications",
        "roles": ["Marketing Intern", "Brand Strategy Intern", "Digital Media Intern", "Public Relations Intern"],
        "companies": [
            ("The Coca-Cola Company", "GA", "cocacola", None), ("Delta Air Lines", "GA", "delta", None),
            ("Walt Disney Company", "CA", None, "DIS"), ("Live Nation Entertainment", "CA", None, "LYV"),
            ("Sony Music Nashville", "TN", "sony", None), ("Marriott International", "MD", "marriott", None),
            ("Carnival Corporation", "FL", None, "CCL"),
        ],
    },
    "gov": {
        "label": "Government & Public Policy",
        "roles": ["Policy Analyst Intern", "Federal Program Intern", "Public Administration Intern", "Government Research Fellow"],
        "companies": [
            ("U.S. Department of Defense", "VA", None, "DOD"), ("National Institutes of Health", "MD", None, "NIH"),
            ("Los Alamos National Laboratory", "NM", None, "LANL"), ("Sandia National Laboratories", "NM", None, "SNL"),
            ("Booz Allen Hamilton", "VA", None, "BAH"), ("MITRE Corporation", "VA", None, "MITRE"),
        ],
    },
    "energy": {
        "label": "Energy, Agriculture & Environment",
        "roles": ["Environmental Science Intern", "Agricultural Research Intern", "Petroleum Engineering Intern", "Sustainability Intern"],
        "companies": [
            ("ExxonMobil", "TX", None, "XOM"), ("Chevron", "TX", None, "CVX"), ("ConocoPhillips", "TX", None, "COP"),
            ("Cargill", "MN", None, "CARG"), ("Tyson Foods", "AR", None, "TSN"), ("John Deere", "IL", "johndeere", None),
            ("Archer-Daniels-Midland", "IL", None, "ADM"), ("NextEra Energy", "FL", None, "NEE"),
        ],
    },
}

STATE_FIELD = {
    "AL": "eng", "AK": "energy", "AZ": "tech", "AR": "finance", "CA": "tech", "CO": "tech", "CT": "finance",
    "DE": "finance", "FL": "market", "GA": "market", "HI": "market", "ID": "tech", "IL": "finance", "IN": "eng",
    "IA": "energy", "KS": "energy", "KY": "eng", "LA": "energy", "ME": "energy", "MD": "gov", "MA": "health",
    "MI": "eng", "MN": "health", "MS": "energy", "MO": "finance", "MT": "energy", "NE": "energy", "NV": "market",
    "NH": "tech", "NJ": "health", "NM": "gov", "NY": "finance", "NC": "health", "ND": "energy", "OH": "eng",
    "OK": "energy", "OR": "tech", "PA": "health", "RI": "health", "SC": "eng", "SD": "energy", "TN": "market",
    "TX": "energy", "UT": "tech", "VT": "energy", "VA": "gov", "WA": "tech", "WV": "energy", "WI": "health", "WY": "energy",
}


def hash_int(s: str) -> int:
    """Port of the dashboard's JS hashInt() -- same 32-bit overflow, same output."""
    h = 0
    for ch in s:
        h = (h * 31 + ord(ch)) & 0xFFFFFFFF
    if h >= 0x80000000:
        h -= 0x100000000
    return abs(h)


def dominant_pick(abbr):
    """The exact field/role/company/undergrad-split the dashboard currently shows for a state."""
    field_key = STATE_FIELD[abbr]
    field = FIELDS[field_key]
    h = hash_int(abbr)
    role = field["roles"][h % len(field["roles"])]
    company = field["companies"][(h >> 3) % len(field["companies"])]
    h2 = hash_int(abbr + "_level")
    undergrad_pct = 30 + (h2 % 55)
    return field_key, role, company, undergrad_pct


def generate_sample_data(path, rows_per_state=300, seed=42):
    """Write synthetic per-internship rows: each state leans toward its dashboard
    field/role/company/degree-split, with noise, so aggregation has to do real work."""
    rng = random.Random(seed)
    other_fields = list(FIELDS.keys())
    fieldnames = ["state", "field", "role", "company", "company_hq", "degree_level"]

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for abbr in STATE_FIELD:
            field_key, role, company, undergrad_pct = dominant_pick(abbr)

            field_weights = [0.62 if k == field_key else 0.38 / (len(other_fields) - 1) for k in other_fields]

            for _ in range(rows_per_state):
                row_field = rng.choices(other_fields, weights=field_weights, k=1)[0]
                fld = FIELDS[row_field]

                if row_field == field_key:
                    role_weights = [0.55 if r == role else 0.45 / (len(fld["roles"]) - 1) for r in fld["roles"]]
                    row_role = rng.choices(fld["roles"], weights=role_weights, k=1)[0]
                    co_weights = [0.4 if c == company else 0.6 / (len(fld["companies"]) - 1) for c in fld["companies"]]
                    row_company = rng.choices(fld["companies"], weights=co_weights, k=1)[0]
                else:
                    row_role = rng.choice(fld["roles"])
                    row_company = rng.choice(fld["companies"])

                is_undergrad = rng.random() * 100 < undergrad_pct
                writer.writerow({
                    "state": abbr,
                    "field": row_field,
                    "role": row_role,
                    "company": row_company[0],
                    "company_hq": row_company[1],
                    "degree_level": "Undergraduate" if is_undergrad else "Graduate",
                })

    print(f"Wrote {len(STATE_FIELD) * rows_per_state} synthetic rows to {path}")


def most_common(series):
    return Counter(series).most_common(1)[0][0]


def company_lookup(field_key, company_name):
    for name, hq, logo, mono in FIELDS[field_key]["companies"]:
        if name == company_name:
            return hq, logo, mono
    return None, None, None


def aggregate(df: pd.DataFrame) -> dict:
    states = {}
    for abbr, group in df.groupby("state"):
        top_field = most_common(group["field"])
        field_rows = group[group["field"] == top_field]
        top_role = most_common(field_rows["role"])
        top_company = most_common(field_rows["company"])
        hq, logo, mono = company_lookup(top_field, top_company)

        undergrad_pct = round((group["degree_level"] == "Undergraduate").mean() * 100)
        states[abbr] = {
            "field": top_field,
            "fieldLabel": FIELDS[top_field]["label"],
            "role": top_role,
            "company": top_company,
            "companyHQ": hq,
            "inState": hq == abbr,
            "logoSlug": logo,
            "mono": mono,
            "undergradPct": undergrad_pct,
            "gradPct": 100 - undergrad_pct,
            "sampleSize": int(len(group)),
        }
    return states


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generate-sample", action="store_true", help="write a synthetic internship_records.csv and exit")
    parser.add_argument("--rows-per-state", type=int, default=300)
    parser.add_argument("--input", help="CSV of internship records (default: internship_records.csv next to this script)")
    parser.add_argument("--output", help="where to write the dashboard JSON (default: state_data.json next to this script)")
    args = parser.parse_args()

    # Resolve relative paths against the script's folder, not the shell's cwd.
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if args.input is None:
        args.input = os.path.join(script_dir, "internship_records.csv")
    if args.output is None:
        args.output = os.path.join(script_dir, "state_data.json")

    if args.generate_sample:
        generate_sample_data(args.input, rows_per_state=args.rows_per_state)
        return

    df = pd.read_csv(args.input)
    required = {"state", "field", "role", "company", "company_hq", "degree_level"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Input CSV is missing required columns: {sorted(missing)}")

    states = aggregate(df)
    missing_states = sorted(set(STATE_FIELD) - set(states))
    if missing_states:
        print(f"Warning: no records found for {len(missing_states)} state(s): {', '.join(missing_states)}")

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_rows": int(len(df)),
        "fields": {k: {"label": v["label"]} for k, v in FIELDS.items()},
        "states": states,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    print(f"Aggregated {len(df)} rows across {len(states)} states -> {args.output}")


if __name__ == "__main__":
    main()
