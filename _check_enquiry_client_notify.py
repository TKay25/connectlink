"""A client whose enquiry an operator logs by hand must be told, like the form does.

The enquiry form replies to the client with a reference number and a 24-hour
promise. Logging the same enquiry from the admin chat panel used to tell only the
admins, so the client heard nothing at all. These checks drive the REAL
/api/enquiries/manual endpoint with a recording stand-in for the database and for
the WhatsApp API, and assert:

  1. the enquiry is still created when WhatsApp fails (a send must never lose it);
  2. the client is messaged, to the normalised number, with the reference, the
     category and the 24-hour promise;
  3. a rejected send is reported honestly (client_notified false), not as success;
  4. an enquiry with no number says so instead of pretending.

Run:  python _check_enquiry_client_notify.py
"""
import contextlib
import os
import re
import sys
import types

os.environ['DATABASE_URL'] = 'postgresql://u:p@127.0.0.1:9/nodb'
os.environ['APP_ENV'] = 'development'
os.environ['FLASK_ENV'] = 'development'
os.environ.pop('ALLOW_PROD_DB_WRITE', None)

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, '_check_enquiry_client_notify_out.txt')
RESULTS = []
SENT = []
SQL = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])
    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(RESULTS) + '\n')


class Cur:
    description = None
    rowcount = 1

    def __init__(self):
        self._rows = []

    def execute(self, sql, params=None):
        SQL.append((' '.join(str(sql).split()), params))
        flat = ' '.join(str(sql).split()).upper()
        if 'RETURNING ID' in flat or 'LASTVAL' in flat:
            self._rows = [(4242,)]
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


class Conn:
    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


@contextlib.contextmanager
def fake_db():
    yield Cur(), Conn()


def fake_execute_query(sql, params=None, fetch_all=False, fetch_one=False, commit=False):
    SQL.append((' '.join(str(sql).split()), params))
    if fetch_all:
        return []
    if fetch_one:
        return None
    return True


wp = types.ModuleType('weasyprint')


class _HTML:
    def __init__(self, *a, **k):
        pass

    def write_pdf(self, *a, **k):
        return b''


wp.HTML = _HTML
wp.CSS = type('CSS', (), {'__init__': lambda self, *a, **k: None})
sys.modules.setdefault('weasyprint', wp)

import db_helper                                                    # noqa: E402

db_helper.get_db = fake_db
db_helper.execute_query = fake_execute_query
db_helper.schema_writes_allowed = lambda: False

import ConnectLink                                                 # noqa: E402

app = ConnectLink.app
app.config['TESTING'] = True

# The admin alert is not under test (and would hit the network).
ConnectLink.send_admin_enquiry_notification = lambda *a, **k: True


class FakeResp:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status


def fake_post(url, json=None, headers=None, timeout=None, **kw):
    """Record the WhatsApp send; answer the way Meta answers."""
    SENT.append({'url': url, 'json': json, 'headers': headers})
    if fake_post.fail:
        return FakeResp('{"error":{"message":"Message failed to send because more than '
                        '24 hours have passed","code":131047}}', 400)
    return FakeResp('{"messages":[{"id":"wamid.TEST123"}]}', 200)


fake_post.fail = False
ConnectLink.requests = types.SimpleNamespace(post=fake_post)


def client(**seed):
    c = app.test_client()
    with c.session_transaction() as sess:
        sess['user_id'] = 1
        sess['userid'] = 1
        sess['user_name'] = 'Operator'
        for k, v in seed.items():
            sess[k] = v
    return c


def submit(phone, name='Tendai Moyo', category='Quotation', details='Needs a quote for a durawall.'):
    SQL.clear()
    SENT.clear()
    data = {'username': name, 'clientwhatsapp': phone,
            'enqcategory': category, 'enq': details}
    resp = client().post('/api/enquiries/manual', data=data,
                         content_type='multipart/form-data')
    return resp, (resp.get_json() or {})


