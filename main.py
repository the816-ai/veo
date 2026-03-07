"""
Veo 3 Flow Automation Tool
Tß╗▒ ─æß╗Öng h├│a Google Flow ─æß╗â tß║ío video Veo 3
"""
import os, sys, time, json, threading, subprocess, shutil, re
from pathlib import Path
from tkinter import *
from tkinter import ttk, filedialog, messagebox, scrolledtext

FLOW_URL = "https://labs.google/fx/vi/tools/flow"
CHROME_PROFILE = os.path.join(os.path.expanduser("~"), "AppData", "Local", "Google", "Chrome", "User Data")
OUTPUT_DIR_TEXT = str(Path.home() / "Downloads" / "VEO3_OUTPUT" / "text_to_video")
OUTPUT_DIR_CHAR = str(Path.home() / "Downloads" / "VEO3_OUTPUT" / "character_video")
CHROMEDRIVER_PATH = None  # auto-detect via webdriver_manager

# ΓöÇΓöÇΓöÇ Selenium imports (graceful) ΓöÇΓöÇΓöÇ
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

# ΓöÇΓöÇΓöÇ Gemini API (graceful) ΓöÇΓöÇΓöÇ
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# BROWSER CONTROLLER
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
class BrowserController:
    def __init__(self, log_fn=None):
        self.driver = None
        self.log = log_fn or print
        self.wait = None
        self._download_dir = OUTPUT_DIR_TEXT

    # ΓöÇΓöÇ T├¼m Chrome executable tr├¬n Windows ΓöÇΓöÇ
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
        # Thß╗¡ lß║Ñy tß╗½ registry
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe")
            path, _ = winreg.QueryValueEx(key, "")
            if os.path.exists(path):
                return path
        except: pass
        return None

    # ΓöÇΓöÇ Kiß╗âm tra port 9222 ─æ├ú mß╗ƒ ch╞░a ΓöÇΓöÇ
    @staticmethod
    def _is_port_open(port=9222, timeout=1.0):
        import socket
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=timeout):
                return True
        except:
            return False

    def connect_existing(self):
        """Kß║┐t nß╗æi tß╗¢i Chrome ─æang chß║íy vß╗¢i --remote-debugging-port=9222"""
        if not HAS_SELENIUM:
            return False

        # Kiß╗âm tra port tr╞░ß╗¢c khi cß╗æ kß║┐t nß╗æi
        if not self._is_port_open(9222):
            self.log("Γ¥î Port 9222 ch╞░a mß╗ƒ ΓÇö Chrome ch╞░a ─æ╞░ß╗úc khß╗ƒi ─æß╗Öng vß╗¢i debug port!")
            self.log("≡ƒÆí D├╣ng n├║t 'Mß╗₧ CHROME' trong tool ─æß╗â mß╗ƒ Chrome ─æ├║ng c├ích.")
            return False

        for attempt in range(1, 4):
            try:
                self.log(f"≡ƒöù Kß║┐t nß╗æi Chrome (lß║ºn {attempt}/3)...")
                opts = Options()
                opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
                # Kh├┤ng cß║ºn profile hay options kh├íc khi attach v├áo Chrome c├│ sß║╡n
                svc = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=svc, options=opts)
                self.wait = WebDriverWait(self.driver, 30)
                url = self.driver.current_url
                self.log(f"Γ£à Kß║┐t nß╗æi th├ánh c├┤ng! URL: {url[:60]}")
                return True
            except Exception as e:
                self.log(f"ΓÜá Lß║ºn {attempt} thß║Ñt bß║íi: {str(e)[:80]}")
                if attempt < 3:
                    time.sleep(2)

        self.log("Γ¥î Kh├┤ng thß╗â kß║┐t nß╗æi sau 3 lß║ºn thß╗¡.")
        self.log("≡ƒÆí Giß║úi ph├íp: Tß║»t Chrome ΓåÆ Bß║Ñm n├║t 'Mß╗₧ CHROME' ΓåÆ ─É─âng nhß║¡p lß║íi.")
        return False

    def open(self, mode="normal", download_dir=None):
        """
        Ph╞░╞íng ph├íp ─É├ÜNG: Launch Chrome bß║▒ng subprocess vß╗¢i debug port.
        Chrome chß║íy ─Éß╗ÿC Lß║¼P ΓÇö kh├┤ng bß╗ï ─æ├│ng khi WebDriver ngß║»t kß║┐t nß╗æi.
        mode: normal | incognito | fresh
        """
        if not HAS_SELENIUM:
            import tkinter.messagebox as _mb
            try: _mb.showerror("Lß╗ùi", "Ch╞░a c├ái selenium!\nChß║íy: pip install selenium webdriver-manager")
            except: pass
            return False

        chrome_exe = self._find_chrome()
        if not chrome_exe:
            self.log("Γ¥î Kh├┤ng t├¼m thß║Ñy Chrome! H├úy c├ái Google Chrome.")
            return False

        dl_dir = download_dir or OUTPUT_DIR_TEXT
        os.makedirs(dl_dir, exist_ok=True)
        self._download_dir = dl_dir

        # Profile ri├¬ng cho tool ΓÇö tr├ính conflict vß╗¢i Chrome ─æang mß╗ƒ
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

        cmd.append(FLOW_URL)  # mß╗ƒ ngay Flow URL

        # Kiß╗âm tra nß║┐u port ─æ├ú d├╣ng (Chrome debug ─æang chß║íy) ΓåÆ ─æ├│ng tr╞░ß╗¢c
        if self._is_port_open(9222):
            self.log("ΓÜá Port 9222 ─æ├ú ─æ╞░ß╗úc d├╣ng ΓÇö thß╗¡ kß║┐t nß╗æi v├áo Chrome ─æ├│...")
            return self.connect_existing()

        self.log(f"≡ƒÜÇ Launch Chrome: {os.path.basename(chrome_exe)}")
        self.log(f"   Profile: VEO3_Profile | Tß║úi vß╗ü: {dl_dir}")
        try:
            # Windows kh├┤ng hß╗ù trß╗ú close_fds=True khi c├│ stdin/stdout
            subprocess.Popen(cmd, creationflags=0x00000008)  # DETACHED_PROCESS
        except Exception as e:
            self.log(f"Γ¥î Kh├┤ng chß║íy ─æ╞░ß╗úc Chrome: {e}")
            return False

        # Chß╗¥ Chrome khß╗ƒi ─æß╗Öng v├á port mß╗ƒ (tß╗æi ─æa 15s)
        self.log("ΓÅ│ Chß╗¥ Chrome khß╗ƒi ─æß╗Öng...")
        for i in range(15):
            time.sleep(1)
            if self._is_port_open(9222):
                self.log(f"Γ£à Chrome ─æ├ú sß║╡n s├áng sau {i+1}s")
                break
        else:
            self.log("ΓÜá Chrome ch╞░a mß╗ƒ port sau 15s ΓÇö thß╗¡ kß║┐t nß╗æi bß║Ñt chß║Ñp...")

        # Kß║┐t nß╗æi WebDriver v├áo Chrome ─æang chß║íy
        return self.connect_existing()


    def is_alive(self):
        try:
            _ = self.driver.title
            return True
        except:
            return False

    def get_status(self):
        if not self.driver:
            return "Ch╞░a mß╗ƒ"
        try:
            url = self.driver.current_url
            if "flow" in url:
                return f"Γ£à ─É├ú mß╗ƒ Flow"
            return f"─Éang ß╗ƒ: {url[:50]}"
        except:
            return "Γ¥î Mß║Ñt kß║┐t nß╗æi"

    def new_project(self):
        """Tß║ío dß╗▒ ├ín mß╗¢i tr├¬n Flow"""
        try:
            self.driver.get(FLOW_URL)
            time.sleep(3)
            # Selector ─æ├ú x├íc nhß║¡n: button.jsIRVP hoß║╖c text 'Dß╗▒ ├ín mß╗¢i'
            try:
                btn = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button.jsIRVP"))
                )
                btn.click()
                time.sleep(2.5)
                self.log("Γ£à ─É├ú tß║ío dß╗▒ ├ín mß╗¢i")
            except TimeoutException:
                # Fallback: t├¼m theo text
                try:
                    btn = self.driver.find_element(
                        By.XPATH, "//button[contains(.,'Dß╗▒ ├ín mß╗¢i') or contains(.,'New project')]"
                    )
                    btn.click()
                    time.sleep(2.5)
                    self.log("Γ£à ─É├ú tß║ío dß╗▒ ├ín mß╗¢i (fallback)")
                except:
                    self.log("Γä╣∩╕Å Kh├┤ng thß║Ñy n├║t Dß╗▒ ├ín mß╗¢i ΓÇö tiß║┐p tß╗Ñc")
            return True
        except Exception as e:
            self.log(f"Γ¥î Lß╗ùi tß║ío dß╗▒ ├ín: {e}")
            return False

    def generate_image_flow(self, prompt, count=1, orientation="ngang", out_dir=None, log_fn=None):
        """
        Tß║ío ß║únh bß║▒ng Nano Banana 2 tr├¬n Google Flow.
        - prompt: nß╗Öi dung ß║únh (tiß║┐ng Anh)
        - count: sß╗æ ß║únh (1/2/3/4)
        - orientation: 'ngang' | 'doc'
        - out_dir: th╞░ mß╗Ñc l╞░u ß║únh tß║úi vß╗ü
        """
        log = log_fn or self.log
        if not self.driver:
            log("Γ¥î Ch╞░a kß║┐t nß╗æi tr├¼nh duyß╗çt!")
            return False
        try:
            # 1. Mß╗ƒ Flow v├á chß╗¥ tß║úi
            log("≡ƒî┐ ─Éang mß╗ƒ trang Flow tß║ío ß║únh...")
            self.driver.get(FLOW_URL)
            time.sleep(3)

            # 2. Click tab 'Image' (h├¼nh ß║únh) ΓÇö t├¼m bß║▒ng text
            try:
                img_tab = WebDriverWait(self.driver, 12).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(.,'Image') or contains(.,'H\u00ecnh ß║únh')]"
                    ))
                )
                self.driver.execute_script("arguments[0].click();", img_tab)
                time.sleep(1)
                log("Γ£à ─É├ú chuyß╗ân sang tab Image")
            except TimeoutException:
                log("ΓÜá Kh├┤ng thß║Ñy tab Image ΓÇö c├│ thß╗â ─æang ß╗ƒ ─æ├║ng tab rß╗ôi")

            # 3. Chß╗ìn h╞░ß╗¢ng: Ngang / Dß╗ìc
            orient_text = "Ngang" if orientation == "ngang" else "Dß╗ìc"
            try:
                orient_btn = self.driver.find_element(
                    By.XPATH,
                    f"//button[contains(.,'{orient_text}') or contains(.,'Landscape') or contains(.,'Portrait')]"
                )
                self.driver.execute_script("arguments[0].click();", orient_btn)
                time.sleep(0.5)
                log(f"Γ£à H╞░ß╗¢ng: {orient_text}")
            except:
                log(f"ΓÜá Kh├┤ng t├¼m ─æ╞░ß╗úc n├║t h╞░ß╗¢ng {orient_text} ΓÇö d├╣ng mß║╖c ─æß╗ïnh")

            # 4. Chß╗ìn sß╗æ l╞░ß╗úng ß║únh (x1, x2, x3, x4)
            try:
                count_btn = self.driver.find_element(
                    By.XPATH, f"//button[normalize-space(.)='x{count}']"
                )
                self.driver.execute_script("arguments[0].click();", count_btn)
                time.sleep(0.5)
                log(f"Γ£à Sß╗æ ß║únh: x{count}")
            except:
                log(f"ΓÜá Kh├┤ng t├¼m ─æ╞░ß╗úc n├║t x{count}")

            # 5. Nhß║¡p prompt v├áo ├┤ text
            log("≡ƒô¥ Nhß║¡p prompt...")
            try:
                # T├¼m textarea placeholder 'Bß║ín muß╗æn tß║ío g├¼?'
                ta = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((
                        By.XPATH,
                        "//textarea | //div[@contenteditable='true'] | //div[@aria-label]"
                    ))
                )
                ta.click()
                time.sleep(0.3)
                ta.clear()
                ta.send_keys(prompt)
                time.sleep(0.5)
                log("Γ£à ─É├ú nhß║¡p prompt")
            except Exception as e:
                log(f"Γ¥î Kh├┤ng nhß║¡p ─æ╞░ß╗úc prompt: {e}")
                return False

            # 6. Click n├║t generate (ΓåÆ)
            log("ΓÅ│ ─Éang gß╗¡i tß║ío ß║únh...")
            try:
                gen_btn = WebDriverWait(self.driver, 8).until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[@aria-label='Generate' or @aria-label='Tß║ío' or "
                        "contains(@class,'generate') or "
                        "(self::button and ./*[name()='svg'])]" # icon arrow button
                    ))
                )
                self.driver.execute_script("arguments[0].click();", gen_btn)
                log("≡ƒÄ¿ Nano Banana 2 ─æang vß║╜ ß║únh...")
            except:
                # Fallback: Enter tr├¬n textarea
                try:
                    ta.send_keys("\n")
                    log("≡ƒÄ¿ Gß╗¡i bß║▒ng Enter...")
                except:
                    log("Γ¥î Kh├┤ng thß╗â bß║Ñm generate!")
                    return False

            # 7. Chß╗¥ ß║únh hiß╗ân ra (tß╗æi ─æa 60s)
            log("ΓÅ│ Chß╗¥ ß║únh render (tß╗æi ─æa 60s)...")
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
                        log(f"Γ£à ─É├ú tß║ío ─æ╞░ß╗úc {len(img_srcs)} ß║únh!")
                        break
                except: pass

            if not img_srcs:
                log("ΓÜá Kh├┤ng t├¼m thß║Ñy ß║únh ΓÇö h├úy kiß╗âm tra tay tr├¬n tr├¼nh duyß╗çt.")
                return True  # Vß║½n c├│ thß╗â user thß║Ñy ß║únh trong browser

            # 8. Tß║úi ß║únh vß╗ü (nß║┐u out_dir c├│ v├á URL kh├┤ng phß║úi blob:)
            if out_dir:
                os.makedirs(out_dir, exist_ok=True)
                saved = 0
                for idx, src in enumerate(img_srcs):
                    if src.startswith("blob:"):
                        log(f"ΓÜá ß║ónh {idx+1}: blob URL ΓÇö cß║ºn tß║úi tay tß╗½ tr├¼nh duyß╗çt")
                        continue
                    try:
                        import urllib.request
                        fname = os.path.join(out_dir, f"nano_banana_{int(time.time())}_{idx+1}.jpg")
                        urllib.request.urlretrieve(src, fname)
                        log(f"≡ƒÆ╛ ─É├ú l╞░u: {fname}")
                        saved += 1
                    except Exception as e:
                        log(f"ΓÜá Kh├┤ng l╞░u ─æ╞░ß╗úc ß║únh {idx+1}: {e}")
                if saved == 0:
                    log("ΓÜá ß║ónh ─æ╞░ß╗úc render trong browser d╞░ß╗¢i dß║íng blob, c├│ thß╗â download thß╗º c├┤ng.")
            return True
        except Exception as e:
            log(f"Γ¥î Lß╗ùi tß║ío ß║únh: {e}")
            return False

    def set_prompt(self, text):
        """Nhß║¡p prompt v├áo Flow ΓÇö clipboard paste (trigger real React paste event)"""
        import subprocess, tempfile

        def _copy_to_clipboard(t):
            """Copy text v├áo Windows clipboard qua PowerShell ΓÇö safe vß╗¢i path bß║Ñt kß╗│"""
            try:
                # Ghi ra file tß║ím vß╗¢i encoding UTF-8
                tmp = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.txt', delete=False, encoding='utf-8'
                )
                tmp.write(t); tmp.close()
                # D├╣ng ─æ╞░ß╗¥ng dß║½n an to├án qua biß║┐n PS (tr├ính lß╗ùi k├╜ tß╗▒ ─æß║╖c biß╗çt)
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
                self.log(f"ΓÜá Clipboard error: {ce}")

        try:
            # Chß╗¥ ├┤ prompt thß╗▒c sß╗▒ clickable
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
                self.log("Γ¥î Kh├┤ng t├¼m thß║Ñy ├┤ prompt (15s timeout)")
                return False

            # Scroll v├áo giß╗»a m├án h├¼nh + JS focus (tr├ính overlay chß║╖n click)
            self.driver.execute_script(
                "arguments[0].scrollIntoView({block:'center', inline:'center'});", box
            )
            time.sleep(0.5)
            self.driver.execute_script("arguments[0].click();", box)
            time.sleep(0.3)

            # ΓöÇΓöÇ Ph╞░╞íng ph├íp 1: send_keys tß╗½ng chunk ΓÇö ─æ├íng tin nhß║Ñt vß╗¢i React ΓöÇΓöÇ
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
                    self.log(f"Γ£à ─É├ú nhß║¡p prompt (send_keys): {text[:60]}...")
                    return True
                self.log("ΓÜá send_keys: text kh├┤ng khß╗¢p, thß╗¡ clipboard...")
            except Exception as e1:
                self.log(f"ΓÜá send_keys: {e1}")

            # ΓöÇΓöÇ Ph╞░╞íng ph├íp 2: Clipboard Ctrl+V ΓöÇΓöÇ
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
                    self.log(f"Γ£à ─É├ú d├ín prompt (Ctrl+V): {text[:60]}...")
                    return True
                self.log("ΓÜá Clipboard: text kh├┤ng xuß║Ñt hiß╗çn, thß╗¡ execCommand...")
            except Exception as e2:
                self.log(f"ΓÜá Clipboard: {e2}")

            # ΓöÇΓöÇ Ph╞░╞íng ph├íp 3: execCommand insertText (deprecated fallback) ΓöÇΓöÇ
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
                    self.log(f"Γ£à ─É├ú d├ín prompt (execCommand): {text[:60]}...")
                    return True
            except Exception as e3:
                self.log(f"ΓÜá execCommand: {e3}")

            self.log("Γ¥î Tß║Ñt cß║ú ph╞░╞íng ph├íp ─æß╗üu thß║Ñt bß║íi")
            return False
        except Exception as e:
            self.log(f"Γ¥î set_prompt: {e}")
            return False

    def click_generate(self):
        """Click n├║t Tß║ío ΓÇö chß╗¥ enabled + ActionChains + Enter fallback"""
        try:
            # Chß╗¥ 1.5s sau khi paste ─æß╗â React cß║¡p nhß║¡t state
            time.sleep(1.5)

            # T├¼m n├║t Tß║ío (button.bMhrec = arrow_forward button)
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
                # Kiß╗âm tra button c├│ bß╗ï disabled kh├┤ng
                disabled = btn.get_attribute("disabled") or btn.get_attribute("aria-disabled")
                if disabled and str(disabled).lower() in ("true", "disabled"):
                    self.log("ΓÜá N├║t Tß║ío ─æang disabled ΓÇö thß╗¡ Enter key...")
                else:
                    # Scroll v├áo view + JS click ─æß╗â bypass overlay
                    self.driver.execute_script(
                        "arguments[0].scrollIntoView({block:'center'});", btn
                    )
                    time.sleep(0.3)
                    try:
                        # Thß╗¡ ActionChains tr╞░ß╗¢c
                        ActionChains(self.driver).move_to_element(btn).click().perform()
                        self.log("Γ£à ─É├ú click n├║t Tß║ío (ActionChains)")
                    except Exception:
                        # Fallback JS click nß║┐u bß╗ï intercept
                        self.driver.execute_script("arguments[0].click();", btn)
                        self.log("Γ£à ─É├ú click n├║t Tß║ío (JS click)")
                    time.sleep(0.5)

                    # X├íc nhß║¡n click c├│ hiß╗çu lß╗▒c bß║▒ng c├ích kiß╗âm tra URL thay ─æß╗òi
                    url_before = self.driver.current_url
                    time.sleep(2)
                    url_after = self.driver.current_url
                    if url_after != url_before or "/edit/" in url_after:
                        self.log("Γ£à X├íc nhß║¡n: trang ─æß╗òi URL ΓÇö generate ─æang chß║íy!")
                        return True
                    self.log("ΓÜá URL kh├┤ng ─æß╗òi ΓÇö thß╗¡ Enter fallback...")

            # Fallback: Enter trong ├┤ prompt (c├ích ─æ├íng tin nhß║Ñt vß╗¢i React)
            try:
                box = self.driver.find_element(By.CSS_SELECTOR, "div[role='textbox']")
                # JS focus + Enter ─æß╗â tr├ính ElementClickInterceptedException
                self.driver.execute_script("arguments[0].focus();", box)
                time.sleep(0.3)
                box.send_keys(Keys.RETURN)
                self.log("Γî¿∩╕Å Sent Enter key ΓåÆ generate")
                return True
            except Exception as ef:
                self.log(f"ΓÜá Enter fallback: {ef}")

            # Fallback 2: JS t├¼m button ph├¡a phß║úi ├┤ prompt (tr├ính lß╗ùi tß╗ìa ─æß╗Ö)
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
                    self.log(f"≡ƒû▒ JS click button phß║úi input: {clicked[:30]}")
                    return True
            except Exception as e2:
                self.log(f"ΓÜá JS coordinate click: {e2}")

            return True  # Tiß║┐p tß╗Ñc d├╣ click c├│ thß╗â kh├┤ng th├ánh c├┤ng
        except Exception as e:
            self.log(f"Γ¥î click_generate: {e}")
            return False


    def wait_for_video(self, timeout=300):
        """Chß╗¥ video tß║ío xong ΓÇö chß╗ë check SUCCESS, kh├┤ng check error giß║ú"""
        self.log(f"ΓÅ│ Chß╗¥ video ho├án th├ánh (tß╗æi ─æa {timeout}s)...")
        start = time.time()
        check_interval = 10  # kiß╗âm tra mß╗ùi 10s
        last_log = 0

        while time.time() - start < timeout:
            time.sleep(check_interval)
            elapsed = int(time.time() - start)

            try:
                # 1. T├¼m n├║t "Tß║úi xuß╗æng" ΓÇö chß╗ë xuß║Ñt hiß╗çn khi video xong
                dl_btns = self.driver.find_elements(
                    By.XPATH,
                    "//button[normalize-space(.)='Tß║úi xuß╗æng' or @aria-label='Tß║úi xuß╗æng' or @aria-label='Download']"
                )
                if dl_btns:
                    self.log(f"Γ£à Video ho├án th├ánh sau {elapsed}s! T├¼m thß║Ñy n├║t Tß║úi xuß╗æng.")
                    return True

                # 2. URL ─æß╗òi sang /edit/ ΓÇö project ─æ├ú tß║ío xong 1 clip
                url = self.driver.current_url
                if "/edit/" in url:
                    # T├¼m video element c├│ src
                    vids = self.driver.find_elements(By.TAG_NAME, "video")
                    for v in vids:
                        src = v.get_attribute("src") or ""
                        if src and ("blob:" in src or "storage.googleapis" in src):
                            self.log(f"Γ£à Video ready sau {elapsed}s!")
                            return True

                # Log tiß║┐n tr├¼nh mß╗ùi 30s
                if elapsed - last_log >= 30:
                    self.log(f"   ΓÅ│ {elapsed}s ΓÇö ─æang render...")
                    last_log = elapsed

            except Exception as e:
                pass  # Chrome bß║¡n, thß╗¡ lß║íi sau

        self.log(f"ΓÅ▒ Timeout sau {timeout}s ΓÇö tiß║┐p prompt tiß║┐p")
        return False

    def wait_for_prompt_ready(self, timeout=30):
        """─Éß╗úi ├┤ prompt xuß║Ñt hiß╗çn trß╗ƒ lß║íi sau khi video render xong.
        D├╣ng ─æß╗â tiß║┐p tß╗Ñc d├ín prompt mß╗¢i m├á kh├┤ng cß║ºn tß║ío project mß╗¢i.
        Trß║ú vß╗ü True nß║┐u ├┤ prompt sß║╡n s├áng.
        """
        self.log("ΓÅ│ Chß╗¥ ├┤ nhß║¡p prompt sß║╡n s├áng...")
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                for sel in ["div[role='textbox']", "div[contenteditable='true']"]:
                    els = self.driver.find_elements(By.CSS_SELECTOR, sel)
                    for el in els:
                        if el.is_displayed():
                            self.log("Γ£à ├ö prompt sß║╡n s├áng!")
                            return True
            except Exception:
                pass
            time.sleep(2)
        self.log("ΓÜá Kh├┤ng thß║Ñy ├┤ prompt sau 30s ΓÇö c├│ thß╗â cß║ºn tß║ío project mß╗¢i")
        return False


    def set_aspect_ratio(self, ratio):
        """Chß╗ìn tß╗╖ lß╗ç khung h├¼nh tr├¬n Flow: 16:9 | 9:16 | 1:1"""
        try:
            # Map ratio ΓåÆ tab text
            ratio_map = {
                "16:9": ["Ngang", "16:9", "Landscape"],
                "9:16": ["Dß╗ìc", "9:16", "Portrait"],
                "1:1": ["Vu├┤ng", "1:1", "Square"],
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
                        self.log(f"Γ£à Tß╗╖ lß╗ç: {ratio}")
                        return True
                except:
                    continue
            return False
        except Exception as e:
            self.log(f"ΓÜá Set aspect ratio: {e}")
            return False

    def click_download(self, save_dir, filename):
        """Click Tß║úi xuß╗æng ΓåÆ chß╗¥ file tß║úi XONG ho├án to├án ΓåÆ ─æß╗òi t├¬n theo thß╗⌐ tß╗▒"""
        try:
            os.makedirs(save_dir, exist_ok=True)

            # ΓöÇΓöÇ B╞░ß╗¢c 1: Set CDP download dir ΓöÇΓöÇ
            try:
                self.driver.execute_cdp_cmd(
                    "Browser.setDownloadBehavior",
                    {"behavior": "allow", "downloadPath": save_dir}
                )
            except: pass

            # Monitor cß║ú save_dir v├á ~/Downloads
            chrome_dl = str(Path.home() / "Downloads")
            watch_dirs = list({save_dir, chrome_dl})

            # Snapshot SAU khi set CDP, TR╞»ß╗ÜC khi click
            snap = {d: set(os.listdir(d)) if os.path.exists(d) else set()
                    for d in watch_dirs}

            # ΓöÇΓöÇ B╞░ß╗¢c 2: T├¼m v├á click n├║t Tß║úi xuß╗æng ΓöÇΓöÇ
            dl_btn = None
            for sel in [
                "//button[normalize-space(.)='Tß║úi xuß╗æng']",
                "//button[@aria-label='Tß║úi xuß╗æng' or @aria-label='Download']",
                "//button[contains(.,'Tß║úi xuß╗æng')]",
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
                self.log("ΓÜá∩╕Å Kh├┤ng t├¼m thß║Ñy n├║t Tß║úi xuß╗æng")
                return False

            ActionChains(self.driver).move_to_element(dl_btn).click().perform()
            self.log("Γ¼ç∩╕Å ─É├ú click Tß║úi xuß╗æng ΓÇö chß╗¥ file...")

            # ΓöÇΓöÇ B╞░ß╗¢c 3: Chß╗¥ file .mp4 xuß║Ñt hiß╗çn (tß╗æi ─æa 90s) ΓöÇΓöÇ
            deadline = time.time() + 90
            new_file = None
            new_dir = save_dir
            while time.time() < deadline:
                time.sleep(1.5)
                for d in watch_dirs:
                    if not os.path.exists(d): continue
                    current = set(os.listdir(d))
                    added = current - snap[d]
                    # File tß║úi xong = .mp4, kh├┤ng phß║úi .crdownload
                    done = [f for f in added
                            if f.endswith(".mp4") and not f.endswith(".crdownload")]
                    if done:
                        new_file = done[0]
                        new_dir = d
                        break
                    # C├▓n ─æang tß║úi ΓåÆ log progress
                    partial = [f for f in added if f.endswith(".crdownload")]
                    if partial:
                        elapsed = int(time.time() - (deadline - 90))
                        self.log(f"   Γ¼ç∩╕Å ─Éang tß║úi... {partial[0]} ({elapsed}s)")
                if new_file:
                    break

            if not new_file:
                self.log("ΓÜá∩╕Å Hß║┐t giß╗¥ 90s ΓÇö file kh├┤ng xuß║Ñt hiß╗çn")
                return False

            # ΓöÇΓöÇ B╞░ß╗¢c 4: Chß╗¥ file ß╗òn ─æß╗ïnh (kh├┤ng c├▓n ghi) ΓöÇΓöÇ
            src = os.path.join(new_dir, new_file)
            self.log(f"ΓÅ│ Chß╗¥ file ß╗òn ─æß╗ïnh: {new_file}")
            prev_size = -1
            stable_count = 0
            for _ in range(15):  # tß╗æi ─æa 15 lß║ºn ├ù 1s = 15s
                time.sleep(1)
                try:
                    cur_size = os.path.getsize(src)
                    if cur_size == prev_size and cur_size > 0:
                        stable_count += 1
                        if stable_count >= 2:  # ß╗òn ─æß╗ïnh 2 lß║ºn li├¬n tiß║┐p
                            break
                    else:
                        stable_count = 0
                    prev_size = cur_size
                except: break

            # ΓöÇΓöÇ B╞░ß╗¢c 5: ─Éß╗òi t├¬n theo thß╗⌐ tß╗▒, ─æß║úm bß║úo kh├┤ng tr├╣ng ΓöÇΓöÇ
            dst = os.path.join(save_dir, filename)
            if os.path.exists(dst):
                ts = time.strftime("%H%M%S")
                dst = os.path.join(save_dir, filename.replace(".mp4", f"_{ts}.mp4"))

            shutil.move(src, dst)
            size_mb = os.path.getsize(dst) / 1024 / 1024
            self.log(f"Γ£à ─É├ú l╞░u: {os.path.basename(dst)} ({size_mb:.1f} MB)")
            return True

        except Exception as e:
            self.log(f"Γ¥î click_download: {e}")
            return False

    def upload_image(self, image_path):
        """Upload ß║únh l├¬n Flow UI mß╗¢i:
        N├║t + (bottom) ΓåÆ Modal media panel ΓåÆ Icon Γåæ upload ΓåÆ file input ΓåÆ x├íc nhß║¡n
        """
        try:
            image_path = str(Path(image_path).resolve())
            if not os.path.exists(image_path):
                self.log(f"Γ¥î File kh├┤ng tß╗ôn tß║íi: {image_path}")
                return False

            # ΓöÇΓöÇ B╞░ß╗¢c 1: Click n├║t "+" ß╗ƒ g├│c d╞░ß╗¢i tr├íi ΓöÇΓöÇ
            # N├║t + trong prompt bar (chß╗⌐a span c├│ text 'add_2' hoß║╖c aria-label add)
            plus_btn = None
            plus_xpaths = [
                "//button[.//span[normalize-space()='add_2']]",
                "//button[@aria-label='Add' or @aria-label='Th├¬m']",
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
                self.log("ΓÜá Kh├┤ng thß║Ñy n├║t + ΓÇö thß╗¡ t├¼m file input trß╗▒c tiß║┐p")
            else:
                ActionChains(self.driver).move_to_element(plus_btn).click().perform()
                self.log("Γ£à ─É├ú click n├║t +")
                time.sleep(1.5)  # chß╗¥ modal/panel mß╗ƒ

            # ΓöÇΓöÇ B╞░ß╗¢c 2: T├¼m n├║t Γåæ (upload) trong panel media ΓöÇΓöÇ
            # Panel c├│ search bar "T├¼m kiß║┐m c├íc th├ánh phß║ºn" + icon upload b├¬n phß║úi
            upload_icon = None
            upload_xpaths = [
                "//input[@placeholder[contains(.,'T├¼m kiß║┐m')]]/following-sibling::button",
                "//input[@placeholder[contains(.,'Search')]]/following-sibling::button",
                "//button[.//span[normalize-space()='file_upload' or normalize-space()='upload']]",
                "//button[@aria-label[contains(.,'upload') or contains(.,'Upload') or contains(.,'Tß║úi')]]",
                # Icon Γåæ th╞░ß╗¥ng l├á button trong search container
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
                self.log("Γ£à ─É├ú click icon upload Γåæ")
                time.sleep(1.0)
            else:
                self.log("ΓÜá Kh├┤ng thß║Ñy icon upload ΓÇö thß╗¡ unhide file input")

            # ΓöÇΓöÇ B╞░ß╗¢c 3: Unhide tß║Ñt cß║ú input[type=file] v├á send_keys ΓöÇΓöÇ
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
                file_input = inputs[-1]  # lß║Ñy c├íi mß╗¢i nhß║Ñt

            if not file_input:
                self.log("Γ¥î Kh├┤ng t├¼m thß║Ñy input[type=file]")
                return False

            file_input.send_keys(image_path)
            self.log(f"≡ƒôñ ─Éang upload: {Path(image_path).name}")

            # ΓöÇΓöÇ B╞░ß╗¢c 4: Chß╗¥ thumbnail xuß║Ñt hiß╗çn trong panel (x├íc nhß║¡n upload OK) ΓöÇΓöÇ
            self.log("ΓÅ│ Chß╗¥ x├íc nhß║¡n upload...")
            deadline = time.time() + 25
            while time.time() < deadline:
                time.sleep(2)
                try:
                    # Thumbnail ß║únh vß╗½a upload sß║╜ c├│ src chß╗⌐a blob hoß║╖c googleusercontent
                    thumbs = self.driver.find_elements(
                        By.XPATH,
                        "//img[contains(@src,'blob:') or contains(@src,'googleusercontent') or contains(@src,'data:image')]"
                    )
                    if thumbs:
                        self.log(f"Γ£à Upload OK: {Path(image_path).name} ({len(thumbs)} ß║únh trong panel)")
                        return True
                except: pass

            self.log(f"ΓÜá Kh├┤ng x├íc nhß║¡n ─æ╞░ß╗úc upload (hß║┐t 25s) ΓÇö c├│ thß╗â vß║½n OK")
            return True

        except Exception as e:
            self.log(f"Γ¥î upload_image: {e}")
            return False



# ΓöÇΓöÇΓöÇ M├áu nß╗ün tß╗æi chuy├¬n nghiß╗çp ΓöÇΓöÇΓöÇ
BG      = "#0D1117"   # nß╗ün ch├¡nh
CARD    = "#161B22"   # card/frame
BORDER  = "#30363D"   # viß╗ün
TEXT    = "#E6EDF3"   # chß╗» s├íng
MUTED   = "#8B949E"   # chß╗» mß╗¥
ACCENT  = "#58A6FF"   # xanh d╞░╞íng
GREEN   = "#3FB950"   # xanh l├í
RED     = "#F85149"   # ─æß╗Å
ORANGE  = "#D29922"   # cam/v├áng
PURPLE  = "#BC8CFF"   # t├¡m

# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# MAIN APP
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
class VeoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("VEO 3 FLOW PRO  ΓÇö  by TechViet AI")
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
        """Thiß║┐t lß║¡p ttk.Style cho dark theme"""
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

    # ΓöÇΓöÇΓöÇ LOG ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
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

    # ΓöÇΓöÇΓöÇ UI BUILD ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    # ΓöÇΓöÇ TAB 8: Viß║┐t sub ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _tab_vietsub(self):
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="≡ƒô¥  Vietsub")

        # ΓöÇΓöÇ H╞░ß╗¢ng dß║½n ΓöÇΓöÇ
        guide = self._card(f, "≡ƒôï H╞░ß╗¢ng dß║½n ─æß╗æt phß╗Ñ ─æß╗ü Viß╗çt v├áo video")
        guide.pack(fill=X, padx=12, pady=(10,4))
        Label(guide, text=(
            "Γæá  Chß╗ìn file video .mp4 cß║ºn th├¬m phß╗Ñ ─æß╗ü\n"
            "Γæí  Nhß║¡p nß╗Öi dung phß╗Ñ ─æß╗ü (─æ╞░ß╗úc tß╗▒ ─æß╗Öng chia theo sß╗æ d├▓ng v├á thß╗¥i l╞░ß╗úng video)\n"
            "Γæó  Chß╗ënh style, nhß║Ñn [BURN VIETSUB] ΓåÆ xuß║Ñt file video_sub.mp4"
        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT
        ).pack(anchor=W, padx=10, pady=8)

        # ΓöÇΓöÇ Chß╗ìn video ΓöÇΓöÇ
        vf = self._card(f, "≡ƒÄ¼ Chß╗ìn video cß║ºn th├¬m phß╗Ñ ─æß╗ü")
        vf.pack(fill=X, padx=12, pady=4)
        vrow = Frame(vf, bg=CARD); vrow.pack(fill=X, padx=8, pady=6)
        Label(vrow, text="File video:", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_video = Entry(vrow, width=55, font=("Segoe UI", 9),
                              bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.vs_video.pack(side=LEFT, padx=6, ipady=3)

        def _browse_video():
            p = filedialog.askopenfilename(
                title="Chß╗ìn file video",
                filetypes=[("Video MP4", "*.mp4"), ("All", "*.*")]
            )
            if p:
                self.vs_video.delete(0, END)
                self.vs_video.insert(0, p)
                # Tß╗▒ ─æß╗Öng lß║Ñy thß╗¥i l╞░ß╗úng bß║▒ng ffprobe nß║┐u c├│
                self._vs_get_duration(p)

        self._btn(vrow, "≡ƒôé", _browse_video,
                  color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)
        self.vs_dur_lbl = Label(vf, text="ΓÅ▒ Thß╗¥i l╞░ß╗úng: ch╞░a x├íc ─æß╗ïnh",
                               font=("Segoe UI", 9), bg=CARD, fg=MUTED)
        self.vs_dur_lbl.pack(anchor=W, padx=10, pady=(0,4))

        # ΓöÇΓöÇ Nß╗Öi dung phß╗Ñ ─æß╗ü ΓöÇΓöÇ
        tf = self._card(f, "≡ƒÆ¼ Nß╗Öi dung phß╗Ñ ─æß╗ü  (mß╗ùi d├▓ng = 1 cß║únh, sß║╜ tß╗▒ chia ─æß╗üu)")
        tf.pack(fill=X, padx=12, pady=4)

        tip_row = Frame(tf, bg=CARD); tip_row.pack(fill=X, padx=8, pady=(4,2))
        Label(tip_row,
              text="≡ƒÆí Mß╗ùi d├▓ng 1 c├óu  ΓöÇ  Hoß║╖c d├╣ng thß╗º c├┤ng: [bß║»t ─æß║ºu-->kß║┐t th├║c]  V├¡ dß╗Ñ: 00:00:00-->00:00:03ΓöéNß╗Öi dung",
              bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(side=LEFT)

        self.vs_text = scrolledtext.ScrolledText(
            tf, height=8, font=("Consolas", 10),
            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.vs_text.pack(fill=X, padx=6, pady=(2,6))
        self.vs_text.insert(END,
            "Alice ─æang ─æi dß║ío trong c├┤ng vi├¬n nhß╗Å\n"
            "Nß║»ng chiß╗üu v├áng chiß║┐u qua h├áng c├óy xanh\n"
            "C├┤ ß║Ñy dß╗½ng lß║íi nh├¼n bß║ºu trß╗¥i\n"
            "Mß╗Öt ng├áy b├¼nh y├¬n tr├┤i qua"
        )

        # ΓöÇΓöÇ Style phß╗Ñ ─æß╗ü ΓöÇΓöÇ
        sf = self._card(f, "≡ƒÄ¿ Style phß╗Ñ ─æß╗ü")
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
        Label(r1, text="  Cß╗í chß╗»:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_size = StringVar(value="28")
        Spinbox(r1, from_=14, to=60, textvariable=self.vs_size,
                width=5, bg=CARD, fg=TEXT, relief="flat").pack(side=LEFT, padx=4)

        r2 = Frame(sf, bg=CARD); r2.pack(fill=X, padx=8, pady=3)
        # M├áu chß╗»
        Label(r2, text="M├áu chß╗»:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_color = StringVar(value="&H00FFFFFF")  # Trß║»ng
        colors = [
            ("Trß║»ng", "&H00FFFFFF"), ("V├áng", "&H0000FFFF"),
            ("Xanh da trß╗¥i", "&H00FFFF00"), ("─Éß╗Å", "&H000000FF"),
            ("─Éen", "&H00000000")
        ]
        for cname, cval in colors:
            Radiobutton(r2, text=cname, variable=self.vs_color, value=cval,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=6)

        r3 = Frame(sf, bg=CARD); r3.pack(fill=X, padx=8, pady=3)
        # Vß╗ï tr├¡
        Label(r3, text="Vß╗ï tr├¡:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_align = StringVar(value="2")  # 2=d╞░ß╗¢i giß╗»a
        positions = [
            ("Γ¼ç D╞░ß╗¢i giß╗»a", "2"),
            ("Γ¼å Tr├¬n giß╗»a", "8"),
            ("Γûª Giß╗»a m├án h├¼nh", "5"),
        ]
        for pname, pval in positions:
            Radiobutton(r3, text=pname, variable=self.vs_align, value=pval,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=8)

        r4 = Frame(sf, bg=CARD); r4.pack(fill=X, padx=8, pady=(3,6))
        # Viß╗ün chß╗» (outline)
        Label(r4, text="Viß╗ün:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_outline = StringVar(value="1")
        Spinbox(r4, from_=0, to=4, textvariable=self.vs_outline,
                width=4, bg=CARD, fg=TEXT, relief="flat").pack(side=LEFT, padx=4)
        Label(r4, text="  B├│ng (─æß╗Ö lß╗çch):", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_shadow = StringVar(value="1")
        Spinbox(r4, from_=0, to=4, textvariable=self.vs_shadow,
                width=4, bg=CARD, fg=TEXT, relief="flat").pack(side=LEFT, padx=4)

        # ΓöÇΓöÇ C├ái ─æß║╖t xuß║Ñt ΓöÇΓöÇ
        of = self._card(f, "≡ƒôé L╞░u vß╗ï tr├¡")
        of.pack(fill=X, padx=12, pady=4)
        orow = Frame(of, bg=CARD); orow.pack(fill=X, padx=8, pady=6)
        Label(orow, text="L╞░u tß║íi:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.vs_out = Entry(orow, width=50, font=("Segoe UI", 9),
                            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        vs_default_out = str(Path.home() / "Downloads" / "VEO3_OUTPUT" / "vietsub")
        self.vs_out.insert(0, vs_default_out)
        self.vs_out.pack(side=LEFT, padx=6, ipady=3)
        self._btn(orow, "≡ƒôé", lambda: self._browse(self.vs_out),
                  color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)

        # ΓöÇΓöÇ Preview SRT ΓöÇΓöÇ
        pf = self._card(f, "≡ƒöì Preview SRT  (tß╗▒ ─æß╗Öng cß║¡p nhß║¡t)")
        pf.pack(fill=X, padx=12, pady=4)
        self.vs_preview = scrolledtext.ScrolledText(
            pf, height=6, font=("Consolas", 8), state=DISABLED,
            bg="#0A0F1A", fg=MUTED, relief="flat")
        self.vs_preview.pack(fill=X, padx=6, pady=4)

        def _update_preview(*_):
            """Cß║¡p nhß║¡t preview SRT khi user ─æang g├╡ text."""
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
        self.root.after(500, _update_preview)  # chß║íy lß║ºn ─æß║ºu

        # ΓöÇΓöÇ Thanh tiß║┐n ─æß╗Ö + n├║t ΓöÇΓöÇ
        bf = Frame(f, bg=BG)
        bf.pack(fill=X, padx=12, pady=6)
        self.vs_prog = ttk.Progressbar(bf, mode="indeterminate", style="TProgressbar")
        self.vs_prog.pack(fill=X, pady=(0,4))
        self.vs_status_lbl = Label(bf, text="Sß║╡n s├áng",
                                   font=("Segoe UI", 9), bg=BG, fg=MUTED)
        self.vs_status_lbl.pack()

        btn_row = Frame(f, bg=BG); btn_row.pack(fill=X, padx=12, pady=(0,10))
        self._btn(btn_row, "  ≡ƒöì  Xem Preview SRT  ", _update_preview,
                  color="#21262D").pack(side=LEFT, fill=X, expand=True,
                                        padx=(0,4), ipady=8)
        self._btn(btn_row, "  ≡ƒöÑ  BURN VIETSUB V├ÇO VIDEO  ",
                  self._burn_vietsub, color=GREEN
                  ).pack(side=LEFT, fill=X, expand=True, ipady=8)

    # ΓöÇΓöÇ Vietsub helpers ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _vs_get_duration(self, video_path):
        """Lß║Ñy thß╗¥i l╞░ß╗úng video bß║▒ng ffprobe (gi├óy)."""
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
                        text=f"ΓÅ▒ Thß╗¥i l╞░ß╗úng: {dur:.1f}s ({int(dur//60)}ph{int(dur%60)}s)",
                        fg=GREEN
                    ))
                else:
                    # Fallback: ╞░ß╗¢c l╞░ß╗úng 8s
                    self._vs_duration = 8.0
                    self.root.after(0, lambda: self.vs_dur_lbl.config(
                        text="ΓÅ▒ Kh├┤ng ─æß╗ìc ─æ╞░ß╗úc thß╗¥i l╞░ß╗úng ΓÇö d├╣ng 8s mß║╖c ─æß╗ïnh", fg=ORANGE
                    ))
            except FileNotFoundError:
                self._vs_duration = 8.0
                self.root.after(0, lambda: self.vs_dur_lbl.config(
                    text="ΓÜá FFprobe ch╞░a c├ái ΓÇö d├╣ng 8s mß║╖c ─æß╗ïnh", fg=ORANGE
                ))
            except Exception as e:
                self._vs_duration = 8.0
        threading.Thread(target=_run, daemon=True).start()

    @staticmethod
    def _srt_time(seconds):
        """Chuyß╗ân gi├óy th├ánh ─æß╗ïnh dß║íng SRT: HH:MM:SS,mmm"""
        s = int(seconds)
        ms = int((seconds - s) * 1000)
        h, rem = divmod(s, 3600)
        m, sec = divmod(rem, 60)
        return f"{h:02d}:{m:02d}:{sec:02d},{ms:03d}"

    def _vs_build_srt(self, raw_text, total_duration):
        """X├óy dß╗▒ng nß╗Öi dung file SRT tß╗½ text v├á thß╗¥i l╞░ß╗úng video.
        Hß╗ù trß╗ú 2 ─æß╗ïnh dß║íng:
          - Tß╗▒ ─æß╗Öng: mß╗ùi d├▓ng 1 c├óu, chia ─æß╗üu
          - Thß╗º c├┤ng: 00:00:00-->00:00:03ΓöéNß╗Öi dung
        """
        lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
        if not lines:
            return "(Ch╞░a c├│ nß╗Öi dung)"

        srt_entries = []

        # Kiß╗âm tra c├│ ─æß╗ïnh dß║íng thß╗º c├┤ng kh├┤ng
        manual = all("|" in l and "-->" in l.split("|")[0] for l in lines)

        if manual:
            # ─Éß╗ïnh dß║íng thß╗º c├┤ng: 00:00:00.000-->00:00:03.000|Nß╗Öi dung
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
            # Tß╗▒ ─æß╗Öng: chia ─æß╗üu thß╗¥i gian
            n = len(lines)
            # ─Éß╗â lß║íi 0.3s kß║┐t th├║c mß╗ùi doanh (khoß║úng c├ích giß╗»a c├íc d├▓ng)
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
        """Parse thß╗¥i gian dß║íng HH:MM:SS hoß║╖c HH:MM:SS.mmm ΓåÆ gi├óy."""
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
        """Xß╗¡ l├╜ burn phß╗Ñ ─æß╗ü v├áo video bß║▒ng FFmpeg."""
        video = self.vs_video.get().strip()
        if not video or not os.path.exists(video):
            messagebox.showerror("Lß╗ùi", "─É╞░ß╗¥ng dß║½n video kh├┤ng hß╗úp lß╗ç!")
            return
        raw_text = self.vs_text.get("1.0", END).strip()
        if not raw_text:
            messagebox.showerror("Lß╗ùi", "Ch╞░a nhß║¡p nß╗Öi dung phß╗Ñ ─æß╗ü!")
            return

        out_dir = self.vs_out.get().strip()
        os.makedirs(out_dir, exist_ok=True)
        stem = Path(video).stem
        out_video = str(Path(out_dir) / f"{stem}_vietsub.mp4")

        dur = getattr(self, '_vs_duration', 8.0)
        srt_content = self._vs_build_srt(raw_text, dur)

        self.vs_prog.start()
        self.vs_status_lbl.config(text="ΓÅ│ ─Éang chuß║⌐n bß╗ï...")

        def _run():
            import tempfile
            srt_path = None  # BUG FIX: khß╗ƒi tß║ío None tr├ính NameError trong finally
            try:
                # Ghi file SRT tß║ím
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".srt", delete=False,
                    encoding="utf-8-sig",  # BOM: ─æß║úm bß║úo FFmpeg ─æß╗ìc ─æ╞░ß╗úc tiß║┐ng Viß╗çt
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

                # BUG FIX: FFmpeg subtitles filter tr├¬n Windows cß║ºn escape ─æ├║ng:
                # C:\path ΓåÆ C\\:/path (escape dß║Ñu hai chß║Ñm chß╗ë ß╗ƒ k├╜ tß╗▒ ß╗ò ─æ─⌐a)
                srt_ffmpeg = srt_path.replace("\\", "/")
                # Chß╗ë escape dß║Ñu ":" ß╗ƒ vß╗ï tr├¡ k├╜ tß╗▒ ß╗ò ─æ─⌐a (C:/ ΓåÆ C\:/)
                if len(srt_ffmpeg) > 1 and srt_ffmpeg[1] == ":":
                    srt_ffmpeg = srt_ffmpeg[0] + "\\:" + srt_ffmpeg[2:]

                vf_filter = f"subtitles='{srt_ffmpeg}':force_style='{style}'"

                self.root.after(0, lambda: self.vs_status_lbl.config(
                    text=f"≡ƒöÑ Burn phß╗Ñ ─æß╗ü v├áo: {Path(video).name}..."
                ))

                cmd = [
                    "ffmpeg", "-y", "-i", video,
                    "-vf", vf_filter,
                    "-c:v", "libx264", "-preset", "fast",
                    "-c:a", "copy",
                    out_video
                ]
                self.log(f"≡ƒô¥ ≡ƒöÑ Burn vietsub: {Path(video).name} ΓåÆ {Path(out_video).name}")
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

                if res.returncode == 0:
                    self.root.after(0, lambda: self.vs_prog.stop())
                    self.root.after(0, lambda: self.vs_status_lbl.config(
                        text=f"Γ£à Xong! ΓåÆ {out_video}", fg=GREEN
                    ))
                    self.root.after(0, lambda: messagebox.showinfo(
                        "Γ£à Burn xong!",
                        f"Phß╗Ñ ─æß╗ü ─æ├ú ─æ╞░ß╗úc ─æß╗æt v├áo video!\n\n{out_video}"
                    ))
                    self.log(f"Γ£à ─É├ú tß║ío: {out_video}")
                else:
                    err = res.stderr[-800:]
                    self.root.after(0, lambda: self.vs_prog.stop())
                    self.root.after(0, lambda: self.vs_status_lbl.config(
                        text="Γ¥î Lß╗ùi FFmpeg!", fg=RED))
                    self.root.after(0, lambda: messagebox.showerror(
                        "Γ¥î Lß╗ùi FFmpeg",
                        f"FFmpeg b├ío lß╗ùi:\n{err}\n\n"
                        f"≡ƒÆí Nß║┐u lß╗ùi 'No such file' vß╗¢i font: ─æß╗òi font sang 'Arial'"
                    ))
            except FileNotFoundError:
                self.root.after(0, lambda: self.vs_prog.stop())
                self.root.after(0, lambda: self.vs_status_lbl.config(
                    text="Γ¥î FFmpeg ch╞░a ─æ╞░ß╗úc c├ái!", fg=RED))
                self.root.after(0, lambda: messagebox.showerror(
                    "Lß╗ùi",
                    "FFmpeg ch╞░a c├ái!\nTß║úi tß║íi: https://ffmpeg.org/download.html\n"
                    "Sau ─æ├│ th├¬m v├áo PATH cß╗ºa Windows."
                ))
            except Exception as e:
                self.root.after(0, lambda: self.vs_prog.stop())
                _e = str(e)
                self.root.after(0, lambda: self.vs_status_lbl.config(
                    text=f"Γ¥î {_e}", fg=RED))
            finally:
                # BUG FIX: chß╗ë x├│a nß║┐u srt_path ─æ├ú ─æ╞░ß╗úc tß║ío
                if srt_path and os.path.exists(srt_path):
                    try: os.unlink(srt_path)
                    except: pass

        threading.Thread(target=_run, daemon=True).start()

    # ΓöÇΓöÇ HELPERS ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    # ΓöÇΓöÇ TAB: GEMINI AI ASSISTANT ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _tab_gemini(self):
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="≡ƒñû  Gemini AI")

        # ΓöÇΓöÇ API Key ΓöÇΓöÇ
        api_card = self._card(f, "≡ƒöæ API Key  (lß║Ñy miß╗àn ph├¡ tß║íi: aistudio.google.com)")
        api_card.pack(fill=X, padx=12, pady=(10,4))
        ar = Frame(api_card, bg=CARD); ar.pack(fill=X, padx=8, pady=6)
        Label(ar, text="API Key:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.gm_key = Entry(ar, width=58, show="ΓÇó", font=("Segoe UI",9),
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
                self.log("≡ƒöæ ─É├ú l╞░u API Key Gemini")
            except: pass
        self._btn(ar, "≡ƒÆ╛ L╞░u", _save_key, color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)

        # ΓöÇΓöÇ Chß╗ìn Model ΓöÇΓöÇ
        mc = self._card(f, "≡ƒñû Chß╗ìn Model")
        mc.pack(fill=X, padx=12, pady=4)
        mr = Frame(mc, bg=CARD); mr.pack(fill=X, padx=8, pady=6)
        Label(mr, text="Model:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.gm_model = StringVar(value="gemini-2.0-flash")
        models = [
            ("gemini-2.0-flash  ΓÅí Nhanh + ─Éa ph╞░╞íng tiß╗çn [KHUYß║╛N NGHß╗è]", "gemini-2.0-flash"),
            ("gemini-1.5-pro    ΓÅí Ph├ón t├¡ch Video d├ái (tß╗æi ─æa 1 giß╗¥)",   "gemini-1.5-pro"),
            ("gemini-1.5-flash  ΓÅí Nhanh, rß║╗ hß║ín mß╗⌐c",                     "gemini-1.5-flash"),
            ("gemini-2.0-flash-exp  ΓÅí Thß╗¡ nghiß╗çm mß╗¢i nhß║Ñt",             "gemini-2.0-flash-exp"),
        ]
        for mname, mval in models:
            Radiobutton(mr, text=mname, variable=self.gm_model, value=mval,
                        bg=CARD, fg=TEXT, selectcolor=BG, font=("Consolas",8),
                        activebackground=CARD).pack(anchor=W, padx=20)

        # ΓöÇΓöÇ Chß║┐ ─æß╗Ö ΓöÇΓöÇ
        mc2 = self._card(f, "≡ƒÄ» Chß║┐ ─æß╗Ö")
        mc2.pack(fill=X, padx=12, pady=4)
        mr2 = Frame(mc2, bg=CARD); mr2.pack(fill=X, padx=8, pady=6)
        self.gm_mode = StringVar(value="text")
        Radiobutton(mr2, text="≡ƒÆ¼ Tß║ío Prompt tß╗½ m├┤ tß║ú (Text)",
                    variable=self.gm_mode, value="text",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD, command=lambda: self._gm_update_ui()
                    ).pack(side=LEFT, padx=8)
        Radiobutton(mr2, text="≡ƒû╝∩╕Å Ph├ón t├¡ch ß║ónh/Video ΓåÆ Prompt",
                    variable=self.gm_mode, value="vision",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD, command=lambda: self._gm_update_ui()
                    ).pack(side=LEFT, padx=8)

        # ΓöÇΓöÇ INPUT (chß║┐ ─æß╗Ö TEXT) ΓöÇΓöÇ
        self.gm_text_card = self._card(f, "≡ƒÆ¼ M├┤ tß║ú nh├ón vß║¡t / cß║únh video bß║ín muß╗æn tß║ío")
        self.gm_text_card.pack(fill=X, padx=12, pady=4)
        Label(self.gm_text_card,
              text="≡ƒÆí M├┤ tß║ú ngß║»n gß╗ìn: ai/nh├ón vß║¡t, bß║ºu kh├┤ng kh├¡, h├ánh ─æß╗Öng, ├ính s├íng, thß╗¥i ─æiß╗âm...",
              bg=CARD, fg=MUTED, font=("Segoe UI",8)).pack(anchor=W, padx=8, pady=(2,0))
        self.gm_input = scrolledtext.ScrolledText(
            self.gm_text_card, height=5, font=("Segoe UI",10),
            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat",
            wrap=WORD)
        self.gm_input.pack(fill=X, padx=6, pady=(2,6))
        self.gm_input.insert(END,
            "Mß╗Öt c├┤ g├íi t├│c d├ái ─æß╗Å ─æi dß║ío trong c├┤ng vi├¬n v├áo buß╗òi chiß╗üu, "
            "├ính nß║»ng v├áng rß╗ìi qua l├í c├óy xanh mß║¡t, kh├┤ng kh├¡ y├¬n b├¼nh v├á n├¬n th╞í"
        )

        # ΓöÇΓöÇ INPUT (chß║┐ ─æß╗Ö VISION) ΓöÇΓöÇ
        self.gm_vision_card = self._card(f, "≡ƒû╝∩╕Å Upload ß║únh hoß║╖c video cß║ºn ph├ón t├¡ch")
        # ß║¿n ban ─æß║ºu (chß║┐ ─æß╗Ö text)

        vr = Frame(self.gm_vision_card, bg=CARD); vr.pack(fill=X, padx=8, pady=6)
        Label(vr, text="File:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.gm_media = Entry(vr, width=52, font=("Segoe UI",9),
                              bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.gm_media.pack(side=LEFT, padx=6, ipady=3)

        def _browse_media():
            p = filedialog.askopenfilename(
                title="Chß╗ìn ß║únh hoß║╖c video",
                filetypes=[
                    ("H├¼nh ß║únh", "*.jpg *.jpeg *.png *.webp *.gif"),
                    ("Video", "*.mp4 *.mov *.avi *.mkv"),
                    ("Tß║Ñt cß║ú", "*.*")
                ])
            if p:
                self.gm_media.delete(0, END)
                self.gm_media.insert(0, p)
        self._btn(vr, "≡ƒôé", _browse_media,
                  color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)

        Label(self.gm_vision_card,
              text="≡ƒÆí Gemini sß║╜ ph├ón t├¡ch nß╗Öi dung rß╗ôi viß║┐t Prompt Veo3 t╞░╞íng ─æ╞░╞íng",
              bg=CARD, fg=MUTED, font=("Segoe UI",8)).pack(anchor=W, padx=10, pady=(0,6))

        # ΓöÇΓöÇ Y├¬u cß║ºu bß╗ò sung (cho cß║ú 2 chß║┐ ─æß╗Ö) ΓöÇΓöÇ
        rc = self._card(f, "ΓÜÖ Y├¬u cß║ºu bß╗ò sung  (t├╣y chß╗ìn)")
        rc.pack(fill=X, padx=12, pady=4)
        Label(rc, text="Th├¬m y├¬u cß║ºu ri├¬ng: phong c├ích quay, di chuyß╗ân camera, thß╗¥i gian...",
              bg=CARD, fg=MUTED, font=("Segoe UI",8)).pack(anchor=W, padx=8, pady=(4,2))
        self.gm_extra = Entry(rc, width=70, font=("Segoe UI",9),
                              bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.gm_extra.insert(0, "slow motion, cinematic, 4K, golden hour lighting, camera pan left")
        self.gm_extra.pack(fill=X, padx=8, pady=(0,6), ipady=3)

        # ΓöÇΓöÇ N├║t gß╗¡i ΓöÇΓöÇ
        br = Frame(f, bg=BG); br.pack(fill=X, padx=12, pady=4)
        self.gm_send_btn = self._btn(
            br, "  Γ£¿  Gß╗¼i cho Gemini AI  ",
            self._gm_send, color="#7C3AED")
        self.gm_send_btn.pack(side=LEFT, fill=X, expand=True, ipady=10)

        # ΓöÇΓöÇ Kß║┐t quß║ú ΓöÇΓöÇ
        oc = self._card(f, "≡ƒô¥ Kß║┐t quß║ú ΓÇö Prompt do Gemini viß║┐t")
        oc.pack(fill=X, padx=12, pady=4)
        self.gm_result = scrolledtext.ScrolledText(
            oc, height=12, font=("Consolas",10), wrap=WORD,
            bg="#0A0F1A", fg="#58D68D", insertbackground=TEXT, relief="flat")
        self.gm_result.pack(fill=X, padx=6, pady=(4,6))

        # N├║t action sau khi c├│ kß║┐t quß║ú
        ab = Frame(f, bg=BG); ab.pack(fill=X, padx=12, pady=(0,6))
        self._btn(ab, "≡ƒôï Sao ch├⌐p",
                  lambda: self._gm_copy(), color="#21262D"
                  ).pack(side=LEFT, padx=(0,4), ipady=6, ipadx=8)
        self._btn(ab, "Γ₧£ Gß╗¡i sang TextΓåÆVideo",
                  lambda: self._gm_send_to_t2v(), color=ACCENT
                  ).pack(side=LEFT, padx=4, ipady=6, ipadx=8)
        self._btn(ab, "Γ₧£ Gß╗¡i sang Tß║ío Video Nh├ón Vß║¡t",
                  lambda: self._gm_send_to_cv(), color="#E67E22"
                  ).pack(side=LEFT, padx=4, ipady=6, ipadx=8)

        # Status
        self.gm_status = Label(f, text="≡ƒñû Sß║╡n s├áng",
                               font=("Segoe UI",9), bg=BG, fg=MUTED)
        self.gm_status.pack(pady=(0,8))

        # ΓöÇΓöÇ Tß║ío ß║únh trß╗▒c tiß║┐p qua Flow (Nano Banana 2) ΓöÇΓöÇ
        img_card = self._card(f, "≡ƒÄ¿ Tß║ío ß║únh bß║▒ng Nano Banana 2 (Google Flow ΓÇö miß╗àn ph├¡!)")
        img_card.pack(fill=X, padx=12, pady=(4,10))

        Label(img_card,
              text="≡ƒÆí Prompt d╞░ß╗¢i ─æ├óy (hoß║╖c tß╗▒ nhß║¡p) ΓÇö d├╣ng kß║┐t quß║ú tß╗½ Gemini bß║▒ng n├║t 'D├╣ng prompt'",
              bg=CARD, fg=MUTED, font=("Segoe UI",8)).pack(anchor=W, padx=8, pady=(4,2))

        self.gm_img_prompt = scrolledtext.ScrolledText(
            img_card, height=4, font=("Segoe UI",9), wrap=WORD,
            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.gm_img_prompt.pack(fill=X, padx=6, pady=(0,4))
        self.gm_img_prompt.insert(END, "A beautiful woman walking in a park, golden hour, cinematic")

        ir1 = Frame(img_card, bg=CARD); ir1.pack(fill=X, padx=8, pady=3)
        # Sß╗æ l╞░ß╗úng ß║únh
        Label(ir1, text="Sß╗æ ß║únh:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.gm_img_count = StringVar(value="1")
        for n in ["1","2","3","4"]:
            Radiobutton(ir1, text=f"x{n}", variable=self.gm_img_count, value=n,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI",9)
                        ).pack(side=LEFT, padx=6)
        # Tß╗ë lß╗ç khung
        Label(ir1, text="  H╞░ß╗¢ng:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT, padx=(12,0))
        self.gm_img_orient = StringVar(value="ngang")
        Radiobutton(ir1, text="Γû¼ Ngang", variable=self.gm_img_orient, value="ngang",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD).pack(side=LEFT, padx=4)
        Radiobutton(ir1, text="Γû« Dß╗ìc", variable=self.gm_img_orient, value="doc",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD).pack(side=LEFT, padx=4)

        ir2 = Frame(img_card, bg=CARD); ir2.pack(fill=X, padx=8, pady=(2,6))
        self._btn(ir2, "Γ¼à D├╣ng Prompt Gemini",
                  lambda: self._gm_use_result_for_img(),
                  color="#21262D").pack(side=LEFT, ipady=5, ipadx=6)
        self._btn(ir2, "  ≡ƒÄ¿  Tß║ío ß║únh Nano Banana 2  ",
                  self._gm_generate_image,
                  color="#C0392B").pack(side=LEFT, padx=6, ipady=5, fill=X, expand=True)

        self.gm_img_status = Label(
            img_card, text="≡ƒÆí Nhß║Ñn n├║t 'Tß║ío ß║únh' ΓÇö tr├¼nh duyß╗çt phß║úi ─æang mß╗ƒ v├á kß║┐t nß╗æi",
            font=("Segoe UI",8), bg=CARD, fg=MUTED, wraplength=700, justify=LEFT)
        self.gm_img_status.pack(anchor=W, padx=8, pady=(0,4))

        # ΓöÇΓöÇ BATCH IMAGE QUEUE (JSON) ΓöÇΓöÇ
        bq = self._card(f, "≡ƒôï Batch Tß║ío ß║únh H├áng Loß║ít ΓÇö JSON / mß╗ùi d├▓ng 1 prompt")
        bq.pack(fill=X, padx=12, pady=(0,10))

        Label(bq,
              text=(
                "≡ƒÆí D├ín prompt JSON: [\"prompt1\",\"prompt2\"] hoß║╖c mß╗ùi d├▓ng 1 prompt.\n"
                "   Tool sß║╜ tß╗▒ split, d├ín tß╗½ng prompt v├áo Flow, ─æß╗úi ß║únh xong rß╗ôi tß║úi vß╗ü theo thß╗⌐ tß╗▒."
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
        Label(bq_r1, text="Sß╗æ ß║únh/prompt:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.bq_count = StringVar(value="1")
        for n in ["1","2","3","4"]:
            Radiobutton(bq_r1, text=f"x{n}", variable=self.bq_count, value=n,
                        bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                        activebackground=CARD).pack(side=LEFT, padx=5)
        Label(bq_r1, text="  H╞░ß╗¢ng:", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT, padx=(12,0))
        self.bq_orient = StringVar(value="ngang")
        Radiobutton(bq_r1, text="Γû¼ Ngang", variable=self.bq_orient, value="ngang",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD).pack(side=LEFT, padx=4)
        Radiobutton(bq_r1, text="Γû« Dß╗ìc", variable=self.bq_orient, value="doc",
                    bg=CARD, fg=TEXT, selectcolor=BG, font=("Segoe UI",9),
                    activebackground=CARD).pack(side=LEFT, padx=4)

        bq_r2 = Frame(bq, bg=CARD); bq_r2.pack(fill=X, padx=8, pady=2)
        Label(bq_r2, text="─Éß╗úi giß╗»a nh├│m (s):", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.bq_delay = Entry(bq_r2, width=5, font=("Segoe UI",9),
                              bg="#0D1117", fg=TEXT, relief="flat", justify=CENTER)
        self.bq_delay.insert(0, "3"); self.bq_delay.pack(side=LEFT, padx=6, ipady=3)
        Label(bq_r2, text="  Max chß╗¥/ß║únh (s):", bg=CARD, fg=MUTED, font=("Segoe UI",9)).pack(side=LEFT)
        self.bq_timeout = Entry(bq_r2, width=5, font=("Segoe UI",9),
                                bg="#0D1117", fg=TEXT, relief="flat", justify=CENTER)
        self.bq_timeout.insert(0, "90"); self.bq_timeout.pack(side=LEFT, padx=6, ipady=3)

        bq_r3 = Frame(bq, bg=CARD); bq_r3.pack(fill=X, padx=8, pady=(2,4))
        self.bq_start_btn = self._btn(
            bq_r3, "  Γû╢∩╕Å  Bß║»t ─æß║ºu Batch Tß║ío ß║únh  ",
            self._img_batch_start, color="#1A7F37")
        self.bq_start_btn.pack(side=LEFT, fill=X, expand=True, ipady=8)
        self.bq_stop_btn = self._btn(
            bq_r3, "ΓÅ╣ Dß╗½ng", self._img_batch_stop, color="#6E2424")
        self.bq_stop_btn.pack(side=LEFT, padx=(4,0), ipady=8, ipadx=10)

        self.bq_progress = ttk.Progressbar(bq, mode="determinate", maximum=100)
        self.bq_progress.pack(fill=X, padx=8, pady=(4,2))
        self.bq_status = Label(
            bq, text="≡ƒôï Sß║╡n s├áng. Nhß║Ñn 'Bß║»t ─æß║ºu' ─æß╗â chß║íy batch.",
            font=("Segoe UI",8), bg=CARD, fg=MUTED, wraplength=700, justify=LEFT)
        self.bq_status.pack(anchor=W, padx=8, pady=(0,6))
        self._bq_running = False

        # ß║¿n vision card ban ─æß║ºu
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
        """X├óy dß╗▒ng system prompt cho Gemini."""
        extra = self.gm_extra.get().strip()
        system = (
            "Bß║ín l├á chuy├¬n gia viß║┐t prompt cho AI tß║ío video Veo3 cß╗ºa Google. "
            "Nhiß╗çm vß╗Ñ: viß║┐t prompt tiß║┐ng Anh CHUß║¿N, cß╗Ñ thß╗â, gi├áu h├¼nh ß║únh. "
            "Format cß║ºn c├│: [subject + action], [environment], [lighting], ["
            "camera movement], [mood/atmosphere], [technical style]. "
            "Rß║ú kß║┐t quß║ú LOß║áI Bß╗Å giß║úi th├¡ch, chß╗ë trß║ú vß╗ü PROMPT THUß║ªN."
        )
        if extra:
            system += f" Th├¬m y├¬u cß║ºu: {extra}."
        return system

    def _gm_send(self):
        key = self.gm_key.get().strip()
        if not key:
            messagebox.showerror("Lß╗ùi", "Ch╞░a nhß║¡p API Key Gemini!\n"
                                         "Lß║Ñy miß╗àn ph├¡ tß║íi: aistudio.google.com")
            return
        if not HAS_GEMINI:
            messagebox.showerror("Lß╗ùi",
                "Ch╞░a c├ái google-generativeai!\n"
                "Chß║íy: pip install google-generativeai")
            return

        mode = self.gm_mode.get()
        if mode == "text":
            user_input = self.gm_input.get("1.0", END).strip()
            if not user_input:
                messagebox.showerror("Lß╗ùi", "Ch╞░a nhß║¡p m├┤ tß║ú!")
                return
        else:
            media_path = self.gm_media.get().strip()
            if not media_path or not os.path.exists(media_path):
                messagebox.showerror("Lß╗ùi", "─É╞░ß╗¥ng dß║½n file kh├┤ng hß╗úp lß╗ç!")
                return

        self.gm_send_btn.config(state=DISABLED, text="ΓÅ│ ─Éang hß╗Åi Gemini...")
        self.gm_status.config(text="ΓÅ│ Gemini ─æang xß╗¡ l├╜...", fg=ORANGE)
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
                        f"Viß║┐t 3 biß║┐n thß╗â PROMPT cho Veo3 dß╗▒a tr├¬n m├┤ tß║ú sau:\n"
                        f"\"{desc}\"\n\n"
                        f"Mß╗ùi prompt tr├¬n 1 d├▓ng ri├¬ng, bß║»t ─æß║ºu bß║▒ng [Prompt 1], [Prompt 2], [Prompt 3]."
                    )
                    response = model.generate_content(prompt_msg)
                    result = response.text

                else:  # vision
                    media_path2 = self.gm_media.get().strip()
                    ext = Path(media_path2).suffix.lower()

                    # Upload file qua File API (cß║ºn thiß║┐t cho video)
                    is_video = ext in (".mp4",".mov",".avi",".mkv")
                    if is_video:
                        self.root.after(0, lambda: self.gm_status.config(
                            text="ΓÅ│ Upload video l├¬n Gemini File API...", fg=ORANGE))
                        uploaded = genai.upload_file(media_path2)
                        # Chß╗¥ xß╗¡ l├╜ xong
                        import time as _t
                        while uploaded.state.name == "PROCESSING":
                            _t.sleep(2)
                            uploaded = genai.get_file(uploaded.name)
                        if uploaded.state.name == "FAILED":
                            raise Exception("Upload video thß║Ñt bß║íi!")
                        content = [
                            uploaded,
                            "Ph├ón t├¡ch video tr├¬n rß╗ôi viß║┐t 3 PROMPT Veo3 ph├╣ hß╗úp. "
                            "Mß╗ùi prompt tr├¬n 1 d├▓ng, bß║»t ─æß║ºu bß║▒ng [Prompt 1], [Prompt 2], [Prompt 3]."
                        ]
                    else:
                        # ß║ónh: ─æß╗ìc trß╗▒c tiß║┐p
                        import PIL.Image
                        img = PIL.Image.open(media_path2)
                        content = [
                            img,
                            (
                                "Ph├ón t├¡ch h├¼nh ß║únh n├áy v├á viß║┐t 3 PROMPT Veo3 "
                                "tß║ío video cß╗ºa cß║únh t╞░╞íng tß╗▒. "
                                "Mß╗ùi prompt tr├¬n 1 d├▓ng, bß║»t ─æß║ºu bß║▒ng [Prompt 1], [Prompt 2], [Prompt 3]."
                            )
                        ]
                    response = model.generate_content(content)
                    result = response.text

                self.root.after(0, lambda: self.gm_result.insert(END, result))
                self.root.after(0, lambda: self.gm_status.config(
                    text=f"Γ£à Gemini ({model_name}) ─æ├ú viß║┐t xong!", fg=GREEN))
                self.log(f"≡ƒñû Gemini tß║ío prompt th├ánh c├┤ng ({model_name})")

            except Exception as e:
                err = str(e)
                self.root.after(0, lambda: self.gm_result.insert(END, f"Γ¥î Lß╗ùi:\n{err}"))
                self.root.after(0, lambda: self.gm_status.config(
                    text=f"Γ¥î {err[:80]}", fg=RED))
                self.log(f"Γ¥î Gemini lß╗ùi: {err}")
            finally:
                self.root.after(0, lambda: self.gm_send_btn.config(
                    state=NORMAL, text="  Γ£¿  Gß╗¼i cho Gemini AI  "))

        threading.Thread(target=_run, daemon=True).start()

    def _gm_copy(self):
        text = self.gm_result.get("1.0", END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.gm_status.config(text="≡ƒôï ─É├ú sao ch├⌐p!", fg=GREEN)

    def _gm_extract_prompts(self):
        """T├ích c├íc prompt tß╗½ kß║┐t quß║ú Gemini."""
        raw = self.gm_result.get("1.0", END).strip()
        if not raw:
            return []
        # T├¼m c├íc d├▓ng [Prompt X] ...
        prompts = re.findall(r"\[Prompt \d+\]\s*(.+?)(?=\[Prompt|$)", raw, re.DOTALL)
        if prompts:
            return [p.strip() for p in prompts if p.strip()]
        # Fallback: trß║ú vß╗ü to├án bß╗Ö
        return [raw]

    def _gm_send_to_t2v(self):
        """Gß╗¡i prompt Gemini sang tab TextΓåÆVideo."""
        prompts = self._gm_extract_prompts()
        if not prompts:
            messagebox.showinfo("Th├┤ng b├ío", "Ch╞░a c├│ kß║┐t quß║ú tß╗½ Gemini!")
            return
        # Th├¬m v├áo ├┤ prompt cß╗ºa tab TextΓåÆVideo
        try:
            self.tv_prompts.delete("1.0", END)
            self.tv_prompts.insert(END, "\n".join(prompts))
            # Chuyß╗ân sang tab TextΓåÆVideo (index 2)
            self.nb.select(2)
            self.gm_status.config(text=f"Γ£à ─É├ú gß╗¡i {len(prompts)} prompt sang TextΓåÆVideo", fg=GREEN)
        except Exception as e:
            messagebox.showerror("Lß╗ùi", f"Kh├┤ng gß╗¡i ─æ╞░ß╗úc: {e}")

    def _gm_send_to_cv(self):
        """Gß╗¡i prompt Gemini sang tab Tß║ío Video Nh├ón Vß║¡t."""
        prompts = self._gm_extract_prompts()
        if not prompts:
            messagebox.showinfo("Th├┤ng b├ío", "Ch╞░a c├│ kß║┐t quß║ú tß╗½ Gemini!")
            return
        try:
            self.cv_prompts.delete("1.0", END)
            self.cv_prompts.insert(END, "\n".join(prompts))
            # Chuyß╗ân sang tab Tß║ío Video (index 4)
            self.nb.select(4)
            self.gm_status.config(text=f"Γ£à ─É├ú gß╗¡i {len(prompts)} prompt sang Tß║ío Video", fg=GREEN)
        except Exception as e:
            messagebox.showerror("Lß╗ùi", f"Kh├┤ng gß╗¡i ─æ╞░ß╗úc: {e}")

    # ΓöÇΓöÇ HELPERS ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _build_ui(self):
        # ΓöÇΓöÇ Header banner ΓöÇΓöÇ
        hdr = Frame(self.root, bg="#0A0F1A", height=56)
        hdr.pack(fill=X)
        hdr.pack_propagate(False)
        Label(hdr, text="≡ƒÄ¼  VEO 3 FLOW PRO",
              font=("Segoe UI", 16, "bold"), bg="#0A0F1A", fg=ACCENT
              ).pack(side=LEFT, padx=18, pady=10)
        Label(hdr, text="Tß╗▒ ─æß╗Öng tß║ío video chß║Ñt l╞░ß╗úng cao ┬╖ Google Flow AI",
              font=("Segoe UI", 9), bg="#0A0F1A", fg=MUTED
              ).pack(side=LEFT, padx=2)
        self.status_var = StringVar(value="Γùë  Ch╞░a kß║┐t nß╗æi")
        Label(hdr, textvariable=self.status_var,
              font=("Segoe UI", 9, "bold"), bg="#0A0F1A", fg=RED
              ).pack(side=RIGHT, padx=20)

        # ΓöÇΓöÇ Notebook ΓöÇΓöÇ
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

        # ΓöÇΓöÇ Status bar ΓöÇΓöÇ
        sb = Frame(self.root, bg=CARD, height=22)
        sb.pack(fill=X, side=BOTTOM)
        sb.pack_propagate(False)
        Label(sb, text="VEO 3 FLOW PRO  v2.0   ┬⌐2025 TechViet AI",
              font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(side=RIGHT, padx=10)
        Label(sb, text="Γ£ª ─Éß║╖t folder output ri├¬ng cho mß╗ùi m├íy khi chß║íy song song",
              font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(side=LEFT, padx=10)

    # ΓöÇΓöÇ Widget helpers ΓöÇΓöÇ
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
        """Tß║ío frame c├│ thß╗â cuß╗Ön l├¬n/xuß╗æng bß║▒ng scrollbar v├á mousewheel.
        Trß║ú vß╗ü (outer, inner): outer pack v├áo notebook, inner d├╣ng ─æß╗â ─æß║╖t widget."""
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
        # Bind mousewheel khi chuß╗Öt ß╗ƒ trong canvas hoß║╖c inner
        canvas.bind("<MouseWheel>", _on_mousewheel)
        inner.bind_all("<MouseWheel>", _on_mousewheel)

        return outer, inner

    # ΓöÇΓöÇ TAB 1: H╞░ß╗¢ng dß║½n ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _tab_note(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="≡ƒôî  H╞░ß╗¢ng Dß║½n")
        hf = Frame(f, bg="#0A0F1A"); hf.pack(fill=X)
        Label(hf, text="≡ƒôî  H╞░ß╗¢ng dß║½n sß╗¡ dß╗Ñng VEO 3 FLOW PRO",
              font=("Segoe UI", 12, "bold"), bg="#0A0F1A", fg=ACCENT
              ).pack(anchor=W, padx=16, pady=10)
        txt = scrolledtext.ScrolledText(f, wrap=WORD, font=("Segoe UI", 10),
                                        bg=CARD, fg=TEXT, insertbackground=TEXT,
                                        relief="flat", bd=0, padx=8, pady=8)
        txt.pack(fill=BOTH, expand=True, padx=12, pady=(0, 10))
        txt.insert(END, """
  ΓÜá∩╕Å  Y├èU Cß║ªU Bß║«T BUß╗ÿC:
  ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
  1. C├ái Google Chrome + ─æ─âng nhß║¡p Google AI Pro tß║íi: labs.google/fx
  2. C├ái Python packages:  pip install selenium webdriver-manager pillow

  ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
  ≡ƒîÉ  BROWSER & Kß║╛T Nß╗ÉI
      ΓåÆ Mß╗ƒ Chrome v├áo Google Flow (Th╞░ß╗¥ng / ß║¿n danh / Chrome mß╗¢i)
      ΓåÆ Kß║┐t nß╗æi Chrome ─æang mß╗ƒ sß║╡n qua remote debug port

  ≡ƒô¥  TEXT TO VIDEO  (Tab ch├¡nh)
      ΓåÆ D├ín danh s├ích prompt ΓÇö mß╗ùi d├▓ng mß╗Öt lß╗çnh
      ΓåÆ Hß╗ù trß╗ú JSON: {"prompt":"...","style":"...","aspect_ratio":"9:16"}
      ΓåÆ [START]  ΓÇö Tuß║ºn tß╗▒: tß║ío xong rß╗ôi tß║úi, sang prompt tiß║┐p
      ΓåÆ [RAPID]  ΓÇö Submit nhanh tß║Ñt cß║ú, render SONG SONG tr├¬n cloud
      ΓåÆ [STOP]   ΓÇö Dß╗½ng tiß║┐n tr├¼nh ─æang chß║íy

  ≡ƒæñ  NH├éN Vß║¼T (Character Setup)
      ΓåÆ Chß╗ìn ß║únh nh├ón vß║¡t ΓåÆ ─Éß║╖t t├¬n ngß║»n (Alice, Bob, NhanVat1...)
      ΓåÆ Upload l├¬n Flow ΓåÆ Tool tß╗▒ ch├¿n ß║únh khi tß║ío video

  ≡ƒÄ₧∩╕Å  Tß║áO VIDEO NH├éN Vß║¼T (Create Video)
      ΓåÆ Nhß║¡p prompt cho tß╗½ng cß║únh
      ΓåÆ Tool tß╗▒ upload ß║únh + generate theo thß╗⌐ tß╗▒

  ≡ƒôï  LOGS   ΓÇö Xem to├án bß╗Ö hoß║ít ─æß╗Öng, l╞░u log ra file TXT

  ≡ƒÄ¼  GH├ëP VIDEO ΓÇö Gh├⌐p nhiß╗üu MP4 th├ánh 1 file (cß║ºn FFmpeg)
      ΓåÆ Tß║úi FFmpeg: https://ffmpeg.org/download.html

  ≡ƒÆí  Mß║╕O: D├╣ng th╞░ mß╗Ñc output RI├èNG cho mß╗ùi phi├¬n/m├íy
           ─æß╗â tr├ính lß║½n file khi chß║íy song song.
""")
        txt.config(state=DISABLED)

    # ΓöÇΓöÇ TAB 2: Browser & Kß║┐t Nß╗æi ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _tab_browser(self):
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="≡ƒîÉ  Kß║┐t Nß╗æi")

        # H╞░ß╗¢ng dß║½n nhanh
        top = self._card(f, "≡ƒôï Quy tr├¼nh kß║┐t nß╗æi")
        top.pack(fill=X, padx=14, pady=(12, 5))
        Label(top, text=(
            "1∩╕ÅΓâú  Bß║Ñm n├║t Mß╗₧ CHROME b├¬n d╞░ß╗¢i  ΓåÆ  ─É─âng nhß║¡p Google nß║┐u cß║ºn\n"
            "2∩╕ÅΓâú  Sau khi ─æ─âng nhß║¡p xong        ΓåÆ  Bß║Ñm 'Γ£ö X├íc nhß║¡n ─æ─âng nhß║¡p'\n"
            "3∩╕ÅΓâú  Sang tab 'Text to Video'       ΓåÆ  Nhß║¡p prompt  ΓåÆ  Bß║Ñm START"
        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT
        ).pack(anchor=W, padx=10, pady=8)

        # N├║t ─æiß╗üu khiß╗ân Chrome
        ctrl = self._card(f, "ΓÜÖ∩╕Å ─Éiß╗üu khiß╗ân Chrome")
        ctrl.pack(fill=X, padx=14, pady=5)

        row1 = Frame(ctrl, bg=CARD); row1.pack(fill=X, padx=8, pady=(8, 3))
        self._btn(row1, "  ≡ƒûÑ  Mß╗ƒ Chrome (Th╞░ß╗¥ng)  ",
                  lambda: self._run_bg(lambda: self.bc.open("normal", download_dir=OUTPUT_DIR_TEXT)),
                  color=ACCENT).pack(side=LEFT, fill=X, expand=True, padx=(0,4), ipady=8)
        self._btn(row1, "  ≡ƒöÆ  Mß╗ƒ Chrome ß║¿n Danh  ",
                  lambda: self._run_bg(lambda: self.bc.open("incognito", download_dir=OUTPUT_DIR_TEXT)),
                  color="#444C56").pack(side=LEFT, fill=X, expand=True, padx=(4,0), ipady=8)

        row2 = Frame(ctrl, bg=CARD); row2.pack(fill=X, padx=8, pady=3)
        self._btn(row2, "  Γ£¿  Chrome Ho├án To├án Mß╗¢i (Fresh)  ",
                  lambda: self._run_bg(lambda: self.bc.open("fresh", download_dir=OUTPUT_DIR_TEXT)),
                  color=PURPLE).pack(side=LEFT, fill=X, expand=True, padx=(0,4), ipady=8)
        self._btn(row2, "  ≡ƒöù  Kß║┐t Nß╗æi Chrome ─Éang Mß╗ƒ  ",
                  lambda: self._run_bg(self._connect_existing_chrome),
                  color=ORANGE).pack(side=LEFT, fill=X, expand=True, padx=(4,0), ipady=8)

        Frame(ctrl, bg=BORDER, height=1).pack(fill=X, padx=8, pady=8)

        self._btn(ctrl, "  Γ£ö  X├íc nhß║¡n ─æ─âng nhß║¡p xong ΓåÆ Bß║»t ─æß║ºu sß╗¡ dß╗Ñng  ",
                  self._confirm_login, color=GREEN
                  ).pack(fill=X, padx=8, pady=(0,5), ipady=10)

        row3 = Frame(ctrl, bg=CARD); row3.pack(fill=X, padx=8, pady=(0,8))
        def refresh_status():
            s = self.bc.get_status()
            self.status_var.set(f"Γùë  {s}")
        self._btn(row3, "≡ƒöä Cß║¡p nhß║¡t trß║íng th├íi", refresh_status,
                  color="#21262D").pack(side=LEFT, padx=(0,4), ipady=5)

        def test_paste():
            if not self.bc.is_alive():
                messagebox.showerror("Lß╗ùi", "Ch╞░a mß╗ƒ Chrome!")
                return
            sample = "A beautiful sunset over the ocean, cinematic lighting, 8K"
            self.log("≡ƒº¬ TEST: Mß╗ƒ project mß╗¢i + d├ín prompt mß║½u...")
            self.nb.select(5)
            def _run():
                ok = self.bc.new_project()
                if ok:
                    self.bc.set_prompt(sample)
                    self.log("Γ£à TEST xong ΓÇö kiß╗âm tra Chrome xem prompt ─æ├ú hiß╗çn ch╞░a!")
                else:
                    self.log("Γ¥î TEST thß║Ñt bß║íi")
            self._run_bg(_run)
        self._btn(row3, "≡ƒº¬ TEST: D├ín prompt mß║½u", test_paste,
                  color="#1B4721").pack(side=LEFT, ipady=5)

    def _confirm_login(self):
        self.log("Γ£à ─É├ú x├íc nhß║¡n ─æ─âng nhß║¡p!")
        self.set_status("Trß║íng th├íi: Γ£à ─É├ú ─æ─âng nhß║¡p")
        messagebox.showinfo("OK", "─É├ú x├íc nhß║¡n ─æ─âng nhß║¡p!\nB├óy giß╗¥ chuyß╗ân sang tab Text to Video ─æß╗â bß║»t ─æß║ºu.")

    def _connect_existing_chrome(self):
        """Kß║┐t nß╗æi tß╗¢i Chrome ─æang mß╗ƒ qua remote debugging port"""
        ok = self.bc.connect_existing()
        if ok:
            self.set_status("Trß║íng th├íi: Γ£à Kß║┐t nß╗æi Chrome th├ánh c├┤ng")
            self.root.after(0, lambda: messagebox.showinfo(
                "Γ£à Kß║┐t nß╗æi OK",
                f"─É├ú kß║┐t nß╗æi Chrome th├ánh c├┤ng!\n{self.bc.get_status()}\n\nB├óy giß╗¥ sang tab Text to Video ─æß╗â tß║ío video."
            ))
        else:
            self.root.after(0, lambda: messagebox.showerror(
                "Γ¥î Kß║┐t nß╗æi thß║Ñt bß║íi",
                "Kh├┤ng kß║┐t nß╗æi ─æ╞░ß╗úc Chrome!\n\n"
                "Giß║úi ph├íp:\n"
                "1. ─É├ôNG Chrome ─æang mß╗ƒ\n"
                "2. Bß║Ñm 'Mß╗₧ CHROME' trong tool\n"
                "3. ─É─âng nhß║¡p Google tr├¬n Chrome ─æ├│\n"
                "4. Bß║Ñm 'Gß╗¼I ─É─éNG NHß║¼P'\n"
                "5. Sang tab Text to Video ΓåÆ START"
            ))

    # ΓöÇΓöÇ TAB 3: Text to Video ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _tab_text2video(self):
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="≡ƒô¥  Text to Video")

        # Prompts
        lf = self._card(f, "≡ƒô¥ Danh s├ích Prompt  (mß╗ùi d├▓ng 1 lß╗çnh ΓÇö hß╗ù trß╗ú JSON)")
        lf.pack(fill=BOTH, expand=True, padx=12, pady=(10,4))

        mode_f = Frame(lf, bg=CARD); mode_f.pack(anchor=W, pady=(4,2))
        Label(mode_f, text="─Éß╗ïnh dß║íng nhß║¡p:  ", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.tv_mode = StringVar(value="normal")
        for txt, val in [("Th├┤ng th╞░ß╗¥ng (mß╗ùi d├▓ng 1 prompt)", "normal"),
                          ("JSON n├óng cao (scene_1, scene_2...)", "json")]:
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
        sf = self._card(f, "ΓÜÖ∩╕Å C├ái ─æß║╖t ─æß║ºu ra")
        sf.pack(fill=X, padx=12, pady=4)
        r1 = Frame(sf, bg=CARD); r1.pack(fill=X, pady=3, padx=8)
        Label(r1, text="T├¬n file:", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.tv_base = Entry(r1, width=20, font=("Segoe UI", 9),
                             bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.tv_base.insert(0, "video")
        self.tv_base.pack(side=LEFT, padx=6, ipady=3)
        Label(r1, text="ΓåÆ  video_01.mp4, video_02.mp4, ...",
              bg=CARD, fg=MUTED, font=("Segoe UI", 8)).pack(side=LEFT)

        r2 = Frame(sf, bg=CARD); r2.pack(fill=X, pady=3, padx=8)
        Label(r2, text="L╞░u tß║íi:", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.tv_out = Entry(r2, width=55, font=("Segoe UI", 9),
                            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.tv_out.insert(0, OUTPUT_DIR_TEXT)
        self.tv_out.pack(side=LEFT, padx=6, ipady=3)
        self._btn(r2, "≡ƒôé", lambda: self._browse(self.tv_out),
                  color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)

        # Delay
        df = self._card(f, "ΓÅ▒ ─Éß╗Ö trß╗à giß╗»a c├íc prompt")
        df.pack(fill=X, padx=12, pady=4)
        df_r = Frame(df, bg=CARD); df_r.pack(anchor=W, padx=8, pady=4)
        self.tv_delay = StringVar(value="normal")
        for txt, val in [("B├¼nh th╞░ß╗¥ng (5s)", "normal"),
                          ("Gß║Ñp ─æ├┤i (10s)", "double"),
                          ("Ngß║½u nhi├¬n (6-15s)", "random")]:
            Radiobutton(df_r, text=txt, variable=self.tv_delay, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=8)

        # Timeout
        tf = self._card(f, "ΓÅ¼ Chß╗¥ video xong ΓåÆ Tß╗▒ ─æß╗Öng tß║úi  |  Hoß║╖c d├ín ngay kh├┤ng chß╗¥")
        tf.pack(fill=X, padx=12, pady=4)
        self.tv_timeout = StringVar(value="600")
        timeout_opts = [
            ("ΓÜí KH├öNG CHß╗£R ΓÇö D├ín prompt tiß║┐p ngay sau delay c├ái ─æß║╖t (fast mode)", "0"),
            ("Tß╗░ ─Éß╗ÿNG ΓÇö Chß╗¥ ─æß║┐n khi xong, tß╗æi ─æa 10 ph├║t  ΓÅ¼  Tß║úi ngay", "600"),
            ("Tß╗æi ─æa 5 ph├║t  ΓÅ¼  Tß║úi ngay khi xong", "300"),
            ("Tß╗æi ─æa 3 ph├║t  ΓÅ¼  Tß║úi ngay khi xong", "180"),
            ("Tß╗æi ─æa 1 ph├║t  ΓÅ¼  Tß║úi ngay khi xong", "60"),
        ]
        for txt, val in timeout_opts:
            Radiobutton(tf, text=txt, variable=self.tv_timeout, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(anchor=W, padx=12)
        Label(tf, text="  Γä╣∩╕Å  Tool tho├ít ngay khi video xong, kh├┤ng cß║ºn ─æß╗úi hß║┐t giß╗¥!",
              font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(anchor=W, padx=20, pady=(0,4))

        # Progress + buttons
        self.tv_progress = ttk.Progressbar(f, mode="indeterminate", style="TProgressbar")
        self.tv_progress.pack(fill=X, padx=12, pady=(6,2))
        self.tv_status_lbl = Label(f, text="", font=("Segoe UI", 8), bg=BG, fg=MUTED)
        self.tv_status_lbl.pack()

        btn_row = Frame(f, bg=BG); btn_row.pack(fill=X, padx=12, pady=8)
        self._btn(btn_row, "  Γû╢  START ΓÇö Tuß║ºn tß╗▒ + Tß║úi vß╗ü",
                  self._start_text2video, color=GREEN
                  ).pack(side=LEFT, fill=X, expand=True, ipady=9, padx=(0,4))
        self._btn(btn_row, "  ΓÜí  RAPID ΓÇö Submit nhanh, render song song",
                  self._start_rapid, color=ORANGE
                  ).pack(side=LEFT, fill=X, expand=True, ipady=9, padx=(0,4))
        self._btn(btn_row, "  ΓÅ╣  STOP",
                  self._stop, color=RED
                  ).pack(side=LEFT, ipady=9, ipadx=8)

    def _start_text2video(self):
        raw = self.tv_prompts.get("1.0", END).strip()
        if not raw:
            messagebox.showerror("Lß╗ùi", "Ch╞░a nhß║¡p prompt!")
            return
        if not self.bc.is_alive():
            messagebox.showerror("Lß╗ùi", "Ch╞░a mß╗ƒ Chrome! V├áo tab Browser & Setup tr╞░ß╗¢c.")
            return
        # Parse theo mode ─æ╞░ß╗úc chß╗ìn
        mode = self.tv_mode.get()   # "normal" hoß║╖c "json"
        parsed = self._parse_all_lines(raw, mode)
        if not parsed:
            messagebox.showerror("Lß╗ùi", "Kh├┤ng t├¼m thß║Ñy prompt hß╗úp lß╗ç!")
            return
        out_dir = self.tv_out.get()
        os.makedirs(out_dir, exist_ok=True)
        self.log(f"≡ƒÜÇ Bß║»t ─æß║ºu TextΓåÆVideo [{mode}]: {len(parsed)} prompt(s)")
        self.nb.select(5)  # switch to Logs tab
        self._run_bg(lambda: self._t2v_worker(parsed, out_dir))

    @staticmethod
    def _parse_all_lines(raw, mode="normal"):
        """Trß║ú vß╗ü list of (prompt_text, aspect_ratio, duration, meta).
        mode='normal': mß╗ùi d├▓ng l├á plain text.
        mode='json'  : tß╗▒ nhß║¡n dß║íng JSON-block (multi-scene) hoß║╖c JSON mß╗ùi d├▓ng.
        """
        results = []
        raw = raw.strip()

        if mode == "json":
            # ΓöÇΓöÇ Thß╗¡ parse to├án bß╗Ö nh╞░ 1 JSON object (multi-scene) ΓöÇΓöÇ
            # V├¡ dß╗Ñ: {"scene_1":{"prompt":"..."},"scene_2":{...}}
            if raw.startswith("{"):
                try:
                    obj = json.loads(raw)
                    # Nß║┐u c├│ key scene_* hoß║╖c key bß║Ñt kß╗│ chß╗⌐a dict vß╗¢i 'prompt'
                    scene_keys = sorted(
                        [k for k, v in obj.items() if isinstance(v, dict)],
                        key=lambda k: k  # sß║»p xß║┐p theo t├¬n key
                    )
                    if scene_keys:
                        for k in scene_keys:
                            scene = obj[k]
                            p, ar, dur, meta = VeoApp._parse_line(json.dumps(scene))
                            if p:
                                results.append((p, ar, dur, meta))
                        return results
                except (json.JSONDecodeError, TypeError):
                    pass  # fallback vß╗ü tß╗½ng d├▓ng

            # ΓöÇΓöÇ Mß╗ùi d├▓ng l├á 1 JSON object ΓöÇΓöÇ
            for line in raw.splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                p, ar, dur, meta = VeoApp._parse_line(line)
                if p:
                    results.append((p, ar, dur, meta))
            return results

        # mode == "normal": mß╗ùi d├▓ng l├á plain text (bß╗Å qua JSON parsing)
        for line in raw.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            results.append((line, "16:9", 8, {}))
        return results

    @staticmethod
    def _parse_line(line):
        """Parse 1 d├▓ng: JSON object hoß║╖c plain text.
        Trß║ú vß╗ü: (prompt_text, aspect_ratio, duration, extra_info)"""
        line = line.strip()
        if line.startswith("{"):
            try:
                obj = json.loads(line)
                # Nhß║¡n nhiß╗üu key alias th╞░ß╗¥ng gß║╖p
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
                    # Kh├┤ng t├¼m thß║Ñy key prompt ΓåÆ trß║ú vß╗ü raw line
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

                # item l├á tuple ─æ├ú parse: (prompt_text, aspect_ratio, duration, meta)
                prompt_text, aspect_ratio, duration, meta = item
                if not prompt_text:
                    self.log(f"   ΓÜá Prompt rß╗ùng tß║íi vß╗ï tr├¡ {i} ΓÇö bß╗Å qua")
                    continue

                self.log(f"\nΓöÇΓöÇ [{i}/{len(lines)}] {prompt_text[:70]}...")
                if meta:
                    self.log(f"   ≡ƒôî Ratio: {aspect_ratio} | Style: {meta.get('style','')}")

                delay_map = {"normal": 5, "double": 10, "random": None}
                d_val = delay_map.get(self.tv_delay.get(), 5)
                delay = d_val if d_val is not None else random.randint(6, 15)

                # ΓöÇΓöÇ Chß╗ë tß║ío project Mß╗ÿT Lß║ªN ─æß║ºu ti├¬n ΓöÇΓöÇ
                if i == 1:
                    self.log("≡ƒåò Lß║ºn ─æß║ºu: tß║ío project mß╗¢i...")
                    ok = self.bc.new_project()
                    if not ok:
                        self.log("Γ¥î Kh├┤ng tß║ío ─æ╞░ß╗úc project ΓÇö dß╗½ng")
                        break
                    time.sleep(2)
                else:
                    # C├íc prompt tiß║┐p theo: chß╗¥ ├┤ prompt sß║╡n s├áng rß╗ôi d├ín lu├┤n
                    self.log(f"Γ₧í∩╕Å Prompt tiß║┐p theo ({i}/{len(lines)}) ΓÇö giß╗» nguy├¬n project, chß╗¥ ├┤ nhß║¡p...")
                    ready = self.bc.wait_for_prompt_ready(timeout=30)
                    if not ready:
                        # Fallback: scroll xuß╗æng ─æß╗â thß╗¡ t├¼m ├┤ prompt
                        self.log("ΓÜá Kh├┤ng thß║Ñy ├┤ prompt ΓÇö thß╗¡ scroll xuß╗æng...")
                        try:
                            self.bc.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                            time.sleep(1.5)
                        except:
                            pass

                # Set tß╗╖ lß╗ç nß║┐u c├│ trong JSON (chß╗ë ─æß╗òi khi kh├íc prompt tr╞░ß╗¢c)
                if aspect_ratio and aspect_ratio != "16:9":
                    self.bc.set_aspect_ratio(aspect_ratio)

                ok = self.bc.set_prompt(prompt_text)
                if not ok:
                    self.log(f"   ΓÜá D├ín prompt thß║Ñt bß║íi, bß╗Å qua prompt {i}")
                    continue
                time.sleep(0.8)

                ok = self.bc.click_generate()
                if not ok: continue

                # Cß║¡p nhß║¡t trß║íng th├íi UI
                self.root.after(0, lambda i=i, t=len(lines): self.tv_status_lbl.config(
                    text=f"ΓÅ│ [{i}/{t}] ─Éang generate..."))

                timeout_val = int(self.tv_timeout.get())

                if timeout_val == 0:
                    # ΓÜí FAST MODE: kh├┤ng chß╗¥ video, d├ín prompt tiß║┐p ngay sau delay
                    self.log(f"   ΓÜí Fast mode ΓÇö kh├┤ng chß╗¥ video, chß╗¥ {delay}s rß╗ôi tiß║┐p...")
                else:
                    # Chß╗¥ video render xong rß╗ôi tß║úi
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
                            text=f"Γ£à ─É├ú tß║úi: {fn}"))
                    else:
                        self.log(f"   ΓÅ¡ Bß╗Å qua tß║úi ΓÇö chuyß╗ân prompt tiß║┐p")

                if i < len(lines):  # Kh├┤ng chß╗¥ sau prompt cuß╗æi
                    self.log(f"ΓÅ│ Chß╗¥ {delay}s rß╗ôi tiß║┐p...")
                    time.sleep(delay)

        finally:
            self.running = False
            self.root.after(0, self.tv_progress.stop)
            self.root.after(0, lambda: self.tv_status_lbl.config(text=""))
            self.log(f"\nΓ£à Ho├án tß║Ñt TextΓåÆVideo [{len(lines)} prompt]! Video ─æ├ú l╞░u tß║íi:\n   {out_dir}")

    def _stop(self):
        """Dß╗½ng worker ─æang chß║íy"""
        if self.running:
            self.running = False
            self.log("ΓÅ╣ ─É├ú gß╗¡i lß╗çnh dß╗½ng ΓÇö chß╗¥ b╞░ß╗¢c hiß╗çn tß║íi kß║┐t th├║c...")
        else:
            self.log("Γä╣∩╕Å Kh├┤ng c├│ tiß║┐n tr├¼nh n├áo ─æang chß║íy")

    def _start_rapid(self):
        """ΓÜí Rapid Mode: Submit tß║Ñt cß║ú nhanh ΓåÆ render song song tr├¬n cloud"""
        raw = self.tv_prompts.get("1.0", END).strip()
        if not raw:
            messagebox.showerror("Lß╗ùi", "Ch╞░a nhß║¡p prompt!")
            return
        if not self.bc.is_alive():
            messagebox.showerror("Lß╗ùi", "Ch╞░a mß╗ƒ Chrome!")
            return
        mode = self.tv_mode.get()
        parsed = self._parse_all_lines(raw, mode)
        if not parsed:
            messagebox.showerror("Lß╗ùi", "Kh├┤ng t├¼m thß║Ñy prompt hß╗úp lß╗ç!")
            return
        out_dir = self.tv_out.get()
        os.makedirs(out_dir, exist_ok=True)
        self.log(f"ΓÜí RAPID MODE [{mode}]: Submit {len(parsed)} prompt(s) nhanh ΓåÆ render song song!")
        self.nb.select(5)
        self._run_bg(lambda: self._rapid_worker(parsed, out_dir))

    def _rapid_worker(self, lines, out_dir):
        """Submit tß║Ñt cß║ú nhanh (30s/prompt), rß╗ôi monitor download folder"""
        self.running = True
        self.root.after(0, self.tv_progress.start)
        import random

        # ΓöÇΓöÇΓöÇ PHASE 1: Submit tß║Ñt cß║ú prompt nhanh ΓöÇΓöÇΓöÇ
        total = len(lines)
        submitted = 0
        try:
            for i, item in enumerate(lines, 1):
                if not self.running: break
                prompt_text, aspect_ratio, duration, meta = item
                if not prompt_text:
                    self.log(f"   ΓÜá Prompt rß╗ùng tß║íi vß╗ï tr├¡ {i} ΓÇö bß╗Å qua")
                    continue
                self.log(f"\nΓÜí [{i}/{total}] Submit: {prompt_text[:60]}...")
                self.root.after(0, lambda i=i, t=total: self.tv_status_lbl.config(
                    text=f"ΓÜí Submit {i}/{t} ΓÇö render song song tr├¬n cloud..."))

                ok = self.bc.new_project()
                if not ok: continue

                if aspect_ratio and aspect_ratio != "16:9":
                    self.bc.set_aspect_ratio(aspect_ratio)

                ok = self.bc.set_prompt(prompt_text)
                if not ok: continue

                ok = self.bc.click_generate()
                if ok:
                    submitted += 1
                    self.log(f"   Γ£à ─É├ú submit #{i}")
                else:
                    self.log(f"   ΓÜá Submit #{i} thß║Ñt bß║íi")

                # Chß╗¥ 30s giß╗»a c├íc prompt (─æß╗º ─æß╗â Flow nhß║¡n request)
                if i < total and self.running:
                    for _ in range(30):
                        if not self.running: break
                        time.sleep(1)

        except Exception as e:
            self.log(f"Γ¥î Submit error: {e}")

        self.log(f"\nΓÜí ─É├ú submit {submitted}/{total} prompt. Bß║»t ─æß║ºu monitor download...")
        self.root.after(0, lambda: self.tv_status_lbl.config(
            text=f"≡ƒôÑ ─Éang chß╗¥ {submitted} video tß╗½ cloud..."))

        # ΓöÇΓöÇΓöÇ PHASE 2: Monitor folder, ─æß╗òi t├¬n tuß║ºn tß╗▒ khi file vß╗ü ΓöÇΓöÇΓöÇ
        if submitted == 0:
            self.running = False
            self.root.after(0, self.tv_progress.stop)
            return

        snap = set(os.listdir(out_dir))
        base = self.tv_base.get()
        video_counter = 1
        # T├¡nh video_counter tiß║┐p theo (tr├ính ghi ─æ├¿ file c┼⌐)
        while os.path.exists(os.path.join(out_dir, f"{base}_{video_counter:02d}.mp4")):
            video_counter += 1

        deadline = time.time() + submitted * 600  # 10 ph├║t/video tß╗æi ─æa
        found = 0
        prev_size_map = {}  # {filename: size}

        while time.time() < deadline and found < submitted and self.running:
            time.sleep(3)
            try:
                current = set(os.listdir(out_dir))
                added = current - snap
                # Chß╗ë lß║Ñy file .mp4 mß╗¢i (kh├┤ng phß║úi .crdownload)
                new_mp4s = sorted([f for f in added
                                   if f.endswith(".mp4") and not f.endswith(".crdownload")])
                for fname in new_mp4s:
                    src = os.path.join(out_dir, fname)
                    # Chß╗¥ file ß╗òn ─æß╗ïnh
                    sz = os.path.getsize(src) if os.path.exists(src) else 0
                    if prev_size_map.get(fname) == sz and sz > 0:
                        # File ß╗òn ─æß╗ïnh ΓåÆ ─æß╗òi t├¬n theo thß╗⌐ tß╗▒
                        dst_name = f"{base}_{video_counter:02d}.mp4"
                        dst = os.path.join(out_dir, dst_name)
                        if not os.path.exists(dst):
                            shutil.move(src, dst)
                            sz_mb = os.path.getsize(dst) / 1024 / 1024
                            self.log(f"Γ£à Tß║úi vß╗ü #{video_counter}: {dst_name} ({sz_mb:.1f} MB)")
                            snap.add(dst_name)  # tr├ính detect lß║íi
                            video_counter += 1
                            found += 1
                            self.root.after(0, lambda f=found, s=submitted:
                                self.tv_status_lbl.config(text=f"≡ƒôÑ ─É├ú nhß║¡n {f}/{s} video"))
                    else:
                        prev_size_map[fname] = sz
            except Exception as e:
                self.log(f"ΓÜá Monitor: {e}")

        self.running = False
        self.root.after(0, self.tv_progress.stop)
        self.root.after(0, lambda: self.tv_status_lbl.config(text=""))
        self.log(f"\nΓ£à RAPID xong! Nhß║¡n {found}/{submitted} video ΓåÆ {out_dir}")

    # ΓöÇΓöÇ TAB 4: Nh├ón Vß║¡t ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _tab_char_setup(self):
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="≡ƒæñ  Nh├ón Vß║¡t")

        # H╞░ß╗¢ng dß║½n
        guide = self._card(f, "≡ƒôï H╞░ß╗¢ng dß║½n")
        guide.pack(fill=X, padx=12, pady=(10,5))
        Label(guide, text=(
            "1. Chon anh nhan vat -> chon nhieu anh (khong gioi han)\n"
            "2. Dat ten ngan gon cho tung nhan vat  (VD: Alice, Bob, NhanVat1)\n"
            "3. Bam Upload tat ca len Flow - tool tu upload theo thu tu\n"
            "4. Sang tab Tao Video de generate video co nhan vat"
        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT
        ).pack(anchor=W, padx=10, pady=8)

        # Danh s├ích nh├ón vß║¡t
        list_lf = self._card(f, "≡ƒôé Danh s├ích nh├ón vß║¡t  (t├¬n: ─æ╞░ß╗¥ng dß║½n ß║únh)")
        list_lf.pack(fill=BOTH, expand=True, padx=12, pady=5)
        self.char_list = scrolledtext.ScrolledText(
            list_lf, height=9, font=("Consolas", 9), state=DISABLED,
            bg="#0D1117", fg=TEXT, relief="flat")
        self.char_list.pack(fill=BOTH, expand=True, padx=4, pady=4)

        # N├║t thao t├íc
        btn_f = Frame(f, bg=BG); btn_f.pack(fill=X, padx=12, pady=6)
        self._btn(btn_f, "  ≡ƒôü  Chß╗ìn ß║únh nh├ón vß║¡t (nhiß╗üu ß║únh)",
                  self._choose_char_images, color=ACCENT
                  ).pack(side=LEFT, fill=X, expand=True, ipady=8, padx=(0,4))
        self._btn(btn_f, "  Γ¼å∩╕Å  Upload tß║Ñt cß║ú l├¬n Flow",
                  self._upload_chars, color=GREEN
                  ).pack(side=LEFT, fill=X, expand=True, ipady=8, padx=(0,4))
        self._btn(btn_f, "  ≡ƒùæ  X├│a hß║┐t",
                  self._clear_chars, color="#444C56"
                  ).pack(side=LEFT, ipady=8, ipadx=6)

        # Progress upload
        up_f = self._card(f, "≡ƒôñ Tiß║┐n ─æß╗Ö upload")
        up_f.pack(fill=X, padx=12, pady=5)
        self.char_progress = ttk.Progressbar(up_f, mode="determinate", style="TProgressbar")
        self.char_progress.pack(fill=X, padx=8, pady=(6,2))
        self.char_status_lbl = Label(up_f, text="Ch╞░a upload",
                                     font=("Segoe UI", 9), bg=CARD, fg=MUTED)
        self.char_status_lbl.pack(pady=(0,6))

    def _choose_char_images(self):
        paths = filedialog.askopenfilenames(
            title="Chß╗ìn ß║únh nh├ón vß║¡t",
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
        self.log(f"Γ£à ─É├ú th├¬m {added} nh├ón vß║¡t. Tß╗òng: {len(self.characters)} ΓÇö {', '.join(self.characters.keys())}")


    def _ask_name(self, default=""):
        """Dialog nhß║¡p t├¬n + m├┤ tß║ú ngoß║íi h├¼nh + b├¡ danh nh├ón vß║¡t."""
        dlg = Toplevel(self.root)
        dlg.title("─Éß║╖t t├¬n nh├ón vß║¡t")
        dlg.geometry("480x280")
        dlg.configure(bg=BG)
        dlg.grab_set()

        Label(dlg, text=f"  ß║ónh: {default[:50]}",
              font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(pady=(10,4), anchor=W, padx=12)

        Label(dlg, text="T├¬n nh├ón vß║¡t  (bß║»t buß╗Öc ΓÇö duyß║Ñt, ngß║»n):",
              font=("Segoe UI", 9, "bold"), bg=BG, fg=TEXT).pack(anchor=W, padx=12)
        name_var = StringVar(value=default)
        Entry(dlg, textvariable=name_var, width=36,
              font=("Segoe UI", 11), bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat"
              ).pack(padx=12, pady=(2,8), ipady=4, fill=X)

        Label(dlg, text="M├┤ tß║ú ngoß║íi h├¼nh  (tiß║┐ng Anh ΓÇö gi├║p AI nhß╗¢ nh├ón vß║¡t):",
              font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(anchor=W, padx=12)
        Label(dlg, text="   VD: tall woman, red hair, blue eyes, white dress",
              font=("Segoe UI", 8), bg=BG, fg=MUTED).pack(anchor=W, padx=12)
        desc_var = StringVar()
        Entry(dlg, textvariable=desc_var, width=54,
              font=("Segoe UI", 10), bg=CARD, fg=TEXT, insertbackground=TEXT, relief="flat"
              ).pack(padx=12, pady=(2,8), ipady=3, fill=X)

        Label(dlg, text="B├¡ danh  (ng─ân c├ích dß║Ñu phß║⌐y ΓÇö t├╣y chß╗ìn):",
              font=("Segoe UI", 9), bg=BG, fg=MUTED).pack(anchor=W, padx=12)
        Label(dlg, text="   VD: c├┤ ß║Ñy, she, her, c├┤ g├íi",
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
        return result[0]  # None = bß╗Å qua, dict nß║┐u c├│ th├┤ng tin

    def _refresh_char_list(self):
        """Cß║¡p nhß║¡t bß║úng danh s├ích nh├ón vß║¡t trong tab Nh├ón Vß║¡t."""
        self.char_list.config(state=NORMAL)
        self.char_list.delete("1.0", END)
        for i, (name, info) in enumerate(self.characters.items(), 1):
            path = info["path"] if isinstance(info, dict) else info
            desc = info.get("desc", "") if isinstance(info, dict) else ""
            aliases = info.get("aliases", []) if isinstance(info, dict) else []
            line = f"#{i} [{name}]  ß║únh: {Path(path).name}"
            if desc:
                line += f"\n     m├┤ tß║ú: {desc}"
            if aliases:
                line += f"\n     b├¡ danh: {', '.join(aliases)}"
            self.char_list.insert(END, line + "\n\n")
        self.char_list.config(state=DISABLED)

    def _refresh_char_display(self):
        """Cß║¡p nhß║¡t nh├ún hiß╗ân thß╗ï nh├ón vß║¡t ß╗ƒ tab Tß║ío Video."""
        if not hasattr(self, 'cv_char_display'): return
        if not self.characters:
            self.cv_char_display.config(
                text="Ch╞░a c├│ nh├ón vß║¡t. V├áo tab 'Nh├ón Vß║¡t' ─æß╗â thiß║┐t lß║¡p tr╞░ß╗¢c."
            )
            return
        lines = []
        for i, (name, info) in enumerate(self.characters.items(), 1):
            desc = info.get("desc", "") if isinstance(info, dict) else ""
            tag = f"{i}. [{name}]" + (f" ΓÇö {desc[:40]}" if desc else "")
            lines.append(tag)
        self.cv_char_display.config(text="\n".join(lines))

    @staticmethod
    def _detect_characters(prompt, characters):
        """Ph├ít hiß╗çn nh├ón vß║¡t xuß║Ñt hiß╗çn trong prompt.
        Hß╗ù trß╗ú: tag [Alice], [ALL], [Tß║ñT Cß║ó], t├¬n ch├¡nh, alias.
        Trß║ú vß╗ü list [(name, char_info)] theo thß╗⌐ tß╗▒.
        """
        import re
        prompt_lower = prompt.lower()

        # ΓöÇΓöÇ Nhß║¡n c├║ ph├íp tag [Ten], [Ten, Ten2] ΓöÇΓöÇ
        tag_match = re.search(r'\[([^\]]+)\]', prompt)
        if tag_match:
            tag_content = tag_match.group(1).strip()
            if tag_content.lower() in ("all", "tß║Ñt cß║ú", "tatca", "tat_ca"):
                return list(characters.items())  # tß║Ñt cß║ú
            tag_names = [t.strip() for t in tag_content.split(",")]
            result = []
            for tn in tag_names:
                for name, info in characters.items():
                    if name.lower() == tn.lower():
                        result.append((name, info))
                        break
            if result:
                return result

        # ΓöÇΓöÇ T├¼m theo t├¬n ch├¡nh (word-boundary match) ΓöÇΓöÇ
        found = []
        for name, info in characters.items():
            # Tho├ít k├╜ tß╗▒ regex trong t├¬n
            pattern = r'(?<![\w\u00C0-\u024F])' + re.escape(name) + r'(?![\w\u00C0-\u024F])'
            if re.search(pattern, prompt, re.IGNORECASE):
                found.append((name, info))
                continue
            # Kiß╗âm tra aliases
            aliases = info.get("aliases", []) if isinstance(info, dict) else []
            for alias in aliases:
                ap = r'(?<![\w\u00C0-\u024F])' + re.escape(alias) + r'(?![\w\u00C0-\u024F])'
                if re.search(ap, prompt, re.IGNORECASE):
                    found.append((name, info))
                    break
        return found

    @staticmethod
    def _build_prompt_with_chars(prompt, detected_chars):
        """Inject m├┤ tß║ú ngoß║íi h├¼nh nh├ón vß║¡t v├áo prompt.
        VD: 'Alice standing on beach' -> 'Alice (tall woman, red hair) standing on beach'
        """
        import re
        result = prompt
        for name, info in detected_chars:
            desc = info.get("desc", "") if isinstance(info, dict) else ""
            if not desc:
                continue
            # Lß║ºn l╞░ß╗út 1: t├¼m t├¬n v├á th├¬m m├┤ tß║ú sau (chß╗ë lß║ºn xuß║Ñt hiß╗çn ─æß║ºu ti├¬n)
            pattern = r'(?<![\w\u00C0-\u024F])(' + re.escape(name) + r')(?![\w\u00C0-\u024F])'
            replacement = fr'\1 ({desc})'
            # Chß╗ë inject lß║ºn ─æß║ºu ti├¬n (─æß╗â kh├┤ng lß║╖p lß║íi nhiß╗üu lß║ºn)
            result = re.sub(pattern, replacement, result, count=1, flags=re.IGNORECASE)
        # X├│a tag [Ten] khß╗Åi prompt gß╗¡i ─æi
        result = re.sub(r'\[[^\]]+\]\s*', '', result).strip()
        return result

    def _clear_chars(self):
        self.characters.clear()
        self.char_list.config(state=NORMAL)
        self.char_list.delete("1.0", END)
        self.char_list.config(state=DISABLED)

    def _upload_chars(self):
        if not self.characters:
            messagebox.showerror("Lß╗ùi", "Ch╞░a chß╗ìn ß║únh nh├ón vß║¡t!")
            return
        if not self.bc.is_alive():
            messagebox.showerror("Lß╗ùi", "Ch╞░a mß╗ƒ Chrome!")
            return
        self._run_bg(self._upload_chars_worker)

    def _upload_chars_worker(self):
        names = list(self.characters.keys())
        total = len(names)
        self.root.after(0, lambda: self.char_progress.config(maximum=total, value=0))
        self.log(f"≡ƒôñ Bß║»t ─æß║ºu upload {total} ß║únh nh├ón vß║¡t...")
        ok_count = 0
        for i, name in enumerate(names, 1):
            char_info = self.characters[name]
            # Hß╗ù trß╗ú cß║ú 2 dß║íng: dict mß╗¢i v├á str c┼⌐
            path = char_info["path"] if isinstance(char_info, dict) else char_info
            desc = char_info.get("desc", "") if isinstance(char_info, dict) else ""
            self.log(f"≡ƒôñ Upload [{i}/{total}]: {name}{' (' + desc[:30] + ')' if desc else ''} ΓÇö ({Path(path).name})")
            self.root.after(0, lambda l=f"Uploading {name}... ({i}/{total})": self.char_status_lbl.config(text=l))
            ok = self.bc.upload_image(path)
            if ok:
                ok_count += 1
            self.root.after(0, lambda v=i: self.char_progress.config(value=v))
            time.sleep(1.5)
        msg = f"Γ£à Upload xong {ok_count}/{total} nh├ón vß║¡t!"
        self.root.after(0, lambda: self.char_status_lbl.config(text=msg))
        self.log(msg)

    # ΓöÇΓöÇ TAB 5: Tß║ío Video Nh├ón Vß║¡t ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _tab_create_video(self):
        outer, f = self._scrollable_frame(self.nb)
        self.nb.add(outer, text="≡ƒÄ₧∩╕Å  Tß║ío Video")

        # H╞░ß╗¢ng dß║½n
        guide = self._card(f, "≡ƒôï H╞░ß╗¢ng dß║½n")
        guide.pack(fill=X, padx=12, pady=(10,4))
        Label(guide, text=(
            "1. Nhap danh sach prompt (moi dong 1 canh)\n"
            "2. Bam START -> Tool tu dong upload anh nhan vat + generate tung video\n"
            "Luu y: Prompt co ten nhan vat -> chen dung anh do | Khong co ten -> upload tat ca"
        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT
        ).pack(anchor=W, padx=10, pady=6)

        # Hiß╗ân thß╗ï nh├ón vß║¡t ─æ├ú setup
        cv_char = self._card(f, "≡ƒæñ Nh├ón vß║¡t ─æ├ú thiß║┐t lß║¡p")
        cv_char.pack(fill=X, padx=12, pady=4)
        self.cv_char_display = Label(cv_char,
                                     text="Ch╞░a c├│ nh├ón vß║¡t. V├áo tab 'Nh├ón Vß║¡t' ─æß╗â thiß║┐t lß║¡p tr╞░ß╗¢c.",
                                     font=("Segoe UI", 9), bg=CARD, fg=MUTED)
        self.cv_char_display.pack(anchor=W, padx=10, pady=6)

        # Prompts
        lf = self._card(f, "≡ƒô¥ Danh s├ích Prompt  (mß╗ùi d├▓ng 1 cß║únh)")
        lf.pack(fill=BOTH, expand=True, padx=12, pady=4)
        mode_f = Frame(lf, bg=CARD); mode_f.pack(anchor=W, pady=(4,2))
        Label(mode_f, text="─Éß╗ïnh dß║íng: ", bg=CARD, fg=MUTED,
              font=("Segoe UI", 9)).pack(side=LEFT)
        self.cv_mode = StringVar(value="normal")
        for txt, val in [("Th├┤ng th╞░ß╗¥ng", "normal"),
                          ("JSON n├óng cao (scene_1, scene_2...)", "json")]:
            Radiobutton(mode_f, text=txt, variable=self.cv_mode, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=6)
        self.cv_prompts = scrolledtext.ScrolledText(
            lf, height=7, font=("Consolas", 9),
            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.cv_prompts.pack(fill=BOTH, expand=True, pady=(2,6))
        self.cv_prompts.insert(END, "Alice v├á Bob ─æang ─æi dß║ío trong c├┤ng vi├¬n\nCharlie ─æang chß║íy tr├¬n b├úi biß╗ân")

        # Settings
        sf = self._card(f, "ΓÜÖ∩╕Å C├ái ─æß║╖t ─æß║ºu ra")
        sf.pack(fill=X, padx=12, pady=4)
        r1 = Frame(sf, bg=CARD); r1.pack(fill=X, pady=3, padx=8)
        Label(r1, text="T├¬n file:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.cv_base = Entry(r1, width=20, font=("Segoe UI", 9),
                             bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.cv_base.insert(0, "character_video")
        self.cv_base.pack(side=LEFT, padx=6, ipady=3)
        r2 = Frame(sf, bg=CARD); r2.pack(fill=X, pady=3, padx=8)
        Label(r2, text="L╞░u tß║íi:", bg=CARD, fg=MUTED, font=("Segoe UI", 9)).pack(side=LEFT)
        self.cv_out = Entry(r2, width=55, font=("Segoe UI", 9),
                            bg="#0D1117", fg=TEXT, insertbackground=TEXT, relief="flat")
        self.cv_out.insert(0, OUTPUT_DIR_CHAR)
        self.cv_out.pack(side=LEFT, padx=6, ipady=3)
        self._btn(r2, "≡ƒôé", lambda: self._browse(self.cv_out),
                  color="#21262D").pack(side=LEFT, ipady=3, ipadx=4)

        # Delay
        df = self._card(f, "ΓÅ▒ ─Éß╗Ö trß╗à giß╗»a c├íc prompt")
        df.pack(fill=X, padx=12, pady=4)
        df_r = Frame(df, bg=CARD); df_r.pack(anchor=W, padx=8, pady=4)
        self.cv_delay = StringVar(value="normal")
        for txt, val in [("B├¼nh th╞░ß╗¥ng (5s)", "normal"),
                          ("Gß║Ñp ─æ├┤i (10s)", "double"),
                          ("Ngß║½u nhi├¬n (6-15s)", "random")]:
            Radiobutton(df_r, text=txt, variable=self.cv_delay, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(side=LEFT, padx=8)

        # Timeout chß╗¥ video + tß║úi tß╗▒ ─æß╗Öng
        tf = self._card(f, "Γ¼ç∩╕Å Chß╗¥ video xong ΓåÆ Tß╗▒ ─æß╗Öng tß║úi (tho├ít sß╗¢m khi xong)")
        tf.pack(fill=X, padx=12, pady=4)
        self.cv_timeout = StringVar(value="600")
        cv_opts = [
            ("Tß╗░ ─Éß╗ÿNG ΓÇö Chß╗¥ ─æß║┐n khi xong (tß╗æi ─æa 10 ph├║t)  Γ¼ç∩╕Å  Tß║úi ngay", "600"),
            ("Tß╗æi ─æa 5 ph├║t  Γ¼ç∩╕Å  Tß║úi ngay khi xong", "300"),
            ("Tß╗æi ─æa 3 ph├║t  Γ¼ç∩╕Å  Tß║úi ngay khi xong", "180"),
            ("30 gi├óy  (submit nhanh, kh├┤ng tß║úi vß╗ü)", "30"),
        ]
        for txt, val in cv_opts:
            Radiobutton(tf, text=txt, variable=self.cv_timeout, value=val,
                        bg=CARD, fg=TEXT, selectcolor=BG,
                        activebackground=CARD, font=("Segoe UI", 9)
                        ).pack(anchor=W, padx=12)
        Label(tf, text="  Γä╣∩╕Å  Tool tho├ít ngay khi video xong!",
              font=("Segoe UI", 8), bg=CARD, fg=MUTED).pack(anchor=W, padx=20, pady=(0,4))

        self.cv_progress = ttk.Progressbar(f, mode="indeterminate", style="TProgressbar")
        self.cv_progress.pack(fill=X, padx=12, pady=(6,2))
        self.cv_status_lbl = Label(f, text="", font=("Segoe UI", 8), bg=BG, fg=MUTED)
        self.cv_status_lbl.pack()

        btn_f = Frame(f, bg=BG); btn_f.pack(fill=X, padx=12, pady=8)
        self._btn(btn_f, "  Γû╢  START ΓÇö Tß║ío video + Tß╗▒ ─æß╗Öng tß║úi",
                  self._start_create_video, color=GREEN
                  ).pack(side=LEFT, fill=X, expand=True, ipady=9, padx=(0,4))
        self._btn(btn_f, "≡ƒº¬ TEST: Chß╗ë chß╗ìn ß║únh (kh├┤ng submit)",
                  self._test_char_select, color="#1B4721"
                  ).pack(side=LEFT, ipady=9, padx=(0,4))
        self._btn(btn_f, "ΓÅ╣ STOP", self._stop, color=RED
                  ).pack(side=LEFT, ipady=9, ipadx=6)

        # Cß║¡p nhß║¡t hiß╗ân thß╗ï nh├ón vß║¡t khi chuyß╗ân tab
        self.nb.bind("<<NotebookTabChanged>>", self._on_tab_change)

    def _refresh_char_display(self):
        """Cß║¡p nhß║¡t label nh├ón vß║¡t trong Create Video tab"""
        if self.characters:
            names = ", ".join(self.characters.keys())
            self.cv_char_display.config(
                text=f"Γ£à {len(self.characters)} nh├ón vß║¡t: {names}\n"
                     f"   ΓåÆ Tß║ñT Cß║ó ß║únh sß║╜ ─æ╞░ß╗úc upload v├áo mß╗ùi video",
                fg="green"
            )
        else:
            self.cv_char_display.config(
                text="Ch╞░a c├│ nh├ón vß║¡t. Setup trong tab 'Character Setup' tr╞░ß╗¢c.", fg="gray"
            )

    def _on_tab_change(self, evt):
        idx = self.nb.index(self.nb.select())
        if idx == 4:  # Create Video tab
            self._refresh_char_display()

    def _start_create_video(self):
        raw = self.cv_prompts.get("1.0", END).strip()
        prompts = [l.strip() for l in raw.splitlines() if l.strip() and not l.startswith("#")]
        if not prompts:
            messagebox.showerror("Lß╗ùi", "Ch╞░a nhß║¡p prompt!")
            return
        if not self.bc.is_alive():
            messagebox.showerror("Lß╗ùi", "Ch╞░a mß╗ƒ Chrome!")
            return
        out_dir = self.cv_out.get()
        os.makedirs(out_dir, exist_ok=True)
        self.log(f"≡ƒÜÇ Create Video: {len(prompts)} prompt(s), {len(self.characters)} nh├ón vß║¡t")
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

                # ΓöÇΓöÇ Detect nh├ón vß║¡t th├┤ng minh (tag, t├¬n, alias) ΓöÇΓöÇ
                detected = self._detect_characters(prompt, self.characters)
                to_upload = detected if detected else list(self.characters.items())

                # ΓöÇΓöÇ Build prompt c├│ inject m├┤ tß║ú nh├ón vß║¡t ΓöÇΓöÇ
                final_prompt = self._build_prompt_with_chars(prompt, detected)

                if to_upload:
                    self.log(f"\nΓöÇΓöÇ [{i}/{len(prompts)}] {final_prompt[:70]}...")
                    char_names = [n for n, _ in to_upload]
                    mode = 'tag/detect' if detected else 'tß║Ñt cß║ú'
                    self.log(f"   ≡ƒæñ Nh├ón vß║¡t [{mode}]: {', '.join(char_names)}")
                    if final_prompt != prompt:
                        self.log(f"   Γ£¿ Prompt vß╗¢i m├┤ tß║ú: {final_prompt[:80]}...")
                else:
                    self.log(f"\nΓöÇΓöÇ [{i}/{len(prompts)}] {final_prompt[:70]}...")
                    self.log(f"   ΓÜá Kh├┤ng c├│ nh├ón vß║¡t n├áo ─æ╞░ß╗úc thiß║┐t lß║¡p")

                ok = self.bc.new_project()
                if not ok: continue
                time.sleep(2)

                # Upload ß║únh nh├ón vß║¡t (theo thß╗⌐ tß╗▒ order nß║┐u c├│)
                sorted_upload = sorted(
                    to_upload,
                    key=lambda x: x[1].get("order", 0) if isinstance(x[1], dict) else 0
                )
                for name, char_info in sorted_upload:
                    path = char_info["path"] if isinstance(char_info, dict) else char_info
                    self.log(f"   ≡ƒôñ Upload ß║únh {name}...")
                    self.bc.upload_image(path)
                    time.sleep(0.5)

                # ─É├│ng panel media nß║┐u ─æang mß╗ƒ
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
                    self.log(f"   ΓÅ¼∩╕Å Tß║úi vß╗ü: {fname}")
                    self.root.after(0, lambda fi=fname: self.cv_status_lbl.config(
                        text=f"ΓÅ¼∩╕Å ─Éang tß║úi {fi}..."))
                    self.bc.click_download(out_dir, fname)
                    self.root.after(0, lambda fi=fname: self.cv_status_lbl.config(
                        text=f"Γ£à Tß║úi xong: {fi}"))
                else:
                    self.log(f"   ΓÅ¡ Bß╗Å qua tß║úi ΓÇö hß║┐t timeout ({self.cv_timeout.get()}s)")

                if i < len(prompts):  # Kh├┤ng chß╗¥ sau prompt cuß╗æi
                    d = delay_map.get(self.cv_delay.get(), 5)
                    d = d if d else random.randint(6, 15)
                    self.log(f"ΓÅ│ Chß╗¥ {d}s rß╗ôi sang prompt tiß║┐p...")
                    time.sleep(d)
        finally:
            self.running = False
            self.root.after(0, self.cv_progress.stop)
            self.root.after(0, lambda: self.cv_status_lbl.config(text=""))
            self.log(f"\nΓ£à Ho├án tß║Ñt Create Video [{len(prompts)} canh]! Video ─æ├ú l╞░u tß║íi:\n   {out_dir}")

    def _test_char_select(self):
        """Test: chß╗ë upload ß║únh, kh├┤ng generate"""
        if not self.characters:
            messagebox.showinfo("Test", "Ch╞░a c├│ nh├ón vß║¡t trong Character Setup!")
            return
        raw = self.cv_prompts.get("1.0", END)
        for name, path in self.characters.items():
            if name.lower() in raw.lower():
                self.log(f"≡ƒº¬ TEST: Sß║╜ upload ß║únh '{name}' tß╗½ {path}")
        messagebox.showinfo("Test OK", f"Detect {len(self.characters)} nh├ón vß║¡t. Xem log ─æß╗â biß║┐t chi tiß║┐t.")

    # ΓöÇΓöÇ TAB 6: Logs ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _tab_logs(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="≡ƒôï  Logs")

        btn_f = Frame(f, bg=BG); btn_f.pack(fill=X, padx=10, pady=6)
        self._btn(btn_f, "≡ƒùæ X├│a log", lambda: (
            self.log_text.config(state=NORMAL),
            self.log_text.delete("1.0", END),
            self.log_text.config(state=DISABLED)
        ), color="#21262D").pack(side=LEFT, ipady=5, padx=(0,4))
        self._btn(btn_f, "ΓÅ╣ Dß╗½ng tiß║┐n tr├¼nh",
                  lambda: setattr(self, "running", False),
                  color=RED).pack(side=LEFT, ipady=5, padx=(0,4))
        self._btn(btn_f, "≡ƒÆ╛ L╞░u log ra file TXT",
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
            self.log(f"Γ£à ─É├ú l╞░u log: {p}")

    # ΓöÇΓöÇ TAB 7: Gh├⌐p Video ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _tab_merge(self):
        f = Frame(self.nb, bg=BG)
        self.nb.add(f, text="≡ƒÄ¼  Gh├⌐p Video")

        hf = Frame(f, bg="#0A0F1A"); hf.pack(fill=X)
        Label(hf, text="≡ƒÄ¼  Gh├⌐p nhiß╗üu video th├ánh 1 file",
              font=("Segoe UI", 12, "bold"), bg="#0A0F1A", fg=ACCENT
              ).pack(anchor=W, padx=16, pady=10)
        Label(hf, text="Y├¬u cß║ºu: FFmpeg ─æ├ú c├ái trong PATH  |  Tß║úi tß║íi: ffmpeg.org",
              font=("Segoe UI", 9), bg="#0A0F1A", fg=MUTED).pack(anchor=W, padx=16, pady=(0,10))

        info = self._card(f, "Γä╣∩╕Å Th├┤ng tin c├┤ng cß╗Ñ")
        info.pack(fill=X, padx=12, pady=(10,5))
        Label(info, text=(
            "ΓÇó Gh├⌐p c├íc file MP4 trong mß╗Öt th╞░ mß╗Ñc th├ánh 1 video duy nhß║Ñt\n"
            "ΓÇó Sß║»p xß║┐p theo t├¬n file (video_01, video_02, ...)\n"
            "ΓÇó Sß╗¡ dß╗Ñng FFmpeg concat ΓÇö giß╗» nguy├¬n chß║Ñt l╞░ß╗úng gß╗æc (kh├┤ng re-encode)"
        ), bg=CARD, fg=TEXT, font=("Segoe UI", 9), justify=LEFT).pack(anchor=W, padx=10, pady=8)

        self._btn(f, "  Γû╢  Mß╗₧ C├öNG Cß╗ñ GH├ëP VIDEO",
                  self._open_merger_window, color=GREEN
                  ).pack(pady=16, ipady=10, ipadx=30)

    def _open_merger_window(self):
        win = Toplevel(self.root)
        win.title("Video Merger Tool")
        win.geometry("560x480")
        win.resizable(False, False)
        win.configure(bg=BG)

        Label(win, text="≡ƒÄ¼ GH├ëP VIDEO TOOL", bg=BG, fg=ACCENT, font=("Segoe UI", 13, "bold")).pack(pady=10)

        # Chß╗ìn folder
        f1 = LabelFrame(win, text="Chß╗ìn Folder Chß╗⌐a Video", padx=8, pady=5)
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
        Button(fr, text="Chß╗ìn Folder", bg=ACCENT, fg="white",
               command=browse_folder).pack(side=LEFT)

        # Danh s├ích video
        f2 = LabelFrame(win, text="Danh S├ích Video", padx=8, pady=5)
        f2.pack(fill=BOTH, expand=True, padx=15, pady=4)
        vid_list = scrolledtext.ScrolledText(f2, height=8, font=("Consolas", 9), state=DISABLED)
        vid_list.pack(fill=BOTH, expand=True)

        # Output
        f3 = LabelFrame(win, text="N╞íi L╞░u File & T├¬n Output", padx=8, pady=5)
        f3.pack(fill=X, padx=15, pady=4)
        r = Frame(f3); r.pack(fill=X)
        Label(r, text="L╞░u v├áo:").pack(side=LEFT)
        out_dir_var = StringVar()
        Entry(r, textvariable=out_dir_var, width=36).pack(side=LEFT, padx=4)
        Button(r, text="Chß╗ìn", command=lambda: out_dir_var.set(filedialog.askdirectory() or out_dir_var.get())
               ).pack(side=LEFT, bg=ACCENT, fg="white")
        r2 = Frame(f3); r2.pack(fill=X, pady=3)
        Label(r2, text="T├¬n file:").pack(side=LEFT)
        fname_var = StringVar(value="video_ghep.mp4")
        Entry(r2, textvariable=fname_var, width=30).pack(side=LEFT, padx=4)

        # Progress
        m_prog = ttk.Progressbar(win, mode="indeterminate")
        m_prog.pack(fill=X, padx=15, pady=4)
        m_status = Label(win, text="Vui l├▓ng chß╗ìn folder chß╗⌐a video")
        m_status.pack()

        def do_merge():
            folder = folder_var.get()
            if not folder:
                messagebox.showerror("Lß╗ùi", "Ch╞░a chß╗ìn folder!")
                return
            out_d = out_dir_var.get() or folder
            fname = fname_var.get() or "video_ghep.mp4"
            out_path = str(Path(out_d) / fname)

            vids = sorted(Path(folder).glob("*.mp4"))
            if not vids:
                messagebox.showerror("Lß╗ùi", "Kh├┤ng c├│ file MP4 trong folder!")
                return

            list_file = str(Path(folder) / "_merge_list.txt")
            with open(list_file, "w", encoding="utf-8") as lf:
                for v in vids:
                    lf.write(f"file '{v}'\n")

            m_prog.start()
            m_status.config(text=f"─Éang gh├⌐p {len(vids)} video...")

            def run():
                try:
                    cmd = ["ffmpeg", "-y", "-f", "concat", "-safe", "0",
                           "-i", list_file, "-c", "copy", out_path]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
                    if res.returncode == 0:
                        win.after(0, lambda: m_prog.stop())
                        win.after(0, lambda: m_status.config(text=f"Γ£à Xong! ΓåÆ {out_path}"))
                        win.after(0, lambda: messagebox.showinfo("Γ£à Done", f"Gh├⌐p xong!\n{out_path}"))
                    else:
                        err = res.stderr[:500]
                        win.after(0, lambda: m_prog.stop())
                        win.after(0, lambda: m_status.config(text="Γ¥î Lß╗ùi FFmpeg"))
                        win.after(0, lambda: messagebox.showerror("Lß╗ùi", f"FFmpeg error:\n{err}"))
                except FileNotFoundError:
                    win.after(0, lambda: m_prog.stop())
                    win.after(0, lambda: m_status.config(text="Γ¥î FFmpeg kh├┤ng c├│ trong PATH"))
                    win.after(0, lambda: messagebox.showerror("Lß╗ùi", "FFmpeg ch╞░a ─æ╞░ß╗úc c├ái!\nTß║úi tß║íi: https://ffmpeg.org"))
                except Exception as e:
                    _e = str(e)
                    win.after(0, lambda: m_prog.stop())
                    win.after(0, lambda: m_status.config(text=f"Γ¥î {_e}"))
            threading.Thread(target=run, daemon=True).start()

        Button(win, text="Γû╢ GH├ëP VIDEO", bg=GREEN, fg="white",
               font=("Segoe UI", 11, "bold"), command=do_merge
               ).pack(fill=X, padx=15, pady=8, ipady=8)

    # ΓöÇΓöÇΓöÇ HELPERS ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    def _browse(self, entry_widget):
        d = filedialog.askdirectory()
        if d:
            entry_widget.delete(0, END)
            entry_widget.insert(0, d)

    def _run_bg(self, fn):
        """Chß║íy fn trong background thread, bß║úo vß╗ç double-start"""
        if self.running:
            self.log("ΓÜá ─Éang chß║íy rß╗ôi ΓÇö chß╗¥ ho├án tß║Ñt tr╞░ß╗¢c!")
            return
        threading.Thread(target=fn, daemon=True).start()


# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
# ENTRY POINT
# ΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉΓòÉ
if __name__ == "__main__":
    # C├ái dependencies nß║┐u thiß║┐u
    if not HAS_SELENIUM:
        print("≡ƒôª C├ái selenium + webdriver-manager...")
        os.system("pip install selenium webdriver-manager -q")
        print("Γ£à Xong! Vui l├▓ng chß║íy lß║íi.")
        sys.exit(0)

    root = Tk()
    app = VeoApp(root)
    root.protocol("WM_DELETE_WINDOW", root.quit)
    root.mainloop()
