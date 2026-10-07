"""Check the height of the PROJECT PROGRESS UPDATE modal (templates/adminpage.html,
`#updateModal`).

The form's body used to be pinned to `max-height: 450px`, so the dialog stayed
short on every screen and the fields scrolled inside a letterbox. The body now
takes whatever is left of the dialog after the header and the footer: the form is
a `display: flex; flex-direction: column` box inside `.modal-container` (which is
capped at 90vh and has `overflow: hidden`), and `.modal-body-custom` already
carries `flex: 1; min-height: 0; overflow-y: auto`, so it gives way to the leftover
height and scrolls its own fields. No height is pinned in pixels anywhere, so the
room that is left is used on every screen (a fixed allowance would be worse than
the 450px it replaced on a 600px-tall window).

The trap this checks for: a taller body that pushes "Save Changes" / "Close" past
the bottom of the 90vh container, where `overflow: hidden` would simply cut them
off. So the header and the footer have to be paid for out of the same 90vh.

How it is checked:
  * static: the old fixed cap is gone, the body carries no inline height at all,
    the form is the flex column that hands it the leftover height, and the ceiling
    it is measured against (90vh, flex column, overflow hidden) is still there. The
    mechanism is only sound while the header and the footer keep their natural
    height -- the footer has no `flex-wrap`, so it cannot grow a second row, and
    nothing in JS re-caps the body afterwards.
  * rendered: the real `#updateModal` markup is lifted out of the template with
    the dialog's own rules from the page plus the two shared sheets (in the page's
    own order), and measured in Chromium at several window sizes, down to 600px
    tall: the dialog really grows to the 90vh the page allows, the header and the
    footer keep their natural height, the body really takes every pixel left between
    them, the form overflows its box and scrolls, the footer is fully inside the
    container, the container is fully inside the window -- and, put back, the old
    fixed 450px body inside a block form, measured in the same page: the dialog is
    never drawn shorter than that was, it is at least 100px taller wherever the
    screen has the room, and where the old layout pushed the footer past the
    container's bottom (a 600px-tall window) the new one does not. The heights that
    have to add up are layout boxes, because design-system.css scales this dialog to
    95% and only resets that for `.modal-content`; see the note at MEASURE below.
    Caveat: Bootstrap comes from a CDN on the real page and is not fetched here,
    so the form's grid is not exercised; the dialog's chrome (the part this change
    touches) is, because its CSS lives in the page itself.

Run:  python _check_update_modal_height.py   (writes _check_update_modal_height_out.txt)
"""
import os
import pathlib
import re
import tempfile

ROOT = pathlib.Path(__file__).parent
TEMPLATE = 'templates/adminpage.html'
OUT = '_check_update_modal_height_out.txt'

RESULTS = []


def _flush():
    try:
        with open(OUT, 'w', encoding='utf-8') as fh:
            fh.write('\n'.join(RESULTS) + '\n')
    except Exception:                                                  # noqa: BLE001
        pass


def check(name, ok, detail=''):
    RESULTS.append(f"{'PASS' if ok else 'FAIL'}  {name}"
                   f"{('  -> ' + detail) if detail else ''}")
    _flush()


def strip_jinja(text):
    return re.sub(r'\{[{%].*?[}%]\}', '', text, flags=re.S)


check('script started', True)

PAGE = (ROOT / TEMPLATE).read_text(encoding='utf-8')
check('read the admin page', True, '%d chars' % len(PAGE))

# ---------------------------------------------------------------- static checks
# The slice that belongs to this modal only: from its own <div> to the end of the
# modal (the next comment is the start of the following one).
start = PAGE.index('id="updateModal"')
start = PAGE.rindex('<div', 0, start)
end = PAGE.index('<!-- CHANGE INSTALLMENT DATE MODAL', start)
MODAL = PAGE[start:end]
check('the PROJECT PROGRESS UPDATE modal is still in the page',
      'PROJECT PROGRESS UPDATE' in MODAL and len(MODAL) > 5000,
      '%d chars from the template' % len(MODAL))

body_tags = re.findall(r'<div class="modal-body-custom"([^>]*)>', MODAL)
check('the modal still has exactly one scrolling body', len(body_tags) == 1,
      '%d found' % len(body_tags))
BODY_ATTRS = body_tags[0] if body_tags else ''
BODY_STYLE = (re.search(r'style="([^"]*)"', BODY_ATTRS).group(1)
              if 'style="' in BODY_ATTRS else '')

