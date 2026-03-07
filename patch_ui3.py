# -*- coding: utf-8 -*-
"""
Patch 3: Apply dark theme comprehensively to all remaining tabs.
Strategy: Replace entire tab-building methods using string injection.
"""
import sys, re

SRC = r"f:\veo3\main.py"
with open(SRC, encoding="utf-8") as f:
    code = f.read()

# ── Helper: replace between two markers ──
def replace_between(code, start_marker, end_marker, new_content):
    s = code.find(start_marker)
    e = code.find(end_marker, s)
    if s == -1 or e == -1:
        print(f"WARNING: marker not found: {start_marker[:40]!r}")
        return code
    return code[:s] + new_content + code[e:]

# ═══════════════════════════════════
# 1. _tab_text2video — full dark rewrite
# ═══════════════════════════════════
NEW_T2V = '''    # ── TAB 3: Text to Video ──────────────────────────────
    def _tab_text2video(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="📝  Text to Video")

        # Prompts
        lf = self._card(f, "📝 Danh sách Prompt  (mỗi dòng 1 lệnh — hỗ trợ JSON)")
        lf.pack(fill=BOTH, expand=True, padx=12, pady=(10,4))

        mode_f = Frame(lf, bg=CARD); mode_f.pack(anchor=W, pady=(4,2))
        Label(mode_f, text="Định dạng nhập:  ", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.tv_mode = StringVar(value="normal")
        for txt, val in [("Thông thường (mỗi dòng 1 prompt)", "normal"),
                          ("JSON nâng cao (scene_1, scene_2...)", "json")]:
            Radiobutton(mode_f, text=txt, variable=self.tv_mode, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=6)

        self.tv_prompts = scrolledtext.ScrolledText(
            lf, height=10, font=("Consolas", 9),
            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.tv_prompts.pack(fill=BOTH, expand=True, pady=(2,6))
        self.tv_prompts.insert(END, "A cinematic sunset over the ocean, 8K, dramatic lighting\\n"
                                    "A futuristic city at night, neon lights, rain, blade runner style")

        # Settings
        sf = self._card(f, "⚙️ Cài đặt đầu ra")
        sf.pack(fill=X, padx=12, pady=4)
        r1 = Frame(sf, bg=CARD); r1.pack(fill=X, pady=3, padx=8)
        Label(r1, text="Tên file:", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.tv_base = Entry(r1, width=20, font=("Segoe UI", 9),
                             bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.tv_base.insert(0, "video")
        self.tv_base.pack(side=LEFT, padx=6, ipady=3)
        Label(r1, text="→  video_01.mp4, video_02.mp4, ...",
              bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(side=LEFT)

        r2 = Frame(sf, bg=CARD); r2.pack(fill=X, pady=3, padx=8)
        Label(r2, text="Lưu tại:", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.tv_out = Entry(r2, width=55, font=("Segoe UI", 9),
                            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.tv_out.insert(0, OUTPUT_DIR_TEXT)
        self.tv_out.pack(side=LEFT, padx=6, ipady=3)
        self._btn(r2, "📂", lambda: self._browse(self.tv_out),
                  color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)

        # Delay
        df = self._card(f, "⏱ Độ trễ giữa các prompt")
        df.pack(fill=X, padx=12, pady=4)
        df_r = Frame(df, bg=CARD); df_r.pack(anchor=W, padx=8, pady=4)
        self.tv_delay = StringVar(value="normal")
        for txt, val in [("Bình thường (5s)", "normal"),
                          ("Gấp đôi (10s)", "double"),
                          ("Ngẫu nhiên (6-15s)", "random")]:
            Radiobutton(df_r, text=txt, variable=self.tv_delay, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=8)

        # Timeout
        tf = self._card(f, "⬇️ Chờ video xong → Tự động tải (thoát sớm khi xong)")
        tf.pack(fill=X, padx=12, pady=4)
        self.tv_timeout = StringVar(value="600")
        timeout_opts = [
            ("TỰ ĐỘNG — Chờ đến khi xong, tối đa 10 phút  ⬇️  Tải ngay", "600"),
            ("Tối đa 5 phút  ⬇️  Tải ngay khi xong", "300"),
            ("Tối đa 3 phút  ⬇️  Tải ngay khi xong", "180"),
            ("Tối đa 1 phút  ⬇️  Tải ngay khi xong", "60"),
            ("30 giây  (submit nhanh, không tải về)", "30"),
        ]
        for txt, val in timeout_opts:
            Radiobutton(tf, text=txt, variable=self.tv_timeout, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(anchor=W, padx=12)
        Label(tf, text="  ℹ️  Tool thoát ngay khi video xong, không cần đợi hết giờ!",
              font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(anchor=W, padx=20, pady=(0,4))

        # Progress + buttons
        self.tv_progress = ttk.Progressbar(f, mode="indeterminate", style="TProgressbar")
        self.tv_progress.pack(fill=X, padx=12, pady=(6,2))
        self.tv_status_lbl = Label(f, text="", font=("Segoe UI", 8), bg=BG, fg=MUTED)
        self.tv_status_lbl.pack()

        btn_row = Frame(f, bg=BG); btn_row.pack(fill=X, padx=12, pady=8)
        self._btn(btn_row, "  ▶  START — Tuần tự + Tải về",
                  self._start_text2video, color=GREEN
                  ).pack(side=LEFT, fill=X, expand=True, ipady=9, padx=(0,4))
        self._btn(btn_row, "  ⚡  RAPID — Submit nhanh, render song song",
                  self._start_rapid, color=ORANGE
                  ).pack(side=LEFT, fill=X, expand=True, ipady=9, padx=(0,4))
        self._btn(btn_row, "  ⏹  STOP",
                  self._stop, color=RED
                  ).pack(side=LEFT, ipady=9, ipadx=8)

'''

