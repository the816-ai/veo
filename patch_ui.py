# -*- coding: utf-8 -*-
"""Patch script: thay thế phần UI của VeoApp bằng dark premium theme"""
import re, sys

SRC = r"f:\veo3\main.py"

# ── Đọc file gốc ──
with open(SRC, encoding="utf-8") as f:
    code = f.read()

# ── Tìm ranh giới phần UI cần thay (từ _build_ui đến hết _tab_browser) ──
# Giữ nguyên: BrowserController, màu sắc, __init__, _setup_style, log, set_status
# Thay toàn bộ: _build_ui và các tab method

NEW_UI = r'''
    # ─── UI BUILD ──────────────────────────────────────
    def _build_ui(self):
        # ── Header banner ──
        hdr = Frame(self.root, bg="#0A0F1A", height=56)
        hdr.pack(fill=X)
        hdr.pack_propagate(False)
        Label(hdr, text="🎬  VEO 3 FLOW PRO",
              font=("Segoe UI", 16, "bold"), bg="#0A0F1A", fg=ACCENT
              ).pack(side=LEFT, padx=18, pady=10)
        Label(hdr, text="Tự động tạo video chất lượng cao · Google Flow AI",
              font=("Segoe UI", 9), bg="#0A0F1A", fg=MUTED
              ).pack(side=LEFT, padx=2)
        self.status_var = StringVar(value="◉  Chưa kết nối")
        Label(hdr, textvariable=self.status_var,
              font=("Segoe UI", 9, "bold"), bg="#0A0F1A", fg=RED
              ).pack(side=RIGHT, padx=20)

        # ── Notebook ──
        self.nb = ttk.Notebook(self.root)
        self.nb.pack(fill=BOTH, expand=True)

        self._tab_note()
        self._tab_browser()
        self._tab_text2video()
        self._tab_char_setup()
        self._tab_create_video()
        self._tab_logs()
        self._tab_merge()

        # ── Status bar ──
        sb = Frame(self.root, bg=CARD, height=22)
        sb.pack(fill=X, side=BOTTOM)
        sb.pack_propagate(False)
        Label(sb, text="VEO 3 FLOW PRO  v2.0   ©2025 TechViet AI",
              font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(side=RIGHT, padx=10)
        Label(sb, text="✦ Đặt folder output riêng cho mỗi máy khi chạy song song",
              font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(side=LEFT, padx=10)

    # ── Widget helpers ──
    def _card(self, parent, title, **kw):
        return LabelFrame(parent, text=f"  {title}  ",
                          font=("Segoe UI", 9, "bold"),
                          bg=CARD, fg=ACCENT, bd=1, relief="groove",
                          labelanchor="nw", **kw)

    def _btn(self, parent, text, cmd, color=None, **kw):
        clr = color or ACCENT
        return Button(parent, text=text, command=cmd,
                      bg=clr, fg="white", font=("Segoe UI", 9, "bold"),
                      relief="flat", cursor="hand2",
                      activebackground=clr, activeforeground="white",
                      bd=0, **kw)

    def _lbl(self, parent, text, size=9, bold=False, color=None, **kw):
        return Label(parent, text=text,
                     font=("Segoe UI", size, "bold" if bold else "normal"),
                     bg=CARD, fg=color or TEXT, **kw)

    # ── TAB 1: Hướng dẫn ──────────────────────────────
    def _tab_note(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="📌  Hướng Dẫn")
        hf = Frame(f, bg="#0A0F1A"); hf.pack(fill=X)
        Label(hf, text="📌  Hướng dẫn sử dụng VEO 3 FLOW PRO",
              font=("Segoe UI", 12, "bold"), bg="#0A0F1A", fg=ACCENT
              ).pack(anchor=W, padx=16, pady=10)
        txt = scrolledtext.ScrolledText(f, wrap=WORD, font=("Segoe UI", 10),
                                        bg=CARD, fg=TEXT, insertbackground=TEXT,
                                        relief="flat", bd=0, padx=8, pady=8)
        txt.pack(fill=BOTH, expand=True, padx=12, pady=(0, 10))
        txt.insert(END, """
  ⚠️  YÊU CẦU BẮT BUỘC:
  ─────────────────────────────────────────────
  1. Cài Google Chrome + đăng nhập Google AI Pro tại: labs.google/fx
  2. Cài Python packages:  pip install selenium webdriver-manager pillow

  ─────────────────────────────────────────────
  🌐  BROWSER & KẾT NỐI
      → Mở Chrome vào Google Flow (Thường / Ẩn danh / Chrome mới)
      → Kết nối Chrome đang mở sẵn qua remote debug port

  📝  TEXT TO VIDEO  (Tab chính)
      → Dán danh sách prompt — mỗi dòng một lệnh
      → Hỗ trợ JSON: {"prompt":"...","style":"...","aspect_ratio":"9:16"}
      → [START]  — Tuần tự: tạo xong rồi tải, sang prompt tiếp
      → [RAPID]  — Submit nhanh tất cả, render SONG SONG trên cloud
      → [STOP]   — Dừng tiến trình đang chạy

  👤  NHÂN VẬT (Character Setup)
      → Chọn ảnh nhân vật → Đặt tên ngắn (Alice, Bob, NhanVat1...)
      → Upload lên Flow → Tool tự chèn ảnh khi tạo video

  🎞️  TẠO VIDEO NHÂN VẬT (Create Video)
      → Nhập prompt cho từng cảnh
      → Tool tự upload ảnh + generate theo thứ tự

  📋  LOGS   — Xem toàn bộ hoạt động, lưu log ra file TXT

  🎬  GHÉP VIDEO — Ghép nhiều MP4 thành 1 file (cần FFmpeg)
      → Tải FFmpeg: https://ffmpeg.org/download.html

  💡  MẸO: Dùng thư mục output RIÊNG cho mỗi phiên/máy
           để tránh lẫn file khi chạy song song.
""")
        txt.config(state=DISABLED)

    # ── TAB 2: Browser & Kết Nối ──────────────────────
    def _tab_browser(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="🌐  Kết Nối")

        # Hướng dẫn nhanh
        top = self._card(f, "📋 Quy trình kết nối")
        top.pack(fill=X, padx=14, pady=(12, 5))
        Label(top, text=(
            "1️⃣  Bấm nút MỞ CHROME bên dưới  →  Đăng nhập Google nếu cần\n"
            "2️⃣  Sau khi đăng nhập xong        →  Bấm '✔ Xác nhận đăng nhập'\n"
            "3️⃣  Sang tab 'Text to Video'       →  Nhập prompt  →  Bấm START"
        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT
        ).pack(anchor=W, padx=10, pady=8)

        # Nút điều khiển Chrome
        ctrl = self._card(f, "⚙️ Điều khiển Chrome")
        ctrl.pack(fill=X, padx=14, pady=5)

        row1 = Frame(ctrl, bg=CARD); row1.pack(fill=X, padx=8, pady=(8, 3))
        self._btn(row1, "  🖥  Mở Chrome (Thường)  ",
                  lambda: self._run_bg(lambda: self.bc.open("normal", download_dir=OUTPUT_DIR_TEXT)),
                  color=ACCENT).pack(side=LEFT, fill=X, expand=True, padx=(0,4), ipady=8)
        self._btn(row1, "  🔒  Mở Chrome Ẩn Danh  ",
                  lambda: self._run_bg(lambda: self.bc.open("incognito", download_dir=OUTPUT_DIR_TEXT)),
                  color="#444C56").pack(side=LEFT, fill=X, expand=True, padx=(4,0), ipady=8)

        row2 = Frame(ctrl, bg=CARD); row2.pack(fill=X, padx=8, pady=3)
        self._btn(row2, "  ✨  Chrome Hoàn Toàn Mới (Fresh)  ",
                  lambda: self._run_bg(lambda: self.bc.open("fresh", download_dir=OUTPUT_DIR_TEXT)),
                  color=PURPLE).pack(side=LEFT, fill=X, expand=True, padx=(0,4), ipady=8)
        self._btn(row2, "  🔗  Kết Nối Chrome Đang Mở  ",
                  lambda: self._run_bg(self._connect_existing_chrome),
                  color=ORANGE).pack(side=LEFT, fill=X, expand=True, padx=(4,0), ipady=8)

        Frame(ctrl, bg=BORDER, height=1).pack(fill=X, padx=8, pady=8)

        self._btn(ctrl, "  ✔  Xác nhận đăng nhập xong → Bắt đầu sử dụng  ",
                  self._confirm_login, color=GREEN
                  ).pack(fill=X, padx=8, pady=(0,5), ipady=10)

        row3 = Frame(ctrl, bg=CARD); row3.pack(fill=X, padx=8, pady=(0,8))
        def refresh_status():
            s = self.bc.get_status()
            self.status_var.set(f"◉  {s}")
        self._btn(row3, "🔄 Cập nhật trạng thái", refresh_status,
                  color="#21262D").pack(side=LEFT, padx=(0,4), ipady=5)

        def test_paste():
            if not self.bc.is_alive():
                messagebox.showerror("Lỗi", "Chưa mở Chrome!")
                return
            sample = "A beautiful sunset over the ocean, cinematic lighting, 8K"
            self.log("🧪 TEST: Mở project mới + dán prompt mẫu...")
            self.nb.select(5)
            def _run():
                ok = self.bc.new_project()
                if ok:
                    self.bc.set_prompt(sample)
                    self.log("✅ TEST xong — kiểm tra Chrome xem prompt đã hiện chưa!")
                else:
                    self.log("❌ TEST thất bại")
            self._run_bg(_run)
        self._btn(row3, "🧪 TEST: Dán prompt mẫu", test_paste,
                  color="#1B4721").pack(side=LEFT, ipady=5)

'''

# ── Tìm điểm bắt đầu và kết thúc để thay ──
# Bắt đầu: "    # ─── UI BUILD" hoặc tương tự
# Kết thúc: dòng đầu tiên của _confirm_login
start_marker = "    def _confirm_login(self):"

# Tìm vị trí
idx = code.find("    def _build_ui(self):")
end_idx = code.find(start_marker)

if idx == -1 or end_idx == -1:
    print(f"ERROR: idx={idx}, end_idx={end_idx}")
    sys.exit(1)

# Tìm đầu dòng comment trước _build_ui
comment_idx = code.rfind("\n", 0, idx) + 1
# Tìm từ "    # ─── UI BUILD" hoặc chỉ dùng idx
# Thực ra cứ từ idx là đủ

new_code = code[:idx] + NEW_UI + code[end_idx:]

with open(SRC, "w", encoding="utf-8", newline="\r\n") as f:
    f.write(new_code)

print(f"✅ Đã patch UI! File size: {len(new_code)} bytes")
print("Đang kiểm tra syntax...")
import py_compile
try:
    py_compile.compile(SRC, doraise=True)
    print("✅ Syntax OK!")
except py_compile.PyCompileError as e:
    print(f"❌ Syntax error: {e}")
