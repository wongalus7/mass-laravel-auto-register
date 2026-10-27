#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Laravel Register Tools (aiohttp/async)
- Cetak respon rapi (TIDAK menyimpan HTML/JSON ke file)
- Hasil (ringkasan) disimpan ke folder: resultlareg_aiohttp/
- Warna konsol kompatibel Windows, Linux, WSL, Git-Bash, dsb
- ALLOWLIST wajib (hanya domain yang Anda miliki/berizin)
- Kredensial tetap:
    username: amrullahmedan
    email   : amrullahmedan01@gmail.com
    password: Amrullah!@1293
"""

import os, sys, re, warnings, random, asyncio, json, importlib, platform, signal
from time import time as timer
from urllib.parse import urlparse, urljoin

# =======================
# 1) CEK DEPENDENCIES
# =======================
REQUIRED = ["aiohttp", "colorama"]

def print_install_help(missing):
    exe = sys.executable or "python"
    os_name = platform.system()  # 'Windows', 'Linux', 'Darwin'
    mods = " ".join(missing)

    print("\n=== Modul Python belum terpasang ===")
    print(f"Modul yang diperlukan: {mods}\n")

    if os_name == "Windows":
        print("Windows (PowerShell/CMD):")
        print(f"  py -m pip install {mods}")
        print("Atau (menggunakan interpreter yang sedang dipakai):")
        print(f"  \"{exe}\" -m pip install {mods}")
    elif os_name == "Darwin":
        print("macOS (Terminal):")
        print(f"  python3 -m pip install {mods}")
        print("Atau (menggunakan interpreter yang sedang dipakai):")
        print(f"  \"{exe}\" -m pip install {mods}")
        print("Jika pip belum ada:  brew install python3  (lalu ulangi perintah di atas)")
    else:
        # Asumsikan Linux/Unix
        print("Linux (Shell):")
        print(f"  python3 -m pip install {mods}")
        print("Atau (menggunakan interpreter yang sedang dipakai):")
        print(f"  \"{exe}\" -m pip install {mods}")
        print("Jika pip belum ada (Debian/Ubuntu):  sudo apt-get update && sudo apt-get install -y python3-pip")
    print("\nTips:")
    print(" - Disarankan pakai virtualenv/venv:  python3 -m venv .venv && source .venv/bin/activate")
    print(f" - Lalu install:  pip install {mods}\n")

def ensure_dependencies():
    missing = []
    for m in REQUIRED:
        try:
            importlib.import_module(m)
        except ImportError:
            missing.append(m)
    if missing:
        print_install_help(missing)
        sys.exit(1)

ensure_dependencies()

# Dependensi aman, lanjutkan import
import aiohttp
from aiohttp import ClientTimeout
from colorama import Fore, Style, init as colorama_init

# =======================
# 2) INISIALISASI WARNA
# =======================
def init_console_colors():
    """
    Inisialisasi warna yang aman lintas-OS & lintas-terminal.
    - Otomatis aktif di Windows CMD/PowerShell (convert=True bila perlu)
    - Hormati NO_COLOR dan FORCE_COLOR
    - Non-ANSI (dipipe ke file) akan strip kecuali FORCE_COLOR
    """
    is_windows = (os.name == "nt")
    is_tty = sys.stdout.isatty()

    no_color = ("NO_COLOR" in os.environ) or (os.environ.get("TERM") == "dumb")
    force_color = ("FORCE_COLOR" in os.environ)

    ansi_env_flags = ("WT_SESSION", "ConEmuANSI", "ANSICON", "TERM_PROGRAM")
    ansi_capable = any(k in os.environ for k in ansi_env_flags) and is_tty

    convert = (is_windows and not ansi_capable) or force_color
    strip = no_color or (not is_tty and not force_color)

    try:
        from colorama import just_fix_windows_console
        just_fix_windows_console()
    except Exception:
        pass

    colorama_init(autoreset=True, convert=convert, strip=strip)

init_console_colors()

RED, GREEN, WHITE, YELLOW, MAGENTA, CYAN, BLUE = (
    Fore.RED, Fore.GREEN, Fore.WHITE, Fore.YELLOW, Fore.MAGENTA, Fore.CYAN, Fore.BLUE
)

# =======================
# 3) KONSTAN & KONFIG
# =======================
# Timeout & concurrency yang realistis agar tidak "stuck"
CONNECT_TIMEOUT = 6      # detik
READ_TIMEOUT    = 8      # detik
TOTAL_TIMEOUT   = 12     # detik (GET)
POST_TOTAL_TIMEOUT = 20  # detik (POST)

CANDIDATE_CONCURRENCY = 12   # berapa kandidat URL per host yang dicoba paralel
HOST_SCAN_BUDGET      = 45   # batas waktu per host untuk scanning (detik)

TIMEOUT = TOTAL_TIMEOUT  # kompatibilitas variabel lama

RESULT_DIR = 'resultlareg_aiohttp'  # <== Semua ringkasan hasil disimpan di sini
RESULT_SCAN_FILE     = os.path.join(RESULT_DIR, 'result_laravelregister.txt')
RESULT_ACCOUNTS_FILE = os.path.join(RESULT_DIR, 'result_laravelregister_accounts.txt')
RESULT_CAPTCHA_FILE  = os.path.join(RESULT_DIR, 'result_laravelregister_captcha.txt')
RESULT_FAILED_FILE   = os.path.join(RESULT_DIR, 'result_laravelregister_failed.txt')

MAX_RESPONSE_PREVIEW = 1200   # potongan HTML yang dicetak
MAX_JSON_PRINT = 4000         # potongan JSON yang dicetak
VERBOSE = False               # True untuk log detail

# Pastikan folder hasil ada
os.makedirs(RESULT_DIR, exist_ok=True)

# User-Agents (cukup beberapa yang wajar)
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Kredensial tetap
FIXED_USERNAME = "amrullahmedan"
FIXED_EMAIL    = "amrullahmedan01@gmail.com"
FIXED_PASSWORD = "Amrullah!@1293"

# Jalur kandidat & Locale
BASE_PATHS = [
    "/register", "/auth/register", "/admin/register",
    "/home/register", "/user/register", "/laravel/register", "/public/register",
    "/signup", "/account/register"
]
LOCALE_PREFIXES = ["", "/en", "/en-US", "/en-GB", "/id", "/id-ID"]

# Allowlist
ALLOWLIST_HOSTS = set()
ALLOWLIST_URLS  = set()

# =======================
# 4) UTIL & BANNER
# =======================
def cls():
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
    except Exception:
        pass

def banner():
    art = r"""
