# -*- coding: utf-8 -*-
"""
Veo 3 — License Module (Offline Machine-Bound)
Xác thực key gắn với phần cứng máy, hết hạn theo thời gian.
Không dùng JWT, không cần internet.
"""

import hashlib, hmac, os, platform, subprocess, uuid, json
from datetime import datetime, timedelta
from pathlib import Path

# ── FIX #1: Obfuscate SECRET — không lưu plaintext ──
# Chia nhỏ thành mảng byte, khó decompile hơn
_S = [86,51,111,95,70,108,48,119,95,50,48,50,54,
      95,36,101,99,114,51,116,95,75,51,121,33,64,35,120,90,57]
_SECRET = bytes(_S)

# Nơi lưu file
LICENSE_DIR = Path.home() / ".veo3"
LICENSE_FILE = LICENSE_DIR / "license.key"
TIMESTAMP_FILE = LICENSE_DIR / "license.ts"  # FIX #3: chống đổi ngày


# ════════════════════════════════════════════
#  MACHINE FINGERPRINT
# ════════════════════════════════════════════

def _get_cpu_id():
    try:
        out = subprocess.check_output(
            ["wmic", "cpu", "get", "ProcessorId"],
            stderr=subprocess.DEVNULL, text=True, timeout=5
        )
        lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
        return lines[-1] if len(lines) >= 2 else "UNKNOWN_CPU"
    except:
        return "UNKNOWN_CPU"


def _get_disk_serial():
    # FIX #5: Chỉ lấy ổ đĩa Index=0 (ổ hệ thống), tránh USB làm thay đổi ID
    try:
        out = subprocess.check_output(
            ["wmic", "diskdrive", "where", "Index=0", "get", "SerialNumber"],
            stderr=subprocess.DEVNULL, text=True, timeout=5
        )
        lines = [l.strip() for l in out.strip().splitlines() if l.strip()]
        return lines[-1] if len(lines) >= 2 else "UNKNOWN_DISK"
    except:
        return "UNKNOWN_DISK"


def _get_mac_address():
    try:
        mac = uuid.getnode()
        return ':'.join(f'{(mac >> i) & 0xff:02x}' for i in range(40, -1, -8))
    except:
        return "UNKNOWN_MAC"


_CACHED_MID = None

def get_machine_id():
    """Tạo Machine ID duy nhất từ phần cứng → 16 ký tự hex.
    Cache lại để nhất quán trong session.
    """
    global _CACHED_MID
    if _CACHED_MID is not None:
        return _CACHED_MID

    hostname = platform.node().strip()
    cpu = _get_cpu_id().strip()
    disk = _get_disk_serial().strip()
    mac = _get_mac_address().strip()
    raw = f"{hostname}|{cpu}|{disk}|{mac}"
    _CACHED_MID = hashlib.sha256(raw.encode()).hexdigest()[:16].upper()
    return _CACHED_MID


# ════════════════════════════════════════════
#  FIX #3: ANTI-CLOCK-TAMPER
# ════════════════════════════════════════════

def _save_last_used():
    """Lưu timestamp lần dùng gần nhất"""
    try:
        LICENSE_DIR.mkdir(parents=True, exist_ok=True)
        ts = int(datetime.now().timestamp())
        TIMESTAMP_FILE.write_text(str(ts), encoding='utf-8')
    except:
        pass


def _check_clock_tamper():
    """Kiểm tra ngày hệ thống có bị tua ngược không.
    Returns: (ok, error_msg)
    """
    try:
        if not TIMESTAMP_FILE.exists():
            _save_last_used()
            return True, None

        last_ts = int(TIMESTAMP_FILE.read_text(encoding='utf-8').strip())
        now_ts = int(datetime.now().timestamp())

        # Cho phép sai lệch 2 giờ (timezone, NTP sync)
        if now_ts < last_ts - 7200:
            hours_back = (last_ts - now_ts) // 3600
            return False, f"Phát hiện đổi ngày hệ thống (lùi {hours_back}h)"

        # Cập nhật timestamp
        _save_last_used()
        return True, None
    except:
        return True, None  # Lỗi đọc file → bỏ qua


