"""Prove the projects dashboard survives hand-entered dates it cannot trust.

Two live projects carry a truncated year in `installment2date` (0006-07-10 and
0026-03-31 - almost certainly a two-digit year that arrived from Excel).  The
installment matrices were built as datetime64[ns], which cannot represent those
years, so `compute_payment_state()` raised "Overflow when converting between
datetime64 units".  `/dashboard` caught the error and rendered the landing page,
so a successful Building Projects login appeared to bounce straight back to
"Choose Your Portal".

This check builds payment frames in memory (no database is opened) and asserts:

  * a year-6 / year-9999 date no longer aborts the dashboard;
  * due-today is still overdue for the status table but not for the cards;
  * unpaid / paid / outstanding money is unchanged.

Run:  python _check_payment_state_dates.py
"""
import datetime as dt
import os
import sys
import types

# Never reach the live database from a developer machine.
os.environ['DATABASE_URL'] = 'postgresql://u:p@127.0.0.1:9/nodb'
os.environ['APP_ENV'] = 'development'
os.environ['FLASK_ENV'] = 'development'
os.environ.pop('ALLOW_PROD_DB_WRITE', None)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, '_check_payment_state_dates_out.txt')
RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                                   # noqa: BLE001
        pass


wp = types.ModuleType('weasyprint')
wp.HTML = object
wp.CSS = object
sys.modules.setdefault('weasyprint', wp)

import numpy as np                                                      # noqa: E402
import pandas as pd                                                     # noqa: E402

import ConnectLink                                                      # noqa: E402

COLS = ConnectLink.PAYMENT_DF_COLUMNS


def make_row(pid, contract, deposit, installments):
    row = {c: None for c in COLS}
    row.update({
        'id': pid, 'clientname': 'Client %s' % pid, 'clientwanumber': '263771000000',
        'projectname': 'Project %s' % pid,
        'totalcontractamount': contract, 'depositorbullet': deposit,
    })
    for i, (amount, due, paid) in enumerate(installments, start=1):
        row['installment%damount' % i] = amount
        row['installment%dduedate' % i] = due
        row['installment%ddate' % i] = paid
    return row


today = dt.date.today()
yesterday = today - dt.timedelta(days=1)
tomorrow = today + dt.timedelta(days=1)

df = pd.DataFrame([
    # 1 - due today and unpaid: the status table counts it as overdue today
    make_row(1, 1000, 100, [(200, today, None)]),
    # 2 - due tomorrow and unpaid: not overdue yet
    make_row(2, 1000, 0, [(200, tomorrow, None)]),
    # 3 - due yesterday, paid
    make_row(3, 1000, 0, [(200, yesterday, yesterday)]),
    # 4/5 - the production poison: years far outside datetime64[ns]
    make_row(4, 1000, 0, [(None, None, None), (1076.67, dt.date(6, 7, 10), dt.date(6, 7, 10))]),
    make_row(5, 1000, 0, [(163, dt.date(26, 3, 31), dt.date(9999, 12, 31))]),
    # 6 - every scheduled installment paid but contract still above deposit+paid
    make_row(6, 1000, 100, [(300, yesterday, yesterday)]),
], columns=COLS)

try:
    state = ConnectLink.compute_payment_state(df)
    crashed = None
except Exception as exc:                                                # noqa: BLE001
    state = None
    crashed = '%s: %s' % (type(exc).__name__, exc)

check('a mistyped year no longer aborts the projects dashboard', crashed is None, crashed)

if state is not None:
    check('installment dates are held at day resolution',
          state['due_naive'].dtype == np.dtype('datetime64[D]')
          and state['paid_naive'].dtype == np.dtype('datetime64[D]'),
          (state['due_naive'].dtype, state['paid_naive'].dtype))
    check('only the installment due today (unpaid) is overdue',
          state['is_overdue'].tolist() == [True, False, False, False, False, False],
          state['is_overdue'].tolist())
    check('the overdue amount is that installment only',
          np.round(state['overdue_amount'], 2).tolist() == [200.0, 0.0, 0.0, 0.0, 0.0, 0.0],
          np.round(state['overdue_amount'], 2).tolist())
    check('due today counts for the status table but not for the cards',
          bool(state['overdue_inst_now'][0, 0]) and not bool(state['overdue_inst'][0, 0]))
    check('a mistyped year still reads as a paid installment',
          bool(state['is_paid'][3, 1]) and bool(state['is_paid'][4, 0]))
    check('deposit + paid installments is unchanged',
          np.round(state['total_paid'], 2).tolist() == [100.0, 0.0, 200.0, 1076.67, 163.0, 400.0],
          np.round(state['total_paid'], 2).tolist())
    check('settled projects with money still owed stay Outstanding, not Overdue',
          state['is_outstanding'].tolist() == [False, False, True, False, True, True]
          and np.round(state['outstanding_balance'], 2).tolist() == [0.0, 0.0, 800.0, 0.0, 837.0, 600.0],
          (state['is_outstanding'].tolist(), np.round(state['outstanding_balance'], 2).tolist()))

    empty = ConnectLink.compute_payment_state(pd.DataFrame(columns=COLS))
    check('an empty portfolio still returns usable shapes',
          empty['amounts'].shape == (0, 10) and empty['installments_due'].shape == (0,),
          (empty['amounts'].shape, empty['installments_due'].shape))

failures = [r for r in RESULTS if r.startswith('FAIL')]
print('\n%d checks, %d failed' % (len(RESULTS), len(failures)))
sys.exit(1 if failures else 0)