┳┳┓┏┓┏┓┏┓  ┓ ┏┓┳┓┏┓┓┏┏┓┓   ┳┓┏┓┏┓┳┏┓┏┳┓┏┓┳┓
┃┃┃┣ ┃┓┣┫  ┃ ┣┫┣┫┣┫┃┃┣ ┃   ┣┫┣ ┃┓┃┗┓ ┃ ┣ ┣┫ [AIOHTTP | Stabil Boss!]
┛ ┗┗┛┗┛┛┗  ┗┛┛┗┛┗┛┗┗┛┗┛┗┛  ┛┗┗┛┗┛┻┗┛ ┻ ┗┛┛┗
Auto Scan Register Laravel & Auto Register Laravel
""".strip("\n")

    def color_mix(s: str, stride: int = 2) -> str:
        """Warnai teks dengan pola kuning–putih bergantian per 'stride' karakter non-spasi."""
        colors = (Fore.WHITE, Fore.YELLOW)
        out = []
        color_idx = 0
        run = 0

        for ch in s:
            if ch == "\n":
                out.append("\n")
                run = 0
                continue
            if ch.isspace():
                out.append(ch)
                continue

            out.append(colors[color_idx] + ch + Style.RESET_ALL)
            run += 1
            if run >= stride:
                color_idx = 1 - color_idx
                run = 0

        return "".join(out)

    print(color_mix(art, stride=2))
    print()

def norm_host(line: str) -> str:
    return (line or "").strip()

def make_headers(host_for_ref: str) -> dict:
    referer = f"https://www.google.com/search?q=register+site%3A{host_for_ref}"
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "id,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "max-age=0",
        "DNT": "1",
        "Upgrade-Insecure-Requests": "1",
        "Referer": referer,
    }

def build_candidates(raw: str):
    """Bangun kandidat URL dari LOCALE_PREFIXES x BASE_PATHS."""
    raw = norm_host(raw)
    if not raw:
        return [], ""
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        schemes = [parsed.scheme]  # hormati skema input
        host = parsed.netloc
    else:
        schemes = ["https", "http"]
        host = raw

    candidates = []
    for sch in schemes:
        base_url = f"{sch}://{host}"
        for lp in LOCALE_PREFIXES:
            for p in BASE_PATHS:
                path = f"{lp}{p}" if lp else p
                candidates.append(f"{base_url}{path}")

    # unik urutan terjaga
    seen, uniq = set(), []
    for u in candidates:
        if u not in seen:
            seen.add(u)
            uniq.append(u)
    return uniq, host

# =======================
# 5) DETEKSI REGISTER
# =======================
def looks_like_register(html: str) -> bool:
    if not html:
        return False
    lower = html.lower()
    form_markers = [
        'name="_token"', "name='_token'",
        'name="csrf-token"', "name='csrf-token'",
        'meta name="csrf-token"', "meta name='csrf-token'",
        'action="/register"', "action='/register'",
        'name="email"', "name='email'",
        'name="password"', "name='password'",
        'type="email"', "type='email'",
        'type="password"', "type='password'"
    ]
    has_form = '<form' in lower and '</form>' in lower
    hits = sum(1 for m in form_markers if m in lower)
    return has_form and hits >= 2  # dilonggarkan sedikit

def is_laravel_like(html: str) -> bool:
    if not html:
        return False
    lower = html.lower()
    has_meta_csrf = ('name="csrf-token"' in lower) or ("name='csrf-token'" in lower)
    has_hidden_token = ('name="_token"' in lower) or ("name='_token'" in lower)
    return has_meta_csrf and has_hidden_token

def has_laravel_cookie_from(headers: dict, cookie_names: set) -> bool:
    names = {n.lower() for n in (cookie_names or set())}
    if 'laravel_session' in names or 'xsrf-token' in names:
        return True
    try:
        sc = (headers.get('Set-Cookie') or '').lower() if headers else ''
        if 'laravel_session' in sc or 'xsrf-token' in sc:
            return True
    except Exception:
        pass
    return False

def detect_captcha(html: str) -> bool:
    if not html:
        return False
    lower = html.lower()
    tokens = [
        # reCAPTCHA
        "www.google.com/recaptcha/api.js", "g-recaptcha", "grecaptcha", "data-sitekey",
        # hCaptcha
        "hcaptcha.com/1/api.js", "h-captcha", "hcaptcha",
        # Cloudflare Turnstile
        "challenges.cloudflare.com", "cf-turnstile",
        # generic
        "captcha", "are you a human", "bot verification"
    ]
    return any(t in lower for t in tokens)

def scan_detection_reason(url: str, headers: dict, cookies: set, html: str):
    """Deteksi longgar khusus SCAN; kembalikan (bool, alasan)"""
    path = urlparse(url).path.lower()
    lower = (html or "").lower()

    # 1) Kalau path jelas register/signup dan ada form + email/password -> ya
    if ('/register' in path or '/signup' in path) and '<form' in lower and ('email' in lower and 'password' in lower):
        return True, "path register + form + email/password"

    # 2) Pola form umum
    if looks_like_register(lower):
        return True, "deteksi form register (longgar)"

    # 3) Laravel markers
    if is_laravel_like(lower) or has_laravel_cookie_from(headers, cookies):
        if '<form' in lower:
            return True, "laravel markers + form"
        return False, "laravel markers tanpa form"

    return False, "tidak ditemukan pola form/email/password"

def looks_like_laravel_register(headers: dict, cookies: set, html: str) -> bool:
    return looks_like_register(html) and (has_laravel_cookie_from(headers, cookies) or is_laravel_like(html))

# =======================
# 6) PARSER FORM
# =======================
_re_token = re.compile(r'name=[\'"]?_token[\'"]?\s+value=[\'"]([^\'"]+)[\'"]', re.I)
_re_meta_token = re.compile(r'<meta[^>]+name=[\'"]csrf-token[\'"][^>]+content=[\'"]([^\'"]+)[\'"]', re.I)
_re_form = re.compile(r'<form\b([^>]*)>(.*?)</form>', re.I | re.S)
_re_action = re.compile(r'action=[\'"]([^\'"]+)[\'"]', re.I)
_re_input = re.compile(r'<input\b([^>]*)>', re.I)
_re_name_attr = re.compile(r'name=[\'"]([^\'"]+)[\'"]', re.I)
_re_value_attr = re.compile(r'value=[\'"]([^\'"]*)[\'"]', re.I)

def extract_csrf(html: str):
    m = _re_token.search(html)
    if m: return m.group(1)
    m = _re_meta_token.search(html)
    if m: return m.group(1)
    return None

def pick_register_form(html: str):
    for fm in _re_form.finditer(html):
        form_attrs = fm.group(1) or ""
        form_body = fm.group(2) or ""
        body_lower = form_body.lower()
        if any(x in body_lower for x in ["name=\"email\"", "name='email'", "name=\"password\"", "name='_token'", "_token", "csrf-token"]):
            return form_attrs, form_body
    fm = _re_form.search(html)
    if fm:
        return fm.group(1) or "", fm.group(2) or ""
    return "", ""

def extract_action(form_attrs: str, page_url: str):
    m = _re_action.search(form_attrs or "")
    if not m:
        return page_url
    act = m.group(1)
    return urljoin(page_url, act)

def extract_fields(form_body: str):
    fields = set()
    for im in _re_input.finditer(form_body):
        attrs = im.group(1) or ""
        nm = _re_name_attr.search(attrs)
        if nm:
            fields.add(nm.group(1))
    return fields

def extract_input_defaults(form_body: str) -> dict:
    defaults = {}
    for im in _re_input.finditer(form_body or ''):
        attrs = im.group(1) or ''
        nm = _re_name_attr.search(attrs)
        vm = _re_value_attr.search(attrs)
        if nm and vm:
            defaults[nm.group(1)] = vm.group(1)
    return defaults

def gen_creds(host: str):
    return FIXED_USERNAME, FIXED_EMAIL, FIXED_PASSWORD

# =======================
# 7) ALLOWLIST HELPERS
# =======================
def _normalize_host(value: str) -> str:
    v = (value or "").strip()
    if not v:
        return ""
    if not (v.startswith("http://") or v.startswith("https://")):
        if "/" in v:
            v = "http://" + v
        else:
            host = v
            if ":" in host and host.split(":")[-1].isdigit():
                host = host.split(":")[0]
            return host.lower()
    try:
        host = urlparse(v).netloc or v
    except Exception:
        host = v
    if ":" in host and host.split(":")[-1].isdigit():
        host = host.split(":")[0]
    return host.lower()

def load_allowlist(paths):
    hosts, urls = set(), set()
    for p in paths:
        p = p.strip()
        if not p: continue
        if not os.path.isfile(p): continue
        try:
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                for ln in f:
                    ln = (ln or "").strip()
                    if not ln or ln.startswith("#"):
                        continue
                    if ln.startswith("http://") or ln.startswith("https://"):
                        try:
                            pr = urlparse(ln)
                            if pr.netloc:
                                hosts.add(_normalize_host(pr.netloc))
                                urls.add(ln)
                            else:
                                h = _normalize_host(ln)
                                if h: hosts.add(h)
                        except Exception:
                            h = _normalize_host(ln)
                            if h: hosts.add(h)
                    else:
                        h = _normalize_host(ln)
                        if h: hosts.add(h)
        except Exception:
            pass
    return hosts, urls

# =======================
# 8) STATE ASYNC
# =======================
class AsyncState:
    def __init__(self):
        self.scan_results = []
        self.reg_results  = []
        self.seen_scan = set()
        self.seen_reg  = set()
        self.seen_cap  = set()
        self.seen_fail = set()
        self.lock_scan = asyncio.Lock()
        self.lock_reg  = asyncio.Lock()
        self.lock_cap  = asyncio.Lock()
        self.lock_fail = asyncio.Lock()

async def _write_append(path: str, line: str, lock: asyncio.Lock, seen_set: set, key: str = None, also_list=None, add_value=None):
    k = key or line
    async with lock:
        if k in seen_set:
            return
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        try:
            with open(path, 'a', encoding='utf-8') as f:
                f.write(line)
                f.flush()
        except Exception:
            pass
        seen_set.add(k)
        if also_list is not None:
            also_list.append(add_value if add_value is not None else line)

async def _write_scan_realtime(state: AsyncState, url: str):
    if not url: return
    await _write_append(RESULT_SCAN_FILE, url.rstrip() + '\n', state.lock_scan, state.seen_scan, key=url, also_list=state.scan_results, add_value=url)

async def _write_register_realtime(state: AsyncState, host: str, reg_path: str, username: str, email: str, password: str):
    if not host: return
    reg_path = reg_path or '/'
    if not reg_path.startswith('/'): reg_path = '/' + reg_path
    key = f"{host}{reg_path}"
    line = f"{host}{reg_path} : {username} : {email} : {password}\n"
    await _write_append(RESULT_ACCOUNTS_FILE, line, state.lock_reg, state.seen_reg, key=key, also_list=state.reg_results, add_value=(host, username, email, password))

async def _write_captcha_realtime(state: AsyncState, host: str, reg_path: str, note: str):
    if not host: return
    reg_path = reg_path or '/'
    if not reg_path.startswith('/'): reg_path = '/' + reg_path
    key = f"{host}{reg_path}"
    line = f"{host}{reg_path} : CAPTCHA : {note}\n"
    await _write_append(RESULT_CAPTCHA_FILE, line, state.lock_cap, state.seen_cap, key=key)

async def _write_failed_realtime(state: AsyncState, host: str, reg_path: str, status: int, reason: str):
    if not host: return
    reg_path = reg_path or '/'
    if not reg_path.startswith('/'): reg_path = '/' + reg_path
    key = f"{host}{reg_path}"
    line = f"{host}{reg_path} : FAILED : HTTP {status} : {reason}\n"
    await _write_append(RESULT_FAILED_FILE, line, state.lock_fail, state.seen_fail, key=key)

# =======================
# 9) HTTP HELPERS
# =======================
def _timeout(total):
    return ClientTimeout(
        sock_connect=CONNECT_TIMEOUT,
        sock_read=READ_TIMEOUT,
        total=total
    )

async def fast_get(session: aiohttp.ClientSession, url: str, headers: dict):
    try:
        async with session.get(url, headers=headers, timeout=_timeout(TOTAL_TIMEOUT), allow_redirects=True, ssl=False) as resp:
            text = await resp.text(errors='ignore')
            cookie_names = set(resp.cookies.keys()) if resp.cookies else set()
            headers_copy = dict(resp.headers) if resp.headers else {}
            return {
                'status': resp.status,
                'url': str(resp.url),
                'headers': headers_copy,
                'cookies': cookie_names,
                'text': text
            }
    except Exception as e:
        return {'error': str(e), 'url': url}

async def post_form(session: aiohttp.ClientSession, url: str, headers: dict, data: dict):
    try:
        async with session.post(url, headers=headers, data=data, timeout=_timeout(POST_TOTAL_TIMEOUT), allow_redirects=True, ssl=False) as resp:
            content = await resp.read()
            try:
                text = content.decode('utf-8', errors='ignore')
            except Exception:
                text = ''
            headers_copy = dict(resp.headers) if resp.headers else {}
            return {
                'status': resp.status,
                'url': str(resp.url),
                'headers': headers_copy,
                'text': text
            }
    except Exception as e:
        return {'error': str(e), 'url': url}

# =======================
# 10) ANALISA GAGAL & SARAN
# =======================
def classify_failure(status: int, body_lower: str, headers: dict):
    reasons = []
    hints = []

    if status in (401, 403):
        reasons.append("Akses ditolak (HTTP 401/403)")
        if 'cloudflare' in (headers.get('Server','').lower() if headers else ''):
            hints.append("Server dilindungi Cloudflare. Kurangi concurrency, whitelist IP, atau gunakan jaringan internal.")
        hints.append("Pastikan header Referer/Origin benar & token CSRF valid.")

    if status == 429:
        reasons.append("Kena rate limit (HTTP 429)")
        hints.append("Kurangi pool/concurrency dan beri jeda antar request.")
        hints.append("Gunakan IP yang diizinkan atau minta whitelist.")

    if status == 400:
        reasons.append("Bad Request (HTTP 400)")
        hints.append("Periksa field wajib & format payload. Samakan nama field dengan form HTML.")

    if status and status >= 500:
        reasons.append("Galat server (HTTP 5xx)")
        hints.append("Cek log server Laravel. Mungkin ada exception/validasi yang gagal.")

    if 'already been taken' in body_lower:
        reasons.append("Email/username sudah terpakai")
        hints.append("Gunakan email/username lain pada lingkungan uji (atau bersihkan seed data).")

    if 'required' in body_lower or 'harus diisi' in body_lower:
        reasons.append("Field wajib belum terisi")
        hints.append("Tambahkan mapping field yang hilang (contoh: name, phone, terms).")

    if 'invalid' in body_lower or 'format is' in body_lower:
        reasons.append("Format field tidak valid")
        hints.append("Sesuaikan format (pola password, format email, dsb).")

    if 'does not match' in body_lower or 'konfirmasi' in body_lower:
        reasons.append("Konfirmasi password tidak cocok")
        hints.append("Pastikan password_confirmation sama dengan password (skrip sudah menyamakan).")

    if 'csrf' in body_lower:
        reasons.append("CSRF token tidak cocok")
        hints.append("Pastikan sesi GET & POST sama (skrip sudah reuse session). Coba ulang sekali lagi.")

    if 'forbidden' in body_lower or 'blocked' in body_lower:
        reasons.append("Diblokir kebijakan server")
        hints.append("Whitelist IP atau jalankan dari jaringan yang diizinkan.")

    if not reasons:
        reasons.append("Alasan belum jelas")
        hints.append("Periksa potongan respons di konsol. Cek field khusus/middleware kustom.")

    return reasons, hints

# =======================
# 11) SCAN (print progres per path)
# =======================
async def scan_host(state: AsyncState, session: aiohttp.ClientSession, entry: str):
    try:
        candidates, host_raw = build_candidates(entry)
        if not candidates:
            print(f"{YELLOW}[SCAN]{Style.RESET_ALL} {entry} tidak punya kandidat.", flush=True)
            return None
        ref_host = _normalize_host(host_raw)
        headers = make_headers(ref_host)

        print(f"{BLUE}[SCAN]{Style.RESET_ALL} Memindai {ref_host} ({len(candidates)} kandidat)...", flush=True)

        sem_cand = asyncio.Semaphore(CANDIDATE_CONCURRENCY)
        found_url = asyncio.Future()

        async def try_candidate(idx: int, url: str, total: int):
            if found_url.done():
                return
            async with sem_cand:
                print(f"{WHITE}[TRY {idx}/{total}]{Style.RESET_ALL} {url}", flush=True)
                r = await fast_get(session, url, headers)
                if not r or 'error' in r:
                    err = r.get('error') if r else 'koneksi/timeout'
                    print(f"  {MAGENTA}[ERR]{Style.RESET_ALL} {err}", flush=True)
                    return

                ok_status = (200 <= r['status'] < 400) or r['status'] in (401, 403)
                is_match, reason = scan_detection_reason(r['url'], r['headers'], r['cookies'], r['text'] or "")

                if ok_status and is_match:
                    print(f"  {GREEN}[KETEMU]{Style.RESET_ALL} {reason} (HTTP {r['status']})", flush=True)
                    if not found_url.done():
                        found_url.set_result(r['url'])
                else:
                    print(f"  {YELLOW}[NO]{Style.RESET_ALL} HTTP {r['status']} | {reason}", flush=True)

        tasks = [asyncio.create_task(try_candidate(i+1, u, len(candidates))) for i, u in enumerate(candidates)]

        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=HOST_SCAN_BUDGET)
        except asyncio.TimeoutError:
            print(f"{YELLOW}[SCAN]{Style.RESET_ALL} Timeout scan pada {ref_host}.", flush=True)

        if found_url.done():
            url = found_url.result()
            await _write_scan_realtime(state, url)
            return url
        else:
            return None

    except Exception as e:
        print(f"{RED}[ERR SCAN]{Style.RESET_ALL} {entry}: {e}", flush=True)
    return None

# =======================
# 12) REGISTER
# =======================
async def do_register(state: AsyncState, session: aiohttp.ClientSession, page_url: str):
    host_for_log = _normalize_host(urlparse(page_url).netloc)
    headers_get = make_headers(host_for_log)

    # GET form
    r = await fast_get(session, page_url, headers_get)
    if not r or 'error' in r or r.get('status') != 200:
        status = r.get('status') if r and 'status' in r else 'ERR'
        errtxt = r.get('error') if r and 'error' in r else ''
        print(f"{RED}[GAGAL GET]{Style.RESET_ALL} {host_for_log} -> {page_url} (HTTP {status}) {errtxt}", flush=True)
        return None

    html = r['text'] or ""
    if not looks_like_laravel_register(r['headers'], r['cookies'], html):
        print(f"{YELLOW}[INFO]{Style.RESET_ALL} {host_for_log} -> {page_url} bukan halaman Register Laravel (lewati).", flush=True)
        return None

    # Deteksi captcha pada form
    pre_captcha = detect_captcha(html)
    if pre_captcha:
        print(f"{CYAN}[INFO]{Style.RESET_ALL} {host_for_log} -> {page_url} terdeteksi CAPTCHA pada form (tetap dicoba POST).", flush=True)

    form_attrs, form_body = pick_register_form(html)
    action_url = extract_action(form_attrs, r['url'])
    token = extract_csrf(html)

    fields = extract_fields(form_body)
    name_key = 'name' if 'name' in fields else ('username' if 'username' in fields else None)
    email_key = 'email' if 'email' in fields else None
    pass_key = 'password' if 'password' in fields else None
    pass2_key = 'password_confirmation' if 'password_confirmation' in fields else ('password-confirm' if 'password-confirm' in fields else None)

    if not (email_key and pass_key):
        print(f"{RED}[FORM TIDAK DIDUKUNG]{Style.RESET_ALL} {host_for_log} -> {page_url} (email/password tidak ditemukan)", flush=True)
        return None

    display_host = _normalize_host(urlparse(action_url).netloc) or host_for_log
    username, email, password = gen_creds(display_host)

    input_defaults = extract_input_defaults(form_body)

    payload = {}
    payload.update(input_defaults)
    if name_key:  payload[name_key]  = payload.get(name_key, username)
    if email_key: payload[email_key] = email
    if pass_key:  payload[pass_key]  = password
    if pass2_key: payload[pass2_key] = password
    if token:     payload['_token']  = token

    # Auto-isi field generik
    for f in fields:
        fl = (f or '').lower()
        if f in payload or f in ('_token', 'csrf-token'):
            continue
        if ('user' in fl or 'name' in fl) and fl not in ('username', 'name'):
            payload[f] = username
        elif 'mail' in fl:
            payload[f] = email
        elif 'pass' in fl and 'confirm' not in fl:
            payload[f] = password
        elif 'confirm' in fl:
            payload[f] = password
        elif 'phone' in fl or 'tel' in fl:
            payload[f] = '081234567890'
        elif 'term' in fl or 'agree' in fl or 'policy' in fl or 'privacy' in fl:
            payload[f] = '1'
        else:
            payload[f] = username

    headers_post = headers_get.copy()
    try:
        pr_url = urlparse(action_url)
        headers_post['Origin']  = f"{pr_url.scheme}://{pr_url.netloc}"
        headers_post['Referer'] = page_url
    except Exception:
        pass
    if token:
        headers_post['X-CSRF-TOKEN'] = token

    # POST
    pr = await post_form(session, action_url, headers_post, payload)
    if not pr or 'error' in pr:
        errtxt = pr.get('error') if pr else 'koneksi/timeout'
        print(f"{RED}[GAGAL POST]{Style.RESET_ALL} {display_host} -> {action_url} ({errtxt})", flush=True)
        return None

    body_text = pr['text'] or ""
    body_lower = body_text.lower()
    submitted_ok = 200 <= pr['status'] < 400

    error_hints = [
        'already been taken', 'required', 'invalid', 'error', 'failed',
        'incorrect', 'does not match', 'format is', 'too short', 'too long',
        'verification failed', 'unverified', 'try again later', 'blocked', 'forbidden'
    ]
    has_errors = any(w in body_lower for w in error_hints)
    post_captcha = detect_captcha(body_text) or (
        pr['status'] in (403, 429) and 'cloudflare' in (pr['headers'].get('Server','').lower() if pr['headers'] else '')
    )

    # Tampilkan respon rapi (TANPA simpan file)
    ct = (pr['headers'].get('Content-Type', '') or '').lower()
    is_json = 'application/json' in ct or ct.endswith('/json') or body_text.strip().startswith('{')

    print(CYAN + "─" * 90 + Style.RESET_ALL, flush=True)
    print(f"{WHITE}Host     :{Style.RESET_ALL} {display_host}", flush=True)
    print(f"{WHITE}Aksi     :{Style.RESET_ALL} POST {action_url}", flush=True)
    print(f"{WHITE}Status   :{Style.RESET_ALL} HTTP {pr['status']} ({'TERKIRIM' if submitted_ok else 'POST GAGAL'})", flush=True)

    if is_json:
        try:
            pretty = json.dumps(json.loads(body_text), ensure_ascii=False, indent=2)
        except Exception:
            pretty = body_text
        if len(pretty) > MAX_JSON_PRINT:
            pretty = pretty[:MAX_JSON_PRINT] + "\n... [dipotong]"
        print(f"{WHITE}Respon   :{Style.RESET_ALL} (JSON, dicetak rapi)", flush=True)
        print(pretty, flush=True)
    else:
        prev = body_text[:MAX_RESPONSE_PREVIEW]
        if not prev.strip():
            prev = "(Kosong)"
        print(f"{WHITE}Respon   :{Style.RESET_ALL} (HTML, potongan {len(prev)} chars)", flush=True)
        print(prev if len(prev) < MAX_RESPONSE_PREVIEW else prev + "\n... [dipotong]", flush=True)

    # CAPTCHA – catat & beri saran
    if pre_captcha atau post_captcha:
        page_path = urlparse(page_url).path or '/'
        await _write_captcha_realtime(state, host_for_log, page_path, "CAPTCHA terdeteksi (registrasi manual diperlukan)")
        print(f"{CYAN}[CAPTCHA]{Style.RESET_ALL} {host_for_log}{page_path} memerlukan registrasi manual.", flush=True)
        print("Saran:", flush=True)
        print("  - Nonaktifkan CAPTCHA pada staging / whitelist IP Anda", flush=True)
        print("  - Daftarkan akun secara manual pada situs tersebut", flush=True)
        print("  - Implementasikan integrasi token CAPTCHA resmi (server-side), jangan bypass", flush=True)
        return None

    looks_success = submitted_ok and not has_errors

    if looks_success:
        page_path = urlparse(page_url).path or '/'
        await _write_register_realtime(state, host_for_log, page_path, username, email, password)
        print(f"{GREEN}[SUKSES]{Style.RESET_ALL} Akun terdaftar (lenient): {username} / {email}", flush=True)
        return (host_for_log, username, email, password)
    else:
        # Klasifikasi & saran
        reasons, hints = classify_failure(pr['status'], body_lower, pr['headers'])
        print(f"{RED}[GAGAL]{Style.RESET_ALL} {host_for_log}{urlparse(page_url).path or '/'}", flush=True)
        print("Penyebab:", flush=True)
        for r in reasons:
            print("  - " + r, flush=True)
        print("Saran:", flush=True)
        for h in hints:
            print("  - " + h, flush=True)

        page_path = urlparse(page_url).path or '/'
        await _write_failed_realtime(state, host_for_log, page_path, pr['status'], "; ".join(reasons))
        return None

def _resolve_item_to_urls(item: str):
    s = (item or "").strip()
    if not s:
        return []
    if s.startswith("http://") or s.startswith("https://"):
        return [s]
    candidates, _ = build_candidates(s)
    return candidates

def _is_allowed_for_register(item: str) -> bool:
    s = (item or "").strip()
    if not s:
        return False
    if s.startswith("http://") or s.startswith("https://"):
        host = _normalize_host(urlparse(s).netloc)
    else:
        host = _normalize_host(s)
    if host in ALLOWLIST_HOSTS:
        return True
    parts = host.split('.')
    for i in range(len(parts)-2):
        parent = '.'.join(parts[i+1:])
        if parent in ALLOWLIST_HOSTS:
            return True
    return False

async def register_item(state: AsyncState, session: aiohttp.ClientSession, item: str):
    try:
        if not _is_allowed_for_register(item):
            print(f"{YELLOW}[LEWATI]{Style.RESET_ALL} {item} (bukan allowlist).", flush=True)
            return None

        host = _normalize_host(item)
        headers = make_headers(host)
        urls = _resolve_item_to_urls(item)

        print(f"{BLUE}[REG]{Style.RESET_ALL} Memeriksa {host} ({len(urls)} kandidat)...", flush=True)

        sem_cand = asyncio.Semaphore(CANDIDATE_CONCURRENCY)
        chosen = asyncio.Future()

        async def try_one(idx: int, u: str, total: int):
            if chosen.done():
                return
            async with sem_cand:
                print(f"{WHITE}[TRY {idx}/{total}]{Style.RESET_ALL} {u}", flush=True)
                r = await fast_get(session, u, headers)
                if not r or 'error' in r:
                    err = r.get('error') if r else 'koneksi/timeout'
                    print(f"  {MAGENTA}[ERR]{Style.RESET_ALL} {err}", flush=True)
                    return
                ok_status = (200 <= r['status'] < 400) or r['status'] in (401, 403)
                is_match, reason = scan_detection_reason(r['url'], r['headers'], r['cookies'], r['text'] or "")
                if ok_status and is_match:
                    print(f"  {GREEN}[KETEMU]{Style.RESET_ALL} {reason} (HTTP {r['status']})", flush=True)
                    if not chosen.done():
                        chosen.set_result(r['url'])
                else:
                    print(f"  {YELLOW}[NO]{Style.RESET_ALL} HTTP {r['status']} | {reason}", flush=True)

        tasks = [asyncio.create_task(try_one(i+1, u, len(urls))) for i, u in enumerate(urls)]

        try:
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=HOST_SCAN_BUDGET)
        except asyncio.TimeoutError:
            print(f"{YELLOW}[REG]{Style.RESET_ALL} Timeout scan register pada {host}.", flush=True)

        if chosen.done():
            await _write_scan_realtime(state, chosen.result())
            return await do_register(state, session, chosen.result())
        else:
            print(f"{YELLOW}[REG]{Style.RESET_ALL} Tidak ditemukan halaman register Laravel untuk {host}.", flush=True)
            return None

    except Exception as e:
        print(f"{RED}[ERR REG]{Style.RESET_ALL} {item}: {e}", flush=True)
        return None

# =======================
# 13) MODE RUNNERS
# =======================
async def run_scan_mode_async(file_path: str, pool: int):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            websites = [ln.strip() for ln in f if ln.strip()]
        if not websites:
            print(f"{RED}[!] Daftar host kosong{Style.RESET_ALL}")
            return
    except Exception:
        print(f"{RED}[!] Tidak bisa membaca file daftar host{Style.RESET_ALL}")
        return

    pool = max(1, min(pool, len(websites)))
    start_time = timer()
    state = AsyncState()

    connector_limit = max(pool * CANDIDATE_CONCURRENCY * 2, 64)
    timeout = ClientTimeout(total=None)  # per-request pakai timeout masing-masing
    conn = aiohttp.TCPConnector(limit=connector_limit, ttl_dns_cache=300)

    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
        sem = asyncio.Semaphore(pool)

        async def worker(entry: str):
            async with sem:
                return await scan_host(state, session, entry)

        await asyncio.gather(*(worker(w) for w in websites))

    dur = timer() - start_time
    print(f"{GREEN}[SCAN SELESAI]{Style.RESET_ALL} URL Register Laravel: {len(state.scan_results)} -> {RESULT_SCAN_FILE}")
    print(f"{YELLOW}Waktu eksekusi: {dur:.2f} detik{Style.RESET_ALL}")

async def run_register_mode_async(sources, allow_src: str, pool: int or None):
    # muat allowlist
    global ALLOWLIST_HOSTS, ALLOWLIST_URLS
    ALLOWLIST_HOSTS, ALLOWLIST_URLS = load_allowlist([allow_src])
    if not ALLOWLIST_HOSTS:
        print(f"{RED}[!] Allowlist kosong/tidak ditemukan. Tambahkan domain milik/berizin ke {allow_src}.{Style.RESET_ALL}")
        return
    else:
        print(f"{GREEN}[ALLOWLIST]{Style.RESET_ALL} {len(ALLOWLIST_HOSTS)} host dimuat.")

    # muat item
    items = []
    for p in sources:
        if os.path.isfile(p):
            with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                for ln in f:
                    ln = (ln or "").strip()
                    if ln and not ln.startswith("#"):
                        items.append(ln)
        else:
            items.extend([x.strip() for x in p.split(",") if x.strip()])

    # De-dup items
    items = list(dict.fromkeys(items))
    if not items:
        print(f"{RED}[!] Tidak ada item valid di sumber{Style.RESET_ALL}")
        return

    if pool is None:
        pool = max(1, (os.cpu_count() or 2) * 4)
        print(f"{CYAN}[INFO]{Style.RESET_ALL} Pool diset otomatis ke {pool}")
    pool = max(1, min(pool, max(1, len(items))))

    start_time = timer()
    state = AsyncState()

    connector_limit = max(pool * CANDIDATE_CONCURRENCY * 2, 64)
    timeout = ClientTimeout(total=None)
    conn = aiohttp.TCPConnector(limit=connector_limit, ttl_dns_cache=300)

    async with aiohttp.ClientSession(timeout=timeout, connector=conn) as session:
        sem = asyncio.Semaphore(pool)

        async def worker(entry: str):
            async with sem:
                return await register_item(state, session, entry)

        await asyncio.gather(*(worker(it) for it in items))

    dur = timer() - start_time
    print(f"{GREEN}[REGISTER SELESAI]{Style.RESET_ALL} Akun sukses (lenient): {len(state.reg_results)} -> {RESULT_ACCOUNTS_FILE}")
    print(f"{CYAN}[CATATAN]{Style.RESET_ALL} Situs dengan CAPTCHA tercatat di '{RESULT_CAPTCHA_FILE}'.")
    print(f"{YELLOW}Waktu eksekusi: {dur:.2f} detik{Style.RESET_ALL}")

# =======================
# 14) MAIN
# =======================
def _install_signal_handlers():
    # Tutup rapi saat Ctrl+C
    try:
        signal.signal(signal.SIGINT, signal.default_int_handler)
    except Exception:
        pass

def main():
    warnings.filterwarnings("ignore")
    _install_signal_handlers()
    cls()
    # Banner cantik
    art = r"""
