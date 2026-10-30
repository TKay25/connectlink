"""Every inline <script> block in adminpage.html must survive parsing.

Two things have bitten this page before:

  * a block on its own can be malformed, which silently deletes every function
    it defines;
  * a `var x` in an early block plus a `let x` in a later block is a
    redeclaration error in the shared global scope, so the LATER block dies
    (this is what once took out the whole quotation block, and with it the
    quotation PDF).

Running the blocks through `node --check` finds both: individually for the
first, and concatenated in source order for the second (the global scope is
shared, so concatenation reproduces the clash).

Run:  python _check_admin_inline_scripts.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(ROOT, 'templates', 'adminpage.html')
OUT = os.path.join(ROOT, '_check_admin_inline_scripts_out.txt')
RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append(('PASS  ' if ok else 'FAIL  ') + name + (('  -> ' + str(detail)) if detail else ''))
    print(RESULTS[-1])


def strip_comments(code):
    """Blank out comments so `// {` cannot unbalance the block splitter."""
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.S)
    return re.sub(r'(?m)(^|[^:\\])//[^\n]*', r'\1', code)


def syntax_error(code, workdir, tag):
    path = os.path.join(workdir, tag + '.js')
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(code)
    proc = subprocess.run(['node', '--check', path], capture_output=True, text=True)
    if proc.returncode == 0:
        return None
    err = (proc.stderr or '').strip().splitlines()
    return ' | '.join(line.strip() for line in err[:4])[:300]


SRC = open(TEMPLATE, encoding='utf-8').read()
BLOCKS = re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>', SRC, re.S)
check('the page still has its inline script blocks', len(BLOCKS) > 30, '%d blocks' % len(BLOCKS))

if shutil.which('node') is None:
    check('node is available to parse the blocks', False, 'install node')
else:
    WORK = tempfile.mkdtemp(prefix='clq_js_')
    try:
        broken = []
        for index, body in enumerate(BLOCKS):
            err = syntax_error(body, WORK, 'block_%02d' % index)
            if err:
                broken.append((index, err))
        check('every inline block parses on its own', not broken,
              broken[:3] if broken else '%d blocks' % len(BLOCKS))

        joined = '\n;\n'.join(BLOCKS)
        err = syntax_error(joined, WORK, 'all_blocks')
        check('no block is killed by a global redeclaration in an earlier block', err is None, err or '')

        # The names the quotation builders and their helpers live on: if the block
        # holding them dies, these are the ones that go missing.
        for name in ('generateQuotationPDF', 'generateKitchenPDF',
                     'downloadQuotationPDFFromPortal'):
            check('the page still defines %s' % name, name in SRC)
    finally:
        shutil.rmtree(WORK, ignore_errors=True)

with open(OUT, 'w', encoding='utf-8') as fh:
    fh.write('\n'.join(RESULTS) + '\n')

failures = [r for r in RESULTS if r.startswith('FAIL')]
print('\n%d checks, %d failed' % (len(RESULTS), len(failures)))
sys.exit(1 if failures else 0)