check('the fixed 450px cap that kept the form in a letterbox is gone',
      '450px' not in BODY_STYLE and 'max-height: 450px' not in MODAL,
      BODY_STYLE or 'no inline style on the body')
check('no height is pinned on the body at all, so it can take what is left',
      'max-height' not in BODY_STYLE, BODY_STYLE or 'no inline style on the body')
check('the body carries no inline sizing, so the stylesheet is what sizes it',
      not re.search(r'(max-height|height|overflow)', BODY_STYLE),
      BODY_STYLE or 'no inline style on the body')
form_tags = re.findall(r'<form id="updateProjectForm"[^>]*>', MODAL)
check('the form is a flex column, which is what hands the body the leftover height',
      len(form_tags) == 1 and 'display: flex' in form_tags[0]
      and 'flex-direction: column' in form_tags[0] and 'min-height: 0' in form_tags[0],
      form_tags[0] if form_tags else 'form not found')
check('the dialog still keeps its width (only the height changed)',
      'class="modal-container xlarge"' in MODAL)

# The ceiling the calc is measured against must still be the real one.
container = re.search(r'\n\.modal-container \{(.*?)\n\}',
                      PAGE, re.S).group(1)
check('the dialog is still capped at 90vh by .modal-container',
      'max-height: 90vh' in container)
check('and that cap still hides any overflow (so a mis-sized body would be cut off)',
      'overflow: hidden' in container and 'flex-direction: column' in container,
      'flex column: header + form, nothing else')

# Why 120px is enough for the header and the footer, on every screen.
footer = re.search(r'\n\.modal-footer-custom \{(.*?)\n\}', PAGE, re.S).group(1)
check('the footer cannot wrap onto a second row (its height is fixed)',
      'flex-wrap' not in footer, 'padding 8px 14px, one row of buttons')
header = re.search(r'\n\.modal-header-custom \{(.*?)\n\}', PAGE, re.S).group(1)
check('the header cannot grow with the dialog either',
      'flex: 0 0 auto' in header, 'padding 10px 14px')
body_rule = re.search(r'\n\.modal-body-custom \{(.*?)\n\}', PAGE, re.S).group(1)
check('the body is the part that gives way, and it scrolls',
      'flex: 1' in body_rule and 'min-height: 0' in body_rule
      and 'overflow-y: auto' in body_rule)
check('no script re-caps the body behind the stylesheet',
      'maxHeight' not in PAGE, 'nothing in the page sets .style.maxHeight')

# The buttons that must never be pushed out of sight.
for label in ('Save Changes', 'Delete Project', '>Close<'):
    check('the footer still carries "%s"' % label.strip('><'), label in MODAL)


# ------------------------------------------------------------- rendered checks
LOG = ROOT / '_check_update_modal_height_log.txt'
try:
    LOG.unlink()
except Exception:                                                      # noqa: BLE001
    pass


def stage(msg):
    """Leave a trail: a silent death (no traceback, no more output) is otherwise
    impossible to tell from a hang."""
    try:
        with LOG.open('a', encoding='utf-8') as fh:
            fh.write(msg + '\n')
    except Exception:                                                  # noqa: BLE001
        pass


def css_rule(css_text, selector):
    """`selector { ... }` copied out of the page verbatim (first match)."""
    hit = re.search(r'(?m)^[ \t]*' + re.escape(selector) + r'\s*\{', css_text)
    if not hit:
        return ''
    depth = 0
    for i in range(hit.end() - 1, len(css_text)):
        if css_text[i] == '{':
            depth += 1
        elif css_text[i] == '}':
            depth -= 1
            if depth == 0:
                return css_text[hit.start():i + 1].strip()
    return ''


# Only the dialog's own rules are carried over (the page repeats its whole
# stylesheet several times, which is megabytes of CSS and none of it is what is
# being measured). These are the rules that size the dialog and its three rows.
DIALOG_SELECTORS = [
    '.modal-overlay', '.modal-overlay.active', '.modal-container',
    '.modal-container.xlarge', '.modal-header-custom', '.modal-header-custom h3',
    '.close-modal', '.modal-body-custom', '.modal-footer-custom',
    '.modal-footer-custom .btn',
]
DIALOG_CSS = [css_rule(PAGE, sel) for sel in DIALOG_SELECTORS]
missing = [sel for sel, css in zip(DIALOG_SELECTORS, DIALOG_CSS) if not css]
check('every rule that sizes the dialog was found in the page', not missing,
      '%d rules copied verbatim' % len(DIALOG_CSS) if not missing else str(missing))
