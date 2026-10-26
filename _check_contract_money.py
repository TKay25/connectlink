"""Capture a project through the REAL /contract_log route and check every amount.

Runs entirely in-process against a recording stand-in for the database, so no
connection is ever made to the live Render Postgres: DATABASE_URL points at a
closed local port and db_helper is replaced before ConnectLink is imported.

Run:  python _check_contract_money.py
"""
import contextlib
import os
import re
import sys
import types
from decimal import Decimal

os.environ['DATABASE_URL'] = 'postgresql://u:p@127.0.0.1:9/nodb'
os.environ['APP_ENV'] = 'development'
os.environ['FLASK_ENV'] = 'development'
os.environ.pop('ALLOW_PROD_DB_WRITE', None)

# WeasyPrint needs GTK on this box and the contract flow never calls it.
wp = types.ModuleType('weasyprint')


class _HTML:
    def __init__(self, *a, **k):
        pass

    def write_pdf(self, *a, **k):
        return b''


class _CSS:
    def __init__(self, *a, **k):
        pass


wp.HTML = _HTML
wp.CSS = _CSS
sys.modules.setdefault('weasyprint', wp)

import db_helper  # noqa: E402

RECORDED = []


class FakeCursor:
    def __init__(self):
        self._rows = []
        self.description = None

    def execute(self, sql, params=None):
        RECORDED.append((' '.join(str(sql).split()), params))
        flat = ' '.join(str(sql).split()).upper()
        if 'LASTVAL' in flat:
            self._rows = [(4242,)]
        elif flat.startswith('SELECT MONTHSTOPAY FROM CONNECTLINKDATABASE'):
            # the edit route asks for the stored plan before rewriting it
            self._rows = [(6,)]
        else:
            self._rows = []

    def executemany(self, sql, seq):
        for p in seq:
            self.execute(sql, p)

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)

    def close(self):
        pass


class FakeConnection:
    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


@contextlib.contextmanager
def fake_get_db():
    yield FakeCursor(), FakeConnection()


def fake_execute_query(sql, params=None, fetch_all=False, fetch_one=False, commit=False):
    RECORDED.append((' '.join(str(sql).split()), params))
    flat = ' '.join(str(sql).split()).upper()
    if 'LASTVAL' in flat:
        return (4242,)
    return [] if fetch_all else (None if fetch_one else True)


db_helper.get_db = fake_get_db
db_helper.execute_query = fake_execute_query
db_helper.schema_writes_allowed = lambda: False

import ConnectLink  # noqa: E402

app = ConnectLink.app
app.config['TESTING'] = True

RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])


def capture(payload):
    """POST the capture form exactly as the browser does and return the INSERT params."""
    RECORDED.clear()
    client = app.test_client()
    with client.session_transaction() as sess:
        sess['user_id'] = 1
        sess['userid'] = 1
        sess['user_uuid'] = 'test-uuid'
        sess['user_name'] = 'Test Capturer'
    resp = client.post('/contract_log', data=payload, follow_redirects=False)
    insert = None
    for sql, params in RECORDED:
        if sql.upper().startswith('INSERT INTO CONNECTLINKDATABASE'):
            insert = (sql, params)
    return resp, insert


def form(contract_price, deposit, months='6'):
    return {
        'client_name': 'Test Client',
        'client_national_id': '63-123456-A-00',
        'client_address': '12 Test Road, Shurugwi',
        'client_whatsapp_number': '263771234567',
        'client_email': 'client@example.com',
        'next_of_kin_name': 'Next Kin',
        'next_of_kin_address': '13 Test Road',
        'next_of_kin_contact_number': '263771234568',
        'relationship': 'Sister',
        'projectadministrator': 'Admin User',
        'project_name': 'Flow Test Project',
        'project_location': 'Shurugwi',
        'project_start_date': '2026-11-01',
        'months_to_completion': '120',
        'project_description': '<p>Build a wall</p>',
        'agreement_date': '2026-10-26',
        'total_contract_price': contract_price,
        'late_payment_interest': '5',
        'payment_method': 'Installments',
        'months_to_pay': months,
        'deposit_required': deposit,
        'deposit_payment_date': '2026-10-26',
        'first_installment_due_date': '2026-11-30',
        'project_notes': '',
    }


def columns_of(insert_sql):
    inside = insert_sql[insert_sql.upper().index('(') + 1: insert_sql.upper().index(')')]
    return [c.strip() for c in inside.split(',')]


def row_dict(insert):
    sql, params = insert
    return dict(zip(columns_of(sql), params))


def near(a, b, tol=0.005):
    return a is not None and b is not None and abs(float(a) - float(b)) <= tol