# ════════════════════════════════════════════
#  KEY GENERATION (dùng trong keygen.py)
# ════════════════════════════════════════════

def generate_key(machine_id, days=30, secret=_SECRET):
    """Tạo license key. Format: VEO3-XXXX-...-XXXX (40 hex chars)"""
    machine_id = machine_id.upper().strip()
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y%m%d")
    payload = f"{machine_id}:{expiry}"
    sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()[:16].upper()
    parts = machine_id + expiry + sig
    chunks = [parts[i:i+4] for i in range(0, len(parts), 4)]
    return "VEO3-" + "-".join(chunks)


def _decode_key(key_str):
    """Giải mã key → (machine_id, expiry, sig_hex)"""
    raw = key_str.strip().upper().replace("VEO3-", "").replace("-", "").replace(" ", "")
    if len(raw) != 40:
        raise ValueError(f"Key sai độ dài ({len(raw)}/40)")
    try:
        int(raw, 16)
    except ValueError:
        raise ValueError("Key chứa ký tự không hợp lệ")
    return raw[:16], raw[16:24], raw[24:40]


# ════════════════════════════════════════════
#  KEY VERIFICATION
# ════════════════════════════════════════════

def verify_key(key_str, secret=_SECRET):
    """Xác thực license key offline."""
    result = {"valid": False, "error": None,
              "machine_id": None, "expiry": None, "days_left": 0}

    try:
        key_machine, expiry_str, sig_hex = _decode_key(key_str)
    except ValueError as e:
        result["error"] = str(e)
        return result

    result["machine_id"] = key_machine
    result["expiry"] = expiry_str

    # 1. Kiểm tra machine ID
    current_machine = get_machine_id()
    if key_machine != current_machine:
        result["error"] = f"Key không dành cho máy này\n(key={key_machine}, máy={current_machine})"
        return result

    # 2. Kiểm tra signature
    payload = f"{key_machine}:{expiry_str}"
    expected_sig = hmac.new(secret, payload.encode(), hashlib.sha256).hexdigest()[:16].upper()
    if sig_hex != expected_sig:
        result["error"] = "Key giả mạo (signature không khớp)"
        return result

    # 3. Kiểm tra hạn
    try:
        expiry_date = datetime.strptime(expiry_str, "%Y%m%d")
    except:
        result["error"] = "Ngày hết hạn không hợp lệ"
        return result

    now = datetime.now()
    if now > expiry_date:
        days_over = (now - expiry_date).days
        result["error"] = f"Key đã hết hạn {days_over} ngày trước"
        result["days_left"] = -days_over
        return result

    # 4. FIX #3: Kiểm tra đổi ngày hệ thống
    clock_ok, clock_err = _check_clock_tamper()
    if not clock_ok:
        result["error"] = clock_err
        return result

    result["valid"] = True
    result["days_left"] = (expiry_date - now).days
    return result


# ════════════════════════════════════════════
#  FILE OPERATIONS
# ════════════════════════════════════════════

def save_key(key_str):
    LICENSE_DIR.mkdir(parents=True, exist_ok=True)
    LICENSE_FILE.write_text(key_str.strip(), encoding='utf-8')
    _save_last_used()  # Reset timestamp khi kích hoạt


def load_key():
    if LICENSE_FILE.exists():
        return LICENSE_FILE.read_text(encoding='utf-8').strip()
    return None


def check_license():
    """Kiểm tra license hiện tại → dict"""
    key = load_key()
    if not key:
        return {
            "valid": False,
            "error": "Chưa kích hoạt — cần nhập License Key",
            "machine_id": get_machine_id(),
            "expiry": None, "days_left": 0
        }
    result = verify_key(key)
    result["machine_id"] = get_machine_id()
    return result


if __name__ == "__main__":
    print("=" * 50)
    print("  VEO 3 — License Module Test")
    print("=" * 50)
    mid = get_machine_id()
    print(f"\n  Machine ID: {mid}")
    status = check_license()
    if status["valid"]:
        print(f"  License OK — {status['days_left']} days left")
    else:
        print(f"  {status['error']}")
    print()
