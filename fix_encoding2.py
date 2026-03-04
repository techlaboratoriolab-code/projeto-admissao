# -*- coding: utf-8 -*-
import re, sys
sys.stdout.reconfigure(encoding='utf-8')

path = r'c:\Users\Windows 11\Desktop\automacao-admissao\backend\api_admissao.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Find all unique 2-3 char sequences starting with Ã or Â
remaining_contexts = set()
for m in re.finditer(r'[\u00c3\u00c2].{0,2}', text):
    s = m.group()
    remaining_contexts.add(repr(s[:3]))

print("Unique remaining patterns:")
for p in sorted(remaining_contexts):
    print(f"  {p}")

# Direct mapping of specific remaining mojibake patterns
# These are chars where latin-1 encode fails because they use
# Windows-1252 extended chars (0x80-0x9F range)
direct_fixes = {
    # Ã + smart quote/special -> uppercase accented
    # Ã\u201c = Ã + " (U+201C) -> this is Ó (C3 93, but 93 in cp1252 = ")
    # So the pattern is: original byte was read as cp1252 instead of latin-1
    '\u00c3\u201c': '\u00d3',   # Ó
    '\u00c3\u0192': '\u00c3',   # Ã
    '\u00c3\u2030': '\u00c9',   # É
    '\u00c3\u2021': '\u00c7',   # Ç
    '\u00c3\u0160': '\u00da',   # Ú
    '\u00c3\u2022': '\u00d5',   # Õ
    '\u00c3\u0153': '\u00dc',   # Ü
    '\u00c3\u0152': '\u00ca',   # Ê
    '\u00c3\u20ac': '\u00c0',   # À
    '\u00c3\u0178': '\u0178',   # Ÿ (unlikely but cover it)
    '\u00c3\u02dc': '\u00d8',   # Ø
    '\u00c3\u2019': '\u00d2',   # Ò (maybe)
    '\u00c3\u2018': '\u00d1',   # Ñ
    '\u00c3\u201d': '\u00d4',   # Ô
    '\u00c3\u2013': '\u00d6',   # Ö
    '\u00c3\u2014': '\u00d7',   # ×
    '\u00c3\u02c6': '\u00c8',   # È
    '\u00c3\u201e': '\u00d4',   # Ô alt
    # Â + control char mojibake
    '\u00c2\u00a0': '\u00a0',   # non-breaking space
    # Broken emoji/special sequences
    # â + windows-1252 chars
    '\u00e2\u0153\u2026': '\u2705',  # ✅
    '\u00e2\u0153\u0085': '\u2705',  # ✅ alt
    '\u00e2\u0153\u201c': '\u2714',  # ✔
    '\u00e2\u0153\u2014': '\u2717',  # ✗
    '\u00e2\u0152\u0152': '\u2764',  # possible heart
    '\u00e2\u0161\u00a0': '\u26a0',  # ⚠
    '\u00e2\u0080\u201c': '\u201c',  # "
    '\u00e2\u0080\u201d': '\u201d',  # "
    '\u00e2\u0080\u2122': '\u2019',  # '
    '\u00e2\u0080\u02dc': '\u2018',  # '
    '\u00e2\u0080\u201e': '\u2014',  # —
    '\u00e2\u0080\u0153': '\u201c',  # "
    '\u00e2\u0080\u009c': '\u201c',  # "
    '\u00e2\u0080\u009d': '\u201d',  # "
}

count = 0
for old, new in direct_fixes.items():
    c = text.count(old)
    if c > 0:
        count += c
        text = text.replace(old, new)
        print(f"  Fixed {repr(old)} -> {new} ({c} times)")

print(f"\nTotal fixes: {count}")

# Check remaining
remaining = list(re.finditer(r'[\u00c3\u00c2]', text))
print(f"Remaining Ã/Â: {len(remaining)}")

if remaining:
    lines = text.split('\n')
    shown = set()
    for m in remaining[:15]:
        ln = text[:m.start()].count('\n')
        if ln not in shown:
            shown.add(ln)
            line = lines[ln]
            # Get context around the char
            pos = m.start() - text[:m.start()].rfind('\n') - 1
            ctx = line[max(0,pos-5):pos+10]
            print(f"  Line {ln+1}: ...{repr(ctx)}... full: {line[:120]}")

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print("\nSalvo!")