check('the rule that sizes the dialog comes from the page as shipped',
      'max-height: 90vh' in css_rule(PAGE, '.modal-container')
      and 'overflow: hidden' in css_rule(PAGE, '.modal-container'))

# The buttons' metrics come from the shared house sheet, so the footer's real
# height is used rather than the browser's default button box.
HOUSE = []
for name in ('static/css/design-system.css', 'static/css/components-ui.css'):
    path = ROOT / name
    if path.exists():
        HOUSE.append(path.read_text(encoding='utf-8'))
check('the shared house stylesheets are on disk', len(HOUSE) == 2,
      ', '.join('%s %d chars' % (n, len(h))
                for n, h in zip(('design-system.css', 'components-ui.css'), HOUSE)))

shown = MODAL.replace('<div id="updateModal" class="modal-overlay">',
                      '<div id="updateModal" class="modal-overlay active">', 1)
check('the modal is opened the way openModal() opens it', 'modal-overlay active' in shown)
check('the markup that was lifted out is well formed',
      shown.count('<div') == shown.count('</div>'),
      '%d <div> vs %d </div>' % (shown.count('<div'), shown.count('</div>')))

harness = (
    '<!DOCTYPE html>\n<html><head><meta charset="utf-8">\n<style>\n'
    + '\n'.join(HOUSE) + '\n'
    + '\n\n'.join(DIALOG_CSS) + '\n'
    # Harness only: freeze the entry animations so every box below is final.
    + '*{animation:none !important;transition:none !important;}\n'
    + '</style></head><body>\n' + strip_jinja(shown) + '\n</body></html>\n'
)
dirpath = pathlib.Path(tempfile.mkdtemp(prefix='update_modal_'))
HARNESS = dirpath / 'update_modal_preview.html'
HARNESS.write_text(harness, encoding='utf-8')
stage('harness written: %d chars' % len(harness))
check('the preview was built from the page as shipped', True,
      '%s (%d chars)' % (HARNESS.name, len(harness)))

# One read: the dialog as it is now, then the layout it replaced -- the body put
# back to the fixed 450px cap inside a block form -- and the boxes that must stay
# on screen.
#
# Note: the page's own .modal-container rule gives the dialog its 90vh cap, but
# design-system.css (`.modal-content, .modal-container, .login-modal`) also puts
# `transform: scale(0.95) translateY(10px)` on it and only resets that for
# `.modal-content`, so this dialog is always drawn 5% smaller than its layout box
# and 9.5px lower. Every getBoundingClientRect() here is therefore scaled: the
# heights that have to add up are read as layout boxes (offsetHeight/clientHeight,
# which transforms do not touch), and the rects are only used to ask "is it inside
# something else", where both sides are scaled the same way.
MEASURE = """() => {
    const body = document.querySelector('#updateModal .modal-body-custom');
    const cont = document.querySelector('#updateModal .modal-container');
    const foot = document.querySelector('#updateModal .modal-footer-custom');
    const head = document.querySelector('#updateModal .modal-header-custom');
    const form = document.querySelector('#updateModal form');
    const read = () => {
        const c = cont.getBoundingClientRect(), f = foot.getBoundingClientRect();
        const b = body.getBoundingClientRect();
        return {dialog: cont.offsetHeight,          // layout box, transform-free
                inner: cont.clientHeight,           // what the rows really share
                body: body.clientHeight, head: head.offsetHeight, foot: foot.offsetHeight,
                rectDialog: Math.round(c.height), rectTop: Math.round(c.top),
                rectBottom: Math.round(c.bottom), rectFootBottom: Math.round(f.bottom),
                bBottom: Math.round(b.bottom),
                clipped: Math.round(f.bottom - c.bottom),
                scrolls: body.scrollHeight > body.clientHeight + 1,
                hidden: Math.round(body.scrollHeight - body.clientHeight),
                vh: innerHeight};
    };
    const savedBody = body.getAttribute('style');
    const savedForm = form.getAttribute('style');
    const now = read();
    body.setAttribute('style', 'max-height: 450px; overflow-y: auto;');   // the old cap
    form.setAttribute('style', 'display: block;');                        // the old block form
    const before = read();
    if (savedBody === null) { body.removeAttribute('style'); }
    else { body.setAttribute('style', savedBody); }
    if (savedForm === null) { form.removeAttribute('style'); }
    else { form.setAttribute('style', savedForm); }
    return {now: now, before: before};
}"""

from playwright.sync_api import sync_playwright                          # noqa: E402

VIEWPORTS = [(1920, 1080), (1440, 900), (1366, 768), (1280, 720), (1280, 600)]