# ---------------------------------------------------------------------------
# 1. The money parser itself, on every shape a clerk can type
# ---------------------------------------------------------------------------
MATRIX = [
    ('58,699.20', 58699.20),      # thousands comma, dot decimal
    ('58699,20', 58699.20),       # comma DECIMAL - the 100x case
    ('1.234,56', 1234.56),        # European
    ('USD 58 699.20', 58699.20),  # currency + space separators
    ('$1,234.56', 1234.56),
    ('1,234', 1234.0),            # thousands, three digits behind the comma
    ('1,234,567', 1234567.0),
    ('58699.2', 58699.2),
    ('(1,234.56)', -1234.56),
    ('  783.5  ', 783.5),
    ('0', 0.0),
]
for text, expected in MATRIX:
    got = ConnectLink._parse_money(text)
    check(f'_parse_money({text!r}) == {expected}', near(got, expected), f'got {got}')
check('_parse_money("") is None', ConnectLink._parse_money('') is None)
check('_parse_money("abc") is None', ConnectLink._parse_money('abc') is None)
check('_parse_money(None) is None', ConnectLink._parse_money(None) is None)
check('_contract_money("58699,2") == "58,699.20"',
      ConnectLink._contract_money('58699,2') == '58,699.20',
      ConnectLink._contract_money('58699,2'))
check('_norm_amount("58699,20") == "58699.20"',
      ConnectLink._norm_amount('58699,20') == '58699.20',
      ConnectLink._norm_amount('58699,20'))
check('_norm_amount("58,699.20") == _norm_amount(Decimal("58699.20"))',
      ConnectLink._norm_amount('58,699.20') == ConnectLink._norm_amount(Decimal('58699.20')))

# ---------------------------------------------------------------------------
# 2. Capture a project with a comma-formatted contract amount
# ---------------------------------------------------------------------------
resp, insert = capture(form('58,699.20', '17,609.76', '6'))
check('capture (thousands comma) returns 302', resp.status_code == 302,
      f'{resp.status_code} {resp.get_data(as_text=True)[:200]}')
check('capture (thousands comma) inserted a row', insert is not None)
if insert:
    row = row_dict(insert)
    check('totalcontractamount == 58699.20', near(row.get('totalcontractamount'), 58699.20),
          row.get('totalcontractamount'))
    check('depositorbullet == 17609.76', near(row.get('depositorbullet'), 17609.76),
          row.get('depositorbullet'))
    check('monthlyinstallment == (58699.20-17609.76)/6', near(row.get('monthlyinstallment'), 6848.24),
          row.get('monthlyinstallment'))
    check('installment1amount == monthly', near(row.get('installment1amount'), 6848.24),
          row.get('installment1amount'))
    check('installment6amount == monthly', near(row.get('installment6amount'), 6848.24),
          row.get('installment6amount'))
    check('deposit + 6 instalments == contract',
          near(float(row.get('depositorbullet')) + 6 * float(row.get('installment1amount')), 58699.20, 0.01),
          float(row.get('depositorbullet')) + 6 * float(row.get('installment1amount')))
    check('installment7amount == 0', near(row.get('installment7amount'), 0.0),
          row.get('installment7amount'))
    check('paymentmethod == Installments', row.get('paymentmethod') == 'Installments',
          row.get('paymentmethod'))

# ---------------------------------------------------------------------------
# 3. The exact 100x shape: a comma used as the decimal point
# ---------------------------------------------------------------------------
resp, insert = capture(form('58699,20', '17609,76', '6'))
check('capture (comma decimal) returns 302', resp.status_code == 302,
      f'{resp.status_code} {resp.get_data(as_text=True)[:300]}')
if insert:
    row = row_dict(insert)
    check('comma-decimal contract is 58,699.20, NOT 5,869,920',
          near(row.get('totalcontractamount'), 58699.20), row.get('totalcontractamount'))
    check('comma-decimal deposit is 17,609.76', near(row.get('depositorbullet'), 17609.76),
          row.get('depositorbullet'))

# ---------------------------------------------------------------------------
# 4. Plain numbers and a once-off payment still behave
# ---------------------------------------------------------------------------
resp, insert = capture(form('58699.20', '17609.76', '6'))
check('capture (plain) returns 302', resp.status_code == 302,
      f'{resp.status_code} {resp.get_data(as_text=True)[:200]}')
if insert:
    check('plain contract amount unchanged', near(row_dict(insert).get('totalcontractamount'), 58699.20),
          row_dict(insert).get('totalcontractamount'))

once_off = form('45,000.00', '0')
once_off['payment_method'] = 'Once Off Payment'
once_off['bullet_payment_date'] = '2026-10-26'
once_off.pop('months_to_pay', None)
once_off.pop('deposit_required', None)
once_off.pop('first_installment_due_date', None)
resp, insert = capture(once_off)
check('capture (once off) returns 302', resp.status_code == 302,
      f'{resp.status_code} {resp.get_data(as_text=True)[:200]}')
