# Diagnosis — store S-014 monthly revenue is too low

## Symptom (from BUG-REPORT.md)

`python -m pipeline report --store S-014` gives an August total of **50 043,47 €**.
Finance, reconciled against the receipts, has **56 232,09 €**. The
transaction count is right (420 on both sides), every other store matches to the
cent, and the pipeline ran without errors.

## Red command

```
python -m pytest tests/test_s014_reconciliation.py -q
```

Rebuilds the warehouse from the real raw files and checks the S-014 total against
the finance figure. On the original code it fails with `S-014 off by 6188.62`;
after the fix it passes (total = `56232.09`).

This is the main command to make sure the numbers will match and the bug resolved.

## Cause

`pipeline.parse.parse_amount` extracts the amount with the regex
`[-+]?[0-9]+(?:[.,][0-9]{1,2})?`, which stops at the first character that is
neither a digit nor `.`/`,`. The partner exporter — the only source that feeds
S-014 — writes amounts of 1000 and over in French regional format, with a
**no-break space (U+00A0) as the thousands separator** (`"1 321,49"`); `str.strip()`
only trims the ends, so that interior space survives, the regex matches only
`"1"`, and the amount is read as `Decimal("1")`. Five S-014 rows are affected and
their combined shortfall is exactly 6 188,62 €

### What pointed me at it

- **Only S-014 is wrong, and S-014 is the only store fed by `partner_export`.**
  `transform`, `load` and `report` are store-agnostic and every other store is
  correct, so the fault is in partner-specific handling — `parse`, which the
  README names as the place the partner's format is reconciled.
- **The count is right and no rows are skipped as duplicates**, so the money is
  lost *inside* rows that are present, not in missing rows — a value problem, not
  a volume problem.
- Used help from AI in a way i would still learn how to find the error, giving Claude Code all the cause ideas to get hints in exchange of where to look at more precisely.



### Ruled out

| Hypothesis | How it was eliminated |
| Rows discarded by de-duplication | Partner `txn_id`s are all unique; `duplicates_skipped == 0` |
| Discount applied wrong for S-014 | `transform.normalise` has no per-store branch; other stores reconcile exactly |
| Rounding | `quantize(CENT, ROUND_HALF_UP)` is uniform; worst case ≈ a few euros over 420 rows, not 6 188 |
| Date parsing (wrong month / lost days) | Partner dates are ISO and all in August; daily breakdown covers 31 days |


## Fix

In `parse_amount`, replace `raw.strip()` with `re.sub(r"\s", "", raw)`: drop
*all* whitespace (including U+00A0 and U+202F) before matching, so grouped
thousands collapse into a plain digit run. The exporters' formats are documented
and unambiguous (POS: `.` decimal; partner: `,` decimal, space for grouping), so
removing whitespace cannot misread any legitimate value, and all existing parse
tests still pass.

## Regression test

`tests/test_parse.py::test_parses_thousands_separator`:

```python
assert parse_amount("1 321,49") == Decimal("1321.49")
```

Red on the original code (`parse_amount` returns `Decimal("1")`), green after the
fix. Verified red by stashing the fix (`git stash push -- src/pipeline/parse.py`)
and running the test.

## Where this finding belongs

It is written in parse_amount that the amounts are written in different shapes so the function that has to adapt to them. Problem is i didn't find anywhere a text to explain what is the format of each exporter exactly. If they decide to change it again in a new way, depending of it, this type of bug might reappear.

## Did this take more than 1h30?

It took 1h30.
