#!/usr/bin/env python3
"""Summarise Shopee MY and Amazon.ae affiliate earnings reports for one month.

Usage:
    python3 affiliate/summarize.py 2026-12
    python3 affiliate/summarize.py 2026-12 --aed-rate 1.22

Put each platform's monthly CSV export in affiliate/reports/. A file whose name
contains "shopee" is read as Shopee, one with "amazon" as Amazon.ae. Nothing is
sent anywhere and no credentials are used. Standard library only.
"""
import argparse
import csv
import glob
import io
import os
import re
import sys
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
REPORTS = os.path.join(HERE, "reports")

# Column names differ between exports and change over time, so each field is
# found by the first alias that appears (case-insensitive, substring match).
ALIASES = {
    "shopee": {
        "date": ["purchase time", "order time", "conversion time", "date"],
        "commission": ["net commission", "total order commission", "order commission",
                       "item total commission", "commission"],
        "status": ["order status", "conversion status", "status"],
        "order": ["order id", "conversion id", "checkout id"],
        "clicks": ["clicks"],
    },
    "amazon": {
        "date": ["date shipped", "date"],
        "commission": ["ad fees", "earnings", "commission"],
        "status": ["status"],
        "order": ["items shipped", "shipped items", "orders", "ordered items"],
        "clicks": ["clicks"],
    },
}
EXCLUDED = ("cancel", "unpaid", "invalid", "return", "reject", "fraud")
PENDING = ("pending", "processing", "to be")
DATE_FORMATS = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d/%m/%Y %H:%M:%S",
                "%d/%m/%Y %H:%M", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%b %d, %Y", "%d %b %Y")


def money(text):
    text = (text or "").replace(",", "")
    m = re.search(r"-?\d+(?:\.\d+)?", text)
    return float(m.group()) if m else 0.0


def month_of(text):
    text = (text or "").strip()
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m")
        except ValueError:
            pass
    m = re.match(r"(\d{4})-(\d{2})", text)
    return f"{m.group(1)}-{m.group(2)}" if m else None


def find(header, names):
    low = [h.lower().strip() for h in header]
    for name in names:
        for i, h in enumerate(low):
            if name in h:
                return i
    return None


def read_rows(path, platform):
    """Return (header, rows), skipping any title lines above the real header."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        lines = list(csv.reader(io.StringIO(f.read())))
    keys = ALIASES[platform]["commission"]
    for n, line in enumerate(lines):
        if find(line, keys) is not None and len(line) > 2:
            return line, [r for r in lines[n + 1:] if any(c.strip() for c in r)]
    raise ValueError(f"{os.path.basename(path)}: no commission column found. "
                     f"Header seen: {lines[0] if lines else 'empty file'}")


def summarise(path, platform, month):
    header, rows = read_rows(path, platform)
    a = ALIASES[platform]
    col = {k: find(header, v) for k, v in a.items()}
    if col["date"] is None:
        raise ValueError(f"{os.path.basename(path)}: no date column found. Header: {header}")
    out = {"clicks": 0, "orders": 0, "pending": 0.0, "approved": 0.0, "rows": 0}
    seen_orders = set()
    for r in rows:
        get = lambda k: r[col[k]] if col[k] is not None and col[k] < len(r) else ""
        if month_of(get("date")) != month:
            continue
        out["rows"] += 1
        status = get("status").lower()
        if any(x in status for x in EXCLUDED):
            continue
        amount = money(get("commission"))
        if any(x in status for x in PENDING):
            out["pending"] += amount
        else:
            out["approved"] += amount
        if col["clicks"] is not None:
            out["clicks"] += int(money(get("clicks")))
        if platform == "shopee":
            oid = get("order")
            if oid and oid not in seen_orders:
                seen_orders.add(oid)
                out["orders"] += 1
        else:
            out["orders"] += int(money(get("order"))) if col["order"] is not None else 1
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("month", help="month to summarise, as YYYY-MM")
    p.add_argument("--aed-rate", type=float, help="RM per 1 AED (asked for if Amazon data is found)")
    p.add_argument("--reports", default=REPORTS, help="folder holding the CSV exports")
    args = p.parse_args()
    if not re.fullmatch(r"\d{4}-\d{2}", args.month):
        sys.exit("Month must look like 2026-12")

    files = sorted(glob.glob(os.path.join(args.reports, "*.csv")))
    totals = {}
    for path in files:
        name = os.path.basename(path).lower()
        platform = "shopee" if "shopee" in name else "amazon" if "amazon" in name else None
        if not platform:
            print(f"Skipped {os.path.basename(path)}: put 'shopee' or 'amazon' in the file name.")
            continue
        try:
            s = summarise(path, platform, args.month)
        except ValueError as e:
            print(f"Skipped {e}")
            continue
        t = totals.setdefault(platform, {"clicks": 0, "orders": 0, "pending": 0.0, "approved": 0.0, "rows": 0})
        for k in t:
            t[k] += s[k]

    if not totals:
        sys.exit(f"No Shopee or Amazon CSVs with {args.month} rows found in {args.reports}")

    rate = args.aed_rate
    if "amazon" in totals and rate is None:
        rate = float(input("AED to RM rate to use (RM for 1 AED, e.g. 1.22): ").strip())

    label = datetime.strptime(args.month, "%Y-%m").strftime("%b %Y")
    print(f"\nAffiliate summary · {label}\n")
    print(f"{'Platform':<12}{'Clicks':>8}{'Orders':>8}{'Pending':>14}{'Approved':>14}")
    grand_pending = grand_approved = 0.0
    lines = []
    for platform, t in totals.items():
        fx, cur, nice = (1.0, "RM", "Shopee") if platform == "shopee" else (rate, "AED", "Amazon.ae")
        pend_rm, appr_rm = t["pending"] * fx, t["approved"] * fx
        grand_pending += pend_rm
        grand_approved += appr_rm
        clicks = str(t["clicks"]) if t["clicks"] else "-"
        print(f"{nice:<12}{clicks:>8}{t['orders']:>8}{'RM %.2f' % pend_rm:>14}{'RM %.2f' % appr_rm:>14}")
        if cur == "AED":
            print(f"{'':<28}(AED {t['pending']:.2f} pending, AED {t['approved']:.2f} approved at {rate} RM/AED)")
        if appr_rm:
            lines.append(f"{nice} commission {label} · RM {appr_rm:.2f} · Status: Expected")
    print(f"{'Total':<28}{'RM %.2f' % grand_pending:>14}{'RM %.2f' % grand_approved:>14}")
    print("\nLog in the ORIRI 10k Tracker (source: Affiliate (Shopee, Amazon)):")
    for line in lines or ["Nothing approved yet this month."]:
        print("  " + line)
    print("When the payout reaches your bank, mark that entry Received.")


if __name__ == "__main__":
    main()
