"""Consolidate imperceptible near-duplicate brand colours in the templates.

WHY
   22 templates contain 461 distinct hex colours. 43 custom properties even get
   *different values on different pages* (--primary alone means 6 different
   colours across 9 pages). That is the root of the "two competing design
   languages" feel. Most of the noise is near-duplicate navies/crimsons that
   nobody can tell apart.

WHAT THIS DOES
   Maps only colours that are imperceptible from a canonical brand colour
   (max per-channel delta <= 10) onto that canonical value - e.g. the 20+ dark
   navies within delta 10 of #1E293B become #1E293B, so every dark theme finally
   matches. Anything a human could actually see is left alone, because the
   instruction was to keep the existing colours.

SAFETY
   * touches ONLY CSS contexts: the inside of <style> blocks and style="..." attributes.
     Never <script> bodies, never markup, never JS/Chart.js colour values.
   * never touches static/css/design-system.css (it is the source of truth).
   * never rewrites a Tailwind-style scale token (--slate-*, --gray-*, --zinc-*,
     --neutral-*) - those are a deliberate systematic palette, not drift.
   * --apply is required to write anything; the default is a dry run.
   * after applying, _verify() proves every byte outside a CSS context is unchanged.

USAGE
   python _consolidate_palette.py           # dry run, prints the plan
   python _consolidate_palette.py --apply   # writes
"""
import re
import sys
import pathlib

ROOT = pathlib.Path(__file__).parent
TEMPLATES = sorted((ROOT / "templates").glob("*.html"))

# The brand colours, exactly as agreed in static/css/design-system.css.
CANONICAL = {
    "#c12b3e": "primary (brand crimson)",
    "#9e1f2e": "primary-dark",
    "#d54556": "primary-hover",
    "#1e293b": "navy",
    "#0f1b2d": "navy-deep",
}
MAX_DELTA = 10          # per-channel; imperceptible on any screen

HEX = re.compile(r"#[0-9a-fA-F]{6}\b")
SCALE_TOKEN = re.compile(r"--(slate|gray|grey|zinc|neutral|stone)-\d+\s*:")
STYLE_BLOCK = re.compile(r"(<style[^>]*>)(.*?)(</style>)", re.S)
STYLE_ATTR = re.compile(r'(style=")([^"]*)(")')


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def delta(a, b):
    return max(abs(x - y) for x, y in zip(rgb(a), rgb(b)))


def build_map(seen):
    """near-duplicate -> canonical, decided once, up front."""
    mapping = {}
    for h in sorted(seen, key=lambda k: -seen[k]):
        if h in CANONICAL:
            continue
        best, best_d = None, MAX_DELTA + 1
        for c in CANONICAL:
            d = delta(h, c)
            if d < best_d:
                best, best_d = c, d
        if best and best_d <= MAX_DELTA:
            mapping[h] = best
    return mapping


def css_regions(text):
    """(start, end) spans of the only places we are allowed to edit."""
    spans = []
    for m in STYLE_BLOCK.finditer(text):
        spans.append((m.start(2), m.end(2)))
    for m in STYLE_ATTR.finditer(text):
        spans.append((m.start(2), m.end(2)))
    return spans


def rewrite(text, mapping, stats):
    """Replace inside CSS regions only. Mirrors back-to-front so offsets hold."""
    out = text
    for start, end in sorted(css_regions(text), key=lambda s: -s[0]):
        region = text[start:end]
        # protect Tailwind-style scale tokens: --slate-800: #1e293b stays put
        protected = set()
        for m in SCALE_TOKEN.finditer(region):
            for h in HEX.finditer(region[m.end():m.end() + 12]):
                protected.add(m.end() + h.start())
        pieces, last = [], 0
        for m in HEX.finditer(region):
            if m.start() in protected:
                continue
            old = m.group(0).lower()
            new = mapping.get(old)
            if not new:
                continue
            pieces.append(region[last:m.start()])
            # keep the case style of the original
            pieces.append(new.upper() if m.group(0) != old else new)
            last = m.end()
            stats[old] = stats.get(old, 0) + 1
        pieces.append(region[last:])
        out = out[:start] + "".join(pieces) + out[end:]
    return out


def mask_css(text):
    """Blank out every CSS region (keeping its delimiters) for byte comparison.

    Both contexts must be masked - an earlier version only masked <style> blocks,
    so a perfectly legitimate change inside style="..." looked like an edit outside
    CSS and aborted the run.
    """
    text = STYLE_BLOCK.sub(lambda m: m.group(1) + m.group(3), text)
    text = STYLE_ATTR.sub(lambda m: m.group(1) + m.group(3), text)
    return text


def verify(before, after):
    """Prove the change is presentational only: everything that is NOT a CSS context
    must be byte-for-byte identical."""
    return mask_css(before) == mask_css(after)


def braces(text):
    """Brace counts cannot be asserted in absolute terms - profile.html and test1.html
    ship imbalanced braces inside JS/regex strings. Comparing before vs after is the
    meaningful check."""
    return (text.count("{"), text.count("}"))


def main():
    apply = "--apply" in sys.argv
    seen = {}
    for f in TEMPLATES:
        for h in HEX.findall(f.read_text(encoding="utf-8", errors="replace")):
            seen[h.lower()] = seen.get(h.lower(), 0) + 1

    mapping = build_map(seen)
    print(f"canonical brand colours : {len(CANONICAL)}")
    print(f"near-duplicates to fold : {len(mapping)} distinct literals")
    print(f"occurrences affected    : {sum(seen[h] for h in mapping)}\n")
    for h in sorted(mapping, key=lambda k: -seen[k]):
        print(f"  {h} x{seen[h]:<4} -> {mapping[h]}   (delta {delta(h, mapping[h])})")

    if not apply:
        print("\nDRY RUN - nothing written. Re-run with --apply")
        return

    print("\napplying...")
    total = {}
    for f in TEMPLATES:
        before = f.read_text(encoding="utf-8", errors="replace")
        after = rewrite(before, mapping, total)
        if after == before:
            continue
        if not verify(before, after):
            print(f"  !! ABORT {f.name}: a byte outside a CSS context changed")
            return
        if braces(before) != braces(after):
            print(f"  !! ABORT {f.name}: brace count changed {braces(before)} -> {braces(after)}")
            return
        f.write_text(after, encoding="utf-8")
        print(f"  {f.name:26s} {len(before):>9} -> {len(after):>9} bytes")

    print(f"\nreplaced {sum(total.values())} literals across {len(total)} distinct colours")
    for h, n in sorted(total.items(), key=lambda kv: -kv[1]):
        print(f"  {h} -> {mapping[h]}  x{n}")


if __name__ == "__main__":
    main()