# ═══════════════════════════════════
# 2. _tab_char_setup
# ═══════════════════════════════════
NEW_CHAR = '''    # ── TAB 4: Nhân Vật ─────────────────────────────────
    def _tab_char_setup(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="👤  Nhân Vật")

        # Hướng dẫn
        guide = self._card(f, "📋 Hướng dẫn")
        guide.pack(fill=X, padx=12, pady=(10,5))
        Label(guide, text=(
            "1️⃣  Bấm 'Chọn ảnh nhân vật' → chọn nhiều ảnh (không giới hạn)\n"
            "2️⃣  Đặt tên ngắn gọn cho từng nhân vật  (VD: Alice, Bob, NhanVat1)\n"
            "3️⃣  Bấm 'Upload tất cả lên Flow' — tool tự upload theo thứ tự\n"
            "4️⃣  Sang tab 'Tạo Video' để generate video có nhân vật"
        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT
        ).pack(anchor=W, padx=10, pady=8)

        # Danh sách nhân vật
        list_lf = self._card(f, "📂 Danh sách nhân vật  (tên: đường dẫn ảnh)")
        list_lf.pack(fill=BOTH, expand=True, padx=12, pady=5)
        self.char_list = scrolledtext.ScrolledText(
            list_lf, height=9, font=("Consolas", 9), state=DISABLED,
            bg="#0D1117", fg=TEXT, relief="flat")
        self.char_list.pack(fill=BOTH, expand=True, padx=4, pady=4)

        # Nút thao tác
        btn_f = Frame(f, bg=BG); btn_f.pack(fill=X, padx=12, pady=6)
        self._btn(btn_f, "  📁  Chọn ảnh nhân vật (nhiều ảnh)",
                  self._choose_char_images, color=ACCENT
                  ).pack(side=LEFT, fill=X, expand=True, ipady=8, padx=(0,4))
        self._btn(btn_f, "  ⬆️  Upload tất cả lên Flow",
                  self._upload_chars, color=GREEN
                  ).pack(side=LEFT, fill=X, expand=True, ipady=8, padx=(0,4))
        self._btn(btn_f, "  🗑  Xóa hết",
                  self._clear_chars, color="#444C56"
                  ).pack(side=LEFT, ipady=8, ipadx=6)

        # Progress upload
        up_f = self._card(f, "📤 Tiến độ upload")
        up_f.pack(fill=X, padx=12, pady=5)
        self.char_progress = ttk.Progressbar(up_f, mode="determinate", style="TProgressbar")
        self.char_progress.pack(fill=X, padx=8, pady=(6,2))
        self.char_status_lbl = Label(up_f, text="Chưa upload",
                                     font=("Segoe UI", 9), bg=CARD, fg=MUTED)
        self.char_status_lbl.pack(pady=(0,6))

'''

