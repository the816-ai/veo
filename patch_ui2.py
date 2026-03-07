# -*- coding: utf-8 -*-
"""Patch 2: Theming remaining tabs with dark colors inline using string replacement"""
import re

SRC = r"f:\veo3\main.py"
with open(SRC, encoding="utf-8") as f:
    code = f.read()

# ── Thay các màu cũ sang dark theme ──
replacements = [
    # LabelFrame thường sang dark
    ('LabelFrame(f,', 'LabelFrame(f, bg=CARD, fg=ACCENT,'),
    ('LabelFrame(f,  bg=CARD', 'LabelFrame(f, bg=CARD'),  # tránh double
    # Frame thường nền trắng → dark
    ('Frame(self.nb)', 'Frame(self.nb, bg=BG)'),
    # Tab labels cũ → mới
    ('"📝 Text to Video"', '"📝  Text to Video"'),
    ('"👤 Character Setup"', '"👤  Nhân Vật"'),
    ('"📋 Logs"', '"📋  Logs"'),
    ('"🎞 Merge Videos"', '"🎬  Ghép Video"'),
    ('"🏗 Create Video"', '"🎞  Tạo Video"'),
    # Scrolledtext log area
    ('bg="#1E1E1E", fg="#D4D4D4"', f'bg=CARD, fg=TEXT'),
]

for old, new in replacements:
    code = code.replace(old, new)

# ── Sửa các nút Button sang dark style chuyên nghiệp ──
# Chỉ sửa font Arial → Segoe UI trong các nút
code = re.sub(r'font=\("Arial", (\d+), "bold"\)', r'font=("Segoe UI", \1, "bold")', code)
code = re.sub(r'font=\("Arial", (\d+)\)', r'font=("Segoe UI", \1)', code)
code = re.sub(r'font=\("Consolas", (\d+)\)', r'font=("Consolas", \1)', code)

# ── ScrolledText và Label bg fix ──
# Thay nền trắng mặc định cho ScrolledText trong các tab
code = code.replace(
    'self.char_list = scrolledtext.ScrolledText(list_lf, height=10, font=("Consolas", 9), state=DISABLED)',
    'self.char_list = scrolledtext.ScrolledText(list_lf, height=10, font=("Consolas", 9), state=DISABLED, bg=CARD, fg=TEXT, relief="flat")'
)
code = code.replace(
    'self.cv_prompts = scrolledtext.ScrolledText(lf, height=8, font=("Consolas", 9))',
    'self.cv_prompts = scrolledtext.ScrolledText(lf, height=8, font=("Consolas", 9), bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")'
)
code = code.replace(
    'self.tv_prompts = scrolledtext.ScrolledText(lf, height=10, font=("Consolas\", 9))',
    'self.tv_prompts = scrolledtext.ScrolledText(lf, height=10, font=("Consolas", 9), bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")'
)
# Fix tv_prompts quoting issue
code = code.replace(
    'self.tv_prompts = scrolledtext.ScrolledText(lf, height=10, font=("Consolas", 9))',
    'self.tv_prompts = scrolledtext.ScrolledText(lf, height=10, font=("Consolas", 9), bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")'
)

# ── Sửa ProgressBar style ──
code = code.replace(
    'self.tv_progress = ttk.Progressbar(f, mode="indeterminate")',
    'self.tv_progress = ttk.Progressbar(f, mode="indeterminate", style="TProgressbar")'
)
code = code.replace(
    'self.cv_progress = ttk.Progressbar(f, mode="indeterminate")',
    'self.cv_progress = ttk.Progressbar(f, mode="indeterminate", style="TProgressbar")'
)

# ── Sửa nút START/RAPID nếu chưa đúng ──
code = code.replace(
    'bg="#2E7D32"', f'bg=GREEN'
)
code = code.replace(
    'bg="#E65100"', f'bg=ORANGE'
)
code = code.replace(
    'bg="#B71C1C"', f'bg=RED'
)
code = code.replace(
    'bg="#C62828"', f'bg=RED'
)
code = code.replace(
    'bg="#1565C0"', f'bg=ACCENT'
)

with open(SRC, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile(SRC, doraise=True)
    print("OK - syntax valid")
except py_compile.PyCompileError as e:
    print(f"ERROR: {e}")
