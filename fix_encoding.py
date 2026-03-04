# -*- coding: utf-8 -*-
import re, sys

path = r'c:\Users\Windows 11\Desktop\automacao-admissao\backend\api_admissao.py'
with open(path, 'r', encoding='utf-8') as f:
    text = f.read()

# Uppercase accented chars (double-encoded)
text = text.replace('\u00c3\u201c', '\u00d3')   # Ã" -> Ó
text = text.replace('\u00c3\u0192', '\u00c3')    # Ãƒ -> Ã
text = text.replace('\u00c3\u2030', '\u00c9')    # Ã‰ -> É
text = text.replace('\u00c3\u2021', '\u00c7')    # Ã‡ -> Ç
text = text.replace('\u00c3\u0160', '\u00da')    # Ãš -> Ú
text = text.replace('\u00c3\u2022', '\u00d5')    # Ã• -> Õ
text = text.replace('\u00c3\u0153', '\u00dc')    # Ãœ -> Ü
text = text.replace('\u00c3\u00160a', '\u00ca')  # ÃŠ -> Ê
text = text.replace('\u00c3\u0152', '\u00ca')    # keep trying patterns
text = text.replace('\u00c3\u20ac', '\u00c0')    # Ã€ -> À

# Fix ÃŠ specifically (Ê)
# ÃŠ = \xc3\x8a when double-encoded becomes Ã + Š
for line_idx, line in enumerate(text.split('\n')):
    pass  # just applying replacements above

# Box drawing (already mostly fixed, handle residuals)
# These are triple-byte UTF-8 chars that got double-encoded into 6 bytes
# â = \xc3\xa2, then the next 2 chars complete the sequence
box_replacements = [
    ('\u00e2\u0095\u0090', '\u2550'),  # ═
    ('\u00e2\u0095\u0094', '\u2554'),  # ╔
    ('\u00e2\u0095\u0097', '\u2557'),  # ╗
    ('\u00e2\u0095\u009a', '\u255a'),  # ╚
    ('\u00e2\u0095\u009d', '\u255d'),  # ╝
    ('\u00e2\u0095\u00a0', '\u2560'),  # ╠
    ('\u00e2\u0095\u00a3', '\u2563'),  # ╣
    ('\u00e2\u0095\u00a6', '\u2566'),  # ╦
    ('\u00e2\u0095\u00a9', '\u2569'),  # ╩
    ('\u00e2\u0095\u0091', '\u2551'),  # ║
]
for old, new in box_replacements:
    text = text.replace(old, new)

# Broader approach: find all remaining sequences starting with Ã or Â
# and try latin1->utf8 decode
def fix_remaining(text):
    """Try to fix any remaining double-encoded sequences character by character."""
    result = []
    i = 0
    chars = list(text)
    n = len(chars)

    while i < n:
        fixed = False
        # Try 4-char, 3-char, 2-char sequences
        for length in [4, 3, 2]:
            if i + length <= n:
                segment = ''.join(chars[i:i+length])
                try:
                    raw_bytes = segment.encode('latin-1')
                    decoded = raw_bytes.decode('utf-8')
                    if decoded != segment and len(decoded) < len(segment):
                        # Verify it's a real character, not garbage
                        if all(ord(c) > 31 for c in decoded):
                            result.append(decoded)
                            i += length
                            fixed = True
                            break
                except (UnicodeEncodeError, UnicodeDecodeError):
                    continue

        if not fixed:
            result.append(chars[i])
            i += 1

    return ''.join(result)

text = fix_remaining(text)

# Count remaining
remaining = len(re.findall(r'[\u00c3\u00c2]', text))
print(f'Remaining bad chars: {remaining}')

# Show sample
lines = text.split('\n')
for i in [64, 102, 210, 316, 762, 1092, 1404]:
    if i < len(lines):
        print(f'Line {i+1}: {lines[i][:120]}')

with open(path, 'w', encoding='utf-8') as f:
    f.write(text)
print('\nArquivo salvo!')