# ═══════════════════════════════════
# 3. _tab_create_video header + char display
# ═══════════════════════════════════
NEW_CV_HEADER = '''    # ── TAB 5: Tạo Video Nhân Vật ───────────────────────
    def _tab_create_video(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="🎞️  Tạo Video")

        # Hướng dẫn
        guide = self._card(f, "📋 Hướng dẫn")
        guide.pack(fill=X, padx=12, pady=(10,4))
        Label(guide, text=(
            "1️⃣  Nhập danh sách prompt (mỗi dòng 1 cảnh)\n"
            "2️⃣  Bấm START → Tool tự động upload ảnh nhân vật + generate từng video\n"
            "⚠️  Prompt có tên nhân vật → chèn đúng ảnh đó  |  Không có tên → upload tất cả"
        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT
        ).pack(anchor=W, padx=10, pady=6)

        # Hiển thị nhân vật đã setup
        cv_char = self._card(f, "👤 Nhân vật đã thiết lập")
        cv_char.pack(fill=X, padx=12, pady=4)
        self.cv_char_display = Label(cv_char,
                                     text="Chưa có nhân vật. Vào tab 'Nhân Vật' để thiết lập trước.",
                                     font=("Segoe UI", 9), bg=CARD, fg=MUTED)
        self.cv_char_display.pack(anchor=W, padx=10, pady=6)

        # Prompts
        lf = self._card(f, "📝 Danh sách Prompt  (mỗi dòng 1 cảnh)")
        lf.pack(fill=BOTH, expand=True, padx=12, pady=4)
        mode_f = Frame(lf, bg=CARD); mode_f.pack(anchor=W, pady=(4,2))
        Label(mode_f, text="Định dạng: ", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.cv_mode = StringVar(value="normal")
        for txt, val in [("Thông thường", "normal"),
                          ("JSON nâng cao (scene_1, scene_2...)", "json")]:
            Radiobutton(mode_f, text=txt, variable=self.cv_mode, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=6)
        self.cv_prompts = scrolledtext.ScrolledText(
            lf, height=7, font=("Consolas", 9),
            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.cv_prompts.pack(fill=BOTH, expand=True, pady=(2,6))
        self.cv_prompts.insert(END, "Alice và Bob đang đi dạo trong công viên\\nCharlie đang chạy trên bãi biển")

        # Settings
        sf = self._card(f, "⚙️ Cài đặt đầu ra")
        sf.pack(fill=X, padx=12, pady=4)
        r1 = Frame(sf, bg=CARD); r1.pack(fill=X, pady=3, padx=8)
        Label(r1, text="Tên file:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.cv_base = Entry(r1, width=20, font=("Segoe UI", 9),
                             bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.cv_base.insert(0, "character_video")
        self.cv_base.pack(side=LEFT, padx=6, ipady=3)
        r2 = Frame(sf, bg=CARD); r2.pack(fill=X, pady=3, padx=8)
        Label(r2, text="Lưu tại:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.cv_out = Entry(r2, width=55, font=("Segoe UI", 9),
                            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.cv_out.insert(0, OUTPUT_DIR_CHAR)
        self.cv_out.pack(side=LEFT, padx=6, ipady=3)
        self._btn(r2, "📂", lambda: self._browse(self.cv_out),
                  color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)

        # Delay
        df = self._card(f, "⏱ Độ trễ giữa các prompt")
        df.pack(fill=X, padx=12, pady=4)
        df_r = Frame(df, bg=CARD); df_r.pack(anchor=W, padx=8, pady=4)
        self.cv_delay = StringVar(value="normal")
        for txt, val in [("Bình thường (5s)", "normal"),
                          ("Gấp đôi (10s)", "double"),
                          ("Ngẫu nhiên (6-15s)", "random")]:
            Radiobutton(df_r, text=txt, variable=self.cv_delay, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=8)

        # Timeout chờ video + tải tự động
        tf = self._card(f, "⬇️ Chờ video xong → Tự động tải (thoát sớm khi xong)")
        tf.pack(fill=X, padx=12, pady=4)
        self.cv_timeout = StringVar(value="600")
        cv_opts = [
            ("TỰ ĐỘNG — Chờ đến khi xong (tối đa 10 phút)  ⬇️  Tải ngay", "600"),
            ("Tối đa 5 phút  ⬇️  Tải ngay khi xong", "300"),
            ("Tối đa 3 phút  ⬇️  Tải ngay khi xong", "180"),
            ("30 giây  (submit nhanh, không tải về)", "30"),
        ]
        for txt, val in cv_opts:
            Radiobutton(tf, text=txt, variable=self.cv_timeout, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(anchor=W, padx=12)
        Label(tf, text="  ℹ️  Tool thoát ngay khi video xong!",
              font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(anchor=W, padx=20, pady=(0,4))

        self.cv_progress = ttk.Progressbar(f, mode="indeterminate", style="TProgressbar")
        self.cv_progress.pack(fill=X, padx=12, pady=(6,2))
        self.cv_status_lbl = Label(f, text="", font=("Segoe UI", 8), bg=BG, fg=MUTED)
        self.cv_status_lbl.pack()

        btn_f = Frame(f, bg=BG); btn_f.pack(fill=X, padx=12, pady=8)
        self._btn(btn_f, "  ▶  START — Tạo video + Tự động tải",
                  self._start_create_video, color=GREEN
                  ).pack(side=LEFT, fill=X, expand=True, ipady=9, padx=(0,4))
        self._btn(btn_f, "🧪 TEST: Chỉ chọn ảnh (không submit)",
                  self._test_char_select, color="#1B4721"
                  ).pack(side=LEFT, ipady=9, padx=(0,4))
        self._btn(btn_f, "⏹ STOP", self._stop, color=RED
                  ).pack(side=LEFT, ipady=9, ipadx=6)

        # Cập nhật hiển thị nhân vật khi chuyển tab
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

'''

