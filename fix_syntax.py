# -*- coding: utf-8 -*-
"""Fix the broken string in _tab_char_setup after bad patch"""
import re

SRC = r"f:\veo3\main.py"
with open(SRC, encoding="utf-8", errors="replace") as f:
    code = f.read()

# The bad multi-line Label text — fix it to a simpler concatenated string
# Find the broken section
old = '''        Label(guide, text=(
            "1\u20e3\ufe0f  B\u1ea5m 'Ch\u1ecdn \u1ea3nh nh\ufffd\ufffdn v\u1eadt' \u2192 ch\u1ecdn nhi\u1ec1u \u1ea3nh (kh\ufffdng gi\u1edbi h\u1ea1n)"
"            "2\u20e3\ufe0f  \u0110\u1eb7t t\u00ean ng\u1eafn g\u1ecdn cho t\u1eebng nh\u00e2n v\u1eadt  (VD: Alice, Bob, NhanVat1)"
"            "3\u20e3\ufe0f  B\u1ea5m 'Upload t\u1ea5t c\u1ea3 l\u00ean Flow' \u2014 tool t\u1ef1 upload theo th\u1ee9 t\u1ef1"
"            "4\u20e3\ufe0f  Sang tab 'T\u1ea1o Video' \u0111\u1ec3 generate video c\u00f3 nh\u00e2n v\u1eadt"
        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT'''

# Just find by searching for the broken pattern
import re
# Find and replace the broken Label guide text
broken_pat = r'Label\(guide, text=\(\s*"1[^\)]{0,500}\), bg=CARD, fg=TEXT, font=\("Segoe UI", 9\), justify=LEFT'
fixed_txt = ('Label(guide, text=(\n'
             '            "1. Chon anh nhan vat -> chon nhieu anh (khong gioi han)\\n"\n'
             '            "2. Dat ten ngan gon: Alice, Bob, NhanVat1...\\n"\n'
             '            "3. Upload tat ca len Flow\\n"\n'
             '            "4. Sang tab \'Tao Video\' de generate video co nhan vat"\n'
             '        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT')

m = re.search(broken_pat, code, re.DOTALL)
if m:
    code = code[:m.start()] + fixed_txt + code[m.end():]
    print("Fixed guide text in _tab_char_setup")
else:
    print("Pattern not found, searching manually...")
    # Find the problem area by line
    lines = code.splitlines()
    for i, l in enumerate(lines):
        if 'Bam' in l and 'nhan vat' in l and i < 1300:
            print(f"L{i+1}: {repr(l[:80])}")

with open(SRC, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile(SRC, doraise=True)
    print("OK - syntax valid")
except py_compile.PyCompileError as e:
    import sys; sys.stderr.write(str(e) + "\n")
    # Show problem line
    lines = code.splitlines()
    err_str = str(e)
    import re as re2
    m2 = re2.search(r'line (\d+)', err_str)
    if m2:
        ln = int(m2.group(1))
        for i in range(max(0,ln-3), min(len(lines), ln+3)):
            print(f"L{i+1}: {repr(lines[i][:100])}")