# ---------------------------------------------------------------------------
# 1. The happy path: enquiry saved AND the client told
# ---------------------------------------------------------------------------
fake_post.fail = False
resp, body = submit('0771234567')
check('logging an enquiry succeeds', resp.status_code == 200 and body.get('status') == 'success',
      '%s %s' % (resp.status_code, body.get('message')))
check('the enquiry row is still written',
      any('insert into connectlinkenquiries' in s.lower() for s, _ in SQL),
      [s[:40] for s, _ in SQL if 'INSERT' in s][:3])

check('the client IS messaged on WhatsApp (this was the missing half)',
      len(SENT) == 1, '%d send(s)' % len(SENT))
if SENT:
    payload = SENT[0]['json'] or {}
    text = ((payload.get('text') or {}).get('body') or '')
    check('...to the normalised number', payload.get('to') == '+263771234567',
          payload.get('to'))
    check('...as a plain text message', payload.get('type') == 'text', payload.get('type'))
    check('...carrying the reference number', '#4242' in text, text[:120].replace('\n', ' | '))
    check('...the category', 'Quotation' in text)
    check('...and the 24-hour promise the form makes',
          'within 24 hours' in text, text[:200].replace('\n', ' | '))
    check('...addressed to the client by name', 'Tendai Moyo' in text)
check('the endpoint reports that the client was reached',
      body.get('client_notified') is True, body.get('client_notified'))
check('...and says so in its message',
      'messaged on WhatsApp' in (body.get('message') or ''), body.get('message'))

# The send is also recorded so the operator sees it in the chat panel.
check('the confirmation is logged in the chat panel too',
      any('insert into whatsapp_messages' in s.lower() for s, _ in SQL),
      [s[:45] for s, _ in SQL if 'WHATSAPP' in s][:2])

# ---------------------------------------------------------------------------
# 2. A local number in another shape is still normalised
# ---------------------------------------------------------------------------
fake_post.fail = False
resp, body = submit('+263 78 987 6543')
check('a number typed with +263 and spaces still reaches the client',
      bool(SENT) and (SENT[0]['json'] or {}).get('to') == '+263789876543',
      (SENT[0]['json'] or {}).get('to') if SENT else 'no send')

# ---------------------------------------------------------------------------
# 3. WhatsApp refuses: the enquiry must survive, and we must not claim success
# ---------------------------------------------------------------------------
fake_post.fail = True
resp, body = submit('0771234567')
check('a refused WhatsApp send does not lose the enquiry',
      resp.status_code == 200 and body.get('status') == 'success',
      '%s %s' % (resp.status_code, body.get('message')))
check('...but the operator is told the client was NOT reached',
      body.get('client_notified') is False, body.get('client_notified'))
check('...in words the panel can show',
      bool(re.search(r'not|could not', (body.get('message') or ''), re.I)),
      body.get('message'))

# ---------------------------------------------------------------------------
# 4. No number: nothing is sent, and it says so
# ---------------------------------------------------------------------------
fake_post.fail = False
SENT.clear()
resp, body = submit('', name='Walk-in Client')
check('an enquiry with no number still posts', body.get('status') == 'success',
      body.get('message'))
check('...and nothing is sent to WhatsApp', not SENT, len(SENT))
check('...and the reply says no message went out',
      'no whatsapp message' in (body.get('message') or '').lower(),
      body.get('message'))

# ---------------------------------------------------------------------------
# 5. The form path still sends its own confirmation (untouched)
# ---------------------------------------------------------------------------
src = open(os.path.join(ROOT, 'ConnectLink.py'), encoding='utf-8').read()
check('the enquiry FORM still sends its confirmation to the client',
      'send_whatsapp_button_image_message(' in src
      and 'has been successfully submitted to ConnectLink Properties Admin' in src)
check('the manual path calls the shared confirmation helper',
      'send_enquiry_confirmation_to_client(' in
      src.split('def create_manual_enquiry(')[1].split('@app.route')[0])

fails = [r for r in RESULTS if r.startswith('FAIL')]
print('\n' + '=' * 70)
print('%d passed, %d failed' % (len(RESULTS) - len(fails), len(fails)))
sys.exit(1 if fails else 0)
