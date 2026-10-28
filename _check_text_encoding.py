"""The app must ship real characters, not UTF-8 that was read back as cp1252.

Mojibake in the source is not a display problem: the WhatsApp webhook sent the
bot's greeting to clients as the literal bytes `ðŸ‘‹`, so every customer received
four garbage characters instead of a waving hand. This check fails if any of it
comes back, in the backend or in the templates.

Run:  python _check_text_encoding.py
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
TARGETS = [os.path.join(ROOT, 'ConnectLink.py')] + [
    os.path.join(ROOT, 'templates', name)
    for name in sorted(os.listdir(os.path.join(ROOT, 'templates')))
    if name.endswith('.html')
]
OUT = os.path.join(ROOT, '_check_text_encoding_out.txt')
RESULTS = []

# The leading characters of a UTF-8 sequence read as cp1252. None of them has any
# business appearing in this project's text.
LEADERS = 'ðâÃïÂŸ'
RUN = re.compile(r'[^\x00-\x7f]{1,}')


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])


def repair(chunk):
    """What the run should be, or None if it is already correct."""
    for enc in ('cp1252', 'latin-1'):
        try:
            fixed = chunk.encode(enc).decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            continue
        if fixed != chunk:
            return fixed
    return None


total_repairable = 0
total_leaders = 0
for path in TARGETS:
    label = os.path.relpath(path, ROOT)
    raw = open(path, 'rb').read()
    try:
        text = raw.decode('utf-8')
    except UnicodeDecodeError as exc:
        check(f'{label} is valid UTF-8', False, str(exc))
        continue
    check(f'{label} is valid UTF-8', True)
    if label == 'ConnectLink.py':
        check(f'{label} carries no byte-order mark', not raw.startswith(b'\xef\xbb\xbf'))

    repairable = []
    leaders = []
    for n, line in enumerate(text.split('\n'), 1):
        for m in RUN.finditer(line):
            if repair(m.group(0)) is not None:
                repairable.append((n, m.group(0), repair(m.group(0))))
        for ch in line:
            if ch in LEADERS:
                leaders.append(n)
                break
    total_repairable += len(repairable)
    total_leaders += len(leaders)
    check(f'{label} has no re-decodable mojibake',
          not repairable, repairable[:4])
    check(f'{label} shows no cp1252 lead characters',
          not leaders, leaders[:8])

src = open(os.path.join(ROOT, 'ConnectLink.py'), encoding='utf-8').read()
check('the WhatsApp greeting carries a real waving hand',
      '\U0001f44b Hey {profile_name}' in src)
check('the greeting footer carries a real bullet',
      'ConnectLink Properties \u2022 Client Panel' in src)
check('no replacement glyph (U+FFFD) was left behind',
      '\ufffd' not in src)
check('no private-use code point was left behind',
      not re.search(r'[\ue000-\uf8ff]', src),
      re.findall(r'[\ue000-\uf8ff]', src)[:5])

with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(RESULTS) + '\n')

failures = [r for r in RESULTS if r.startswith('FAIL')]
print('\n%d checks, %d failed' % (len(RESULTS), len(failures)))
sys.exit(1 if failures else 0)
