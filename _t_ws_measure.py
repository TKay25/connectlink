"""Measure the workshop report's flowables so the page break can be reasoned about.

Patches `reportlab.platypus.SimpleDocTemplate.build` so NOTHING is drawn: the story is
wrapped flowable by flowable against the real A4 frame and the heights are printed.
Run:  python _t_ws_measure.py
"""
import reportlab.platypus as P
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm

ROWS = []


class Spy(P.SimpleDocTemplate):
    def build(self, story, **kw):
        avail_w = A4[0] - 28 * mm
        avail_h = A4[1] - 27 * mm
        print(f'frame: {avail_w / mm:.1f} x {avail_h / mm:.1f} mm')
        total = 0.0
        for f in story:
            name = type(f).__name__
            label = ''
            if name == 'Spacer':
                h = f.height
                label = f'spacer {h / mm:.1f}mm'
            else:
                try:
                    _w, h = f.wrap(avail_w, avail_h)
                except Exception as e:            # a flowable that cannot wrap
                    h = 0.0
                    label = f'WRAP FAILED {e}'
                t = getattr(f, 'text', None)
                if t:
                    label = str(t)[:46]
                if name == 'Table':
                    label = f'Table {len(f._cellvalues)} rows x {len(f._cellvalues[0])} cols :: {label}'
            ROWS.append((name, h))
            total += h
            print(f'  {h / mm:7.1f}mm  {name:12s} {label}')
        print(f'\nTOTAL {total / mm:.1f}mm against a {avail_h / mm:.1f}mm frame -> '
              f'{"ONE PAGE" if total <= avail_h else "SPILLS by %.1fmm" % ((total - avail_h) / mm)}')
        # where would the natural break fall?
        acc = 0.0
        for i, (name, h) in enumerate(ROWS, 1):
            acc += h
            if acc > avail_h:
                print(f'  first flowable past the frame: #{i} ({name}, {h / mm:.1f}mm)')
                break
        return None


P.SimpleDocTemplate = Spy
src = open(r"c:\Users\tzvakasikwa\OneDrive - CBZ Bank Limited\Documents\GitHub\connectlink\_t_ws_render.py",
           encoding='utf-8').read()
exec(compile(src, '_t_ws_render.py', 'exec'), {'__name__': '__main__'})