if insert:
    row = row_dict(insert)
    check('once-off total == 45000.00', near(row.get('totalcontractamount'), 45000.0),
          row.get('totalcontractamount'))
    check('once-off deposit == 45000.00', near(row.get('depositorbullet'), 45000.0),
          row.get('depositorbullet'))
    check('once-off monthly == 0', near(row.get('monthlyinstallment'), 0.0),
          row.get('monthlyinstallment'))

# ---------------------------------------------------------------------------
# 5. The amount the CONTRACT prints
# ---------------------------------------------------------------------------
check('contract prints USD 58,699.20',
      ConnectLink._contract_money(Decimal('58699.20')) == '58,699.20',
      ConnectLink._contract_money(Decimal('58699.20')))
check('contract deposit prints USD 17,609.76',
      ConnectLink._contract_money(Decimal('17609.76')) == '17,609.76',
      ConnectLink._contract_money(Decimal('17609.76')))

# ---------------------------------------------------------------------------
# 6. Editing an existing project with the same shapes
# ---------------------------------------------------------------------------
def edit_form(contract_price, deposit, monthly, months='6'):
    payload = {
        'project_id': '4242',
        'ClientName': 'Test Client',
        'completion_status': 'Ongoing',
        'ProjectName': 'Flow Test Project',
        'ProjectStartDate': '2026-11-01',
        'projscope': '<p>Build a wall</p>',
        'TotalContractAmount': contract_price,
        'MonthsToPay': months,
        'depositpaid': deposit,
        'deposit_date_paid': '2026-10-26',
        'AdminName': 'Admin User',
        'project_quotation_id': '',
    }
    for i in range(1, 11):
        payload[f'Installment{i}Amount'] = monthly if i <= int(months) else ''
        payload[f'Installment{i}DueDate'] = f'2026-{min(10 + i, 12):02d}-28' if i <= int(months) else ''
        payload[f'installment{i}_paid_date'] = ''
    return payload


RECORDED.clear()
client = app.test_client()
with client.session_transaction() as sess:
    sess['user_id'] = 1
    sess['userid'] = 1
    sess['user_uuid'] = 'test-uuid'
    sess['user_name'] = 'Test Capturer'
resp = client.post('/update_project', data=edit_form('58,699.20', '17,609.76', '6,848.24', '6'),
                   follow_redirects=False)
check('update_project returns 200/302', resp.status_code in (200, 302),
      f'{resp.status_code} {resp.get_data(as_text=True)[:300]}')
update = None
for sql, params in RECORDED:
    if sql.upper().startswith('UPDATE CONNECTLINKDATABASE'):
        update = (sql, params)
check('update_project ran an UPDATE', update is not None)
if update:
    sql, params = update
    pairs = re.findall(r'(\w+)\s*=\s*%s', sql)
    updated = dict(zip(pairs, params))
    check('update stores totalcontractamount 58699.20',
          near(updated.get('totalcontractamount'), 58699.20), updated.get('totalcontractamount'))
    check('update stores depositorbullet 17609.76',
          near(updated.get('depositorbullet'), 17609.76), updated.get('depositorbullet'))
    check('update stores monthlyinstallment 6848.24',
          near(updated.get('monthlyinstallment'), 6848.24), updated.get('monthlyinstallment'))
    check('update stores installment1amount 6848.24',
          near(updated.get('installment1amount'), 6848.24), updated.get('installment1amount'))
    check('update keeps unused installment7amount at 0',
          near(updated.get('installment7amount'), 0.0), updated.get('installment7amount'))

# ---------------------------------------------------------------------------
# 7. The consolidated "All Branches" view must report on every branch
# ---------------------------------------------------------------------------
from flask import session as flask_session  # noqa: E402

with app.test_request_context('/'):
    flask_session['branch_id'] = 0          # POS_ALL_BRANCHES_ID
    check('All Branches applies NO branch filter',
          ConnectLink.branch_read_clause('t.branch_id') == ('', []),
          ConnectLink.branch_read_clause('t.branch_id'))
    flask_session['branch_id'] = 2          # a real shop
    check('a real branch is scoped to itself',
          ConnectLink.branch_read_clause('t.branch_id')[0] == ' AND t.branch_id = %s',
          ConnectLink.branch_read_clause('t.branch_id'))
    flask_session['department'] = 'furniture'
    check('the department switch reads Furniture',
          ConnectLink.current_department() == 'furniture', ConnectLink.current_department())
    flask_session['department'] = 'nonsense'
    check('an unknown department falls back to Hardware',
          ConnectLink.current_department() == 'hardware', ConnectLink.current_department())

fails = [r for r in RESULTS if r.startswith('FAIL')]
print('\n' + '=' * 70)
print(f'{len(RESULTS) - len(fails)} passed, {len(fails)} failed')
if fails:
    for f in fails:
        print(f)
sys.exit(1 if fails else 0)