# ═══════════════════════════════════
# 4. _tab_logs
# ═══════════════════════════════════
NEW_LOGS = '''    # ── TAB 6: Logs ──────────────────────────────────────
    def _tab_logs(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="📋  Logs")

        btn_f = Frame(f, bg=BG); btn_f.pack(fill=X, padx=10, pady=6)
        self._btn(btn_f, "🗑 Xóa log", lambda: (
            self.log_text.config(state=NORMAL),
            self.log_text.delete("1.0", END),
            self.log_text.config(state=DISABLED)
        ), color="#21262D").pack(side=LEFT, ipady=5, padx=(0,4))
        self._btn(btn_f, "⏹ Dừng tiến trình",
                  lambda: setattr(self, "running", False),
                  color=RED).pack(side=LEFT, ipady=5, padx=(0,4))
        self._btn(btn_f, "💾 Lưu log ra file TXT",
                  self._save_log, color="#21262D").pack(side=LEFT, ipady=5)

        self.log_text = scrolledtext.ScrolledText(
            f, font=("Consolas", 9), state=DISABLED,
            bg="#0D1117", fg="#C9D1D9",
            insertbackground=TEXT, relief="flat",
            selectbackground=ACCENT)
        self.log_text.pack(fill=BOTH, expand=True, padx=10, pady=(0,10))

'''

