"""
Veo 3 Flow Automation Tool
Tự động hóa Google Flow để tạo video Veo 3
"""
import json
import os, sys, time, json, threading, subprocess, shutil, re
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox, scrolledtext

FLOW_URL = "https://labs.google/fx/vi/tools/flow"
CHROME_PROFILE = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data")
OUTPUT_DIR_TEXT = str(Path.home() / "Downloads" / "VEO3_OUTPUT" / "text_to_video")
OUTPUT_DIR_CHAR = str(Path.home() / "Downloads" / "VEO3_OUTPUT" / "character_video")
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

# ─── Gemini API (graceful) ───
try:
    # Bug 12: ưu tiên package mới google.genai, fallback sang google.generativeai cũ
    try:
        import google.genai as genai
        HAS_GEMINI = True
        GEMINI_NEW_SDK = True
    except ImportError:
        import google.generativeai as genai
        HAS_GEMINI = True
        GEMINI_NEW_SDK = False
except ImportError:
    HAS_GEMINI = False
    GEMINI_NEW_SDK = False


# ═══════════════════════════════════════════════════════
# BROWSER CONTROLLER
# ═══════════════════════════════════════════════════════
class BrowserController:
    def __init__(self, log_fn=None):
        self.driver = None
        self.log = log_fn or print
        self.wait = None
        self._download_dir = OUTPUT_DIR_TEXT

    # ── Tìm Chrome executable trên Windows ──
    @staticmethod
    def _find_chrome():
        candidates = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.join(os.environ.get("LOCALAPPDATA",""),
                         "Google","Chrome","Application","chrome.exe"),
            r"C:\Program Files\Google\Chrome Beta\Application\chrome.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                return c
        # Thử lấy từ registry
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
            path, _ = winreg.QueryValueEx(key, "")
            if os.path.exists(path):
                return path
        except: pass
        return None

    # ── Kiểm tra port 9222 đã mở chưa ──
    @staticmethod
    def _is_port_open(port=9222, timeout=1.0):
        import socket
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=timeout):
                return True
        except:
            return False

    def connect_existing(self):
        """Kết nối tới Chrome đang chạy với --remote-debugging-port=9222"""
        if not HAS_SELENIUM:
            return False

        # Kiểm tra port trước khi cố kết nối
        if not self._is_port_open(9222):
            self.log("❌ Port 9222 chưa mở — Chrome chưa được khởi động với debug port!")
            self.log("💡 Dùng nút 'MỞ CHROME' trong tool để mở Chrome đúng cách.")
            return False

        for attempt in range(1, 4):
            try:
                self.log(f"🔗 Kết nối Chrome (lần {attempt}/3)...")
                opts = Options()
                opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                # Không cần profile hay options khác khi attach vào Chrome có sẵn
                svc = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=svc, options=opts)
                self.wait = WebDriverWait(self.driver, 30)
                url = self.driver.current_url
                self.log(f"✅ Kết nối thành công! URL: {url[:60]}")
                return True
            except Exception as e:
                self.log(f"⚠ Lần {attempt} thất bại: {str(e)[:80]}")
                if attempt < 3:
                    time.sleep(2)

        self.log("❌ Không thể kết nối sau 3 lần thử.")
        self.log("💡 Giải pháp: Tắt Chrome → Bấm nút 'MỞ CHROME' → Đăng nhập lại.")
        return False

    def open(self, mode="normal", download_dir=None):
        """
        Phương pháp ĐÚNG: Launch Chrome bằng subprocess với debug port.
        Chrome chạy ĐỘC LẬP — không bị đóng khi WebDriver ngắt kết nối.
        mode: normal | incognito | fresh
        """
        if not HAS_SELENIUM:
            import tkinter.messagebox as _mb
            try: _mb.showerror("Lỗi", "Chưa cài selenium!\nChạy: pip install selenium webdriver-manager")
            except: pass
            return False

        chrome_exe = self._find_chrome()
        if not chrome_exe:
            self.log("❌ Không tìm thấy Chrome! Hãy cài Google Chrome.")
            return False

        dl_dir = download_dir or OUTPUT_DIR_TEXT
        os.makedirs(dl_dir, exist_ok=True)
        self._download_dir = dl_dir

        # Profile riêng cho tool — tránh conflict với Chrome đang mở
        veo_profile = os.path.join(
            os.path.expanduser("~"), "AppData", "Local",
            "Google", "Chrome", "VEO3_Profile"
        )
        os.makedirs(veo_profile, exist_ok=True)

        # Build Chrome command
        cmd = [chrome_exe]
        cmd += [
            "--remote-debugging-port=9222",
            f"--user-data-dir={veo_profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--start-maximized",
        ]
        if mode == "incognito":
            cmd.append("--incognito")

        cmd.append(FLOW_URL)  # mở ngay Flow URL

        # Kiểm tra nếu port đã dùng (Chrome debug đang chạy) → đóng trước
        if self._is_port_open(9222):
            self.log("⚠ Port 9222 đã được dùng — thử kết nối vào Chrome đó...")
            return self.connect_existing()

        self.log(f"🚀 Launch Chrome: {os.path.basename(chrome_exe)}")
        self.log(f"   Profile: VEO3_Profile | Tải về: {dl_dir}")
        try:
            # Windows không hỗ trợ close_fds=True khi có stdin/stdout
            subprocess.Popen(cmd, creationflags=0x00000008)  # DETACHED_PROCESS
        except Exception as e:
            self.log(f"❌ Không chạy được Chrome: {e}")
            return False

        # Chờ Chrome khởi động và port mở (tối đa 15s)
        self.log("⏳ Chờ Chrome khởi động...")
        for i in range(15):
            time.sleep(1)
            if self._is_port_open(9222):
                self.log(f"✅ Chrome đã sẵn sàng sau {i+1}s")
                break
        else:
            self.log("⚠ Chrome chưa mở port sau 15s — thử kết nối bất chấp...")

        # Kết nối WebDriver vào Chrome đang chạy
        return self.connect_existing()


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

    def generate_image_flow(self, prompt, count=1, orientation="ngang", out_dir=None, log_fn=None):
        """
        Tạo ảnh bằng Nano Banana 2 trên Google Flow.
        - prompt: nội dung ảnh (tiếng Anh)
        - count: số ảnh (1/2/3/4)
        - orientation: 'ngang' | 'doc'
        - out_dir: thư mục lưu ảnh tải về
        """
        log = log_fn or self.log
        if not self.driver:
            log("❌ Chưa kết nối trình duyệt!")
            return False
        try:
            # 1. Mở Flow và chờ tải
            log("🌿 Đang mở trang Flow tạo ảnh...")
            self.driver.get(FLOW_URL)
            time.sleep(3)

            # 2. Click tab 'Image' (hình ảnh) — tìm bằng text
            try:
                img_tab = WebDriverWait(self.driver, 12).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(.,'Image') or contains(.,'H\u00ecnh ảnh')]"
                    ))
                )
                self.driver.execute_script("arguments[0].click();", img_tab)
                time.sleep(1)
                log("✅ Đã chuyển sang tab Image")
            except TimeoutException:
                log("⚠ Không thấy tab Image — có thể đang ở đúng tab rồi")

            # 3. Chọn hướng: Ngang / Dọc
            orient_text = "Ngang" if orientation == "ngang" else "Dọc"
            try:
                orient_btn = self.driver.find_element(
                    By.XPATH,
                    f"//button[contains(.,'{orient_text}') or contains(.,'Landscape') or contains(.,'Portrait')]"
                )
                self.driver.execute_script("arguments[0].click();", orient_btn)
                time.sleep(0.5)
                log(f"✅ Hướng: {orient_text}")
            except:
                log(f"⚠ Không tìm được nút hướng {orient_text} — dùng mặc định")

            # 4. Chọn số lượng ảnh (x1, x2, x3, x4)
            try:
                count_btn = self.driver.find_element(
                    By.XPATH, f"//button[normalize-space(.)='x{count}']"
                )
                self.driver.execute_script("arguments[0].click();", count_btn)
                time.sleep(0.5)
                log(f"✅ Số ảnh: x{count}")
            except:
                log(f"⚠ Không tìm được nút x{count}")

            # 5. Nhập prompt vào ô text
            log("📝 Nhập prompt...")
            try:
                # Tìm textarea placeholder 'Bạn muốn tạo gì?'
                # Bug 4 fixed: ưu tiên textarea, rồi contenteditable, KHÔNG dùng div[@aria-label] quá rộng
                ta = None
                for _sel in ["textarea", "div[contenteditable='true'][role='textbox']",
                             "div[contenteditable='true']"]:
                    try:
                        _el = WebDriverWait(self.driver, 8).until(
                            EC.element_to_be_clickable((By.CSS_SELECTOR, _sel))
                        )
                        if _el and _el.is_displayed():
                            ta = _el
                            break
                    except:
                        continue
                if not ta:
                    raise Exception("Không tìm thấy ô nhập prompt cho ảnh")
                self.driver.execute_script(
                    "arguments[0].focus();"
                    "document.execCommand('selectAll',false,null);"
                    "document.execCommand('delete',false,null);", ta)
                time.sleep(0.2)
                ta.send_keys(prompt)
                time.sleep(0.5)
                log("✅ Đã nhập prompt")
            except Exception as e:
                log(f"❌ Không nhập được prompt: {e}")
                return False

            # 6. Click nút generate (→)
            log("⏳ Đang gửi tạo ảnh...")
            try:
                gen_btn = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[@aria-label='Generate' or @aria-label='Tạo' or "
                        "contains(@class,'generate') or "
                        "(self::button and ./*[name()='svg'])]" # icon arrow button
                    ))
                )
                self.driver.execute_script("arguments[0].click();", gen_btn)
                log("🎨 Nano Banana 2 đang vẽ ảnh...")
            except:
                # Fallback: Enter trên textarea
                try:
                    ta.send_keys("\n")
                    log("🎨 Gửi bằng Enter...")
                except:
                    log("❌ Không thể bấm generate!")
                    return False

            # 7. Chờ ảnh hiển ra (tối đa 60s)
            log("⏳ Chờ ảnh render (tối đa 60s)...")
            img_srcs = []
            for i in range(60):
                time.sleep(1)
                try:
                    imgs = self.driver.find_elements(
                        By.XPATH,
                        "//img[contains(@src,'blob:') or contains(@src,'data:image') or "
                        "contains(@src,'generativelanguage') or contains(@src,'usercontent')]"
                    )
                    if len(imgs) >= count:
                        img_srcs = [im.get_attribute("src") for im in imgs[:count]]
                        log(f"✅ Đã tạo được {len(img_srcs)} ảnh!")
                        break
                except: pass

            if not img_srcs:
                log("⚠ Không tìm thấy ảnh — hãy kiểm tra tay trên trình duyệt.")
                return True  # Vẫn có thể user thấy ảnh trong browser

            # 8. Tải ảnh về (nếu out_dir có và URL không phải blob:)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
                saved = 0
                for idx, src in enumerate(img_srcs):
                    if src.startswith("blob:"):
                        log(f"⚠ Ảnh {idx+1}: blob URL — cần tải tay từ trình duyệt")
                        continue
                    try:
                        import urllib.request
                        fname = os.path.join(out_dir, f"nano_banana_{int(time.time())}_{idx+1}.jpg")
                        urllib.request.urlretrieve(src, fname)
                        log(f"💾 Đã lưu: {fname}")
                        saved += 1
                    except Exception as e:
                        log(f"⚠ Không lưu được ảnh {idx+1}: {e}")
                if saved == 0:
                    log("⚠ Ảnh được render trong browser dưới dạng blob, có thể download thủ công.")
            return True
        except Exception as e:
            log(f"❌ Lỗi tạo ảnh: {e}")
            return False

    def set_prompt(self, text):
        """Nhập prompt vào Flow — clipboard paste (trigger real React paste event)"""
        import subprocess, tempfile

        def _copy_to_clipboard(t):
            """Copy text vào Windows clipboard qua PowerShell — safe với path bất kỳ"""
            try:
                # Ghi ra file tạm với encoding UTF-8
                tmp = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.txt', delete=False, encoding='utf-8'
                )
                tmp.write(t); tmp.close()
                # Dùng đường dẫn an toàn qua biến PS (tránh lỗi ký tự đặc biệt)
                subprocess.run(
                    ["powershell", "-Command",
                     "$p = [System.IO.Path]::GetFullPath($args[0]);"
                     "Set-Clipboard -Value ([System.IO.File]::ReadAllText($p, [System.Text.Encoding]::UTF8))",
                     tmp.name],
                    capture_output=True, timeout=8
                )
                try: os.unlink(tmp.name)
                except: pass
            except Exception as ce:
                self.log(f"⚠ Clipboard error: {ce}")

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

            # Scroll vào giữa màn hình + JS focus (tránh overlay chặn click)
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});", box
            )
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", box)
            time.sleep(0.3)

            # ── Phương pháp 1: send_keys từng chunk — đáng tin nhất với React ──
            try:
                self.driver.execute_script("""
                    arguments[0].focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('delete', false, null);
                """, box)
                time.sleep(0.2)
                for chunk in [text[i:i+80] for i in range(0, len(text), 80)]:
                    box.send_keys(chunk)
                    time.sleep(0.05)
                time.sleep(0.4)
                actual = self.driver.execute_script("return arguments[0].innerText;", box)
                if actual and text[:30].lower() in actual.lower():
                    self.log(f"✅ Đã nhập prompt (send_keys): {text[:60]}...")
                    return True
                self.log("⚠ send_keys: text không khớp, thử clipboard...")
            except Exception as e1:
                self.log(f"⚠ send_keys: {e1}")

            # ── Phương pháp 2: Clipboard Ctrl+V ──
            try:
                _copy_to_clipboard(text)
                self.driver.execute_script("""
                    arguments[0].focus();
                    document.execCommand('selectAll', false, null);
                    document.execCommand('delete', false, null);
                """, box)
                time.sleep(0.2)
                box.send_keys(Keys.CONTROL + "v")
                time.sleep(0.8)
                actual = self.driver.execute_script("return arguments[0].innerText;", box)
                if actual and text[:30].lower() in actual.lower():
                    self.log(f"✅ Đã dán prompt (Ctrl+V): {text[:60]}...")
                    return True
                self.log("⚠ Clipboard: text không xuất hiện, thử execCommand...")
            except Exception as e2:
                self.log(f"⚠ Clipboard: {e2}")

            # ── Phương pháp 3: execCommand insertText (deprecated fallback) ──
            try:
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
            except Exception as e3:
                self.log(f"⚠ execCommand: {e3}")

            self.log("❌ Tất cả phương pháp đều thất bại")
            return False
        except Exception as e:
            self.log(f"❌ set_prompt: {e}")
            return False

    def click_generate(self):
        """Click nút Tạo — chờ enabled + ActionChains + Enter fallback"""
        try:
            # Chờ 1.5s sau khi paste để React cập nhật state
            time.sleep(1.5)
            # Bug 2 fixed: aria-label selector bền hơn class (không bị Google update)
            btn_selectors = [
                (By.XPATH, "//button[@aria-label='Generate' or @aria-label='Submit']"),
                (By.XPATH, "//button[@aria-label='Tạo' or @aria-label='Gửi']"),
                (By.XPATH, "//button[.//span[normalize-space()='arrow_forward'] or .//span[normalize-space()='send']]"),
                (By.XPATH, "//button[.//mat-icon[contains(.,'arrow_forward')]]"),
                # Fallback class (có thể đổi theo Google update)
                (By.CSS_SELECTOR, "button.bMhrec"),
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
                    # Scroll vào view + JS click để bypass overlay
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", btn
                    )
                    time.sleep(0.3)
                    try:
                        # Thử ActionChains trước
                        ActionChains(self.driver).move_to_element(btn).click().perform()
                        self.log("✅ Đã click nút Tạo (ActionChains)")
                    except Exception:
                        # Fallback JS click nếu bị intercept
                        self.driver.execute_script("arguments[0].click();", btn)
                        self.log("✅ Đã click nút Tạo (JS click)")
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
                # JS focus + Enter để tránh ElementClickInterceptedException
                self.driver.execute_script("arguments[0].focus();", box)
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

            # Bug 3 fixed: log cảnh báo thay vì im lặng return True
            self.log("⚠ Tất cả phương pháp click generate đều thất bại!")
            return False
        except Exception as e:
            self.log(f"❌ click_generate: {e}")
            return False


    def wait_for_video(self, timeout=300):
        """Chờ video tạo xong — chỉ check SUCCESS, không check error giả"""
        self.log(f"⏳ Chờ video hoàn thành (tối đa {timeout}s)...")
        start = time.time()
        check_interval = 10  # kiểm tra mỗi 10s
        last_log = 0

        while time.time() - start < timeout:
            time.sleep(check_interval)
            elapsed = int(time.time() - start)

            try:
                # 1. Tìm nút "Tải xuống" — chỉ xuất hiện khi video xong
                dl_btns = self.driver.find_elements(
                    By.XPATH,
                    "//button[normalize-space(.)='Tải xuống' or @aria-label='Tải xuống' or @aria-label='Download']"
                )
                if dl_btns:
                    self.log(f"✅ Video hoàn thành sau {elapsed}s! Tìm thấy nút Tải xuống.")
                    return True

                # 2. URL đổi sang /edit/ — project đã tạo xong 1 clip
                url = self.driver.current_url
                if "/edit/" in url:
                    # Tìm video element có src
                    vids = self.driver.find_elements(By.TAG_NAME, "video")
                    for v in vids:
                        src = v.get_attribute("src") or ""
                        if src and ("blob:" in src or "storage.googleapis" in src):
                            self.log(f"✅ Video ready sau {elapsed}s!")
                            return True

                # Log tiến trình mỗi 30s
                if elapsed - last_log >= 30:
                    self.log(f"   ⏳ {elapsed}s — đang render...")
                    last_log = elapsed

            except Exception as e:
                pass  # Chrome bận, thử lại sau

        self.log(f"⏱ Timeout sau {timeout}s — tiếp prompt tiếp")
        return False

    def wait_for_prompt_ready(self, timeout=30):
        """Đợi ô prompt xuất hiện trở lại sau khi video render xong.
        Dùng để tiếp tục dán prompt mới mà không cần tạo project mới.
        Trả về True nếu ô prompt sẵn sàng.
        """
        self.log("⏳ Chờ ô nhập prompt sẵn sàng...")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                for sel in ["div[role='textbox']", "div[contenteditable='true']"]:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for el in els:
                        if el.is_displayed():
                            self.log("✅ Ô prompt sẵn sàng!")
                            return True
            except Exception:
                pass
            time.sleep(2)
        self.log("⚠ Không thấy ô prompt sau 30s — có thể cần tạo project mới")
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
        """Click Tải xuống → chờ file tải XONG hoàn toàn → đổi tên theo thứ tự"""
        try:
            os.makedirs(save_dir, exist_ok=True)

            # ── Bước 1: Set CDP download dir ──
            try:
                self.driver.execute_cdp_cmd(
                    "Browser.setDownloadBehavior",
                    {"behavior": "allow", "downloadPath": save_dir}
                )
            except: pass

            # Monitor cả save_dir và ~/Downloads
            chrome_dl = str(Path.home() / "Downloads")
            watch_dirs = list({save_dir, chrome_dl})

            # Snapshot SAU khi set CDP, TRƯỚC khi click
            snap = {d: set(os.listdir(d)) if os.path.exists(d) else set()
                    for d in watch_dirs}

            # ── Bước 2: Tìm và click nút Tải xuống ──
            dl_btn = None
            for sel in [
                "//button[normalize-space(.)='Tải xuống']",
                "//button[@aria-label='Tải xuống' or @aria-label='Download']",
                "//button[contains(.,'Tải xuống')]",
                "//button[contains(.,'Download')]",
                "//a[contains(@href,'.mp4')]",
            ]:
                try:
                    el = self.driver.find_element(By.XPATH, sel)
                    if el and el.is_displayed():
                        dl_btn = el
                        break
                except: continue

            if not dl_btn:
                self.log("⚠️ Không tìm thấy nút Tải xuống")
                return False

            ActionChains(self.driver).move_to_element(dl_btn).click().perform()
            self.log("⬇️ Đã click Tải xuống — chờ file...")

            # ── Bước 3: Chờ file .mp4 xuất hiện (tối đa 90s) ──
            # Bug 10 fixed: 90s quá ngắn, tăng lên 180s cho mạng chậm
            deadline = time.time() + 180
            new_file = None
            new_dir = save_dir
            while time.time() < deadline:
                time.sleep(1.5)
                for d in watch_dirs:
                    if not os.path.exists(d): continue
                    current = set(os.listdir(d))
                    added = current - snap[d]
                    # File tải xong = .mp4, không phải .crdownload
                    done = [f for f in added
                            if f.endswith(".mp4") and not f.endswith(".crdownload")]
                    if done:
                        new_file = done[0]
                        new_dir = d
                        break
                    # Còn đang tải → log progress
                    partial = [f for f in added if f.endswith(".crdownload")]
                    if partial:
                        elapsed = int(time.time() - (deadline - 90))
                        self.log(f"   ⬇️ Đang tải... {partial[0]} ({elapsed}s)")
                if new_file:
                    break

            if not new_file:
                self.log("⚠️ Hết giờ 90s — file không xuất hiện")
                return False

            # ── Bước 4: Chờ file ổn định (không còn ghi) ──
            src = os.path.join(new_dir, new_file)
            self.log(f"⏳ Chờ file ổn định: {new_file}")
            prev_size = -1
            stable_count = 0
            for _ in range(15):  # tối đa 15 lần × 1s = 15s
                time.sleep(1)
                try:
                    cur_size = os.path.getsize(src)
                    if cur_size == prev_size and cur_size > 0:
                        stable_count += 1
                        if stable_count >= 2:  # ổn định 2 lần liên tiếp
                            break
                    else:
                        stable_count = 0
                    prev_size = cur_size
                except: break

            # ── Bước 5: Đổi tên theo thứ tự, đảm bảo không trùng ──
            dst = os.path.join(save_dir, filename)
            if os.path.exists(dst):
                ts = time.strftime("%H%M%S")
                dst = os.path.join(save_dir, filename.replace(".mp4", f"_{ts}.mp4"))

            shutil.move(src, dst)
            size_mb = os.path.getsize(dst) / 1024 / 1024
            self.log(f"✅ Đã lưu: {os.path.basename(dst)} ({size_mb:.1f} MB)")
            return True

        except Exception as e:
            self.log(f"❌ click_download: {e}")
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

            # ── Bước 4: Chờ thumbnail mới xuất hiện (so sánh trước/sau) ──
            # Bug 9 fixed: snapshot số lượng ảnh TRƯỚC khi upload để detect ảnh MỚI
            try:
                before_thumbs = len(self.driver.find_elements(By.XPATH,
                    "//img[contains(@src,'blob:') or contains(@src,'googleusercontent') or contains(@src,'data:image')]"))
            except:
                before_thumbs = 0
            self.log(f"⏳ Chờ xác nhận upload (trước: {before_thumbs} ảnh)...")
            deadline = time.time() + 25
            while time.time() < deadline:
                time.sleep(2)
                try:
                    thumbs = self.driver.find_elements(By.XPATH,
                        "//img[contains(@src,'blob:') or contains(@src,'googleusercontent') or contains(@src,'data:image')]")
                    if len(thumbs) > before_thumbs:
                        self.log(f"✅ Upload OK: {Path(image_path).name} (+{len(thumbs)-before_thumbs} ảnh mới)")
                        return True
                except: pass

            self.log(f"⚠ Không xác nhận được upload (hết 25s) — có thể vẫn OK")
            return True

        except Exception as e:
            self.log(f"❌ upload_image: {e}")
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
        # characters: {name: {"path":str, "desc":str, "aliases":list}}
        self.characters = {}
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

    # ── TAB 8: Viết sub ────────────────────────────
    def _tab_vietsub(self):
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="📝  Vietsub")

        # ── Hướng dẫn ──
        guide = self._card(f, "📋 Hướng dẫn đốt phụ đề Việt vào video")
        guide.pack(fill=X, padx=12, pady=(10,4))
        Label(guide, text=(
            "①  Chọn file video .mp4 cần thêm phụ đề\n"
            "②  Nhập nội dung phụ đề (được tự động chia theo số dòng và thời lượng video)\n"
            "③  Chỉnh style, nhấn [BURN VIETSUB] → xuất file video_sub.mp4"
        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT
        ).pack(anchor=W, padx=10, pady=8)

        # ── Chọn video ──
        vf = self._card(f, "🎬 Chọn video cần thêm phụ đề")
        vf.pack(fill=X, padx=12, pady=4)
        vrow = Frame(vf, bg=CARD); vrow.pack(fill=X, padx=8, pady=6)
        Label(vrow, text="File video:", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_video = Entry(vrow, width=55, font=("Segoe UI", 9),
                              bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.vs_video.pack(side=LEFT, padx=6, ipady=3)

        def _browse_video():
            p = filedialog.askopenfilename(
                title="Chọn file video",
                filetypes=[("Video MP4", "*.mp4"), ("All", "*.*")]
            )
            if p:
                self.vs_video.delete(0, END)
                self.vs_video.insert(0, p)
                # Tự động lấy thời lượng bằng ffprobe nếu có
                self._vs_get_duration(p)

        self._btn(vrow, "📂", _browse_video,
                  color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)
        self.vs_dur_lbl = Label(vf, text="⏱ Thời lượng: chưa xác định",
                               font=("Segoe UI", 9), bg=CARD, fg=MUTED)
        self.vs_dur_lbl.pack(anchor=W, padx=10, pady=(0,4))

        # ── Nội dung phụ đề ──
        tf = self._card(f, "💬 Nội dung phụ đề  (mỗi dòng = 1 cảnh, sẽ tự chia đều)")
        tf.pack(fill=X, padx=12, pady=4)

        tip_row = Frame(tf, bg=CARD); tip_row.pack(fill=X, padx=8, pady=(4,2))
        Label(tip_row,
              text="💡 Mỗi dòng 1 câu  ─  Hoặc dùng thủ công: [bắt đầu-->kết thúc]  Ví dụ: 00:00:00-->00:00:03│Nội dung",
              bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(side=LEFT)

        self.vs_text = scrolledtext.ScrolledText(
            tf, height=8, font=("Consolas", 10),
            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.vs_text.pack(fill=X, padx=6, pady=(2,6))
        self.vs_text.insert(END,
            "Alice đang đi dạo trong công viên nhỏ\n"
            "Nắng chiều vàng chiếu qua hàng cây xanh\n"
            "Cô ấy dừng lại nhìn bầu trời\n"
            "Một ngày bình yên trôi qua"
        )

        # ── Style phụ đề ──
        sf = self._card(f, "🎨 Style phụ đề")
        sf.pack(fill=X, padx=12, pady=4)

        r1 = Frame(sf, bg=CARD); r1.pack(fill=X, padx=8, pady=(6,3))
        # Font
        Label(r1, text="Font:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_font = StringVar(value="Arial")
        font_opts = ["Arial", "Times New Roman", "Tahoma", "Calibri",
                     "SVN-Arial", "UTM-Arial", "Times-Viet"]
        OptionMenu(r1, self.vs_font, *font_opts
                   ).pack(side=LEFT, padx=4)
        # Size
        Label(r1, text="  Cỡ chữ:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_size = StringVar(value="28")
        Spinbox(r1, from_=14, to=60, textvariable=self.vs_size,
                width=5, bg=CARD, fg=TEXT, relief="flat").pack(side=LEFT, padx=4)

        r2 = Frame(sf, bg=CARD); r2.pack(fill=X, padx=8, pady=3)
        # Màu chữ
        Label(r2, text="Màu chữ:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_color = StringVar(value="&H00FFFFFF")  # Trắng
        colors = [
            ("Trắng", "&H00FFFFFF"), ("Vàng", "&H0000FFFF"),
            ("Xanh da trời", "&H00FFFF00"), ("Đỏ", "&H000000FF"),
            ("Đen", "&H00000000")
        ]
        for cname, cval in colors:
            Radiobutton(r2, text=cname, variable=self.vs_color, value=cval,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=6)

        r3 = Frame(sf, bg=CARD); r3.pack(fill=X, padx=8, pady=3)
        # Vị trí
        Label(r3, text="Vị trí:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_align = StringVar(value="2")  # 2=dưới giữa
        positions = [
            ("⬇ Dưới giữa", "2"),
            ("⬆ Trên giữa", "8"),
            ("▦ Giữa màn hình", "5"),
        ]
        for pname, pval in positions:
            Radiobutton(r3, text=pname, variable=self.vs_align, value=pval,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=8)

        r4 = Frame(sf, bg=CARD); r4.pack(fill=X, padx=8, pady=(3,6))
        # Viền chữ (outline)
        Label(r4, text="Viền:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_outline = StringVar(value="1")
        Spinbox(r4, from_=0, to=4, textvariable=self.vs_outline,
                width=4, bg=CARD, fg=TEXT, relief="flat").pack(side=LEFT, padx=4)
        Label(r4, text="  Bóng (độ lệch):", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_shadow = StringVar(value="1")
        Spinbox(r4, from_=0, to=4, textvariable=self.vs_shadow,
                width=4, bg=CARD, fg=TEXT, relief="flat").pack(side=LEFT, padx=4)

        # ── Cài đặt xuất ──
        of = self._card(f, "📂 Lưu vị trí")
        of.pack(fill=X, padx=12, pady=4)
        orow = Frame(of, bg=CARD); orow.pack(fill=X, padx=8, pady=6)
        Label(orow, text="Lưu tại:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_out = Entry(orow, width=50, font=("Segoe UI", 9),
                            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        vs_default_out = str(Path.home() / "Downloads" / "VEO3_OUTPUT" / "vietsub")
        self.vs_out.insert(0, vs_default_out)
        self.vs_out.pack(side=LEFT, padx=6, ipady=3)
        self._btn(orow, "📂", lambda: self._browse(self.vs_out),
                  color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)

        # ── Preview SRT ──
        pf = self._card(f, "🔍 Preview SRT  (tự động cập nhật)")
        pf.pack(fill=X, padx=12, pady=4)
        self.vs_preview = scrolledtext.ScrolledText(
            pf, height=6, font=("Consolas", 8), state=DISABLED,
            bg="#0A0F1A", fg=MUTED, relief="flat")
        self.vs_preview.pack(fill=X, padx=6, pady=4)

        def _update_preview(*_):
            """Cập nhật preview SRT khi user đang gõ text."""
            try:
                dur = getattr(self, '_vs_duration', 8.0)
                srt = self._vs_build_srt(
                    self.vs_text.get("1.0", END).strip(), dur
                )
                self.vs_preview.config(state=NORMAL)
                self.vs_preview.delete("1.0", END)
                self.vs_preview.insert(END, srt[:1500])
                self.vs_preview.config(state=DISABLED)
            except: pass

        self.vs_text.bind("<KeyRelease>", _update_preview)
        self.root.after(500, _update_preview)  # chạy lần đầu

        # ── Thanh tiến độ + nút ──
        bf = Frame(f, bg=BG)
        bf.pack(fill=X, padx=12, pady=6)
        self.vs_prog = ttk.Progressbar(bf, mode="indeterminate", style="TProgressbar")
        self.vs_prog.pack(fill=X, pady=(0,4))
        self.vs_status_lbl = Label(bf, text="Sẵn sàng",
                                   font=("Segoe UI", 9), bg=BG, fg=MUTED)
        self.vs_status_lbl.pack()

        btn_row = Frame(f, bg=BG); btn_row.pack(fill=X, padx=12, pady=(0,10))
        self._btn(btn_row, "  🔍  Xem Preview SRT  ", _update_preview,
                  color="#21262D").pack(side=LEFT, fill=X, expand=True,
                                        padx=(0,4), ipady=8)
        self._btn(btn_row, "  🔥  BURN VIETSUB VÀO VIDEO  ",
                  self._burn_vietsub, color=GREEN
                  ).pack(side=LEFT, fill=X, expand=True, ipady=8)

    # ── Vietsub helpers ─────────────────────────────────────
    def _vs_get_duration(self, video_path):
        """Lấy thời lượng video bằng ffprobe (giây)."""
        def _run():
            try:
                result = subprocess.run(
                    ["ffprobe","-v","quiet","-print_format","json",
                     "-show_streams", video_path],
                    capture_output=True, text=True, timeout=10
                )
                info = json.loads(result.stdout)
                dur = 0.0
                for s in info.get("streams", []):
                    d = float(s.get("duration", 0) or 0)
                    if d > dur:
                        dur = d
                if dur > 0:
                    self._vs_duration = dur
                    self.root.after(0, lambda: self.vs_dur_lbl.config(
                        text=f"⏱ Thời lượng: {dur:.1f}s ({int(dur//60)}ph{int(dur%60)}s)",
                        fg=GREEN
                    ))
                else:
                    # Fallback: ước lượng 8s
                    self._vs_duration = 8.0
                    self.root.after(0, lambda: self.vs_dur_lbl.config(
                        text="⏱ Không đọc được thời lượng — dùng 8s mặc định", fg=ORANGE
                    ))
            except FileNotFoundError:
                self._vs_duration = 8.0
                self.root.after(0, lambda: self.vs_dur_lbl.config(
                    text="⚠ FFprobe chưa cài — dùng 8s mặc định", fg=ORANGE
                ))
            except Exception as e:
                self._vs_duration = 8.0
        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def _srt_time(seconds):
        """Chuyển giây thành định dạng SRT: HH:MM:SS,mmm"""
        s = int(seconds)
        ms = int((seconds - s) * 1000)
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

    def _vs_build_srt(self, raw_text, total_duration):
        """Xây dựng nội dung file SRT từ text và thời lượng video.
        Hỗ trợ 2 định dạng:
          - Tự động: mỗi dòng 1 câu, chia đều
          - Thủ công: 00:00:00-->00:00:03│Nội dung
        """
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        if not lines:
            return "(Chưa có nội dung)"

        srt_entries = []

        # Kiểm tra có định dạng thủ công không
        manual = all("|" in l and "-->" in l.split("|")[0] for l in lines)

        if manual:
            # Định dạng thủ công: 00:00:00.000-->00:00:03.000|Nội dung
            for i, line in enumerate(lines, 1):
                time_part, _, text_part = line.partition("|")
                start_s, _, end_s = time_part.partition("-->")
                srt_entries.append(
                    f"{i}\n"
                    f"{self._srt_time(self._parse_time(start_s.strip()))} --> "
                    f"{self._srt_time(self._parse_time(end_s.strip()))}\n"
                    f"{text_part.strip()}\n"
                )
        else:
            # Tự động: chia đều thời gian
            n = len(lines)
            # Để lại 0.3s kết thúc mỗi doanh (khoảng cách giữa các dòng)
            seg = total_duration / n
            for i, line in enumerate(lines):
                start = i * seg
                end = start + seg - 0.3
                if end <= start:
                    end = start + seg
                srt_entries.append(
                    f"{i+1}\n"
                    f"{self._srt_time(start)} --> {self._srt_time(end)}\n"
                    f"{line}\n"
                )
        return "\n".join(srt_entries)

    @staticmethod
    def _parse_time(t_str):
        """Parse thời gian dạng HH:MM:SS hoặc HH:MM:SS.mmm → giây."""
        try:
            t_str = t_str.replace(",", ".").strip()
            parts = t_str.split(":")
            if len(parts) == 3:
                h, m, s = parts
                return int(h)*3600 + int(m)*60 + float(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m)*60 + float(s)
            else:
                return float(t_str)
        except:
            return 0.0

    def _burn_vietsub(self):
        """Xử lý burn phụ đề vào video bằng FFmpeg."""
        video = self.vs_video.get().strip()
        if not video or not os.path.exists(video):
            messagebox.showerror("Lỗi", "Đường dẫn video không hợp lệ!")
            return
        raw_text = self.vs_text.get("1.0", END).strip()
        if not raw_text:
            messagebox.showerror("Lỗi", "Chưa nhập nội dung phụ đề!")
            return

        out_dir = self.vs_out.get().strip()
        os.makedirs(out_dir, exist_ok=True)
        stem = Path(video).stem
        out_video = str(Path(out_dir) / f"{stem}_vietsub.mp4")

        dur = getattr(self, '_vs_duration', 8.0)
        srt_content = self._vs_build_srt(raw_text, dur)

        self.vs_prog.start()
        self.vs_status_lbl.config(text="⏳ Đang chuẩn bị...")

        def _run():
            import tempfile
            srt_path = None  # BUG FIX: khởi tạo None tránh NameError trong finally
            try:
                # Ghi file SRT tạm
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".srt", delete=False,
                    encoding="utf-8-sig",  # BOM: đảm bảo FFmpeg đọc được tiếng Việt
                    prefix="veo3_sub_"
                ) as tmp:
                    tmp.write(srt_content)
                    srt_path = tmp.name

                # Build ASS style string
                font  = self.vs_font.get()
                size  = self.vs_size.get()
                color = self.vs_color.get()
                align = self.vs_align.get()
                outline = self.vs_outline.get()
                shadow  = self.vs_shadow.get()

                style = (
                    f"FontName={font},FontSize={size},"
                    f"PrimaryColour={color},"
                    f"OutlineColour=&H00000000,"
                    f"BackColour=&H80000000,"
                    f"Bold=1,Italic=0,"
                    f"Outline={outline},Shadow={shadow},"
                    f"Alignment={align},MarginV=30"
                )

                # BUG FIX: FFmpeg subtitles filter trên Windows cần escape đúng:
                # C:\path → C\\:/path (escape dấu hai chấm chỉ ở ký tự ổ đĩa)
                srt_ffmpeg = srt_path.replace("\\", "/")
                # Chỉ escape dấu ":" ở vị trí ký tự ổ đĩa (C:/ → C\:/)
                if len(srt_ffmpeg) > 1 and srt_ffmpeg[1] == ":":
                    srt_ffmpeg = srt_ffmpeg[0] + "\\:" + srt_ffmpeg[2:]

                vf_filter = f"subtitles='{srt_ffmpeg}':force_style='{style}'"

                self.root.after(0, lambda: self.vs_status_lbl.config(
                    text=f"🔥 Burn phụ đề vào: {Path(video).name}..."
                ))

                cmd = [
                    "ffmpeg", "-y", "-i", video,
                    "-vf", vf_filter,
                    "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "copy",
                    out_video
                ]
                self.log(f"📝 🔥 Burn vietsub: {Path(video).name} → {Path(out_video).name}")
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

                if res.returncode == 0:
                    self.root.after(0, lambda: self.vs_prog.stop())
                    self.root.after(0, lambda: self.vs_status_lbl.config(
                        text=f"✅ Xong! → {out_video}", fg=GREEN
                    ))
                    self.root.after(0, lambda: messagebox.showinfo(
                        "✅ Burn xong!",
                        f"Phụ đề đã được đốt vào video!\n\n{out_video}"
                    ))
                    self.log(f"✅ Đã tạo: {out_video}")
                else:
                    err = res.stderr[-800:]
                    self.root.after(0, lambda: self.vs_prog.stop())
                    self.root.after(0, lambda: self.vs_status_lbl.config(
                        text="❌ Lỗi FFmpeg!", fg=RED))
                    self.root.after(0, lambda: messagebox.showerror(
                        "❌ Lỗi FFmpeg",
                        f"FFmpeg báo lỗi:\n{err}\n\n"
                        f"💡 Nếu lỗi 'No such file' với font: đổi font sang 'Arial'"
                    ))
            except FileNotFoundError:
                self.root.after(0, lambda: self.vs_prog.stop())
                self.root.after(0, lambda: self.vs_status_lbl.config(
                    text="❌ FFmpeg chưa được cài!", fg=RED))
                self.root.after(0, lambda: messagebox.showerror(
                    "Lỗi",
                    "FFmpeg chưa cài!\nTải tại: https://ffmpeg.org/download.html\n"
                    "Sau đó thêm vào PATH của Windows."
                ))
            except Exception as e:
                self.root.after(0, lambda: self.vs_prog.stop())
                _e = str(e)
                self.root.after(0, lambda: self.vs_status_lbl.config(
                    text=f"❌ {_e}", fg=RED))
            finally:
                # BUG FIX: chỉ xóa nếu srt_path đã được tạo
                if srt_path and os.path.exists(srt_path):
                    try: os.unlink(srt_path)
                    except: pass

        threading.Thread(target=_run, daemon=True).start()

    # ── HELPERS ─────────────────────────────────────
    # ── TAB: GEMINI AI ASSISTANT ──────────────────────────
    def _tab_gemini(self):
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="🤖  Gemini AI")

        # ── API Key ──
        api_card = self._card(f, "🔑 API Key  (lấy miễn phí tại: aistudio.google.com)")
        api_card.pack(fill=X, padx=12, pady=(10,4))
        ar = Frame(api_card, bg=CARD); ar.pack(fill=X, padx=8, pady=6)
        Label(ar, text="API Key:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.gm_key = Entry(ar, width=58, show="•", font=("Segoe UI",9),
                            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.gm_key.pack(side=LEFT, padx=6, ipady=3)

        # Load saved key
        _key_file = os.path.join(os.path.expanduser("~"), ".veo3_gemini_key")
        if os.path.exists(_key_file):
            try: self.gm_key.insert(0, open(_key_file).read().strip())
            except: pass

        def _save_key():
            try:
                open(_key_file, "w").write(self.gm_key.get().strip())
                self.log("🔑 Đã lưu API Key Gemini")
            except: pass
        self._btn(ar, "💾 Lưu", _save_key, color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)

        # ── Chọn Model ──
        mc = self._card(f, "🤖 Chọn Model")
        mc.pack(fill=X, padx=12, pady=4)
        mr = Frame(mc, bg=CARD); mr.pack(fill=X, padx=8, pady=6)
        Label(mr, text="Model:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.gm_model = StringVar(value="gemini-2.0-flash")
        models = [
            ("gemini-2.0-flash  ⏡ Nhanh + Đa phương tiện [KHUYẾN NGHỊ]", "gemini-2.0-flash"),
            ("gemini-1.5-pro    ⏡ Phân tích Video dài (tối đa 1 giờ)",   "gemini-1.5-pro"),
            ("gemini-1.5-flash  ⏡ Nhanh, rẻ hạn mức",                     "gemini-1.5-flash"),
            ("gemini-2.0-flash-exp  ⏡ Thử nghiệm mới nhất",             "gemini-2.0-flash-exp"),
        ]
        for mname, mval in models:
            Radiobutton(mr, text=mname, variable=self.gm_model, value=mval,
                        bg=CARD, fg=TEXT, selectcolor=BG, font=("Consolas",8),
                        activebackground=CARD).pack(anchor=W, padx=20)

        # ── Chế độ ──
        mc2 = self._card(f, "🎯 Chế độ")
        mc2.pack(fill=X, padx=12, pady=4)
        mr2 = Frame(mc2, bg=CARD); mr2.pack(fill=X, padx=8, pady=6)
        self.gm_mode = StringVar(value="text")
        Radiobutton(mr2, text="💬 Tạo Prompt từ mô tả (Text)",
                    variable=self.gm_mode, value="text",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD, command=lambda: self._gm_update_ui()
                    ).pack(side=LEFT, padx=8)
        Radiobutton(mr2, text="🖼️ Phân tích Ảnh/Video → Prompt",
                    variable=self.gm_mode, value="vision",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD, command=lambda: self._gm_update_ui()
                    ).pack(side=LEFT, padx=8)

        # ── INPUT (chế độ TEXT) ──
        self.gm_text_card = self._card(f, "💬 Mô tả nhân vật / cảnh video bạn muốn tạo")
        self.gm_text_card.pack(fill=X, padx=12, pady=4)
        Label(self.gm_text_card,
              text="💡 Mô tả ngắn gọn: ai/nhân vật, bầu không khí, hành động, ánh sáng, thời điểm...",
              bg=CARD, fg=MUTED, font=("Segoe UI",8)).pack(anchor=W, padx=8, pady=(2,0))
        self.gm_input = scrolledtext.ScrolledText(
            self.gm_text_card, height=5, font=("Segoe UI",10),
            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat",
            wrap=WORD)
        self.gm_input.pack(fill=X, padx=6, pady=(2,6))
        self.gm_input.insert(END,
            "Một cô gái tóc dài đỏ đi dạo trong công viên vào buổi chiều, "
            "ánh nắng vàng rọi qua lá cây xanh mật, không khí yên bình và nên thơ"
        )

        # ── INPUT (chế độ VISION) ──
        self.gm_vision_card = self._card(f, "🖼️ Upload ảnh hoặc video cần phân tích")
        # Ẩn ban đầu (chế độ text)

        vr = Frame(self.gm_vision_card, bg=CARD); vr.pack(fill=X, padx=8, pady=6)
        Label(vr, text="File:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.gm_media = Entry(vr, width=52, font=("Segoe UI",9),
                              bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.gm_media.pack(side=LEFT, padx=6, ipady=3)

        def _browse_media():
            p = filedialog.askopenfilename(
                title="Chọn ảnh hoặc video",
                filetypes=[
                    ("Hình ảnh", "*.jpg *.jpeg *.png *.webp *.gif"),
                    ("Video", "*.mp4 *.mov *.avi *.mkv"),
                    ("Tất cả", "*.*")
                ])
            if p:
                self.gm_media.delete(0, END)
                self.gm_media.insert(0, p)
        self._btn(vr, "📂", _browse_media,
                  color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)

        Label(self.gm_vision_card,
              text="💡 Gemini sẽ phân tích nội dung rồi viết Prompt Veo3 tương đương",
              bg=CARD, fg=MUTED, font=("Segoe UI",8)).pack(anchor=W, padx=10, pady=(0,6))

        # ── Yêu cầu bổ sung (cho cả 2 chế độ) ──
        rc = self._card(f, "⚙ Yêu cầu bổ sung  (tùy chọn)")
        rc.pack(fill=X, padx=12, pady=4)
        Label(rc, text="Thêm yêu cầu riêng: phong cách quay, di chuyển camera, thời gian...",
              bg=CARD, fg=MUTED, font=("Segoe UI",8)).pack(anchor=W, padx=8, pady=(4,2))
        self.gm_extra = Entry(rc, width=70, font=("Segoe UI",9),
                              bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.gm_extra.insert(0, "slow motion, cinematic, 4K, golden hour lighting, camera pan left")
        self.gm_extra.pack(fill=X, padx=8, pady=(0,6), ipady=3)

        # ── Nút gửi ──
        br = Frame(f, bg=BG); br.pack(fill=X, padx=12, pady=4)
        self.gm_send_btn = self._btn(
            br, "  ✨  GỬi cho Gemini AI  ",
            self._gm_send, color="#7C3AED")
        self.gm_send_btn.pack(side=LEFT, fill=X, expand=True, ipady=10)

        # ── Kết quả ──
        oc = self._card(f, "📝 Kết quả — Prompt do Gemini viết")
        oc.pack(fill=X, padx=12, pady=4)
        self.gm_result = scrolledtext.ScrolledText(
            oc, height=12, font=("Consolas",10), wrap=WORD,
            bg="#0A0F1A", fg="#58D68D", insertbackground=TEXT, relief="flat")
        self.gm_result.pack(fill=X, padx=6, pady=(4,6))

        # Nút action sau khi có kết quả
        ab = Frame(f, bg=BG); ab.pack(fill=X, padx=12, pady=(0,6))
        self._btn(ab, "📋 Sao chép",
                  lambda: self._gm_copy(), color="#21262D"
                  ).pack(side=LEFT, padx=(0,4), ipady=6, ipadx=8)
        self._btn(ab, "➜ Gửi sang Text→Video",
                  lambda: self._gm_send_to_t2v(), color=ACCENT
                  ).pack(side=LEFT, padx=4, ipady=6, ipadx=8)
        self._btn(ab, "➜ Gửi sang Tạo Video Nhân Vật",
                  lambda: self._gm_send_to_cv(), color="#E67E22"
                  ).pack(side=LEFT, padx=4, ipady=6, ipadx=8)

        # Status
        self.gm_status = Label(f, text="🤖 Sẵn sàng",
                               font=("Segoe UI",9), bg=BG, fg=MUTED)
        self.gm_status.pack(pady=(0,8))

        # ── Tạo ảnh trực tiếp qua Flow (Nano Banana 2) ──
        img_card = self._card(f, "🎨 Tạo ảnh bằng Nano Banana 2 (Google Flow — miễn phí!)")
        img_card.pack(fill=X, padx=12, pady=(4,10))

        Label(img_card,
              text="💡 Prompt dưới đây (hoặc tự nhập) — dùng kết quả từ Gemini bằng nút 'Dùng prompt'",
              bg=CARD, fg=MUTED, font=("Segoe UI",8)).pack(anchor=W, padx=8, pady=(4,2))

        self.gm_img_prompt = scrolledtext.ScrolledText(
            img_card, height=4, font=("Segoe UI",9), wrap=WORD,
            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.gm_img_prompt.pack(fill=X, padx=6, pady=(0,4))
        self.gm_img_prompt.insert(END, "A beautiful woman walking in a park, golden hour, cinematic")

        ir1 = Frame(img_card, bg=CARD); ir1.pack(fill=X, padx=8, pady=3)
        # Số lượng ảnh
        Label(ir1, text="Số ảnh:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.gm_img_count = StringVar(value="1")
        for n in ["1","2","3","4"]:
            Radiobutton(ir1, text=f"x{n}", variable=self.gm_img_count, value=n,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI",9)
                        ).pack(side=LEFT, padx=6)
        # Tỉ lệ khung
        Label(ir1, text="  Hướng:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT, padx=(12,0))
        self.gm_img_orient = StringVar(value="ngang")
        Radiobutton(ir1, text="▬ Ngang", variable=self.gm_img_orient, value="ngang",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD).pack(side=LEFT, padx=4)
        Radiobutton(ir1, text="▮ Dọc", variable=self.gm_img_orient, value="doc",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD).pack(side=LEFT, padx=4)

        ir2 = Frame(img_card, bg=CARD); ir2.pack(fill=X, padx=8, pady=(2,6))
        self._btn(ir2, "⬅ Dùng Prompt Gemini",
                  lambda: self._gm_use_result_for_img(),
                  color="#21262D").pack(side=LEFT, ipady=5, ipadx=6)
        self._btn(ir2, "  🎨  Tạo ảnh Nano Banana 2  ",
                  self._gm_generate_image,
                  color="#C0392B").pack(side=LEFT, padx=6, ipady=5, fill=X, expand=True)

        self.gm_img_status = Label(
            img_card, text="💡 Nhấn nút 'Tạo ảnh' — trình duyệt phải đang mở và kết nối",
            font=("Segoe UI",8), bg=CARD, fg=MUTED, wraplength=700, justify=LEFT)
        self.gm_img_status.pack(anchor=W, padx=8, pady=(0,4))

        # ── BATCH IMAGE QUEUE (JSON) ──
        bq = self._card(f, "📋 Batch Tạo ảnh Hàng Loạt — JSON / mỗi dòng 1 prompt")
        bq.pack(fill=X, padx=12, pady=(0,10))

        Label(bq,
              text=(
                "💡 Dán prompt JSON: [\"prompt1\",\"prompt2\"] hoặc mỗi dòng 1 prompt.\n"
                "   Tool sẽ tự split, dán từng prompt vào Flow, đợi ảnh xong rồi tải về theo thứ tự."
              ),
              bg=CARD, fg=MUTED, font=("Segoe UI", 8),
              justify=LEFT).pack(anchor=W, padx=8, pady=(4, 2))

        self.bq_text = scrolledtext.ScrolledText(
            bq, height=7, font=("Consolas", 9), wrap=WORD,
            bg="#0D1117", fg="#F9E64F", insertbackground=TEXT, relief="flat")
        self.bq_text.pack(fill=X, padx=6, pady=(0, 4))
        self.bq_text.insert(END,
            '\n'.join([
                '[',
                '  "A samurai warrior in cherry blossom rain, cinematic, 4K",',
                '  "Futuristic neon city at night, cyberpunk style, rain reflections",',
                '  "Baby panda eating bamboo in a misty forest, cute, soft light"',
                ']'
            ])
        )

        bq_r1 = Frame(bq, bg=CARD); bq_r1.pack(fill=X, padx=8, pady=3)
        Label(bq_r1, text="Số ảnh/prompt:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.bq_count = StringVar(value="1")
        for n in ["1","2","3","4"]:
            Radiobutton(bq_r1, text=f"x{n}", variable=self.bq_count, value=n,
                        bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                        activebackground=CARD).pack(side=LEFT, padx=5)
        Label(bq_r1, text="  Hướng:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT, padx=(12,0))
        self.bq_orient = StringVar(value="ngang")
        Radiobutton(bq_r1, text="▬ Ngang", variable=self.bq_orient, value="ngang",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD).pack(side=LEFT, padx=4)
        Radiobutton(bq_r1, text="▮ Dọc", variable=self.bq_orient, value="doc",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD).pack(side=LEFT, padx=4)

        bq_r2 = Frame(bq, bg=CARD); bq_r2.pack(fill=X, padx=8, pady=2)
        Label(bq_r2, text="Đợi giữa nhóm (s):", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.bq_delay = Entry(bq_r2, width=5, font=("Segoe UI",9),
                              bg="#0D1117", fg=TEXT, relief="flat", justify=CENTER)
        self.bq_delay.insert(0, "3"); self.bq_delay.pack(side=LEFT, padx=6, ipady=3)
        Label(bq_r2, text="  Max chờ/ảnh (s):", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.bq_timeout = Entry(bq_r2, width=5, font=("Segoe UI",9),
                                bg="#0D1117", fg=TEXT, relief="flat", justify=CENTER)
        self.bq_timeout.insert(0, "90"); self.bq_timeout.pack(side=LEFT, padx=6, ipady=3)

        bq_r3 = Frame(bq, bg=CARD); bq_r3.pack(fill=X, padx=8, pady=(2,4))
        self.bq_start_btn = self._btn(
            bq_r3, "  ▶️  Bắt đầu Batch Tạo ảnh  ",
            self._img_batch_start, color="#1A7F37")
        self.bq_start_btn.pack(side=LEFT, fill=X, expand=True, ipady=8)
        self.bq_stop_btn = self._btn(
            bq_r3, "⏹ Dừng", self._img_batch_stop, color="#6E2424")
        self.bq_stop_btn.pack(side=LEFT, padx=(4,0), ipady=8, ipadx=10)

        self.bq_progress = ttk.Progressbar(bq, mode="determinate", maximum=100)
        self.bq_progress.pack(fill=X, padx=8, pady=(4,2))
        self.bq_status = Label(
            bq, text="📋 Sẵn sàng. Nhấn 'Bắt đầu' để chạy batch.",
            font=("Segoe UI",8), bg=CARD, fg=MUTED, wraplength=700, justify=LEFT)
        self.bq_status.pack(anchor=W, padx=8, pady=(0,6))
        self._bq_running = False

        # Ẩn vision card ban đầu
        self._gm_update_ui()


    def _gm_update_ui(self):
        m = self.gm_mode.get()
        if m == "text":
            self.gm_text_card.pack(fill=X, padx=12, pady=4)
            self.gm_vision_card.pack_forget()
        else:
            self.gm_text_card.pack_forget()
            self.gm_vision_card.pack(fill=X, padx=12, pady=4)

    # \u2500\u2500 BATCH IMAGE \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    def _img_batch_start(self):
        """Parse JSON/lines v\u00e0 ch\u1ea1y batch t\u1ea1o \u1ea3nh."""
        if not self.browser.driver:
            messagebox.showerror("L\u1ed7i",
                "Tr\u00ecnh duy\u1ec7t ch\u01b0a k\u1ebft n\u1ed1i!\nV\u00e0o tab 'K\u1ebft N\u1ed1i' \u2192 M\u1edf Chrome.")
            return
        raw = self.bq_text.get("1.0", END).strip()
        if not raw:
            messagebox.showerror("L\u1ed7i", "Ch\u01b0a nh\u1eadp prompts!")
            return

        # Parse: JSON array ho\u1eb7c m\u1ed7i d\u00f2ng 1 prompt
        prompts = []
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, list):
                prompts = [str(p).strip() for p in parsed if str(p).strip()]
            else:
                prompts = [str(parsed).strip()]
        except json.JSONDecodeError:
            # M\u1ed7i d\u00f2ng 1 prompt
            prompts = [ln.strip().strip('",') for ln in raw.splitlines()
                       if ln.strip() and not ln.strip().startswith('[')
                       and not ln.strip() == ']']

        if not prompts:
            messagebox.showerror("L\u1ed7i", "Kh\u00f4ng t\u00ecm th\u1ea5y prompt n\u00e0o!")
            return

        self._bq_running = True
        self.bq_start_btn.config(state=DISABLED, text="\u23f3 \u0110ang ch\u1ea1y...")
        self.bq_progress["value"] = 0
        self.bq_progress["maximum"] = len(prompts)

        count = int(self.bq_count.get())
        orient = self.bq_orient.get()
        delay = float(self.bq_delay.get() or "3")
        timeout = int(self.bq_timeout.get() or "90")
        out_dir = str(Path.home() / "Downloads" / "VEO3_OUTPUT" / "images")

        self.log(f"\ud83d\udccb B\u1eaft \u0111\u1ea7u batch: {len(prompts)} prompts, x{count} \u1ea3nh m\u1ed7i prompt")
        threading.Thread(
            target=self._img_batch_run,
            args=(prompts, count, orient, delay, timeout, out_dir),
            daemon=True
        ).start()

    def _img_batch_stop(self):
        self._bq_running = False
        self.bq_status.config(text="\u23f9 \u0110\u00e3 d\u1eebng batch.", fg=RED)
        self.bq_start_btn.config(state=NORMAL, text="  \u25b6\ufe0f  B\u1eaft \u0111\u1ea7u Batch T\u1ea1o \u1ea3nh  ")
        self.log("\u23f9 Batch \u0111\u01b0\u1ee3c d\u1eebng b\u1edfi ng\u01b0\u1eddi d\u00f9ng.")

    def _img_batch_run(self, prompts, count, orient, delay, timeout, out_dir):
        """
        Pipeline batch:
        - Main loop: d\u00e1n prompt li\u00ean t\u1ee5c, ch\u1ec9 \u0111\u1ee3i ~delay gi\u00e2y gi\u1eefa m\u1ed7i prompt
        - Watcher thread: c\u1ee9 2s scan browser, t\u1ef1 download \u1ea3nh m\u1edbi xu\u1ea5t hi\u1ec7n
        """
        os.makedirs(out_dir, exist_ok=True)
        total = len(prompts)
        done_prompts = [0]
        img_serial  = [1]
        seen_srcs   = set()   # \u0111\u00e3 download ho\u1eb7c \u0111\u00e3 g\u1eb7p

        # \u2500\u2500 WATCHER THREAD \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        watcher_alive = [True]

        def _watcher():
            import urllib.request as _ur
            while watcher_alive[0]:
                time.sleep(2)
                drv2 = self.browser.driver
                if not drv2:
                    continue
                try:
                    imgs = drv2.find_elements(By.XPATH,
                        "//img["
                        "contains(@src,'generativelanguage') or "
                        "contains(@src,'usercontent') or "
                        "contains(@src,'data:image') or "
                        "contains(@src,'blob:')]"
                    )
                    for im in imgs:
                        src = im.get_attribute("src") or ""
                        if not src or src in seen_srcs:
                            continue
                        seen_srcs.add(src)
                        if src.startswith("blob:"):
                            self.log(f"   \u26a0 blob URL \u2014 c\u1ea7n t\u1ea3i tay t\u1eeb browser")
                            continue
                        try:
                            fname = os.path.join(
                                out_dir, f"img_{img_serial[0]:04d}.jpg")
                            _ur.urlretrieve(src, fname)
                            self.log(f"   \ud83d\udcbe \u0110\u00e3 t\u1ea3i: img_{img_serial[0]:04d}.jpg")
                            img_serial[0] += 1
                        except Exception as e:
                            self.log(f"   \u274c L\u01b0u l\u1ed7i: {e}")
                except Exception:
                    pass

        watcher_thread = threading.Thread(target=_watcher, daemon=True)
        watcher_thread.start()

        # \u2500\u2500 MAIN LOOP: D\u00e1n prompt li\u00ean t\u1ee5c \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        drv = self.browser.driver
        if not drv:
            self.log("\u274c Kh\u00f4ng c\u00f3 browser!")
            watcher_alive[0] = False
            self._bq_running = False
            return

        # M\u1edf Flow m\u1ed9t l\u1ea7n duy nh\u1ea5t
        self.log("\ud83c\udf0f M\u1edf Flow...")
        drv.get(FLOW_URL)
        time.sleep(3)

        # Click Image tab m\u1ed9t l\u1ea7n
        try:
            tab = WebDriverWait(drv, 12).until(
                EC.element_to_be_clickable((By.XPATH,
                    "//button[contains(.,'Image') or contains(.,'H\u00ecnh \u1ea3nh')]"))
            )
            drv.execute_script("arguments[0].click();", tab)
            time.sleep(1)
            self.log("\u2705 Tab Image")
        except: pass

        # Ch\u1ecdn h\u01b0\u1edbng m\u1ed9t l\u1ea7n
        orient_text = "Ngang" if orient == "ngang" else "D\u1ecdc"
        try:
            ob = drv.find_element(By.XPATH,
                f"//button[contains(.,'{orient_text}') or "
                f"contains(.,'Landscape') or contains(.,'Portrait')]")
            drv.execute_script("arguments[0].click();", ob)
            time.sleep(0.4)
        except: pass

        # Ch\u1ecdn s\u1ed1 l\u01b0\u1ee3ng m\u1ed9t l\u1ea7n
        try:
            cb = drv.find_element(By.XPATH,
                f"//button[normalize-space(.)='x{count}']")
            drv.execute_script("arguments[0].click();", cb)
            time.sleep(0.4)
        except: pass

        # V\u00f2ng l\u1eb7p d\u00e1n t\u1eebng prompt
        for idx, prompt in enumerate(prompts):
            if not self._bq_running:
                break

            self.root.after(0, lambda i=idx, p=prompt: self.bq_status.config(
                text=f"\ud83d\ude80 [{i+1}/{total}] D\u00e1n: {p[:60]}...",
                fg=ORANGE
            ))
            self.log(f"\n\ud83c\udfa8 [{idx+1}/{total}] {prompt[:80]}")

            try:
                # Nh\u1eadp prompt v\u00e0o textarea
                ta = WebDriverWait(drv, 10).until(
                    EC.presence_of_element_located((By.XPATH,
                        "//textarea | //div[@contenteditable='true']"))
                )
                # X\u00f3a s\u1ea1ch v\u00e0 g\u00f5 m\u1edbi
                drv.execute_script(
                    "arguments[0].value=''; "
                    "arguments[0].dispatchEvent(new Event('input',{bubbles:true}));",
                    ta
                )
                time.sleep(0.2)
                ta.click()
                ta.send_keys(prompt)
                time.sleep(0.4)

                # Click Generate
                try:
                    gb = WebDriverWait(drv, 8).until(
                        EC.element_to_be_clickable((By.XPATH,
                            "//button[@aria-label='Generate' or @aria-label='T\u1ea1o' "
                            "or contains(@class,'generate')]"))
                    )
                    drv.execute_script("arguments[0].click();", gb)
                    self.log(f"   \u2705 \u0110\u00e3 g\u1eedi generate")
                except:
                    ta.send_keys("\n")
                    self.log(f"   \u2705 G\u1eedi qua Enter")

            except Exception as e:
                self.log(f"   \u274c L\u1ed7i: {e}")

            done_prompts[0] += 1
            self.root.after(0, lambda d=done_prompts[0]:
                self.bq_progress.configure(value=d))

            # Ch\u1edd ng\u1eafn r\u1ed3i d\u00e1n prompt ti\u1ebfp
            if idx < total - 1 and self._bq_running:
                self.log(f"   \u23f3 Ch\u1edd {delay:.0f}s r\u1ed3i d\u00e1n prompt ti\u1ebfp...")
                time.sleep(delay)

        # \u0110\u00e3 d\u00e1n h\u1ebft prompts. \u0110\u1ee3i watcher b\u1eaft \u1ea3nh cu\u1ed1i c\u00f9ng
        if self._bq_running:
            self.log(f"\n\u23f3 \u0110\u00e3 d\u00e1n {total} prompts. Ch\u1edd watcher b\u1eaft \u1ea3nh cu\u1ed1i (60s)...")
            self.root.after(0, lambda: self.bq_status.config(
                text=f"\u23f3 \u0110\u00e3 d\u00e1n xong {total} prompts. Watcher \u0111ang ch\u1edd \u1ea3nh render...",
                fg=ORANGE
            ))
            for _ in range(60):
                if not self._bq_running:
                    break
                time.sleep(1)

        # D\u1eebng watcher
        watcher_alive[0] = False
        self._bq_running = False

        dl_count = img_serial[0] - 1
        self.root.after(0, lambda: [
            self.bq_start_btn.config(state=NORMAL,
                text="  \u25b6\ufe0f  B\u1eaft \u0111\u1ea7u Batch T\u1ea1o \u1ea3nh  "),
            self.bq_status.config(
                text=f"\u2705 Xong! {total} prompts d\u00e1n. "
                     f"\u0110\u00e3 download {dl_count} \u1ea3nh \u2192 {out_dir}",
                fg=GREEN
            )
        ])
        self.log(f"\n\ud83c\udf89 Batch xong! D\u00e1n {total} prompts, download {dl_count} \u1ea3nh.")
        self.log(f"\ud83d\udcc1 \u1ea2nh l\u01b0u: {out_dir}")


    def _gm_build_prompt(self):
        """Xây dựng system prompt cho Gemini."""
        extra = self.gm_extra.get().strip()
        system = (
            "Bạn là chuyên gia viết prompt cho AI tạo video Veo3 của Google. "
            "Nhiệm vụ: viết prompt tiếng Anh CHUẨN, cụ thể, giàu hình ảnh. "
            "Format cần có: [subject + action], [environment], [lighting], ["
            "camera movement], [mood/atmosphere], [technical style]. "
            "Rả kết quả LOẠI Bỏ giải thích, chỉ trả về PROMPT THUẦN."
        )
        if extra:
            system += f" Thêm yêu cầu: {extra}."
        return system

    def _gm_send(self):
        key = self.gm_key.get().strip()
        if not key:
            messagebox.showerror("Lỗi", "Chưa nhập API Key Gemini!\n"
                                         "Lấy miễn phí tại: aistudio.google.com")
            return
        if not HAS_GEMINI:
            messagebox.showerror("Lỗi",
                "Chưa cài google-generativeai!\n"
                "Chạy: pip install google-generativeai")
            return

        mode = self.gm_mode.get()
        if mode == "text":
            user_input = self.gm_input.get("1.0", END).strip()
            if not user_input:
                messagebox.showerror("Lỗi", "Chưa nhập mô tả!")
                return
        else:
            media_path = self.gm_media.get().strip()
            if not media_path or not os.path.exists(media_path):
                messagebox.showerror("Lỗi", "Đường dẫn file không hợp lệ!")
                return

        self.gm_send_btn.config(state=DISABLED, text="⏳ Đang hỏi Gemini...")
        self.gm_status.config(text="⏳ Gemini đang xử lý...", fg=ORANGE)
        self.gm_result.delete("1.0", END)

        def _run():
            try:
                genai.configure(api_key=key)
                model_name = self.gm_model.get()
                model = genai.GenerativeModel(
                    model_name=model_name,
                    system_instruction=self._gm_build_prompt()
                )

                if mode == "text":
                    desc = self.gm_input.get("1.0", END).strip()
                    prompt_msg = (
                        f"Viết 3 biến thể PROMPT cho Veo3 dựa trên mô tả sau:\n"
                        f"\"{desc}\"\n\n"
                        f"Mỗi prompt trên 1 dòng riêng, bắt đầu bằng [Prompt 1], [Prompt 2], [Prompt 3]."
                    )
                    response = model.generate_content(prompt_msg)
                    result = response.text

                else:  # vision
                    media_path2 = self.gm_media.get().strip()
                    ext = Path(media_path2).suffix.lower()

                    # Upload file qua File API (cần thiết cho video)
                    is_video = ext in (".mp4",".mov",".avi",".mkv")
                    if is_video:
                        self.root.after(0, lambda: self.gm_status.config(
                            text="⏳ Upload video lên Gemini File API...", fg=ORANGE))
                        uploaded = genai.upload_file(media_path2)
                        # Chờ xử lý xong
                        import time as _t
                        while uploaded.state.name == "PROCESSING":
                            _t.sleep(2)
                            uploaded = genai.get_file(uploaded.name)
                        if uploaded.state.name == "FAILED":
                            raise Exception("Upload video thất bại!")
                        content = [
                            uploaded,
                            "Phân tích video trên rồi viết 3 PROMPT Veo3 phù hợp. "
                            "Mỗi prompt trên 1 dòng, bắt đầu bằng [Prompt 1], [Prompt 2], [Prompt 3]."
                        ]
                    else:
                        # Ảnh: đọc trực tiếp
                        import PIL.Image
                        img = PIL.Image.open(media_path2)
                        content = [
                            img,
                            (
                                "Phân tích hình ảnh này và viết 3 PROMPT Veo3 "
                                "tạo video của cảnh tương tự. "
                                "Mỗi prompt trên 1 dòng, bắt đầu bằng [Prompt 1], [Prompt 2], [Prompt 3]."
                            )
                        ]
                    response = model.generate_content(content)
                    result = response.text

                self.root.after(0, lambda: self.gm_result.insert(END, result))
                self.root.after(0, lambda: self.gm_status.config(
                    text=f"✅ Gemini ({model_name}) đã viết xong!", fg=GREEN))
                self.log(f"🤖 Gemini tạo prompt thành công ({model_name})")

            except Exception as e:
                err = str(e)
                self.root.after(0, lambda: self.gm_result.insert(END, f"❌ Lỗi:\n{err}"))
                self.root.after(0, lambda: self.gm_status.config(
                    text=f"❌ {err[:80]}", fg=RED))
                self.log(f"❌ Gemini lỗi: {err}")
            finally:
                self.root.after(0, lambda: self.gm_send_btn.config(
                    state=NORMAL, text="  ✨  GỬi cho Gemini AI  "))

        threading.Thread(target=_run, daemon=True).start()

    def _gm_copy(self):
        text = self.gm_result.get("1.0", END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.gm_status.config(text="📋 Đã sao chép!", fg=GREEN)

    def _gm_extract_prompts(self):
        """Tách các prompt từ kết quả Gemini."""
        raw = self.gm_result.get("1.0", END).strip()
        if not raw:
            return []
        # Tìm các dòng [Prompt X] ...
        # Bug 15 fixed: dùng \Z thay $ để match đúng cuối chuỗi trong DOTALL
        prompts = re.findall(r"\[Prompt \d+\]\s*(.+?)(?=\[Prompt|\Z)", raw, re.DOTALL)
        if prompts:
            return [p.strip() for p in prompts if p.strip()]
        # Fallback: trả về toàn bộ
        return [raw]

    def _gm_send_to_t2v(self):
        """Gửi prompt Gemini sang tab Text→Video."""
        prompts = self._gm_extract_prompts()
        if not prompts:
            messagebox.showinfo("Thông báo", "Chưa có kết quả từ Gemini!")
            return
        # Thêm vào ô prompt của tab Text→Video
        try:
            self.tv_prompts.delete("1.0", END)
            self.tv_prompts.insert(END, "\n".join(prompts))
            # Chuyển sang tab Text→Video (index 2)
            self.nb.select(2)
            self.gm_status.config(text=f"✅ Đã gửi {len(prompts)} prompt sang Text→Video", fg=GREEN)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không gửi được: {e}")

    def _gm_send_to_cv(self):
        """Gửi prompt Gemini sang tab Tạo Video Nhân Vật."""
        prompts = self._gm_extract_prompts()
        if not prompts:
            messagebox.showinfo("Thông báo", "Chưa có kết quả từ Gemini!")
            return
        try:
            self.cv_prompts.delete("1.0", END)
            self.cv_prompts.insert(END, "\n".join(prompts))
            # Chuyển sang tab Tạo Video (index 4)
            self.nb.select(4)
            self.gm_status.config(text=f"✅ Đã gửi {len(prompts)} prompt sang Tạo Video", fg=GREEN)
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không gửi được: {e}")

    def _gm_use_result_for_img(self):
        """Copy ket qua Gemini vao o prompt tao anh."""
        prompts = self._gm_extract_prompts()
        if not prompts:
            from tkinter import messagebox
            messagebox.showinfo("Thong bao", "Chua co ket qua Gemini!")
            return
        self.gm_img_prompt.delete("1.0", "end")
        self.gm_img_prompt.insert("end", prompts[0].strip())
        self.gm_status.config(text="Da copy prompt Gemini sang o tao anh")

    def _gm_generate_image(self):
        """Tao anh Nano Banana 2 qua Google Flow."""
        import threading
        from pathlib import Path
        if not self.bc.driver:
            from tkinter import messagebox
            messagebox.showerror("Loi", "Trinh duyet chua ket noi!\nVao tab Ket Noi -> Mo Chrome.")
            return
        prompt = self.gm_img_prompt.get("1.0", "end").strip()
        if not prompt:
            from tkinter import messagebox
            messagebox.showerror("Loi", "Chua nhap prompt tao anh!")
            return
        count = int(self.gm_img_count.get())
        orient = self.gm_img_orient.get()
        out_dir = str(Path.home() / "Downloads" / "VEO3_OUTPUT" / "images")
        self.gm_img_status.config(text="Dang tao anh...", fg="#E67E22")
        self.log(f"Tao anh x{count} ({orient}): {prompt[:60]}")
        def _run():
            try:
                self.bc.generate_image_flow(
                    prompt=prompt, count=count,
                    orientation=orient, out_dir=out_dir, log_fn=self.log)
                self.root.after(0, lambda: self.gm_img_status.config(
                    text=f"Xong! Anh luu tai: {out_dir}", fg="#2ECC71"))
                self.log(f"Tao anh xong -> {out_dir}")
            except Exception as e:
                _err = str(e)
                self.root.after(0, lambda: self.gm_img_status.config(
                    text=f"Loi: {_err}", fg="#E74C3C"))
                self.log(f"Loi: {_err}")
        threading.Thread(target=_run, daemon=True).start()


    # ── HELPERS ─────────────────────────────────────
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
        self._tab_vietsub()
        self._tab_gemini()

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

    def _scrollable_frame(self, parent):
        """Tạo frame có thể cuộn lên/xuống bằng scrollbar và mousewheel.
        Trả về (outer, inner): outer pack vào notebook, inner dùng để đặt widget."""
        outer = Frame(parent, bg=BG)

        canvas = Canvas(outer, bg=BG, highlightthickness=0)
        sb = Scrollbar(outer, orient=VERTICAL, command=canvas.yview)
        canvas.configure(yscrollcommand=sb.set)

        sb.pack(side=RIGHT, fill=Y)
        canvas.pack(side=LEFT, fill=BOTH, expand=True)

        inner = Frame(canvas, bg=BG)
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        def _on_resize(event):
            canvas.itemconfig(window_id, width=event.width)
        canvas.bind("<Configure>", _on_resize)

        def _on_inner_resize(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", _on_inner_resize)

        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        # Bind mousewheel khi chuột ở trong canvas hoặc inner
        canvas.bind("<MouseWheel>", _on_mousewheel)
        # bind_all causes scroll conflict - bind only to canvas and inner
        outer.bind("<Enter>", lambda e: canvas.bind_all("<MouseWheel>", _on_mousewheel))
        outer.bind("<Leave>", lambda e: canvas.unbind_all("<MouseWheel>"))

        return outer, inner

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
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="🌐  Kết Nối")

        # Hướng dẫn nhanh
        # ── Trạng thái đăng nhập (hiển thị ngay đầu tab) ──
        status_bar = Frame(f, bg="#0D1B2A", pady=6)
        status_bar.pack(fill=X, padx=14, pady=(10, 0))
        cfg = self._load_config()
        _init_text = ("🟢 Session đã lưu — tự động kết nối khi khởi động"
                      if cfg.get("logged_in") else "⚪ Chưa đăng nhập lần nào")
        _init_color = GREEN if cfg.get("logged_in") else MUTED
        self.login_status_lbl = Label(
            status_bar, text=_init_text, fg=_init_color,
            font=("Segoe UI", 10, "bold"), bg="#0D1B2A")
        self.login_status_lbl.pack(side=LEFT, padx=12)

        def _clear_session():
            self._save_config("logged_in", False)
            self._update_login_indicator("none")
            self.log("Đã xóa session — lần sau phải đăng nhập lại.")
        self._btn(status_bar, "Xoa session", _clear_session,
                  color="#6E2424").pack(side=RIGHT, padx=12, ipady=4)

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
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="📝  Text to Video")

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

        # Timeout
        tf = self._card(f, "⏬ Chờ video xong → Tự động tải  |  Hoặc dán ngay không chờ")
        tf.pack(fill=X, padx=12, pady=4)
        self.tv_timeout = StringVar(value="600")
        timeout_opts = [
            ("⚡ KHÔNG CHỜR — Dán prompt tiếp ngay sau delay cài đặt (fast mode)", "0"),
            ("TỰ ĐỘNG — Chờ đến khi xong, tối đa 10 phút  ⏬  Tải ngay", "600"),
            ("Tối đa 5 phút  ⏬  Tải ngay khi xong", "300"),
            ("Tối đa 3 phút  ⏬  Tải ngay khi xong", "180"),
            ("Tối đa 1 phút  ⏬  Tải ngay khi xong", "60"),
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

    def _start_text2video(self):
        # Bug 6 fixed: guard chống 2 worker cùng chạy
        # Bug 6 fixed: guard chống 2 worker cùng chạy
        if self.running:
            messagebox.showwarning("Đang chạy", "Đang có tiến trình! Nhấn STOP trước.")
            return
        if self.running:
            from tkinter import messagebox
            messagebox.showwarning("Đang chạy", "Đang có tiến trình chạy rồi! Nhấn STOP trước.")
            return
        raw = self.tv_prompts.get("1.0", END).strip()
        if not raw:
            messagebox.showerror("Lỗi", "Chưa nhập prompt!")
            return
        if not self.bc.is_alive():
            messagebox.showerror("Lỗi", "Chưa mở Chrome! Vào tab Browser & Setup trước.")
            return
        # Parse theo mode được chọn
        mode = self.tv_mode.get()   # "normal" hoặc "json"
        parsed = self._parse_all_lines(raw, mode)
        if not parsed:
            messagebox.showerror("Lỗi", "Không tìm thấy prompt hợp lệ!")
            return
        out_dir = self.tv_out.get()
        os.makedirs(out_dir, exist_ok=True)
        self.log(f"🚀 Bắt đầu Text→Video [{mode}]: {len(parsed)} prompt(s)")
        self.nb.select(5)  # switch to Logs tab
        self._run_bg(lambda: self._t2v_worker(parsed, out_dir))

    @staticmethod
    def _parse_all_lines(raw, mode="normal"):
        """Trả về list of (prompt_text, aspect_ratio, duration, meta).
        mode='normal': mỗi dòng là plain text.
        mode='json'  : tự nhận dạng JSON-block (multi-scene) hoặc JSON mỗi dòng.
        """
        results = []
        raw = raw.strip()

        if mode == "json":
            # ── Thử parse toàn bộ như 1 JSON object (multi-scene) ──
            # Ví dụ: {"scene_1":{"prompt":"..."},"scene_2":{...}}
            if raw.startswith("{"):
                try:
                    obj = json.loads(raw)
                    # Nếu có key scene_* hoặc key bất kỳ chứa dict với 'prompt'
                    scene_keys = sorted(
                        [k for k, v in obj.items() if isinstance(v, dict)],
                        key=lambda k: [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', k)]  # natural sort
                    )
                    if scene_keys:
                        for k in scene_keys:
                            scene = obj[k]
                            p, ar, dur, meta = VeoApp._parse_line(json.dumps(scene))
                            if p:
                                results.append((p, ar, dur, meta))
                        return results
                except (json.JSONDecodeError, TypeError):
                    pass  # fallback về từng dòng

            # ── Mỗi dòng là 1 JSON object ──
            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                p, ar, dur, meta = VeoApp._parse_line(line)
                if p:
                    results.append((p, ar, dur, meta))
            return results

        # mode == "normal": mỗi dòng là plain text (bỏ qua JSON parsing)
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            results.append((line, "16:9", 8, {}))
        return results

    @staticmethod
    def _parse_line(line):
        """Parse 1 dòng: JSON object hoặc plain text.
        Trả về: (prompt_text, aspect_ratio, duration, extra_info)"""
        line = line.strip()
        if line.startswith("{"):
            try:
                obj = json.loads(line)
                # Nhận nhiều key alias thường gặp
                prompt = (obj.get("prompt")
                          or obj.get("text")
                          or obj.get("content")
                          or obj.get("description")
                          or "")
                style  = obj.get("style", "")
                camera = obj.get("camera_motion", obj.get("camera", ""))
                aspect = obj.get("aspect_ratio", obj.get("ratio", "16:9"))
                duration = obj.get("duration", 8)
                extra_parts = []
                if style:  extra_parts.append(style)
                if camera: extra_parts.append(camera)
                full_prompt = prompt
                if extra_parts:
                    full_prompt = f"{prompt}. Style: {', '.join(extra_parts)}"
                if not full_prompt:
                    # Không tìm thấy key prompt → trả về raw line
                    return line, aspect, duration, obj
                return full_prompt, aspect, duration, obj
            except json.JSONDecodeError:
                pass
        # Plain text
        return line, "16:9", 8, {}

    def _t2v_worker(self, lines, out_dir):
        self.running = True
        self.root.after(0, self.tv_progress.start)
        import random
        try:
            for i, item in enumerate(lines, 1):
                if not self.running: break

                # item là tuple đã parse: (prompt_text, aspect_ratio, duration, meta)
                prompt_text, aspect_ratio, duration, meta = item
                if not prompt_text:
                    self.log(f"   ⚠ Prompt rỗng tại vị trí {i} — bỏ qua")
                    continue

                self.log(f"\n── [{i}/{len(lines)}] {prompt_text[:70]}...")
                if meta:
                    self.log(f"   📌 Ratio: {aspect_ratio} | Style: {meta.get('style','')}")

                delay_map = {"normal": 5, "double": 10, "random": None}
                d_val = delay_map.get(self.tv_delay.get(), 5)
                delay = d_val if d_val is not None else random.randint(6, 15)

                # ── Chỉ tạo project MỘT LẦN đầu tiên ──
                if i == 1:
                    self.log("🆕 Lần đầu: tạo project mới...")
                    ok = self.bc.new_project()
                    if not ok:
                        self.log("❌ Không tạo được project — dừng")
                        break
                    time.sleep(2)
                else:
                    # Các prompt tiếp theo: chờ ô prompt sẵn sàng rồi dán luôn
                    self.log(f"➡️ Prompt tiếp theo ({i}/{len(lines)}) — giữ nguyên project, chờ ô nhập...")
                    ready = self.bc.wait_for_prompt_ready(timeout=30)
                    if not ready:
                        # Fallback: scroll xuống để thử tìm ô prompt
                        self.log("⚠ Không thấy ô prompt — thử scroll xuống...")
                        try:
                            self.bc.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(1.5)
                        except:
                            pass

                # Set tỷ lệ nếu có trong JSON (chỉ đổi khi khác prompt trước)
                if aspect_ratio and aspect_ratio != "16:9":
                    self.bc.set_aspect_ratio(aspect_ratio)

                ok = self.bc.set_prompt(prompt_text)
                if not ok:
                    self.log(f"   ⚠ Dán prompt thất bại, bỏ qua prompt {i}")
                    continue
                time.sleep(0.8)

                ok = self.bc.click_generate()
                if not ok: continue

                # Cập nhật trạng thái UI
                self.root.after(0, lambda i=i, t=len(lines): self.tv_status_lbl.config(
                    text=f"⏳ [{i}/{t}] Đang generate..."))

                timeout_val = int(self.tv_timeout.get())

                if timeout_val == 0:
                    # ⚡ FAST MODE: không chờ video, dán prompt tiếp ngay sau delay
                    self.log(f"   ⚡ Fast mode — không chờ video, chờ {delay}s rồi tiếp...")
                else:
                    # Chờ video render xong rồi tải
                    ok = self.bc.wait_for_video(timeout=timeout_val)
                    if ok:
                        fname = f"{self.tv_base.get()}_{i:02d}.mp4"
                        try:
                            self.bc.driver.execute_cdp_cmd(
                                "Browser.setDownloadBehavior",
                                {"behavior": "allow", "downloadPath": out_dir}
                            )
                        except:
                            pass
                        self.bc.click_download(out_dir, fname)
                        self.root.after(0, lambda fn=fname: self.tv_status_lbl.config(
                            text=f"✅ Đã tải: {fn}"))
                    else:
                        self.log(f"   ⏭ Bỏ qua tải — chuyển prompt tiếp")

                if i < len(lines):  # Không chờ sau prompt cuối
                    self.log(f"⏳ Chờ {delay}s rồi tiếp...")
                    time.sleep(delay)

        finally:
            self.running = False
            self.root.after(0, self.tv_progress.stop)
            self.root.after(0, lambda: self.tv_status_lbl.config(text=""))
            processed = sum(1 for p in lines if p[0])
            self.log(f"\n✅ Hoàn tất Text→Video! Video đã lưu tại:\n   {out_dir}")

    def _stop(self):
        """Dừng worker đang chạy"""
        if self.running:
            self.running = False
            self.log("⏹ Đã gửi lệnh dừng — chờ bước hiện tại kết thúc...")
        else:
            self.log("ℹ️ Không có tiến trình nào đang chạy")

    def _start_rapid(self):
        """⚡ Rapid Mode: Submit tất cả nhanh → render song song trên cloud"""
        # Bug 6 fixed: guard chống 2 worker cùng chạy
        if self.running:
            messagebox.showwarning("Đang chạy", "Đang có tiến trình! Nhấn STOP trước.")
            return
        # Bug 6 fixed: guard chống 2 worker cùng chạy
        if self.running:
            from tkinter import messagebox
            messagebox.showwarning("Đang chạy", "Đang có tiến trình chạy rồi! Nhấn STOP trước.")
            return
        raw = self.tv_prompts.get("1.0", END).strip()
        if not raw:
            messagebox.showerror("Lỗi", "Chưa nhập prompt!")
            return
        if not self.bc.is_alive():
            messagebox.showerror("Lỗi", "Chưa mở Chrome!")
            return
        mode = self.tv_mode.get()
        parsed = self._parse_all_lines(raw, mode)
        if not parsed:
            messagebox.showerror("Lỗi", "Không tìm thấy prompt hợp lệ!")
            return
        out_dir = self.tv_out.get()
        os.makedirs(out_dir, exist_ok=True)
        self.log(f"⚡ RAPID MODE [{mode}]: Submit {len(parsed)} prompt(s) nhanh → render song song!")
        self.nb.select(5)
        self._run_bg(lambda: self._rapid_worker(parsed, out_dir))

    def _rapid_worker(self, lines, out_dir):
        """Submit tất cả nhanh (30s/prompt), rồi monitor download folder"""
        self.running = True
        self.root.after(0, self.tv_progress.start)
        import random

        # ─── PHASE 1: Submit tất cả prompt nhanh ───
        total = len(lines)
        submitted = 0
        try:
            for i, item in enumerate(lines, 1):
                if not self.running: break
                prompt_text, aspect_ratio, duration, meta = item
                if not prompt_text:
                    self.log(f"   ⚠ Prompt rỗng tại vị trí {i} — bỏ qua")
                    continue
                self.log(f"\n⚡ [{i}/{total}] Submit: {prompt_text[:60]}...")
                self.root.after(0, lambda i=i, t=total: self.tv_status_lbl.config(
                    text=f"⚡ Submit {i}/{t} — render song song trên cloud..."))

                # Bug 11 fixed: chỉ tạo project MỚI cho prompt đầu tiên
                # Các prompt tiếp theo tái dùng project (nhanh hơn nhiều)
                if i == 1:
                    ok = self.bc.new_project()
                    if not ok: continue
                    self.log("🆕 Đã tạo project mới cho RAPID mode")
                else:
                    ready = self.bc.wait_for_prompt_ready(timeout=20)
                    if not ready:
                        self.log(f"   ⚠ Prompt chưa sẵn sàng, thử submit vẫn")

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

        # Bug 5 fixed: Chrome tải về ~/Downloads, phải monitor cả 2 folder
        chrome_dl = str(Path.home() / "Downloads")
        monitor_dirs = list({out_dir, chrome_dl})
        snap = {d: set(os.listdir(d)) if os.path.exists(d) else set() for d in monitor_dirs}
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
                # Bug 5 fixed: scan ca hai folder
                for _mdir in monitor_dirs:
                    if not os.path.exists(_mdir): continue
                    current = set(os.listdir(_mdir))
                    added = current - snap.get(_mdir, set())
                    new_mp4s = sorted([f for f in added
                                       if f.endswith('.mp4') and not f.endswith('.crdownload')])
                    for fname in new_mp4s:
                        _fp = os.path.join(_mdir, fname)
                        sz = os.path.getsize(_fp) if os.path.exists(_fp) else 0
                        if prev_size_map.get(fname) == sz and sz > 0:
                            dst_name = f"{base}_{video_counter:02d}.mp4"
                            dst = os.path.join(out_dir, dst_name)
                            if not os.path.exists(dst):
                                shutil.move(_fp, dst)
                                sz_mb = os.path.getsize(dst) / 1024 / 1024
                                self.log(f"Tai ve #{video_counter}: {dst_name} ({sz_mb:.1f} MB)")
                                snap.setdefault(_mdir, set()).add(dst_name)
                                video_counter += 1
                                found += 1
                                self.root.after(0, lambda f=found, s=submitted:
                                    self.tv_status_lbl.config(text=f"Da nhan {f}/{s} video"))
                        else:
                            prev_size_map[fname] = sz
            except Exception as e:
                self.log(f"Monitor: {e}")

        self.log(f"\n✅ RAPID xong! Nhận {found}/{submitted} video → {out_dir}")

    # ── TAB 4: Nhân Vật ─────────────────────────────────
    def _tab_char_setup(self):
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="👤  Nhân Vật")

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
        added = 0
        for idx, p in enumerate(paths, 1):
            stem = Path(p).stem
            default_name = f"NhanVat_{len(self.characters)+1}" if (len(stem) > 20 or '-' in stem) else stem
            info = self._ask_name(default_name)
            if info and info.get("name"):
                name = info["name"]
                self.characters[name] = {
                    "path": str(p),
                    "desc": info.get("desc", ""),
                    "aliases": info.get("aliases", []),
                    "order": len(self.characters) + 1
                }
                added += 1

        self._refresh_char_list()
        self._refresh_char_display()
        self.log(f"✅ Đã thêm {added} nhân vật. Tổng: {len(self.characters)} — {', '.join(self.characters.keys())}")


    def _ask_name(self, default=""):
        """Dialog nhập tên + mô tả ngoại hình + bí danh nhân vật."""
        dlg = Toplevel(self.root)
        dlg.title("Đặt tên nhân vật")
        dlg.geometry("480x280")
        dlg.configure(bg=BG)
        dlg.grab_set()

        Label(dlg, text=f"  Ảnh: {default[:50]}",
              font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(pady=(10,4), anchor=W, padx=12)

        Label(dlg, text="Tên nhân vật  (bắt buộc — duyất, ngắn):",
              font=("Segoe UI", 9, "bold"), bg=BG, fg=TEXT).pack(anchor=W, padx=12)
        name_var = StringVar(value=default)
        Entry(dlg, textvariable=name_var, width=36,
              font=("Segoe UI", 11), bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat"
              ).pack(padx=12, pady=(2,8), ipady=4, fill=X)

        Label(dlg, text="Mô tả ngoại hình  (tiếng Anh — giúp AI nhớ nhân vật):",
              font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(anchor=W, padx=12)
        Label(dlg, text="   VD: tall woman, red hair, blue eyes, white dress",
              font=("Segoe UI", 8), bg=BG, fg=MUTED).pack(anchor=W, padx=12)
        desc_var = StringVar()
        Entry(dlg, textvariable=desc_var, width=54,
              font=("Segoe UI", 10), bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat"
              ).pack(padx=12, pady=(2,8), ipady=3, fill=X)

        Label(dlg, text="Bí danh  (ngăn cách dấu phẩy — tùy chọn):",
              font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(anchor=W, padx=12)
        Label(dlg, text="   VD: cô ấy, she, her, cô gái",
              font=("Segoe UI", 8), bg=BG, fg=MUTED).pack(anchor=W, padx=12)
        alias_var = StringVar()
        Entry(dlg, textvariable=alias_var, width=54,
              font=("Segoe UI", 10), bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat"
              ).pack(padx=12, pady=(2,10), ipady=3, fill=X)

        result = [None]
        def ok():
            v = name_var.get().strip()
            result[0] = {
                "name": v if v else None,
                "desc": desc_var.get().strip(),
                "aliases": [a.strip() for a in alias_var.get().split(",") if a.strip()]
            }
            dlg.destroy()
        def on_close():
            result[0] = None
            dlg.destroy()
        dlg.protocol("WM_DELETE_WINDOW", on_close)
        Button(dlg, text="  OK  ", command=ok, bg=GREEN, fg="white",
               font=("Segoe UI", 10, "bold")).pack(pady=4)
        dlg.wait_window()
        return result[0]  # None = bỏ qua, dict nếu có thông tin

    def _refresh_char_list(self):
        """Cập nhật bảng danh sách nhân vật trong tab Nhân Vật."""
        self.char_list.config(state=NORMAL)
        self.char_list.delete("1.0", END)
        for i, (name, info) in enumerate(self.characters.items(), 1):
            path = info["path"] if isinstance(info, dict) else info
            desc = info.get("desc", "") if isinstance(info, dict) else ""
            aliases = info.get("aliases", []) if isinstance(info, dict) else []
            line = f"#{i} [{name}]  ảnh: {Path(path).name}"
            if desc:
                line += f"\n     mô tả: {desc}"
            if aliases:
                line += f"\n     bí danh: {', '.join(aliases)}"
            self.char_list.insert(END, line + "\n\n")
        self.char_list.config(state=DISABLED)

    def _refresh_char_display(self):
        """Cập nhật nhãn hiển thị nhân vật ở tab Tạo Video."""
        if not hasattr(self, 'cv_char_display'): return
        if not self.characters:
            self.cv_char_display.config(
                text="Chưa có nhân vật. Vào tab 'Nhân Vật' để thiết lập trước."
            )
            return
        lines = []
        for i, (name, info) in enumerate(self.characters.items(), 1):
            desc = info.get("desc", "") if isinstance(info, dict) else ""
            tag = f"{i}. [{name}]" + (f" — {desc[:40]}" if desc else "")
            lines.append(tag)
        self.cv_char_display.config(text="\n".join(lines))

    @staticmethod
    def _detect_characters(prompt, characters):
        """Phát hiện nhân vật xuất hiện trong prompt.
        Hỗ trợ: tag [Alice], [ALL], [TẤT CẢ], tên chính, alias.
        Trả về list [(name, char_info)] theo thứ tự.
        """
        import re
        prompt_lower = prompt.lower()

        # ── Nhận cú pháp tag [Ten], [Ten, Ten2] ──
        tag_match = re.search(r'\[([^\]]+)\]', prompt)
        if tag_match:
            tag_content = tag_match.group(1).strip()
            if tag_content.lower() in ("all", "tất cả", "tatca", "tat_ca"):
                return list(characters.items())  # tất cả
            tag_names = [t.strip() for t in tag_content.split(",")]
            result = []
            for tn in tag_names:
                for name, info in characters.items():
                    if name.lower() == tn.lower():
                        result.append((name, info))
                        break
            if result:
                return result

        # ── Tìm theo tên chính (word-boundary match) ──
        found = []
        for name, info in characters.items():
            # Thoát ký tự regex trong tên
            pattern = r'(?<![\w\u00C0-\u024F])' + re.escape(name) + r'(?![\w\u00C0-\u024F])'
            if re.search(pattern, prompt, re.IGNORECASE):
                found.append((name, info))
                continue
            # Kiểm tra aliases
            aliases = info.get("aliases", []) if isinstance(info, dict) else []
            for alias in aliases:
                ap = r'(?<![\w\u00C0-\u024F])' + re.escape(alias) + r'(?![\w\u00C0-\u024F])'
                if re.search(ap, prompt, re.IGNORECASE):
                    found.append((name, info))
                    break
        return found

    @staticmethod
    def _build_prompt_with_chars(prompt, detected_chars):
        """Inject mô tả ngoại hình nhân vật vào prompt.
        VD: 'Alice standing on beach' -> 'Alice (tall woman, red hair) standing on beach'
        """
        import re
        result = prompt
        for name, info in detected_chars:
            desc = info.get("desc", "") if isinstance(info, dict) else ""
            if not desc:
                continue
            # Lần lượt 1: tìm tên và thêm mô tả sau (chỉ lần xuất hiện đầu tiên)
            pattern = r'(?<![\w\u00C0-\u024F])(' + re.escape(name) + r')(?![\w\u00C0-\u024F])'
            replacement = fr'\1 ({desc})'
            # Chỉ inject lần đầu tiên (để không lặp lại nhiều lần)
            result = re.sub(pattern, replacement, result, count=1, flags=re.IGNORECASE)
        # Xóa tag [Ten] khỏi prompt gửi đi
        result = re.sub(r'\[[^\]]+\]\s*', '', result).strip()
        return result

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
            char_info = self.characters[name]
            # Hỗ trợ cả 2 dạng: dict mới và str cũ
            path = char_info["path"] if isinstance(char_info, dict) else char_info
            desc = char_info.get("desc", "") if isinstance(char_info, dict) else ""
            self.log(f"📤 Upload [{i}/{total}]: {name}{' (' + desc[:30] + ')' if desc else ''} — ({Path(path).name})")
            self.root.after(0, lambda l=f"Uploading {name}... ({i}/{total})": self.char_status_lbl.config(text=l))
            ok = self.bc.upload_image(path)
            if ok:
                ok_count += 1
            self.root.after(0, lambda v=i: self.char_progress.config(value=v))
            time.sleep(1.5)
        msg = f"✅ Upload xong {ok_count}/{total} nhân vật!"
        self.root.after(0, lambda: self.char_status_lbl.config(text=msg))
        self.log(msg)

    # ── TAB 5: Tạo Video Nhân Vật ───────────────────────
    def _tab_create_video(self):
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="🎞️  Tạo Video")

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
        if idx == 4:  # Create Video tab
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
        self.nb.select(5)
        self._run_bg(lambda: self._create_video_worker(prompts, out_dir))

    def _create_video_worker(self, prompts, out_dir):
        self.running = True
        self.root.after(0, self.cv_progress.start)
        import random
        delay_map = {"normal": 5, "double": 10, "random": None}
        try:
            for i, prompt in enumerate(prompts, 1):
                if not self.running: break

                # ── Detect nhân vật thông minh (tag, tên, alias) ──
                detected = self._detect_characters(prompt, self.characters)
                to_upload = detected if detected else list(self.characters.items())

                # ── Build prompt có inject mô tả nhân vật ──
                final_prompt = self._build_prompt_with_chars(prompt, detected)

                if to_upload:
                    self.log(f"\n── [{i}/{len(prompts)}] {final_prompt[:70]}...")
                    char_names = [n for n, _ in to_upload]
                    mode = 'tag/detect' if detected else 'tất cả'
                    self.log(f"   👤 Nhân vật [{mode}]: {', '.join(char_names)}")
                    if final_prompt != prompt:
                        self.log(f"   ✨ Prompt với mô tả: {final_prompt[:80]}...")
                else:
                    self.log(f"\n── [{i}/{len(prompts)}] {final_prompt[:70]}...")
                    self.log(f"   ⚠ Không có nhân vật nào được thiết lập")

                ok = self.bc.new_project()
                if not ok: continue
                time.sleep(2)

                # Upload ảnh nhân vật (theo thứ tự order nếu có)
                sorted_upload = sorted(
                    to_upload,
                    key=lambda x: x[1].get("order", 0) if isinstance(x[1], dict) else 0
                )
                for name, char_info in sorted_upload:
                    path = char_info["path"] if isinstance(char_info, dict) else char_info
                    self.log(f"   📤 Upload ảnh {name}...")
                    self.bc.upload_image(path)
                    time.sleep(0.5)

                # Đóng panel media nếu đang mở
                try:
                    from selenium.webdriver.common.keys import Keys
                    self.bc.driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                    time.sleep(0.5)
                except: pass

                ok = self.bc.set_prompt(final_prompt)
                if not ok: continue
                time.sleep(1)

                ok = self.bc.click_generate()
                if not ok: continue

                ok = self.bc.wait_for_video(timeout=int(self.cv_timeout.get()))
                fname = f"{self.cv_base.get()}_{i:02d}.mp4"
                if ok:
                    self.log(f"   ⏬️ Tải về: {fname}")
                    self.root.after(0, lambda fi=fname: self.cv_status_lbl.config(
                        text=f"⏬️ Đang tải {fi}..."))
                    self.bc.click_download(out_dir, fname)
                    self.root.after(0, lambda fi=fname: self.cv_status_lbl.config(
                        text=f"✅ Tải xong: {fi}"))
                else:
                    self.log(f"   ⏭ Bỏ qua tải — hết timeout ({self.cv_timeout.get()}s)")

                if i < len(prompts):  # Không chờ sau prompt cuối
                    d = delay_map.get(self.cv_delay.get(), 5)
                    d = d if d else random.randint(6, 15)
                    self.log(f"⏳ Chờ {d}s rồi sang prompt tiếp...")
                    time.sleep(d)
        finally:
            self.running = False
            self.root.after(0, self.cv_progress.stop)
            self.root.after(0, lambda: self.cv_status_lbl.config(text=""))
            self.log(f"\n✅ Hoàn tất Create Video [{len(prompts)} canh]! Video đã lưu tại:\n   {out_dir}")

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
