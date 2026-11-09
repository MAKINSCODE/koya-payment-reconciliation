#!/usr/bin/env python3
"""Payment reconciliation.

Reads payments.jsonl and works out how much money we actually collected.
Run:  python3 reconcile.py
"""
import json


def parse_amount(value):
    """Turn an amount into a number, whatever form it arrives in.

    Most amounts are plain numbers (3533.05), but some come through as text
    with thousands separators ("55,707.77"). Those are still real payments,
    so we strip the commas rather than throwing the row away.
    """
    if isinstance(value, str):
        value = value.replace(",", "").strip()
    return float(value)


# A payment can be attempted several times, and every attempt shares the same
# txn_id. Only the most recent attempt counts, so we keep one event per txn_id:
# whichever has the latest timestamp.
#
# The file isn't in time order, so we can't just take the last line we see.
# Instead we compare timestamps. They all use the same format
# ("2026-09-21T15:30:26Z"), so comparing them as text gives the right order.
latest = {}

with open("payments.jsonl", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if not line:
            continue  # blank line, nothing to read

        # The export isn't perfectly clean: some lines were cut off partway
        # through and aren't valid JSON. The README says to ignore them.
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        # Events without a txn_id can't be matched to a payment, so skip them.
        if not isinstance(event, dict) or not event.get("txn_id"):
            continue

        # Keep this event only if it's the first attempt we've seen for this
        # txn_id, or if it happened later than the one we already have.
        txn_id = event["txn_id"]
        current = latest.get(txn_id)
        if current is None or event["ts"] > current["ts"]:
            latest[txn_id] = event

# Now that each payment is down to its latest attempt, count it as collected
# only if that attempt succeeded. An earlier success followed by a later
# failure means the money wasn't collected.
total = 0.0
count = 0
for event in latest.values():
    if event["status"] == "success":
        total += parse_amount(event["amount"])
        count += 1

with open("expected.txt") as f:
    expected = int(f.read().strip())

if count != expected:
    print(f"Check failed: counted {count} successful payments, expected {expected}.")
    print("Something in the data isn't being handled the way the README describes.")
else:
    print(f"Check passed: {count} successful payments.")
    print(f"Your code: KOYA-{round(total)}")
