"""Syntax-check ConnectLink.py alone (the big file) and record the verdict.

Kept separate from _check.py because reading + parsing ~19k lines is slow enough
that the shell teardown can interrupt a combined run.
"""
import ast

try:
    with open('ConnectLink.py', encoding='utf-8') as fh:
        ast.parse(fh.read(), filename='ConnectLink.py')
    verdict = 'CONNECTLINK_SYNTAX_OK'
except SyntaxError as exc:
    verdict = f'CONNECTLINK_SYNTAX_FAIL line {exc.lineno}: {exc.msg}'
except Exception as exc:                                   # noqa: BLE001
    verdict = f'CONNECTLINK_SYNTAX_FAIL {type(exc).__name__}: {exc}'

with open('_syntax_out.txt', 'w', encoding='utf-8') as fh:
    fh.write(verdict + '\n')
