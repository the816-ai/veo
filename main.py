"""
Veo 3 Flow Automation Tool
Tự động hóa Google Flow để tạo video Veo 3
"""
import os, sys, time, json, threading, subprocess, shutil, re, random
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox, scrolledtext

FLOW_URL = "https://labs.google/fx/vi/tools/flow"
CHROME_PROFILE = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data")
OUTPUT_DIR_TEXT = str(Path.home() / "Downloads" / "VEO3_OUTPUT" / "text_to_video")
OUTPUT_DIR_CHAR = str(Path.home() / "Downloads" / "VEO3_OUTPUT" / "character_video")
OUTPUT_DIR_IMAGE = str(Path.home() / "Downloads" / "VEO3_OUTPUT" / "images")
CHROMEDRIVER_PATH = None  # auto-detect via webdriver_manager

# ─── Selenium imports (graceful) ───
try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.common.keys import Keys
    from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException
    from webdriver_manager.chrome import ChromeDriverManager
    HAS_SELENIUM = True
except ImportError:
    HAS_SELENIUM = False


# ═══════════════════════════════════════════════════════
# BROWSER CONTROLLER
# ═══════════════════════════════════════════════════════
class BrowserController:
    def __init__(self, log_fn=None):
        self.driver = None
        self.log = log_fn or print
        self.wait = None
        self._download_dir = OUTPUT_DIR_TEXT  # Bug fix: init before connect_existing

    def _opts(self, incognito=False, fresh=False, download_dir=None):
        opts = Options()
        opts.add_argument("--remote-debugging-port=9222")
        if fresh:
            opts.add_argument("--no-first-run")
            opts.add_argument("--no-default-browser-check")
        elif incognito:
            opts.add_argument("--incognito")
        else:
            opts.add_argument(f"--user-data-dir={CHROME_PROFILE}")
            opts.add_argument("--profile-directory=Default")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        # Set thư mục tải xuống tự động
        dl_dir = download_dir or OUTPUT_DIR_TEXT
        os.makedirs(dl_dir, exist_ok=True)
        prefs = {
            "download.default_directory": dl_dir,
            "download.prompt_for_download": False,
            "download.directory_upgrade": True,
            "safebrowsing.enabled": True,
        }
        opts.add_experimental_option("prefs", prefs)
        self._download_dir = dl_dir
        return opts

    def connect_existing(self):
        """Kết nối tới Chrome đang mở qua remote debug port 9222"""
        if not HAS_SELENIUM:
            return False
        try:
            self.log("🔗 Đang kết nối Chrome đang mở (port 9222)...")
            opts = Options()
            opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
            svc = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=svc, options=opts)
            self.wait = WebDriverWait(self.driver, 30)
            url = self.driver.current_url
            self.log(f"✅ Kết nối thành công! Đang ở: {url[:60]}")
            return True
        except Exception as e:
            self.log(f"❌ Kết nối thất bại: {e}")
            self.log("💡 Hãy mở Chrome bằng nút 'MỞ CHROME' trong tool thay vì mở thủ công!")
            return False

    def open(self, mode="normal", download_dir=None):
        """mode: normal | incognito | fresh"""
        if not HAS_SELENIUM:
            # messagebox PHẢI gọi từ main thread
            import tkinter.messagebox as _mb
            try: _mb.showerror("Lỗi", "Chưa cài selenium!\nChạy: pip install selenium webdriver-manager")
            except: pass
            return False
        try:
            self.log("🌐 Đang mở Chrome...")
            opts = self._opts(
                incognito=(mode == "incognito"),
                fresh=(mode == "fresh"),
                download_dir=download_dir
            )
            svc = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=svc, options=opts)
            self.driver.maximize_window()
            self.wait = WebDriverWait(self.driver, 30)
            self.driver.get(FLOW_URL)
            self.driver.execute_script("document.body.style.zoom='100%'")
            self.log(f"✅ Chrome mở | Tải về: {self._download_dir}")
            return True
        except Exception as e:
            self.log(f"❌ Lỗi mở Chrome: {e}")
            return False

    def is_alive(self):
        try:
            _ = self.driver.title
            return True
        except:
            return False

    def get_status(self):
        if not self.driver:
            return "Chưa mở"
        try:
            url = self.driver.current_url
            if "flow" in url:
                return f"✅ Đã mở Flow"
            return f"Đang ở: {url[:50]}"
        except:
            return "❌ Mất kết nối"

    def new_project(self):
        """Tạo dự án mới trên Flow"""
        try:
            self.driver.get(FLOW_URL)
            time.sleep(3)
            # Selector đã xác nhận: button.jsIRVP hoặc text 'Dự án mới'
            try:
                btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.jsIRVP"))
                )
                btn.click()
                time.sleep(2.5)
                self.log("✅ Đã tạo dự án mới")
            except TimeoutException:
                # Fallback: tìm theo text
                try:
                    btn = self.driver.find_element(
                        By.XPATH, "//button[contains(.,'Dự án mới') or contains(.,'New project')]"
                    )
                    btn.click()
                    time.sleep(2.5)
                    self.log("✅ Đã tạo dự án mới (fallback)")
                except:
                    self.log("ℹ️ Không thấy nút Dự án mới — tiếp tục")
            return True
        except Exception as e:
            self.log(f"❌ Lỗi tạo dự án: {e}")
            return False

    def set_prompt(self, text):
        """Nhập prompt vào Flow — clipboard paste (trigger real React paste event)"""
        import subprocess, tempfile

        def _copy_to_clipboard(t):
            """Copy text vào Windows clipboard qua PowerShell"""
            tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt',
                                               delete=False, encoding='utf-8')
            tmp.write(t); tmp.close()
            subprocess.run(
                ["powershell", "-Command",
                 f"Get-Content '{tmp.name}' -Raw | Set-Clipboard"],
                capture_output=True, timeout=5
            )
            try: os.unlink(tmp.name)
            except: pass

        try:
            # Chờ ô prompt thực sự clickable
            box = None
            for sel in ["div.fyuIsy[role='textbox']", "div[role='textbox']",
                        "div[contenteditable='true']"]:
                try:
                    box = WebDriverWait(self.driver, 15).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, sel))
                    )
                    if box and box.is_displayed():
                        break
                    box = None
                except:
                    continue

            if not box:
                self.log("❌ Không tìm thấy ô prompt (15s timeout)")
                return False

            # Scroll và focus
            self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", box)
            time.sleep(0.4)

            # ── Phương pháp 1: Clipboard Ctrl+V (React nhận real paste event) ──
            try:
                _copy_to_clipboard(text)
                box.click()
                time.sleep(0.3)
                # Xóa nội dung cũ
                box.send_keys(Keys.CONTROL + "a")
                time.sleep(0.1)
                box.send_keys(Keys.DELETE)
                time.sleep(0.2)
                # Paste từ clipboard → React nhận real paste event
                box.send_keys(Keys.CONTROL + "v")
                time.sleep(0.6)
                actual = self.driver.execute_script("return arguments[0].innerText;", box)
                if actual and actual.strip():
                    self.log(f"✅ Đã dán prompt (Ctrl+V): {text[:60]}...")
                    return True
                self.log("⚠ Clipboard paste: text không xuất hiện, thử fallback...")
            except Exception as e1:
                self.log(f"⚠ Clipboard: {e1}")

            # ── Phương pháp 2: execCommand(insertText) — React-safe ──
            try:
                box.click(); time.sleep(0.2)
                self.driver.execute_script("""
                    arguments[0].focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('delete', false, null);
                    document.execCommand('insertText', false, arguments[1]);
                """, box, text)
                time.sleep(0.5)
                actual = self.driver.execute_script("return arguments[0].innerText;", box)
                if actual and actual.strip():
                    self.log(f"✅ Đã dán prompt (execCommand): {text[:60]}...")
                    return True
            except Exception as e2:
                self.log(f"⚠ execCommand: {e2}")

            # ── Phương pháp 3: send_keys từng ký tự ──
            try:
                box.click(); time.sleep(0.3)
                box.send_keys(Keys.CONTROL + "a")
                box.send_keys(Keys.DELETE)
                time.sleep(0.2)
                for chunk in [text[i:i+60] for i in range(0, len(text), 60)]:
                    box.send_keys(chunk)
                    time.sleep(0.08)
                self.log(f"✅ Đã nhập prompt (send_keys): {text[:60]}...")
                return True
            except Exception as e3:
                self.log(f"❌ send_keys: {e3}")

            return False
        except Exception as e:
            self.log(f"❌ set_prompt: {e}")
            return False

    def click_generate(self):
        """Click nút Tạo — chờ enabled + ActionChains + Enter fallback"""
        try:
            # Chờ 1.5s sau khi paste để React cập nhật state
            time.sleep(1.5)

            # Tìm nút Tạo (button.bMhrec = arrow_forward button)
            btn_selectors = [
                (By.CSS_SELECTOR, "button.bMhrec"),
                (By.XPATH, "//button[.//span[normalize-space()='arrow_forward']]"),
                (By.XPATH, "//button[contains(@class,'bMhrec')]"),
            ]
            btn = None
            for by, sel in btn_selectors:
                try:
                    el = self.driver.find_element(by, sel)
                    if el and el.is_displayed():
                        btn = el
                        break
                except:
                    continue

            if btn:
                # Kiểm tra button có bị disabled không
                disabled = btn.get_attribute("disabled") or btn.get_attribute("aria-disabled")
                if disabled and str(disabled).lower() in ("true", "disabled"):
                    self.log("⚠ Nút Tạo đang disabled — thử Enter key...")
                else:
                    # Scroll vào view + ActionChains click (giống chuột thật)
                    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", btn)
                    time.sleep(0.3)
                    ActionChains(self.driver).move_to_element(btn).click().perform()
                    self.log("✅ Đã click nút Tạo (ActionChains)")
                    time.sleep(0.5)

                    # Xác nhận click có hiệu lực bằng cách kiểm tra URL thay đổi
                    url_before = self.driver.current_url
                    time.sleep(2)
                    url_after = self.driver.current_url
                    if url_after != url_before or "/edit/" in url_after:
                        self.log("✅ Xác nhận: trang đổi URL — generate đang chạy!")
                        return True
                    self.log("⚠ URL không đổi — thử Enter fallback...")

            # Fallback: Enter trong ô prompt (cách đáng tin nhất với React)
            try:
                box = self.driver.find_element(By.CSS_SELECTOR, "div[role='textbox']")
                box.click()
                time.sleep(0.3)
                box.send_keys(Keys.RETURN)
                self.log("⌨️ Sent Enter key → generate")
                return True
            except Exception as ef:
                self.log(f"⚠ Enter fallback: {ef}")

            # Fallback 2: JS tìm button phía phải ô prompt (tránh lỗi tọa độ)
            try:
                box = self.driver.find_element(By.CSS_SELECTOR, "div[role='textbox']")
                clicked = self.driver.execute_script("""
                    var box = arguments[0];
                    var rect = box.getBoundingClientRect();
                    var x = rect.right + 60, y = rect.top + rect.height / 2;
                    var els = document.elementsFromPoint(x, y);
                    for (var i = 0; i < els.length; i++) {
                        if (els[i].tagName === 'BUTTON') {
                            els[i].click();
                            return els[i].className || 'button';
                        }
                    }
                    return null;
                """, box)
                if clicked:
                    self.log(f"🖱 JS click button phải input: {clicked[:30]}")
                    return True
            except Exception as e2:
                self.log(f"⚠ JS coordinate click: {e2}")

            return False  # Tất cả fallback đều fail
        except Exception as e:
            self.log(f"❌ click_generate: {e}")
            return False


    def wait_for_video(self, timeout=300):
        """Chờ video tạo xong — đa selector, log tiến độ rõ ràng"""
        self.log(f"⏳ Chờ video hoàn thành (tối đa {timeout}s)...")
        start = time.time()
        last_log = 0

        # Tất cả selector có thể chỉ ra video xong
        DL_XPATHS = [
            "//button[normalize-space(.)='Tải xuống']",
            "//button[normalize-space(.)='Download']",
            "//button[@aria-label='Tải xuống' or @aria-label='Download']",
            "//button[contains(.,'Tải xuống') or contains(.,'Download')]",
            "//a[contains(@href,'.mp4') and @download]",
            "//button[.//mat-icon[contains(.,'download')] or .//span[contains(.,'download')]]",
        ]

        while time.time() - start < timeout:
            time.sleep(8)
            elapsed = int(time.time() - start)

            try:
                # 1. Tìm nút Download (nhiều selector)
                for xpath in DL_XPATHS:
                    try:
                        btns = self.driver.find_elements(By.XPATH, xpath)
                        visible = [b for b in btns if b.is_displayed()]
                        if visible:
                            self.log(f"✅ Video xong sau {elapsed}s! Nút tải xuống sẵn sàng.")
                            return True
                    except: continue

                # 2. Kiểm tra video element có src hợp lệ
                try:
                    vids = self.driver.find_elements(By.TAG_NAME, "video")
                    for v in vids:
                        src = v.get_attribute("src") or ""
                        if src and not src.startswith("data:") and len(src) > 10:
                            self.log(f"✅ Video element sẵn sàng sau {elapsed}s!")
                            return True
                except: pass

                # 3. Kiểm tra URL /edit/ có video blob
                try:
                    url = self.driver.current_url
                    if "/edit/" in url or "/project/" in url:
                        vids = self.driver.find_elements(By.XPATH,
                            "//video[contains(@src,'blob:') or contains(@src,'storage.google')]")
                        if vids:
                            self.log(f"✅ Video blob sẵn sàng sau {elapsed}s!")
                            return True
                except: pass

                # Log mỗi 30s
                if elapsed - last_log >= 30:
                    pct = min(95, int(elapsed / timeout * 100))
                    self.log(f"   ⏳ {elapsed}s/{timeout}s (~{pct}%) — Flow đang render...")
                    last_log = elapsed

            except Exception:
                pass

        self.log(f"⏱ Timeout {timeout}s — video chưa xong, bỏ qua tải")
        return False

    def wait_and_download(self, save_dir, filename, timeout=300):
        """Gộp chờ + tải: ngay khi phát hiện nút Tải xuống → click ngay → lưu file.
        Không cần gọi riêng wait_for_video() + click_download()."""
        self.log(f"⏳ Chờ video + tự động tải ngay (tối đa {timeout}s)...")
        os.makedirs(save_dir, exist_ok=True)
        start    = time.time()
        last_log = 0

        # Set CDP download folder ngay từ đầu
        try:
            self.driver.execute_cdp_cmd(
                "Browser.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": save_dir}
            )
        except: pass

        # Snapshot thư mục trước khi click
        chrome_dl  = str(Path.home() / "Downloads")
        watch_dirs = list({save_dir, chrome_dl})
        snap = {d: set(os.listdir(d)) if os.path.exists(d) else set()
                for d in watch_dirs}

        DL_XPATHS = [
            "//button[normalize-space(.)='Tải xuống']",
            "//button[normalize-space(.)='Download']",
            "//button[@aria-label='Tải xuống' or @aria-label='Download']",
            "//button[contains(.,'Tải xuống') or contains(.,'Download')]",
            "//a[contains(@href,'.mp4') and @download]",
            "//button[.//mat-icon[contains(.,'download')]]",
        ]

        dl_btn = None
        while time.time() - start < timeout:
            time.sleep(6)
            elapsed = int(time.time() - start)

            try:
                # Tìm nút Tải xuống → thoát vòng lặp ngay
                for xpath in DL_XPATHS:
                    try:
                        btns = self.driver.find_elements(By.XPATH, xpath)
                        vis  = [b for b in btns if b.is_displayed()]
                        if vis:
                            dl_btn = vis[0]
                            break
                    except: continue

                if dl_btn:
                    self.log(f"🎉 Video xong sau {elapsed}s! Click tải ngay...")
                    break

                # Fallback: video element có src → thử JS download
                try:
                    vids = self.driver.find_elements(By.TAG_NAME, "video")
                    for v in vids:
                        src = v.get_attribute("src") or ""
                        if src and not src.startswith("data:") and len(src) > 10:
                            self.log(f"📹 Video element ready ({elapsed}s) — thử JS download...")
                            if self._js_download_fallback(save_dir, filename):
                                return True
                            break
                except: pass

                # Log tiến độ mỗi 30s
                if elapsed - last_log >= 30:
                    pct = min(95, int(elapsed / timeout * 100))
                    self.log(f"   ⏳ {elapsed}s/{timeout}s (~{pct}%) — đang render...")
                    last_log = elapsed

            except Exception: pass

        if not dl_btn:
            self.log(f"⏱ Timeout — thử JS download fallback...")
            return self._js_download_fallback(save_dir, filename)

        # ── Click nút (3 cách) ──
        clicked = False
        for attempt in range(3):
            try:
                if attempt == 0:
                    ActionChains(self.driver).move_to_element(dl_btn).click().perform()
                elif attempt == 1:
                    self.driver.execute_script("arguments[0].click();", dl_btn)
                else:
                    dl_btn.click()
                self.log(f"⬇️ Đã click tải xuống (cách {attempt+1})")
                clicked = True
                break
            except Exception as ce:
                self.log(f"   ⚠ Click lần {attempt+1}: {ce}")
                time.sleep(0.5)

        if not clicked:
            self.log("⚠ Không click được — thử JS fallback...")
            return self._js_download_fallback(save_dir, filename)

        # ── Chờ file xuất hiện (180s) ──
        deadline    = time.time() + 180
        new_file    = None
        new_dir     = save_dir
        last_sz_log = time.time()

        while time.time() < deadline:
            time.sleep(2)
            for d in watch_dirs:
                if not os.path.exists(d): continue
                current = set(os.listdir(d))
                added   = current - snap[d]
                done    = [f for f in added
                           if f.lower().endswith(".mp4")
                           and not f.endswith(".crdownload")]
                if done:
                    new_file = done[0]; new_dir = d; break
                partial = [f for f in added if f.endswith(".crdownload")]
                if partial and time.time() - last_sz_log > 8:
                    try:
                        sz = os.path.getsize(os.path.join(d, partial[0]))
                        self.log(f"   ⬇️ Đang tải: {sz//1024//1024} MB...")
                    except: pass
                    last_sz_log = time.time()
            if new_file: break

        if not new_file:
            self.log("⚠ File không xuất hiện sau 180s")
            return False

        # ── Chờ ổn định → đổi tên ──
        src = os.path.join(new_dir, new_file)
        prev = -1; stable = 0
        for _ in range(20):
            time.sleep(1)
            try:
                sz = os.path.getsize(src)
                if sz == prev and sz > 0:
                    stable += 1
                    if stable >= 2: break
                else: stable = 0
                prev = sz
            except: break

        dst = os.path.join(save_dir, filename)
        if os.path.exists(dst):
            ts  = time.strftime("%H%M%S")
            dst = dst.replace(".mp4", f"_{ts}.mp4")
        try:
            shutil.move(src, dst)
            mb = os.path.getsize(dst) / 1024 / 1024
            self.log(f"✅ Đã lưu: {os.path.basename(dst)} ({mb:.1f} MB)")
            return True
        except Exception as me:
            self.log(f"⚠ Di chuyển file lỗi: {me} — file vẫn ở: {src}")
            return False

    def wait_for_prompt_ready(self, timeout=60):
        """Chờ ô nhập prompt xuất hiện lại sau khi video xong.
        Dùng để dán prompt tiếp mà không cần tạo project mới."""
        self.log("⏳ Chờ ô nhập prompt sẵn sàng...")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                for sel in [
                    "div[role='textbox']",
                    "div[contenteditable='true']",
                    "textarea",
                ]:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for el in els:
                        if el.is_displayed():
                            # Kiểm tra ô trống hoặc đã reset
                            txt = (el.get_attribute("innerText") or "").strip()
                            if len(txt) < 20:  # ô gần như trống = sẵn sàng
                                self.log("✅ Ô prompt sẵn sàng!")
                                return True
            except Exception:
                pass
            time.sleep(3)
        self.log(f"⚠ Không thấy ô prompt sau {timeout}s — sẽ tạo project mới")
        return False

    def set_aspect_ratio(self, ratio):
        """Chọn tỷ lệ khung hình trên Flow: 16:9 | 9:16 | 1:1"""
        try:
            # Map ratio → tab text
            ratio_map = {
                "16:9": ["Ngang", "16:9", "Landscape"],
                "9:16": ["Dọc", "9:16", "Portrait"],
                "1:1": ["Vuông", "1:1", "Square"],
            }
            labels = ratio_map.get(ratio, [])
            if not labels:
                return False

            for label in labels:
                try:
                    btn = self.driver.find_element(
                        By.XPATH,
                        f"//button[@role='tab' and (contains(.,'{label}') or @aria-label='{label}')]"
                    )
                    if btn:
                        btn.click()
                        time.sleep(0.5)
                        self.log(f"✅ Tỷ lệ: {ratio}")
                        return True
                except:
                    continue
            return False
        except Exception as e:
            self.log(f"⚠ Set aspect ratio: {e}")
            return False

    def click_download(self, save_dir, filename):
        """Click Tải xuống → nhiều phương pháp → chờ file ổn định → đổi tên"""
        try:
            os.makedirs(save_dir, exist_ok=True)

            # ── Bước 1: Set CDP để Chrome tự lưu đúng folder ──
            try:
                self.driver.execute_cdp_cmd(
                    "Browser.setDownloadBehavior",
                    {"behavior": "allow", "downloadPath": save_dir}
                )
                self.log(f"📂 Thư mục tải về: {save_dir}")
            except: pass

            # Monitor cả save_dir VÀ ~/Downloads (Chrome có thể tải vào đây)
            chrome_dl = str(Path.home() / "Downloads")
            watch_dirs = list({save_dir, chrome_dl})
            snap = {d: set(os.listdir(d)) if os.path.exists(d) else set()
                    for d in watch_dirs}

            # ── Bước 2: Tìm nút Tải xuống — 8 selector ──
            DL_SELECTORS = [
                (By.XPATH, "//button[normalize-space(.)='Tải xuống']"),
                (By.XPATH, "//button[normalize-space(.)='Download']"),
                (By.XPATH, "//button[@aria-label='Tải xuống']"),
                (By.XPATH, "//button[@aria-label='Download']"),
                (By.XPATH, "//button[contains(.,'Tải xuống')]"),
                (By.XPATH, "//button[contains(.,'Download')]"),
                (By.XPATH, "//a[contains(@href,'.mp4') and @download]"),
                (By.XPATH, "//button[.//mat-icon[contains(.,'download')]]"),
            ]

            dl_btn = None
            for by, sel in DL_SELECTORS:
                try:
                    els = self.driver.find_elements(by, sel)
                    visible = [e for e in els if e.is_displayed()]
                    if visible:
                        dl_btn = visible[0]
                        self.log(f"🔍 Tìm thấy nút tải: {sel[:50]}")
                        break
                except: continue

            if not dl_btn:
                self.log("⚠️ Không tìm thấy nút Tải xuống — thử JS fallback...")
                # ── Fallback: JS tìm <a href=.mp4> và tải trực tiếp ──
                js_downloaded = self._js_download_fallback(save_dir, filename)
                if js_downloaded:
                    return True
                self.log("❌ Không tải được — cần tải thủ công")
                return False

            # ── Bước 3: Click nút (thử 3 cách) ──
            clicked = False
            for attempt in range(3):
                try:
                    if attempt == 0:
                        ActionChains(self.driver).move_to_element(dl_btn).click().perform()
                    elif attempt == 1:
                        self.driver.execute_script("arguments[0].click();", dl_btn)
                    else:
                        dl_btn.click()
                    clicked = True
                    self.log(f"⬇️ Đã click nút Tải xuống (cách {attempt+1})")
                    break
                except Exception as ce:
                    self.log(f"   ⚠ Click lần {attempt+1} thất bại: {ce}")
                    time.sleep(0.5)

            if not clicked:
                self.log("❌ Không click được nút Tải xuống")
                return False

            # ── Bước 4: Chờ file xuất hiện (tối đa 180s) ──
            deadline = time.time() + 180
            new_file = None
            new_dir  = save_dir
            last_log = time.time()

            while time.time() < deadline:
                time.sleep(2)
                for d in watch_dirs:
                    if not os.path.exists(d): continue
                    current = set(os.listdir(d))
                    added   = current - snap[d]

                    # File hoàn chỉnh (.mp4 không phải .crdownload)
                    done = [f for f in added
                            if f.lower().endswith(".mp4")
                            and not f.endswith(".crdownload")]
                    if done:
                        new_file = done[0]; new_dir = d; break

                    # Đang tải → log kích thước
                    partial = [f for f in added if f.endswith(".crdownload")]
                    if partial and time.time() - last_log > 10:
                        try:
                            sz = os.path.getsize(os.path.join(d, partial[0]))
                            self.log(f"   ⬇️ Đang tải: {partial[0]} ({sz//1024//1024} MB)")
                        except: pass
                        last_log = time.time()

                if new_file: break

            if not new_file:
                self.log("⚠️ Hết 180s — file không xuất hiện")
                # Thử tìm file lớn nhất trong save_dir mới tạo
                try:
                    candidates = [
                        f for f in os.listdir(save_dir)
                        if f.lower().endswith(".mp4") and f not in snap.get(save_dir, set())
                    ]
                    if candidates:
                        mp4s = sorted(candidates,
                            key=lambda x: os.path.getmtime(os.path.join(save_dir, x)),
                            reverse=True)
                        new_file = mp4s[0]; new_dir = save_dir
                        self.log(f"♻️ Tìm thấy file mới: {new_file}")
                except: pass

            if not new_file:
                return False

            # ── Bước 5: Chờ file ổn định (không còn ghi) ──
            src = os.path.join(new_dir, new_file)
            self.log(f"⏳ Chờ file ổn định: {new_file}")
            prev_size = -1; stable = 0
            for _ in range(20):
                time.sleep(1)
                try:
                    sz = os.path.getsize(src)
                    if sz == prev_size and sz > 0:
                        stable += 1
                        if stable >= 2: break
                    else:
                        stable = 0
                    prev_size = sz
                    if sz > 0:
                        self.log(f"   📦 File size: {sz//1024//1024} MB...")
                except: break

            # ── Bước 6: Di chuyển + đổi tên ──
            dst = os.path.join(save_dir, filename)
            if os.path.exists(dst):
                ts  = time.strftime("%H%M%S")
                dst = dst.replace(".mp4", f"_{ts}.mp4")

            try:
                shutil.move(src, dst)
                size_mb = os.path.getsize(dst) / 1024 / 1024
                self.log(f"✅ Đã lưu: {os.path.basename(dst)} ({size_mb:.1f} MB)")
                return True
            except Exception as me:
                self.log(f"⚠ Di chuyển file lỗi: {me} — file vẫn ở: {src}")
                return False

        except Exception as e:
            self.log(f"❌ click_download lỗi: {e}")
            return False

    def _js_download_fallback(self, save_dir, filename):
        """Fallback: tìm URL video trong DOM và tải bằng JS fetch / requests."""
        try:
            # Tìm các URL video trong DOM
            video_urls = self.driver.execute_script("""
                var urls = [];
                // <video src=...>
                document.querySelectorAll('video[src]').forEach(v => {
                    if (v.src && v.src.length > 10) urls.push(v.src);
                });
                // <source src=...>
                document.querySelectorAll('source[src]').forEach(s => {
                    if (s.src && s.src.includes('mp4')) urls.push(s.src);
                });
                // <a href=*.mp4>
                document.querySelectorAll('a[href]').forEach(a => {
                    if (a.href && a.href.includes('.mp4')) urls.push(a.href);
                });
                return urls;
            """)

            if not video_urls:
                return False

            url = video_urls[0]
            self.log(f"🔗 JS fallback URL: {url[:80]}...")

            if url.startswith("blob:"):
                # Tải blob qua JS XHR
                b64 = self.driver.execute_script("""
                    var url = arguments[0];
                    var xhr = new XMLHttpRequest();
                    xhr.open('GET', url, false);
                    xhr.responseType = 'arraybuffer';
                    xhr.send();
                    if (xhr.status !== 200) return null;
                    var arr = new Uint8Array(xhr.response), bin = '';
                    for (var i = 0; i < arr.length; i++) bin += String.fromCharCode(arr[i]);
                    return btoa(bin);
                """, url)
                if b64:
                    import base64
                    dst = os.path.join(save_dir, filename)
                    with open(dst, 'wb') as f:
                        f.write(base64.b64decode(b64))
                    sz = os.path.getsize(dst) / 1024 / 1024
                    self.log(f"✅ JS blob download: {filename} ({sz:.1f} MB)")
                    return True
            else:
                # Tải URL thường bằng requests với cookie browser
                try:
                    import urllib.request as _ur
                    cookies = self.driver.get_cookies()
                    cookie_str = '; '.join(f"{c['name']}={c['value']}" for c in cookies)
                    req = _ur.Request(url, headers={
                        'User-Agent': 'Mozilla/5.0',
                        'Cookie': cookie_str,
                        'Referer': self.driver.current_url,
                    })
                    dst = os.path.join(save_dir, filename)
                    with _ur.urlopen(req, timeout=120) as resp, open(dst, 'wb') as f:
                        f.write(resp.read())
                    sz = os.path.getsize(dst) / 1024 / 1024
                    self.log(f"✅ URL download: {filename} ({sz:.1f} MB)")
                    return True
                except Exception as ue:
                    self.log(f"⚠ URL download lỗi: {ue}")
        except Exception as e:
            self.log(f"⚠ JS fallback lỗi: {e}")
        return False

    def upload_image(self, image_path):
        """Upload ảnh lên Flow UI mới:
        Nút + (bottom) → Modal media panel → Icon ↑ upload → file input → xác nhận
        """
        try:
            image_path = str(Path(image_path).resolve())
            if not os.path.exists(image_path):
                self.log(f"❌ File không tồn tại: {image_path}")
                return False

            # ── Bước 1: Click nút "+" ở góc dưới trái ──
            # Nút + trong prompt bar (chứa span có text 'add_2' hoặc aria-label add)
            plus_btn = None
            plus_xpaths = [
                "//button[.//span[normalize-space()='add_2']]",
                "//button[@aria-label='Add' or @aria-label='Thêm']",
                "//button[contains(@class,'add') and not(contains(.,'arrow'))]",
            ]
            for xp in plus_xpaths:
                try:
                    el = WebDriverWait(self.driver, 8).until(
                        EC.element_to_be_clickable((By.XPATH, xp))
                    )
                    if el:
                        plus_btn = el
                        break
                except: continue

            if not plus_btn:
                self.log("⚠ Không thấy nút + — thử tìm file input trực tiếp")
            else:
                ActionChains(self.driver).move_to_element(plus_btn).click().perform()
                self.log("✅ Đã click nút +")
                time.sleep(1.5)  # chờ modal/panel mở

            # ── Bước 2: Tìm nút ↑ (upload) trong panel media ──
            # Panel có search bar "Tìm kiếm các thành phần" + icon upload bên phải
            upload_icon = None
            upload_xpaths = [
                "//input[@placeholder[contains(.,'Tìm kiếm')]]/following-sibling::button",
                "//input[@placeholder[contains(.,'Search')]]/following-sibling::button",
                "//button[.//span[normalize-space()='file_upload' or normalize-space()='upload']]",
                "//button[@aria-label[contains(.,'upload') or contains(.,'Upload') or contains(.,'Tải')]]",
                # Icon ↑ thường là button trong search container
                "//div[.//input[@placeholder]]//button[last()]",
            ]
            for xp in upload_xpaths:
                try:
                    el = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.XPATH, xp))
                    )
                    if el:
                        upload_icon = el
                        break
                except: continue

            if upload_icon:
                ActionChains(self.driver).move_to_element(upload_icon).click().perform()
                self.log("✅ Đã click icon upload ↑")
                time.sleep(1.0)
            else:
                self.log("⚠ Không thấy icon upload — thử unhide file input")

            # ── Bước 3: Unhide tất cả input[type=file] và send_keys ──
            self.driver.execute_script("""
                document.querySelectorAll("input[type='file']").forEach(function(el) {
                    el.style.cssText = 'display:block!important;opacity:1!important;' +
                                       'visibility:visible!important;width:1px!important;height:1px!important;';
                });
            """)
            time.sleep(0.4)

            inputs = self.driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
            file_input = None
            for inp in inputs:
                accept = inp.get_attribute("accept") or ""
                if "image" in accept or "video" in accept or "*" in accept:
                    file_input = inp
                    break
            if not file_input and inputs:
                file_input = inputs[-1]  # lấy cái mới nhất

            if not file_input:
                self.log("❌ Không tìm thấy input[type=file]")
                return False

            file_input.send_keys(image_path)
            self.log(f"📤 Đang upload: {Path(image_path).name}")

            # ── Bước 4: Chờ thumbnail xuất hiện trong panel (xác nhận upload OK) ──
            self.log("⏳ Chờ xác nhận upload...")
            deadline = time.time() + 25
            while time.time() < deadline:
                time.sleep(2)
                try:
                    # Thumbnail ảnh vừa upload sẽ có src chứa blob hoặc googleusercontent
                    thumbs = self.driver.find_elements(
                        By.XPATH,
                        "//img[contains(@src,'blob:') or contains(@src,'googleusercontent') or contains(@src,'data:image')]"
                    )
                    if thumbs:
                        self.log(f"✅ Upload OK: {Path(image_path).name} ({len(thumbs)} ảnh trong panel)")
                        return True
                except: pass

            self.log(f"⚠ Không xác nhận được upload (hết 25s) — có thể vẫn OK")
            return True

        except Exception as e:
            self.log(f"❌ upload_image: {e}")
            return False

    def wait_and_download_image(self, save_dir, filename, timeout=180):
        """Chờ ảnh tạo xong trên Flow → tải về ngay.
        Detect: nút Tải xuống / thẻ <img> mới / link download."""
        self.log(f"⏳ Chờ ảnh + tự động tải (tối đa {timeout}s)...")
        os.makedirs(save_dir, exist_ok=True)
        start    = time.time()
        last_log = 0

        # Set CDP download folder
        try:
            self.driver.execute_cdp_cmd(
                "Browser.setDownloadBehavior",
                {"behavior": "allow", "downloadPath": save_dir}
            )
        except: pass

        # Snapshot thư mục
        chrome_dl  = str(Path.home() / "Downloads")
        watch_dirs = list({save_dir, chrome_dl})
        snap = {d: set(os.listdir(d)) if os.path.exists(d) else set()
                for d in watch_dirs}

        DL_XPATHS = [
            "//button[normalize-space(.)='Tải xuống']",
            "//button[normalize-space(.)='Download']",
            "//button[@aria-label='Tải xuống' or @aria-label='Download']",
            "//button[contains(.,'Tải xuống') or contains(.,'Download')]",
            "//a[contains(@href,'.png') or contains(@href,'.jpg') or contains(@href,'.webp')]",
        ]

        dl_btn = None
        while time.time() - start < timeout:
            time.sleep(5)
            elapsed = int(time.time() - start)

            try:
                # 1. Tìm nút Tải xuống
                for xpath in DL_XPATHS:
                    try:
                        btns = self.driver.find_elements(By.XPATH, xpath)
                        vis  = [b for b in btns if b.is_displayed()]
                        if vis:
                            dl_btn = vis[0]
                            break
                    except: continue

                if dl_btn:
                    self.log(f"🎉 Ảnh xong sau {elapsed}s! Click tải ngay...")
                    break

                # 2. Detect ảnh qua JS: tìm img mới hoặc canvas
                try:
                    img_ready = self.driver.execute_script("""
                        // Tìm ảnh generated (không phải icon/avatar)
                        var imgs = document.querySelectorAll('img[src]');
                        for (var i = 0; i < imgs.length; i++) {
                            var src = imgs[i].src;
                            var w = imgs[i].naturalWidth || 0;
                            if (w > 200 && (src.includes('blob:') || src.includes('storage.google')
                                || src.includes('generated') || src.includes('lh3.google'))) {
                                return src;
                            }
                        }
                        return null;
                    """)
                    if img_ready and not dl_btn:
                        self.log(f"📸 Ảnh detected ({elapsed}s) — thử tải trực tiếp...")
                        # Thử tải ảnh qua JS
                        if self._download_image_js(img_ready, save_dir, filename):
                            return True
                except: pass

                # Log mỗi 30s
                if elapsed - last_log >= 30:
                    pct = min(95, int(elapsed / timeout * 100))
                    self.log(f"   ⏳ {elapsed}s/{timeout}s (~{pct}%) — đang tạo ảnh...")
                    last_log = elapsed

            except Exception: pass

        if not dl_btn:
            # Thử lần cuối: tải ảnh lớn nhất trong DOM
            self.log("⏱ Timeout — thử tải ảnh từ DOM...")
            return self._download_largest_image(save_dir, filename)

        # ── Click nút (3 cách) ──
        clicked = False
        for attempt in range(3):
            try:
                if attempt == 0:
                    ActionChains(self.driver).move_to_element(dl_btn).click().perform()
                elif attempt == 1:
                    self.driver.execute_script("arguments[0].click();", dl_btn)
                else:
                    dl_btn.click()
                self.log(f"⬇️ Đã click tải ảnh (cách {attempt+1})")
                clicked = True
                break
            except Exception as ce:
                self.log(f"   ⚠ Click lần {attempt+1}: {ce}")
                time.sleep(0.5)

        if not clicked:
            return self._download_largest_image(save_dir, filename)

        # ── Chờ file xuất hiện (60s) ──
        deadline = time.time() + 60
        new_file = None
        new_dir  = save_dir
        img_exts = (".png", ".jpg", ".jpeg", ".webp")

        while time.time() < deadline:
            time.sleep(2)
            for d in watch_dirs:
                if not os.path.exists(d): continue
                current = set(os.listdir(d))
                added   = current - snap[d]
                done = [f for f in added
                        if any(f.lower().endswith(e) for e in img_exts)
                        and not f.endswith(".crdownload")]
                if done:
                    new_file = done[0]; new_dir = d; break
            if new_file: break

        if not new_file:
            self.log("⚠ File ảnh không xuất hiện — thử tải từ DOM...")
            return self._download_largest_image(save_dir, filename)

        # Chờ ổn định
        src = os.path.join(new_dir, new_file)
        time.sleep(2)

        # Đổi tên
        ext = Path(new_file).suffix or ".png"
        dst = os.path.join(save_dir, filename.rsplit('.', 1)[0] + ext)
        if os.path.exists(dst):
            ts  = time.strftime("%H%M%S")
            dst = dst.rsplit('.', 1)[0] + f"_{ts}" + ext
        try:
            shutil.move(src, dst)
            kb = os.path.getsize(dst) / 1024
            self.log(f"✅ Đã lưu ảnh: {os.path.basename(dst)} ({kb:.0f} KB)")
            return True
        except Exception as me:
            self.log(f"⚠ Di chuyển file lỗi: {me}")
            return False

    def _download_image_js(self, img_url, save_dir, filename):
        """Tải ảnh từ URL (blob: hoặc https) qua JS."""
        try:
            if img_url.startswith("blob:"):
                # Dùng sync XHR thay vì Promise (execute_script không await Promise)
                b64 = self.driver.execute_script("""
                    try {
                        var xhr = new XMLHttpRequest();
                        xhr.open('GET', arguments[0], false);
                        xhr.responseType = 'arraybuffer';
                        xhr.send();
                        if (xhr.status !== 200) return null;
                        var arr = new Uint8Array(xhr.response), bin = '';
                        for (var i = 0; i < arr.length; i++) bin += String.fromCharCode(arr[i]);
                        return btoa(bin);
                    } catch(e) { return null; }
                """, img_url)
                if b64:
                    import base64
                    dst = os.path.join(save_dir, filename.rsplit('.', 1)[0] + ".png")
                    with open(dst, 'wb') as f:
                        f.write(base64.b64decode(b64))
                    kb = os.path.getsize(dst) / 1024
                    self.log(f"✅ JS blob ảnh: {os.path.basename(dst)} ({kb:.0f} KB)")
                    return True
            else:
                import urllib.request as _ur
                cookies = self.driver.get_cookies()
                cookie_str = '; '.join(f"{c['name']}={c['value']}" for c in cookies)
                req = _ur.Request(img_url, headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Cookie': cookie_str,
                    'Referer': self.driver.current_url,
                })
                ext = ".png"
                for e in ['.jpg', '.jpeg', '.webp', '.png']:
                    if e in img_url.lower():
                        ext = e; break
                dst = os.path.join(save_dir, filename.rsplit('.', 1)[0] + ext)
                with _ur.urlopen(req, timeout=30) as resp, open(dst, 'wb') as f:
                    f.write(resp.read())
                kb = os.path.getsize(dst) / 1024
                self.log(f"✅ URL ảnh: {os.path.basename(dst)} ({kb:.0f} KB)")
                return True
        except Exception as e:
            self.log(f"⚠ Download ảnh JS lỗi: {e}")
        return False

    def _download_largest_image(self, save_dir, filename):
        """Fallback: tìm ảnh lớn nhất trong DOM rồi tải."""
        try:
            result = self.driver.execute_script("""
                var best = null, maxW = 0;
                document.querySelectorAll('img[src]').forEach(function(img) {
                    var w = img.naturalWidth || 0;
                    if (w > maxW && w > 200) { maxW = w; best = img.src; }
                });
                return best;
            """)
            if result:
                self.log(f"🔍 Tìm thấy ảnh {result[:60]}...")
                return self._download_image_js(result, save_dir, filename)
        except Exception as e:
            self.log(f"⚠ Fallback ảnh lỗi: {e}")
        self.log("❌ Không tìm thấy ảnh để tải")
        return False