# ═══════════════════════════════════
# 5. _tab_merge
# ═══════════════════════════════════
NEW_MERGE = '''    # ── TAB 7: Ghép Video ───────────────────────────────
    def _tab_merge(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="🎬  Ghép Video")

        hf = Frame(f, bg="#0A0F1A"); hf.pack(fill=X)
        Label(hf, text="🎬  Ghép nhiều video thành 1 file",
              font=("Segoe UI", 12, "bold"), bg="#0A0F1A", fg=ACCENT
              ).pack(anchor=W, padx=16, pady=10)
        Label(hf, text="Yêu cầu: FFmpeg đã cài trong PATH  |  Tải tại: ffmpeg.org",
              font=("Segoe UI", 9), bg="#0A0F1A", fg=MUTED).pack(anchor=W, padx=16, pady=(0,10))

        info = self._card(f, "ℹ️ Thông tin công cụ")
        info.pack(fill=X, padx=12, pady=(10,5))
        Label(info, text=(
            "• Ghép các file MP4 trong một thư mục thành 1 video duy nhất\n"
            "• Sắp xếp theo tên file (video_01, video_02, ...)\n"
            "• Sử dụng FFmpeg concat — giữ nguyên chất lượng gốc (không re-encode)"
        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT).pack(anchor=W, padx=10, pady=8)

        self._btn(f, "  ▶  MỞ CÔNG CỤ GHÉP VIDEO",
                  self._open_merger_window, color=GREEN
                  ).pack(pady=16, ipady=10, ipadx=30)

'''

# ─────────────────────────────────────
# Apply replacements
# ─────────────────────────────────────
code = replace_between(code,
    "    # ── TAB 3: Text to Video",
    "    def _start_text2video(self):",
    NEW_T2V + "    def _start_text2video(self):")

code = replace_between(code,
    "    # ── TAB 4: Character Setup",
    "    def _choose_char_images(self):",
    NEW_CHAR + "    def _choose_char_images(self):")

code = replace_between(code,
    "    # ── TAB 5: Create Video",
    "    def _refresh_char_display(self):",
    NEW_CV_HEADER + "    def _refresh_char_display(self):")

code = replace_between(code,
    "    # ── TAB 6: Logs",
    "    def _save_log(self):",
    NEW_LOGS + "    def _save_log(self):")

code = replace_between(code,
    "    # ── TAB 7: Merge Videos",
    "    def _open_merger_window(self):",
    NEW_MERGE + "    def _open_merger_window(self):")

# Patch _open_merger_window for dark theme too
code = code.replace(
    'win.geometry("520x440")\n        win.resizable(False, False)',
    'win.geometry("560x480")\n        win.resizable(False, False)\n        win.configure(bg=BG)'
)
code = code.replace(
    'Label(win, text="🎞 VIDEO MERGER TOOL"',
    'Label(win, text="🎬 GHÉP VIDEO TOOL", bg=BG, fg=ACCENT'
)

# Dark theme for _ask_name dialog
code = code.replace(
    'dlg.geometry("350x130")',
    'dlg.geometry("360x150")\n        dlg.configure(bg=BG)'
)
code = code.replace(
    'Label(dlg, text=f"Tên nhân vật cho ảnh: {default[:40]}",\n              font=("Segoe UI", 9)).pack(pady=8)',
    'Label(dlg, text=f"  Đặt tên nhân vật cho ảnh: {default[:40]}",\n              font=("Segoe UI", 9), bg=BG, fg=TEXT).pack(pady=8, anchor=W, padx=10)'
)
code = code.replace(
    'Entry(dlg, textvariable=var, width=30, font=("Segoe UI", 11)).pack(pady=4)',
    'Entry(dlg, textvariable=var, width=32, font=("Segoe UI", 11), bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat").pack(pady=4, ipady=4)'
)

with open(SRC, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(code)

import py_compile
try:
    py_compile.compile(SRC, doraise=True)
    print("OK - syntax valid")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