try:
    stage('imported playwright')
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        stage('chromium up')
        page = browser.new_page()
        page.set_default_timeout(20000)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)[:160]))
        # No external network: the CDN sheets are not part of what is being measured
        # and reaching for them only makes the run slow and flaky.
        page.route(re.compile(r'https?://'), lambda r: r.abort())
        page.goto(HARNESS.as_uri(), wait_until='load', timeout=30000)
        stage('preview loaded')
        check('the modal renders in a real browser',
              page.evaluate('() => getComputedStyle('
                            'document.getElementById("updateModal")).display') == 'flex')
        check('the modal is on screen, exactly as the real page opens it',
              page.evaluate('() => document.getElementById("updateModal")'
                            '.classList.contains("active")'))

        for width, height in VIEWPORTS:
            page.set_viewport_size({'width': width, 'height': height})
            page.wait_for_timeout(250)
            m = page.evaluate(MEASURE)
            stage('measured %dx%d' % (width, height))
            now, before = m['now'], m['before']
            tag = '%dx%d' % (width, height)
            cap = round(0.9 * height)
            fits = now['inner'] - now['head'] - now['foot']
            check('%s: the dialog fills the 90vh it is allowed' % tag,
                  abs(now['dialog'] - cap) <= 2,
                  'dialog %dpx of layout, 90vh = %dpx' % (now['dialog'], cap))
            check('%s: the body takes exactly the room left between header and footer' % tag,
                  abs(now['body'] - fits) <= 3,
                  'body %dpx, %dpx left in the dialog (header %dpx + footer %dpx)'
                  % (now['body'], fits, now['head'], now['foot']))
            check('%s: the footer (Save Changes / Close) is fully inside the dialog' % tag,
                  now['rectFootBottom'] <= now['rectBottom'] + 1,
                  'footer bottom %dpx, dialog bottom %dpx'
                  % (now['rectFootBottom'], now['rectBottom']))
            check('%s: the dialog is inside the window, top and bottom' % tag,
                  now['rectTop'] >= -1 and now['rectBottom'] <= now['vh'] + 1,
                  'top %dpx, bottom %dpx, window %dpx'
                  % (now['rectTop'], now['rectBottom'], now['vh']))
            check('%s: the body ends above the footer, not under it' % tag,
                  now['bBottom'] <= now['rectFootBottom'] + 1,
                  'body bottom %dpx, footer bottom %dpx' % (now['bBottom'], now['rectFootBottom']))
            check('%s: the form is longer than its box, so it scrolls' % tag,
                  now['scrolls'] and now['hidden'] > 50,
                  '%dpx of fields below the fold' % now['hidden'])
            check('%s: the dialog is never shorter on screen than the old fixed 450px one' % tag,
                  now['rectDialog'] >= before['rectDialog'] - 1,
                  'dialog %dpx, was %dpx (header + 450px + footer = %dpx of layout)'
                  % (now['rectDialog'], before['rectDialog'], before['dialog']))
            check('%s: and it is at least 100px taller of layout, or as tall as the cap allows' % tag,
                  now['dialog'] >= min(before['dialog'] + 100, cap - 1),
                  'dialog %dpx of layout, was %dpx under the old cap, 90vh = %dpx'
                  % (now['dialog'], before['dialog'], cap))
            if before['clipped'] > 0:
                check('%s: the old cap used to push the footer %dpx past the dialog; it cannot now'
                      % (tag, before['clipped']),
                      now['rectFootBottom'] <= now['rectBottom'] + 1,
                      'the old dialog overflowed by %dpx and overflow: hidden cut it off'
                      % before['clipped'])
            else:
                check('%s: the form shows at least the 450px the old cap allowed' % tag,
                      now['body'] >= before['body'] - 3,
                      '%dpx of form, was %dpx' % (now['body'], before['body']))

        check('no page error was raised while the modal was opened', not errors,
              str(errors[:2]))
        stage('all viewports measured')
        browser.close()
except Exception as exc:                                              # noqa: BLE001
    check('the rendered half ran to the end', False,
          '%s: %s' % (type(exc).__name__, exc))

failed = [line for line in RESULTS if line.startswith('FAIL')]
print('\n'.join(RESULTS))
print('\n%d checks, %d FAIL' % (len(RESULTS), len(failed)))
try:
    HARNESS.unlink()
    dirpath.rmdir()
except Exception:                                                     # noqa: BLE001
    pass
if not failed:                                                        # keep the trail on a FAIL
    try:
        LOG.unlink()
    except Exception:                                                 # noqa: BLE001
        pass
raise SystemExit(1 if failed else 0)