┳┳┓┏┓┏┓┏┓  ┓ ┏┓┳┓┏┓┓┏┏┓┓   ┳┓┏┓┏┓┳┏┓┏┳┓┏┓┳┓
┃┃┃┣ ┃┓┣┫  ┃ ┣┫┣┫┣┫┃┃┣ ┃   ┣┫┣ ┃┓┃┗┓ ┃ ┣ ┣┫ [AIOHTTP | Stabil Boss!]
┛ ┗┗┛┗┛┛┗  ┗┛┛┗┛┗┛┗┗┛┗┛┗┛  ┛┗┗┛┗┛┻┗┛ ┻ ┗┛┛┗
Auto Scan Register Laravel & Auto Register Laravel
""".strip("\n")
    from colorama import Fore, Style
    def color_mix(s: str, stride: int = 2) -> str:
        colors = (Fore.WHITE, Fore.YELLOW)
        out, color_idx, run = [], 0, 0
        for ch in s:
            if ch == "\n":
                out.append("\n"); run = 0; continue
            if ch.isspace():
                out.append(ch); continue
            out.append(colors[color_idx] + ch + Style.RESET_ALL)
            run += 1
            if run >= stride:
                color_idx = 1 - color_idx; run = 0
        return "".join(out)
    print(color_mix(art, 2)); print()

    print(f"{WHITE}Folder hasil:{Style.RESET_ALL} {RESULT_DIR}")
    print("1. Mass Scan Register")
    print("2. Mass Register Laravel")
    try:
        choice = input(f"{YELLOW}Pilih (1/2): {WHITE}").strip()
    except EOFError:
        return

    if choice == "1":
        try:
            file_path = input(f"{YELLOW}Path list host/domains untuk SCAN: {WHITE}")
            pool = int(input(f"{YELLOW}Pool (concurrency): {WHITE}"))
        except Exception:
            print(f"{RED}[!] Input tidak valid{Style.RESET_ALL}")
            return
        print(f"{YELLOW}[INFO]{Style.RESET_ALL} Setelah scan, Anda dapat menyalin '{RESULT_SCAN_FILE}' menjadi 'allowlist.txt' (HANYA domain milik/berizin).")
        asyncio.run(run_scan_mode_async(file_path, pool))
    elif choice == "2":
        try:
            src = input(f"{YELLOW}List URL/host untuk auto regist [{RESULT_SCAN_FILE}]: {WHITE}").strip()
            sources = [s.strip() for s in src.split(",") if s.strip()] if src else [RESULT_SCAN_FILE]
            allow_src = input(f"{YELLOW}Path [allowlist.txt]: {WHITE}").strip() or "allowlist.txt"
            pool_input = input(f"{YELLOW}Pool (disarankan >= CPU*4, kosong=auto): {WHITE}").strip()
            pool = int(pool_input) if pool_input else None
        except Exception:
            print(f"{RED}[!] Input tidak valid{Style.RESET_ALL}")
            return
        print(f"{YELLOW}[INFO]{Style.RESET_ALL} Registrasi otomatis hanya untuk halaman Laravel TANPA CAPTCHA. Hasil sukses dicatat di '{RESULT_ACCOUNTS_FILE}'.")
        asyncio.run(run_register_mode_async(sources, allow_src, pool))
    else:
        print(f"{RED}Pilihan tidak valid{Style.RESET_ALL}")

if __name__ == "__main__":
    main()
