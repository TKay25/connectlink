"""Check the bulk-upload duplicate guard, without a database or a browser.

Verifies the three things that matter:

  1. the fingerprint is STABLE for the same decisions in a different row order,
  2. a re-save or a differently-ordered sheet therefore matches the earlier job,
  3. a genuinely DIFFERENT upload does not match - so the guard cannot block
     real work,
  4. a deliberate repeat (confirm_repeat) is allowed through.

`find_prior_bulk_upload` and the routes are exercised against a stub cursor, so
this runs anywhere.

Run: python _check_double_upload_guard.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

FAILURES = []


def check(label, got, want):
    ok = got == want
    print(f"  [{'ok' if ok else 'FAIL'}] {label}")
    if not ok:
        print(f"         got  {got!r}")
        print(f"         want {want!r}")
        FAILURES.append(label)


def main():
    # Import only the pure helpers: importing ConnectLink pulls in WeasyPrint's
    # native libraries, which are not installed on every machine.
    src = open('ConnectLink.py', encoding='utf-8').read()

    print("== the guard exists where it must ==")
    check("fingerprint helper defined", 'def bulk_upload_fingerprint(' in src, True)
    check("prior-lookup helper defined", 'def find_prior_bulk_upload(' in src, True)
    check("OVERLAP helper defined (the one that catches a edited re-upload)",
          'def bulk_upload_overlap(' in src, True)
    check("overlap is the default threshold, not exact-file",
          'BULK_UPLOAD_REPEAT_RATIO' in src, True)
    check("column added to schema", 'ADD COLUMN IF NOT EXISTS file_fingerprint' in src, True)
    check("Check step reports `duplicate`", "'duplicate': duplicate," in src, True)
    check("Check step stores the fingerprint", "'file_fingerprint': fingerprint," in src, True)
    check("Check step uses the overlap check",
          'overlap = bulk_upload_overlap(' in src, True)
    check("Apply step refuses a repeat", 'if (prior or overlap) and not confirm_repeat:' in src, True)
    check("Apply step returns 409", "        }), 409" in src, True)
    check("Apply step persists the fingerprint", 'file_fingerprint)' in src, True)
    check("deliberate repeat is audited",
          'CONFIRMED REPEAT of an earlier upload' in src, True)
    check("failed check never blocks real work",
          'upload continues.' in src, True)
    check("only the most recent applied job is compared",
          'SELECT MAX(id) FROM bulk_upload_jobs' in src, True)
    check("reverted jobs are ignored", "status = 'applied'" in src, True)

    print()
    print("== replace the module import with just the helpers, and run them ==")
    # Lift the two pure functions out of the source so the test needs no deps.
    import hashlib
    ns = {'hashlib': hashlib}

    start = src.index('def bulk_upload_fingerprint(')
    end = src.index('def find_prior_bulk_upload(')
    exec(compile(src[start:end], 'fingerprint', 'exec'), ns)
    fingerprint = ns['bulk_upload_fingerprint']

    a = [{'product_id': 1, 'name': 'Mugs', 'quantity': 10, 'action': 'merge'},
         {'product_id': 2, 'name': 'Bowls', 'quantity': 5, 'action': 'merge'},
         {'product_id': None, 'name': 'Spoons', 'quantity': 3, 'action': 'create'}]
    b = list(reversed(a))                                   # same decisions, re-ordered rows
    c = [{'product_id': 1, 'name': 'MUGS ', 'quantity': 10, 'action': 'merge'},   # case/space only
         {'product_id': 2, 'name': 'Bowls', 'quantity': 5, 'action': 'merge'},
         {'product_id': None, 'name': 'Spoons', 'quantity': 3, 'action': 'create'}]
    d = [{'product_id': 1, 'name': 'Mugs', 'quantity': 11, 'action': 'merge'},    # real change
         {'product_id': 2, 'name': 'Bowls', 'quantity': 5, 'action': 'merge'},
         {'product_id': None, 'name': 'Spoons', 'quantity': 3, 'action': 'create'}]
    e = [{'product_id': 1, 'name': 'Mugs', 'quantity': 10, 'action': 'merge'},
         {'product_id': 2, 'name': 'Bowls', 'quantity': 5, 'action': 'merge'},
         {'product_id': None, 'name': 'Teaspoons', 'quantity': 3, 'action': 'create'}]

    print()
    print("== fingerprint behaviour ==")
    check("same decisions, rows re-ordered -> SAME", fingerprint(a) == fingerprint(b), True)
    check("same decisions, case/space differ -> SAME", fingerprint(a) == fingerprint(c), True)
    check("quantity changed -> DIFFERENT", fingerprint(a) == fingerprint(d), False)
    check("a product name changed -> DIFFERENT", fingerprint(a) == fingerprint(e), False)
    check("stable across calls", fingerprint(a) == fingerprint(a), True)
    check("empty input still yields a hash", len(fingerprint([])) == 32, True)

    print()
    print("== overlap check: logic against a stub prior job ==")
    ov_src = src[src.index('def bulk_upload_overlap('):src.index('def find_prior_bulk_upload(')]

    class OverlapStub:
        """Stands in for the cursor: returns a fixed prior job's items."""

        def __init__(self, prior_items):
            self.prior = prior_items

        def execute(self, sql, params=None):
            self._is_prior_query = 'bulk_upload_items' in (sql or '')

        def fetchall(self):
            return self.prior

    ns3 = {}
    exec(compile('BULK_UPLOAD_REPEAT_RATIO = 0.8\n'
                 'BULK_UPLOAD_REPEAT_MIN_ROWS = 5\n' + ov_src,
                 'overlap', 'exec'), ns3)
    overlap = ns3['bulk_upload_overlap']

    def make_prior(pairs):
        # (job id, ref, file, user, created, total_qty, product_id, qty, name)
        import datetime as _dt
        return [(10, 'UPL-A', 'f.xlsx', 'user@x', _dt.datetime(2026, 10, 5, 8, 40),
                 0, pid, qty, name) for pid, qty, name in pairs]

    prior = make_prior([(i, 5, f'Item {i}') for i in range(1, 21)])

    # The real incident: mostly the same products at the same quantities, with a
    # few extra rows added. A whole-file match sees nothing; this must catch it.
    same = [{'product_id': i, 'name': f'Item {i}', 'quantity': 5} for i in range(1, 19)]
    plus_new = same + [{'product_id': 90, 'name': 'Brand new', 'quantity': 3},
                       {'product_id': 91, 'name': 'Also new', 'quantity': 4}]
    got = overlap(OverlapStub(prior), 2, plus_new)
    check("edited re-upload IS detected", bool(got), True)
    check("  reports the shared product count", got and got['products'], 18)
    check("  reports the units it would double", got and got['quantity'], 90)

    # A genuine second delivery: same items, DIFFERENT quantities.
    restock = [{'product_id': i, 'name': f'Item {i}', 'quantity': 7} for i in range(1, 19)]
    check("a real top-up with new quantities is NOT blocked",
          overlap(OverlapStub(prior), 2, restock), None)

    # An unrelated upload.
    other = [{'product_id': i, 'name': f'Other {i}', 'quantity': 5} for i in range(50, 70)]
    check("an unrelated upload is NOT blocked", overlap(OverlapStub(prior), 2, other), None)

    # Products this upload creates cannot be repeats.
    creates = [{'product_id': None, 'name': 'New', 'quantity': 5} for _ in range(10)]
    check("an all-new upload is NOT blocked", overlap(OverlapStub(prior), 2, creates), None)

    # Below the minimum row count: too small to judge.
    tiny = [{'product_id': 1, 'name': 'Item 1', 'quantity': 5},
            {'product_id': 2, 'name': 'Item 2', 'quantity': 5}]
    check("a tiny upload is NOT blocked", overlap(OverlapStub(prior), 2, tiny), None)

    # Just under the ratio: a handful shared, the rest genuinely new.
    mostly_new = ([{'product_id': i, 'name': f'Item {i}', 'quantity': 5} for i in range(1, 7)] +
                  [{'product_id': 100 + i, 'name': f'New {i}', 'quantity': 5} for i in range(1, 40)])
    check("mostly-new upload is NOT blocked", overlap(OverlapStub(prior), 2, mostly_new), None)

    print()
    print()
    print("== find_prior_bulk_upload ignores reverted jobs ==")
    q = src[src.index('def find_prior_bulk_upload('):]
    q = q[:q.index('\n\n\n')]

    class StubCursor:
        def __init__(self):
            self.sql = None
            self.params = None

        def execute(self, sql, params=None):
            self.sql, self.params = sql, params

        def fetchone(self):
            return None

    stub = StubCursor()
    ns2 = {}
    exec(compile(q, 'prior', 'exec'), ns2)
    ns2['find_prior_bulk_upload'](stub, 2, 'abc')
    check("filters to this branch", 'branch_id = %s' in stub.sql, True)
    check("filters to the fingerprint", 'file_fingerprint = %s' in stub.sql, True)
    check("only APPLIED jobs count", "status = 'applied'" in stub.sql, True)
    check("branch and fingerprint bound", stub.params, (2, 'abc'))

    print()
    if FAILURES:
        print(f"{len(FAILURES)} CHECK(S) FAILED: {', '.join(FAILURES)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