# ─── Màu nền tối chuyên nghiệp ───
BG      = "#0D1117"   # nền chính
CARD    = "#161B22"   # card/frame
BORDER  = "#30363D"   # viền
TEXT    = "#E6EDF3"   # chữ sáng
MUTED   = "#8B949E"   # chữ mờ
ACCENT  = "#58A6FF"   # xanh dương
GREEN   = "#3FB950"   # xanh lá
RED     = "#F85149"   # đỏ
ORANGE  = "#D29922"   # cam/vàng
PURPLE  = "#BC8CFF"   # tím

# ═══════════════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════════════
class VeoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VEO 3 FLOW PRO  —  by TechViet AI")
        self.root.geometry("1060x700")
        self.root.resizable(True, True)
        self.root.configure(bg=BG)

        self.bc = BrowserController(log_fn=self.log)
        self.characters = {}   # {tên: đường_dẫn_ảnh}
        self.running = False

        self._setup_style()
        self._build_ui()

    def _setup_style(self):
        """Thiết lập ttk.Style cho dark theme"""
        s = ttk.Style()
        s.theme_use("clam")
        # Notebook
        s.configure("TNotebook", background=BG, borderwidth=0)
        s.configure("TNotebook.Tab", background=CARD, foreground=MUTED,
                    padding=[14, 6], font=("Segoe UI", 9, "bold"))
        s.map("TNotebook.Tab",
              background=[("selected", ACCENT)],
              foreground=[("selected", "white")])
        # Progressbar
        s.configure("TProgressbar", troughcolor=CARD, background=ACCENT,
                    borderwidth=0, thickness=6)
        # Frame/LabelFrame
        s.configure("Dark.TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD)

    # ─── LOG ───────────────────────────────
    def log(self, msg):
        def _do():
            ts = time.strftime("%H:%M:%S")
            self.log_text.config(state=NORMAL)
            self.log_text.insert(END, f"[{ts}] {msg}\n")
            self.log_text.see(END)
            self.log_text.config(state=DISABLED)
        self.root.after(0, _do)

    def set_status(self, msg):
        self.root.after(0, lambda: self.status_var.set(msg))

    # ─── UI BUILD ──────────────────────────

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
        self._tab_text2image()
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
            self.nb.select(6)
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

    def _confirm_login(self):
        self.log("✅ Đã xác nhận đăng nhập!")
        self.set_status("Trạng thái: ✅ Đã đăng nhập")
        messagebox.showinfo("OK", "Đã xác nhận đăng nhập!\nBây giờ chuyển sang tab Text to Video để bắt đầu.")

    def _connect_existing_chrome(self):
        """Kết nối tới Chrome đang mở qua remote debugging port"""
        ok = self.bc.connect_existing()
        if ok:
            self.set_status("Trạng thái: ✅ Kết nối Chrome thành công")
            self.root.after(0, lambda: messagebox.showinfo(
                "✅ Kết nối OK",
                f"Đã kết nối Chrome thành công!\n{self.bc.get_status()}\n\nBây giờ sang tab Text to Video để tạo video."
            ))
        else:
            self.root.after(0, lambda: messagebox.showerror(
                "❌ Kết nối thất bại",
                "Không kết nối được Chrome!\n\n"
                "Giải pháp:\n"
                "1. ĐÓNG Chrome đang mở\n"
                "2. Bấm 'MỞ CHROME' trong tool\n"
                "3. Đăng nhập Google trên Chrome đó\n"
                "4. Bấm 'GỬI ĐĂNG NHẬP'\n"
                "5. Sang tab Text to Video → START"
            ))

    # ── TAB 3: Text to Video ──────────────────────────────
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
        self.tv_prompts.insert(END, "A cinematic sunset over the ocean, 8K, dramatic lighting\n"
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

        # Timeout — cố định 10 phút, phát hiện xong tải ngay
        tf = self._card(f, "⬇️ Tự động chờ video xong → Tải về ngay")
        tf.pack(fill=X, padx=12, pady=4)
        self.tv_timeout = StringVar(value="600")
        Label(tf, text="  ⏳  Chờ đến khi video xong, tối đa 10 phút  →  Tải xuống ngay khi phát hiện hoàn tất",
              font=("Segoe UI", 9, "bold"), bg=CARD, fg=GREEN).pack(anchor=W, padx=12, pady=6)
        Label(tf, text="  ℹ️  Tool phát hiện video xong sẽ tải ngay, không cần chờ hết 10 phút!",
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

    def _start_text2video(self):
        raw = self.tv_prompts.get("1.0", END).strip()
        lines = [l.strip() for l in raw.splitlines() if l.strip() and not l.startswith("#")]
        if not lines:
            messagebox.showerror("Lỗi", "Chưa nhập prompt!")
            return
        if not self.bc.is_alive():
            messagebox.showerror("Lỗi", "Chưa mở Chrome! Vào tab Browser & Setup trước.")
            return
        out_dir = self.tv_out.get()
        os.makedirs(out_dir, exist_ok=True)
        self.log(f"🚀 Bắt đầu Text→Video: {len(lines)} prompt(s)")
        self.nb.select(6)  # switch to Logs tab
        self._run_bg(lambda: self._t2v_worker(lines, out_dir))

    @staticmethod
    def _parse_line(line):
        """Parse 1 dòng: JSON object hoặc plain text.
        Trả về: (prompt_text, aspect_ratio, duration, extra_info)"""
        line = line.strip()
        if line.startswith("{"):
            try:
                obj = json.loads(line)
                prompt = obj.get("prompt", "")
                style = obj.get("style", "")
                camera = obj.get("camera_motion", "")
                aspect = obj.get("aspect_ratio", "16:9")
                duration = obj.get("duration", 8)
                # Ghép style + camera vào cuối prompt để hướng dẫn cảnh
                extra_parts = []
                if style: extra_parts.append(style)
                if camera: extra_parts.append(camera)
                full_prompt = prompt
                if extra_parts:
                    full_prompt = f"{prompt}. Style: {', '.join(extra_parts)}"
                return full_prompt, aspect, duration, obj
            except json.JSONDecodeError:
                pass
        # Plain text
        return line, "16:9", 8, {}

    def _t2v_worker(self, lines, out_dir):
        self.running = True
        self.root.after(0, self.tv_progress.start)
        results = []
        submitted = []  # [(index, short, fname, project_url)]

        try:
            # ════════════════════════════════════════════
            # PHASE 1: Submit tất cả prompt nhanh
            # ════════════════════════════════════════════
            total = len(lines)
            self.log(f"\n{'═'*60}")
            self.log(f"📤  PHASE 1 — Submit {total} prompt(s)")
            self.log(f"{'═'*60}")

            delay_map = {"normal": 5, "double": 10, "random": None}
            d_val = delay_map.get(self.tv_delay.get(), 5)

            for i, line in enumerate(lines, 1):
                if not self.running:
                    results.append((i, line[:50], '⏹ Dừng', ''))
                    break

                prompt_text, aspect_ratio, duration, meta = self._parse_line(line)
                short = prompt_text[:60]
                fname = f"{self.tv_base.get()}_{i:02d}.mp4"
                self.log(f"\n📤 [{i}/{total}] {short}...")
                self.root.after(0, lambda ii=i, t=total:
                    self.tv_status_lbl.config(text=f"📤 Submit [{ii}/{t}]..."))

                # Prompt 1: tạo project mới. Prompt 2+: tái dùng, chỉ dán text
                if i == 1:
                    self.log("🆕 Tạo project mới (lần đầu)...")
                    ok = self.bc.new_project()
                    if not ok:
                        results.append((i, short, '❌ Lỗi tạo project', ''))
                        break
                    time.sleep(2)
                else:
                    self.log(f"♻️ Tái dùng project — chờ ô prompt [{i}/{total}]...")
                    ready = self.bc.wait_for_prompt_ready(timeout=60)
                    if not ready:
                        self.log("⚠ Không thấy ô prompt — tạo project mới...")
                        ok = self.bc.new_project()
                        if not ok:
                            results.append((i, short, '❌ Lỗi tạo project', ''))
                            continue
                        time.sleep(2)

                if aspect_ratio and aspect_ratio != "16:9":
                    self.bc.set_aspect_ratio(aspect_ratio)

                ok = self.bc.set_prompt(prompt_text)
                if not ok:
                    results.append((i, short, '❌ Lỗi dán prompt', ''))
                    continue
                time.sleep(0.8)

                ok = self.bc.click_generate()
                if not ok:
                    results.append((i, short, '❌ Lỗi nút Tạo', ''))
                    continue

                # Lưu URL project để quay lại tải
                proj_url = self.bc.driver.current_url
                submitted.append((i, short, fname, proj_url))
                self.log(f"   ✅ Đã submit #{i} — URL: {proj_url[:80]}")

                # Delay giữa các prompt
                if i < total and self.running:
                    delay = d_val if d_val is not None else random.randint(6, 15)
                    self.log(f"   ⏳ Chờ {delay}s rồi prompt tiếp...")
                    time.sleep(delay)

            self.log(f"\n📤 Phase 1 xong: {len(submitted)}/{total} prompt đã submit")

            if not submitted:
                self.log("⚠ Không có prompt nào submit được")
                return

            # ════════════════════════════════════════════
            # PHASE 2: Quay lại tải từng video theo thứ tự
            # ════════════════════════════════════════════
            self.log(f"\n{'═'*60}")
            self.log(f"⬇️  PHASE 2 — Tải {len(submitted)} video theo thứ tự")
            self.log(f"{'═'*60}")

            for idx, (i, short, fname, proj_url) in enumerate(submitted, 1):
                if not self.running:
                    results.append((i, short, '⏹ Dừng tải', ''))
                    break

                self.log(f"\n⬇️ [{idx}/{len(submitted)}] Quay lại: {short}...")
                self.root.after(0, lambda ii=idx, t=len(submitted), fn=fname:
                    self.tv_status_lbl.config(text=f"⬇️ Tải [{ii}/{t}] {fn}..."))

                # Mở lại URL project
                try:
                    self.bc.driver.get(proj_url)
                    time.sleep(3)
                except Exception as e:
                    self.log(f"   ❌ Không mở được URL: {e}")
                    results.append((i, short, '❌ Lỗi mở URL project', ''))
                    continue

                # Chờ video xong + tải ngay
                dl_ok = self.bc.wait_and_download(out_dir, fname,
                    timeout=int(self.tv_timeout.get()))
                if dl_ok:
                    results.append((i, short, '✅ Thành công', fname))
                    self.log(f"   ✅ Tải xong: {fname}")
                else:
                    results.append((i, short, '⚠ Không tải được', fname))
                    self.log(f"   ⚠ Không tải được: {fname}")

        except Exception as e:
            self.log(f"❌ Lỗi ngoài dự kiến: {e}")
        finally:
            self.running = False
            self.root.after(0, self.tv_progress.stop)
            self.root.after(0, lambda: self.tv_status_lbl.config(text=""))
            self._log_summary("Text→Video", results, out_dir)

    def _stop(self):
        """Dừng worker đang chạy"""
        if self.running:
            self.running = False
            self.log("⏹ Đã gửi lệnh dừng — chờ bước hiện tại kết thúc...")
        else:
            self.log("ℹ️ Không có tiến trình nào đang chạy")

    def _log_summary(self, mode_name, results, out_dir):
        """In bảng tổng kết cuối cùng — prompt nào OK, prompt nào lỗi ở bước nào."""
        total   = len(results)
        ok_list = [r for r in results if '✅' in r[2]]
        fail_list = [r for r in results if '❌' in r[2] or '⚠' in r[2]]
        stop_list = [r for r in results if '⏹' in r[2]]

        self.log(f"\n{'═'*60}")
        self.log(f"📊  TỔNG KẾT — {mode_name}")
        self.log(f"{'═'*60}")
        self.log(f"   Tổng: {total}  |  ✅ Thành công: {len(ok_list)}  |  ❌ Lỗi: {len(fail_list)}  |  ⏹ Dừng: {len(stop_list)}")
        self.log(f"   📂 Thư mục: {out_dir}")

        if ok_list:
            self.log(f"\n   ── ✅ THÀNH CÔNG ({len(ok_list)}) ──")
            for idx, short, status, fname in ok_list:
                self.log(f"   #{idx:02d}  {fname}  ←  {short}")

        if fail_list:
            self.log(f"\n   ── ❌ THẤT BẠI ({len(fail_list)}) ──")
            for idx, short, status, fname in fail_list:
                self.log(f"   #{idx:02d}  {status}  ←  {short}")

        if stop_list:
            self.log(f"\n   ── ⏹ DỪNG ──")
            for idx, short, status, fname in stop_list:
                self.log(f"   #{idx:02d}  {status}  ←  {short}")

        self.log(f"{'═'*60}\n")

    def _start_rapid(self):
        """⚡ Rapid Mode: Submit tất cả nhanh → render song song trên cloud"""
        raw = self.tv_prompts.get("1.0", END).strip()
        lines = [l.strip() for l in raw.splitlines() if l.strip() and not l.startswith("#")]
        if not lines:
            messagebox.showerror("Lỗi", "Chưa nhập prompt!")
            return
        if not self.bc.is_alive():
            messagebox.showerror("Lỗi", "Chưa mở Chrome!")
            return
        out_dir = self.tv_out.get()
        os.makedirs(out_dir, exist_ok=True)
        self.log(f"⚡ RAPID MODE: Submit {len(lines)} prompt(s) nhanh → render song song!")
        self.nb.select(6)
        self._run_bg(lambda: self._rapid_worker(lines, out_dir))

    def _rapid_worker(self, lines, out_dir):
        """Submit tất cả nhanh (30s/prompt), rồi monitor download folder"""
        self.running = True
        self.root.after(0, self.tv_progress.start)

        # ─── PHASE 1: Submit tất cả prompt nhanh ───
        total = len(lines)
        submitted = 0
        try:
            for i, line in enumerate(lines, 1):
                if not self.running: break
                prompt_text, aspect_ratio, duration, meta = self._parse_line(line)
                self.log(f"\n⚡ [{i}/{total}] Submit: {prompt_text[:60]}...")
                self.root.after(0, lambda i=i, t=total: self.tv_status_lbl.config(
                    text=f"⚡ Submit {i}/{t} — render song song trên cloud..."))

                # ── Lần đầu: tạo project mới. Từ lần 2+: chờ ô prompt rồi dán thẳng ──
                if i == 1:
                    self.log("🆕 Tạo project mới (lần đầu)...")
                    ok = self.bc.new_project()
                    if not ok:
                        self.log("❌ Không tạo được project — dừng")
                        break
                else:
                    self.log(f"♻️ Tái dùng project — chờ ô prompt [{i}/{total}]...")
                    ready = self.bc.wait_for_prompt_ready(timeout=45)
                    if not ready:
                        self.log("⚠ Không thấy ô prompt — tạo project mới...")
                        ok = self.bc.new_project()
                        if not ok: continue

                if aspect_ratio and aspect_ratio != "16:9":
                    self.bc.set_aspect_ratio(aspect_ratio)

                ok = self.bc.set_prompt(prompt_text)
                if not ok: continue

                ok = self.bc.click_generate()
                if ok:
                    submitted += 1
                    self.log(f"   ✅ Đã submit #{i}")
                else:
                    self.log(f"   ⚠ Submit #{i} thất bại")

                # Chờ 30s giữa các prompt (đủ để Flow nhận request)
                if i < total and self.running:
                    for _ in range(30):
                        if not self.running: break
                        time.sleep(1)

        except Exception as e:
            self.log(f"❌ Submit error: {e}")

        self.log(f"\n⚡ Đã submit {submitted}/{total} prompt. Bắt đầu monitor download...")
        self.root.after(0, lambda: self.tv_status_lbl.config(
            text=f"📥 Đang chờ {submitted} video từ cloud..."))

        # ─── PHASE 2: Monitor folder, đổi tên tuần tự khi file về ───
        if submitted == 0:
            self.running = False
            self.root.after(0, self.tv_progress.stop)
            return

        snap = set(os.listdir(out_dir))
        base = self.tv_base.get()
        video_counter = 1
        # Tính video_counter tiếp theo (tránh ghi đè file cũ)
        while os.path.exists(os.path.join(out_dir, f"{base}_{video_counter:02d}.mp4")):
            video_counter += 1

        deadline = time.time() + submitted * 600  # 10 phút/video tối đa
        found = 0
        prev_size_map = {}  # {filename: size}

        while time.time() < deadline and found < submitted and self.running:
            time.sleep(3)
            try:
                current = set(os.listdir(out_dir))
                added = current - snap
                # Chỉ lấy file .mp4 mới (không phải .crdownload)
                new_mp4s = sorted([f for f in added
                                   if f.endswith(".mp4") and not f.endswith(".crdownload")])
                for fname in new_mp4s:
                    src = os.path.join(out_dir, fname)
                    # Chờ file ổn định
                    sz = os.path.getsize(src) if os.path.exists(src) else 0
                    if prev_size_map.get(fname) == sz and sz > 0:
                        # File ổn định → đổi tên theo thứ tự
                        dst_name = f"{base}_{video_counter:02d}.mp4"
                        dst = os.path.join(out_dir, dst_name)
                        if not os.path.exists(dst):
                            shutil.move(src, dst)
                            sz_mb = os.path.getsize(dst) / 1024 / 1024
                            self.log(f"✅ Tải về #{video_counter}: {dst_name} ({sz_mb:.1f} MB)")
                            snap.add(dst_name)  # tránh detect lại
                            video_counter += 1
                            found += 1
                            self.root.after(0, lambda f=found, s=submitted:
                                self.tv_status_lbl.config(text=f"📥 Đã nhận {f}/{s} video"))
                    else:
                        prev_size_map[fname] = sz
            except Exception as e:
                self.log(f"⚠ Monitor: {e}")

        self.running = False
        self.root.after(0, self.tv_progress.stop)
        self.root.after(0, lambda: self.tv_status_lbl.config(text=""))
        self.log(f"\n✅ RAPID xong! Nhận {found}/{submitted} video → {out_dir}")

    # ── TAB: Tạo Ảnh ─────────────────────────────────────
    def _tab_text2image(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="🖼️  Tạo Ảnh")

        # Header
        hf = Frame(f, bg="#0A0F1A"); hf.pack(fill=X)
        Label(hf, text="🖼️  Text → Image  (Nano Banana 2 trên Flow)",
              font=("Segoe UI", 12, "bold"), bg="#0A0F1A", fg=ACCENT
              ).pack(anchor=W, padx=16, pady=10)

        # Prompt box
        lf = self._card(f, "📝 Danh sách Prompt  (mỗi dòng 1 ảnh)")
        lf.pack(fill=BOTH, expand=True, padx=12, pady=6)
        self.ti_prompts = scrolledtext.ScrolledText(
            lf, height=8, font=("Consolas", 9),
            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.ti_prompts.pack(fill=BOTH, expand=True, padx=4, pady=4)
        self.ti_prompts.insert(END,
            "A cute cat sitting on a rainbow cloud, digital art\n"
            "A futuristic cityscape at sunset, cyberpunk style\n"
            "Portrait of a samurai warrior, watercolor painting")

        # Settings
        sf = self._card(f, "⚙️ Cài đặt")
        sf.pack(fill=X, padx=12, pady=4)
        r1 = Frame(sf, bg=CARD); r1.pack(fill=X, pady=3, padx=8)
        Label(r1, text="Tên file:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.ti_base = Entry(r1, width=20, font=("Segoe UI", 9),
                             bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.ti_base.insert(0, "image")
        self.ti_base.pack(side=LEFT, padx=6, ipady=3)
        r2 = Frame(sf, bg=CARD); r2.pack(fill=X, pady=3, padx=8)
        Label(r2, text="Lưu tại:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.ti_out = Entry(r2, width=55, font=("Segoe UI", 9),
                            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.ti_out.insert(0, OUTPUT_DIR_IMAGE)
        self.ti_out.pack(side=LEFT, padx=6, ipady=3)
        self._btn(r2, "📂", lambda: self._browse(self.ti_out),
                  color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)

        # Delay
        df = self._card(f, "⏱ Độ trễ giữa các prompt")
        df.pack(fill=X, padx=12, pady=4)
        df_r = Frame(df, bg=CARD); df_r.pack(anchor=W, padx=8, pady=4)
        self.ti_delay = StringVar(value="normal")
        for txt, val in [("Bình thường (5s)", "normal"),
                          ("Gấp đôi (10s)", "double"),
                          ("Ngẫu nhiên (6-15s)", "random")]:
            Radiobutton(df_r, text=txt, variable=self.ti_delay, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=8)

        # Timeout — cố định 5 phút
        tf = self._card(f, "⬇️ Tự động chờ ảnh xong → Tải về ngay")
        tf.pack(fill=X, padx=12, pady=4)
        self.ti_timeout = StringVar(value="300")
        Label(tf, text="  ⏳  Chờ đến khi ảnh xong, tối đa 5 phút  →  Tải xuống ngay khi phát hiện hoàn tất",
              font=("Segoe UI", 9, "bold"), bg=CARD, fg=GREEN).pack(anchor=W, padx=12, pady=6)
        Label(tf, text="  ℹ️  Tool phát hiện ảnh xong sẽ tải ngay, không cần chờ hết 5 phút!",
              font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(anchor=W, padx=20, pady=(0, 4))

        # Progress
        self.ti_progress = ttk.Progressbar(f, mode="indeterminate", style="TProgressbar")
        self.ti_progress.pack(fill=X, padx=12, pady=(6, 2))
        self.ti_status_lbl = Label(f, text="", font=("Segoe UI", 8), bg=BG, fg=MUTED)
        self.ti_status_lbl.pack()

        # Buttons
        btn_row = Frame(f, bg=BG); btn_row.pack(fill=X, padx=12, pady=8)
        self._btn(btn_row, "  ▶  START — Tạo ảnh tuần tự + Tải về",
                  self._start_text2image, color=GREEN
                  ).pack(side=LEFT, fill=X, expand=True, ipady=9, padx=(0, 4))
        self._btn(btn_row, "  ⏹  STOP",
                  self._stop, color=RED
                  ).pack(side=LEFT, ipady=9, ipadx=8)

    def _start_text2image(self):
        raw = self.ti_prompts.get("1.0", END).strip()
        lines = [l.strip() for l in raw.splitlines() if l.strip() and not l.startswith("#")]
        if not lines:
            messagebox.showerror("Lỗi", "Chưa nhập prompt!")
            return
        if not self.bc.is_alive():
            messagebox.showerror("Lỗi", "Chưa mở Chrome! Vào tab Browser & Setup trước.")
            return
        out_dir = self.ti_out.get()
        os.makedirs(out_dir, exist_ok=True)
        self.log(f"🖼️ Bắt đầu Text→Image: {len(lines)} prompt(s)")
        self.nb.select(6)  # switch to Logs tab (index shifted)
        self._run_bg(lambda: self._t2i_worker(lines, out_dir))

    def _t2i_worker(self, lines, out_dir):
        self.running = True
        self.root.after(0, self.ti_progress.start)
        results = []
        try:
            for i, prompt in enumerate(lines, 1):
                if not self.running:
                    results.append((i, prompt[:50], '⏹ Dừng', ''))
                    break

                short = prompt[:60]
                self.log(f"\n══ 🖼️ [{i}/{len(lines)}] {short}...")
                self.root.after(0, lambda ii=i, t=len(lines), p=prompt[:40]:
                    self.ti_status_lbl.config(text=f"🖼️ [{ii}/{t}] {p}..."))

                delay_map = {"normal": 5, "double": 10, "random": None}
                d_val = delay_map.get(self.ti_delay.get(), 5)
                delay = d_val if d_val is not None else random.randint(6, 15)

                if i == 1:
                    self.log("🆕 Tạo project mới...")
                    ok = self.bc.new_project()
                    if not ok:
                        results.append((i, short, '❌ Lỗi tạo project', ''))
                        break
                    time.sleep(2)
                else:
                    self.log(f"♻️ Tái dùng project [{i}/{len(lines)}]...")
                    ready = self.bc.wait_for_prompt_ready(timeout=60)
                    if not ready:
                        ok = self.bc.new_project()
                        if not ok:
                            results.append((i, short, '❌ Lỗi tạo project', ''))
                            continue
                        time.sleep(2)

                ok = self.bc.set_prompt(prompt)
                if not ok:
                    results.append((i, short, '❌ Lỗi dán prompt', ''))
                    continue
                time.sleep(0.8)

                ok = self.bc.click_generate()
                if not ok:
                    results.append((i, short, '❌ Lỗi nút Tạo', ''))
                    continue

                fname = f"{self.ti_base.get()}_{i:02d}.png"
                dl_ok = self.bc.wait_and_download_image(out_dir, fname,
                    timeout=int(self.ti_timeout.get()))
                if dl_ok:
                    results.append((i, short, '✅ Thành công', fname))
                else:
                    results.append((i, short, '⚠ Không tải được', fname))

                if i < len(lines):
                    self.log(f"⏳ Chờ {delay}s rồi prompt tiếp...")
                    time.sleep(delay)
        except Exception as e:
            self.log(f"❌ Lỗi ngoài dự kiến: {e}")
        finally:
            self.running = False
            self.root.after(0, self.ti_progress.stop)
            self.root.after(0, lambda: self.ti_status_lbl.config(text=""))
            self._log_summary("Text→Image", results, out_dir)

    # ── TAB 4: Nhân Vật ─────────────────────────────────
    def _tab_char_setup(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="👤  Nhân Vật")

        # Hướng dẫn
        guide = self._card(f, "📋 Hướng dẫn")
        guide.pack(fill=X, padx=12, pady=(10,5))
        Label(guide, text=(
            "1. Chon anh nhan vat -> chon nhieu anh (khong gioi han)\n"
            "2. Dat ten ngan gon cho tung nhan vat  (VD: Alice, Bob, NhanVat1)\n"
            "3. Bam Upload tat ca len Flow - tool tu upload theo thu tu\n"
            "4. Sang tab Tao Video de generate video co nhan vat"
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

    def _choose_char_images(self):
        paths = filedialog.askopenfilenames(
            title="Chọn ảnh nhân vật",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.webp *.jfif"), ("All", "*.*")]
        )
        if not paths: return
        self.characters.clear()
        for idx, p in enumerate(paths, 1):
            stem = Path(p).stem
            # Gợi ý tên đơn giản: nếu tên file là UUID thì dùng 'Nhan_vat_1'
            if len(stem) > 20 or '-' in stem:
                default_name = f"Nhan_vat_{idx}"
            else:
                default_name = stem
            name = self._ask_name(default_name)
            if name:
                self.characters[name] = p

        self.char_list.config(state=NORMAL)
        self.char_list.delete("1.0", END)
        for n, pth in self.characters.items():
            self.char_list.insert(END, f"{n}: {pth}\n")
        self.char_list.config(state=DISABLED)
        self.log(f"✅ Đã chọn {len(self.characters)} nhân vật: {', '.join(self.characters.keys())}")
        # Cập nhật Create Video tab
        self._refresh_char_display()

    def _ask_name(self, default=""):
        dlg = Toplevel(self.root)
        dlg.title("Đặt tên nhân vật")
        dlg.geometry("360x150")
        dlg.configure(bg=BG)
        dlg.grab_set()
        Label(dlg, text=f"  Đặt tên nhân vật cho ảnh: {default[:40]}",
              font=("Segoe UI", 9), bg=BG, fg=TEXT).pack(pady=8, anchor=W, padx=10)
        var = StringVar(value=default)
        Entry(dlg, textvariable=var, width=32, font=("Segoe UI", 11), bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat").pack(pady=4, ipady=4)
        result = [None]  # Bug fix: default None, không phải default filename
        def ok():
            v = var.get().strip()
            result[0] = v if v else None
            dlg.destroy()
        def on_close():
            result[0] = None  # X-close = bỏ qua ảnh này
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", on_close)
        Button(dlg, text="OK", command=ok, bg=GREEN, fg="white", width=10).pack(pady=6)
        dlg.wait_window()
        return result[0]  # None nếu bỏ qua, string nếu có tên

    def _clear_chars(self):
        self.characters.clear()
        self.char_list.config(state=NORMAL)
        self.char_list.delete("1.0", END)
        self.char_list.config(state=DISABLED)

    def _upload_chars(self):
        if not self.characters:
            messagebox.showerror("Lỗi", "Chưa chọn ảnh nhân vật!")
            return
        if not self.bc.is_alive():
            messagebox.showerror("Lỗi", "Chưa mở Chrome!")
            return
        self._run_bg(self._upload_chars_worker)

    def _upload_chars_worker(self):
        names = list(self.characters.keys())
        total = len(names)
        self.root.after(0, lambda: self.char_progress.config(maximum=total, value=0))
        self.log(f"📤 Bắt đầu upload {total} ảnh nhân vật...")
        ok_count = 0
        for i, name in enumerate(names, 1):
            path = self.characters[name]
            self.log(f"📤 Upload [{i}/{total}]: {name} ({Path(path).name})")
            self.root.after(0, lambda l=f"Uploading {name}... ({i}/{total})": self.char_status_lbl.config(text=l))
            # KHÔNG gọi new_project() — upload tất cả vào project hiện tại
            ok = self.bc.upload_image(path)
            if ok:
                ok_count += 1
            self.root.after(0, lambda v=i: self.char_progress.config(value=v))
            time.sleep(1.5)  # chờ mọi thứ ổn định giữa các ảnh
        msg = f"✅ Upload xong {ok_count}/{total} nhân vật!"
        self.root.after(0, lambda: self.char_status_lbl.config(text=msg))
        self.log(msg)

    # ── TAB 5: Tạo Video Nhân Vật ───────────────────────
    def _tab_create_video(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="🎞️  Tạo Video")

        # Hướng dẫn
        guide = self._card(f, "📋 Hướng dẫn")
        guide.pack(fill=X, padx=12, pady=(10,4))
        Label(guide, text=(
            "1. Nhap danh sach prompt (moi dong 1 canh)\n"
            "2. Bam START -> Tool tu dong upload anh nhan vat + generate tung video\n"
            "Luu y: Prompt co ten nhan vat -> chen dung anh do | Khong co ten -> upload tat ca"
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
        self.cv_prompts.insert(END, "Alice và Bob đang đi dạo trong công viên\nCharlie đang chạy trên bãi biển")

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

        # Timeout — cố định 10 phút, phát hiện xong tải ngay
        tf = self._card(f, "⬇️ Tự động chờ video xong → Tải về ngay")
        tf.pack(fill=X, padx=12, pady=4)
        self.cv_timeout = StringVar(value="600")
        Label(tf, text="  ⏳  Chờ đến khi video xong, tối đa 10 phút  →  Tải xuống ngay khi phát hiện hoàn tất",
              font=("Segoe UI", 9, "bold"), bg=CARD, fg=GREEN).pack(anchor=W, padx=12, pady=6)
        Label(tf, text="  ℹ️  Tool phát hiện video xong sẽ tải ngay, không cần chờ hết 10 phút!",
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

    def _refresh_char_display(self):
        """Cập nhật label nhân vật trong Create Video tab"""
        if self.characters:
            names = ", ".join(self.characters.keys())
            self.cv_char_display.config(
                text=f"✅ {len(self.characters)} nhân vật: {names}\n"
                     f"   → TẤT CẢ ảnh sẽ được upload vào mỗi video",
                fg="green"
            )
        else:
            self.cv_char_display.config(
                text="Chưa có nhân vật. Setup trong tab 'Character Setup' trước.", fg="gray"
            )

    def _on_tab_change(self, evt):
        idx = self.nb.index(self.nb.select())
        if idx == 5:  # Create Video tab
            self._refresh_char_display()

    def _start_create_video(self):
        raw = self.cv_prompts.get("1.0", END).strip()
        prompts = [l.strip() for l in raw.splitlines() if l.strip() and not l.startswith("#")]
        if not prompts:
            messagebox.showerror("Lỗi", "Chưa nhập prompt!")
            return
        if not self.bc.is_alive():
            messagebox.showerror("Lỗi", "Chưa mở Chrome!")
            return
        out_dir = self.cv_out.get()
        os.makedirs(out_dir, exist_ok=True)
        self.log(f"🚀 Create Video: {len(prompts)} prompt(s), {len(self.characters)} nhân vật")
        self.nb.select(6)
        self._run_bg(lambda: self._create_video_worker(prompts, out_dir))

    def _create_video_worker(self, prompts, out_dir):
        self.running = True
        self.root.after(0, self.cv_progress.start)
        import random
        delay_map = {"normal": 5, "double": 10, "random": None}
        chars = list(self.characters.items())
        results = []
        submitted = []  # [(index, short, fname, project_url)]

        try:
            # ════════════════════════════════════════════
            # PHASE 1: Submit tất cả prompt nhanh
            # ════════════════════════════════════════════
            total = len(prompts)
            self.log(f"\n{'═'*60}")
            self.log(f"📤  PHASE 1 — Submit {total} prompt(s) + upload nhân vật")
            self.log(f"{'═'*60}")

            d_val = delay_map.get(self.cv_delay.get(), 5)

            for i, prompt in enumerate(prompts, 1):
                if not self.running:
                    results.append((i, prompt[:50], '⏹ Dừng', ''))
                    break
                short = prompt[:50]
                fname = f"{self.cv_base.get()}_{i:02d}.mp4"
                self.log(f"\n📤 [{i}/{total}] {short}...")
                self.root.after(0, lambda ii=i, t=total:
                    self.cv_status_lbl.config(text=f"📤 Submit [{ii}/{t}]..."))

                detected = [(n, p) for n, p in chars if n.lower() in prompt.lower()]
                to_upload = detected if detected else chars
                if to_upload:
                    self.log(f"   👤 Nhân vật: {[n for n,_ in to_upload]}")

                ok = self.bc.new_project()
                if not ok:
                    results.append((i, short, '❌ Lỗi tạo project', ''))
                    continue
                time.sleep(2)

                # Upload ảnh nhân vật
                for name, img_path in to_upload:
                    self.log(f"   📤 Upload ảnh {name}...")
                    self.bc.upload_image(img_path)
                    time.sleep(0.5)

                # Đóng panel media
                try:
                    from selenium.webdriver.common.keys import Keys
                    self.bc.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(0.5)
                except: pass

                ok = self.bc.set_prompt(prompt)
                if not ok:
                    results.append((i, short, '❌ Lỗi dán prompt', ''))
                    continue
                time.sleep(1)

                ok = self.bc.click_generate()
                if not ok:
                    results.append((i, short, '❌ Lỗi nút Tạo', ''))
                    continue

                proj_url = self.bc.driver.current_url
                submitted.append((i, short, fname, proj_url))
                self.log(f"   ✅ Đã submit #{i}")

                if i < total and self.running:
                    delay = d_val if d_val is not None else random.randint(6, 15)
                    self.log(f"   ⏳ Chờ {delay}s...")
                    time.sleep(delay)

            self.log(f"\n📤 Phase 1 xong: {len(submitted)}/{total} prompt đã submit")

            if not submitted:
                return

            # ════════════════════════════════════════════
            # PHASE 2: Quay lại tải từng video theo thứ tự
            # ════════════════════════════════════════════
            self.log(f"\n{'═'*60}")
            self.log(f"⬇️  PHASE 2 — Tải {len(submitted)} video theo thứ tự")
            self.log(f"{'═'*60}")

            for idx, (i, short, fname, proj_url) in enumerate(submitted, 1):
                if not self.running:
                    results.append((i, short, '⏹ Dừng tải', ''))
                    break

                self.log(f"\n⬇️ [{idx}/{len(submitted)}] Quay lại: {short}...")
                self.root.after(0, lambda ii=idx, t=len(submitted), fn=fname:
                    self.cv_status_lbl.config(text=f"⬇️ Tải [{ii}/{t}] {fn}..."))

                try:
                    self.bc.driver.get(proj_url)
                    time.sleep(3)
                except Exception as e:
                    results.append((i, short, '❌ Lỗi mở URL', ''))
                    continue

                dl_ok = self.bc.wait_and_download(out_dir, fname,
                    timeout=int(self.cv_timeout.get()))
                if dl_ok:
                    results.append((i, short, '✅ Thành công', fname))
                    self.root.after(0, lambda fn=fname: self.cv_status_lbl.config(
                        text=f"✅ Tải xong: {fn}"))
                else:
                    results.append((i, short, '⚠ Không tải được', fname))
                    self.root.after(0, lambda fn=fname: self.cv_status_lbl.config(
                        text=f"⏭ Bỏ qua: {fn}"))

        except Exception as e:
            self.log(f"❌ Lỗi ngoài dự kiến: {e}")
        finally:
            self.running = False
            self.root.after(0, self.cv_progress.stop)
            self.root.after(0, lambda: self.cv_status_lbl.config(text=""))
            self._log_summary("Tạo Video Nhân Vật", results, out_dir)

    def _test_char_select(self):
        """Test: chỉ upload ảnh, không generate"""
        if not self.characters:
            messagebox.showinfo("Test", "Chưa có nhân vật trong Character Setup!")
            return
        raw = self.cv_prompts.get("1.0", END)
        for name, path in self.characters.items():
            if name.lower() in raw.lower():
                self.log(f"🧪 TEST: Sẽ upload ảnh '{name}' từ {path}")
        messagebox.showinfo("Test OK", f"Detect {len(self.characters)} nhân vật. Xem log để biết chi tiết.")

    # ── TAB 6: Logs ──────────────────────────────────────
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

    def _save_log(self):
        p = filedialog.asksaveasfilename(defaultextension=".txt",
                                          filetypes=[("Text", "*.txt")])
        if p:
            self.log_text.config(state=NORMAL)
            content = self.log_text.get("1.0", END)
            self.log_text.config(state=DISABLED)
            Path(p).write_text(content, encoding="utf-8")
            self.log(f"✅ Đã lưu log: {p}")

    # ── TAB 7: Ghép Video ───────────────────────────────
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

    def _open_merger_window(self):
        win = Toplevel(self.root)
        win.title("Video Merger Tool")
        win.geometry("560x480")
        win.resizable(False, False)
        win.configure(bg=BG)

        Label(win, text="🎬 GHÉP VIDEO TOOL", bg=BG, fg=ACCENT, font=("Segoe UI", 13, "bold")).pack(pady=10)

        # Chọn folder
        f1 = LabelFrame(win, text="Chọn Folder Chứa Video", padx=8, pady=5)
        f1.pack(fill=X, padx=15, pady=6)
        folder_var = StringVar()
        fr = Frame(f1); fr.pack(fill=X)
        Entry(fr, textvariable=folder_var, width=40).pack(side=LEFT, padx=4)
        def browse_folder():
            d = filedialog.askdirectory()
            if d:
                folder_var.set(d)
                vids = sorted(Path(d).glob("*.mp4"))
                vid_list.config(state=NORMAL)
                vid_list.delete("1.0", END)
                for v in vids:
                    vid_list.insert(END, f"{v.name}\n")
                vid_list.config(state=DISABLED)
        Button(fr, text="Chọn Folder", bg=ACCENT, fg="white",
               command=browse_folder).pack(side=LEFT)

        # Danh sách video
        f2 = LabelFrame(win, text="Danh Sách Video", padx=8, pady=5)
        f2.pack(fill=BOTH, expand=True, padx=15, pady=4)
        vid_list = scrolledtext.ScrolledText(f2, height=8, font=("Consolas", 9), state=DISABLED)
        vid_list.pack(fill=BOTH, expand=True)

        # Output
        f3 = LabelFrame(win, text="Nơi Lưu File & Tên Output", padx=8, pady=5)
        f3.pack(fill=X, padx=15, pady=4)
        r = Frame(f3); r.pack(fill=X)
        Label(r, text="Lưu vào:").pack(side=LEFT)
        out_dir_var = StringVar()
        Entry(r, textvariable=out_dir_var, width=36).pack(side=LEFT, padx=4)
        Button(r, text="Chọn", command=lambda: out_dir_var.set(filedialog.askdirectory() or out_dir_var.get())
               ).pack(side=LEFT, bg=ACCENT, fg="white")
        r2 = Frame(f3); r2.pack(fill=X, pady=3)
        Label(r2, text="Tên file:").pack(side=LEFT)
        fname_var = StringVar(value="video_ghep.mp4")
        Entry(r2, textvariable=fname_var, width=30).pack(side=LEFT, padx=4)

        # Progress
        m_prog = ttk.Progressbar(win, mode="indeterminate")
        m_prog.pack(fill=X, padx=15, pady=4)
        m_status = Label(win, text="Vui lòng chọn folder chứa video")
        m_status.pack()

        def do_merge():
            folder = folder_var.get()
            if not folder:
                messagebox.showerror("Lỗi", "Chưa chọn folder!")
                return
            out_d = out_dir_var.get() or folder
            fname = fname_var.get() or "video_ghep.mp4"
            out_path = str(Path(out_d) / fname)

            vids = sorted(Path(folder).glob("*.mp4"))
            if not vids:
                messagebox.showerror("Lỗi", "Không có file MP4 trong folder!")
                return

            list_file = str(Path(folder) / "_merge_list.txt")
            with open(list_file, "w", encoding="utf-8") as lf:
                for v in vids:
                    lf.write(f"file '{v}'\n")

            m_prog.start()
            m_status.config(text=f"Đang ghép {len(vids)} video...")

            def run():
                try:
                    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                           "-i", list_file, "-c", "copy", out_path]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                    if res.returncode == 0:
                        win.after(0, lambda: m_prog.stop())
                        win.after(0, lambda: m_status.config(text=f"✅ Xong! → {out_path}"))
                        win.after(0, lambda: messagebox.showinfo("✅ Done", f"Ghép xong!\n{out_path}"))
                    else:
                        err = res.stderr[:500]
                        win.after(0, lambda: m_prog.stop())
                        win.after(0, lambda: m_status.config(text="❌ Lỗi FFmpeg"))
                        win.after(0, lambda: messagebox.showerror("Lỗi", f"FFmpeg error:\n{err}"))
                except FileNotFoundError:
                    win.after(0, lambda: m_prog.stop())
                    win.after(0, lambda: m_status.config(text="❌ FFmpeg không có trong PATH"))
                    win.after(0, lambda: messagebox.showerror("Lỗi", "FFmpeg chưa được cài!\nTải tại: https://ffmpeg.org"))
                except Exception as e:
                    _e = str(e)
                    win.after(0, lambda: m_prog.stop())
                    win.after(0, lambda: m_status.config(text=f"❌ {_e}"))
            threading.Thread(target=run, daemon=True).start()

        Button(win, text="▶ GHÉP VIDEO", bg=GREEN, fg="white",
               font=("Segoe UI", 11, "bold"), command=do_merge
               ).pack(fill=X, padx=15, pady=8, ipady=8)

    # ─── HELPERS ────────────────────────────
    def _browse(self, entry_widget):
        d = filedialog.askdirectory()
        if d:
            entry_widget.delete(0, END)
            entry_widget.insert(0, d)

    def _run_bg(self, fn):
        """Chạy fn trong background thread, bảo vệ double-start"""
        if self.running:
            self.log("⚠ Đang chạy rồi — chờ hoàn tất trước!")
            return
        threading.Thread(target=fn, daemon=True).start()


# ═══════════════════════════════════════
# ENTRY POINT
# ═══════════════════════════════════════
if __name__ == "__main__":
    # Cài dependencies nếu thiếu
    if not HAS_SELENIUM:
        print("📦 Cài selenium + webdriver-manager...")
        os.system("pip install selenium webdriver-manager -q")
        print("✅ Xong! Vui lòng chạy lại.")
        sys.exit(0)

    root = Tk()
    app = VeoApp(root)
    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()
