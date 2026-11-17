#!/usr/bin/env python3
"""aside-relay guided setup.

Interactive:      python3 scripts/setup.py
Non-interactive:  python3 scripts/setup.py --yes            (defaults, local-only)
Service install:  python3 scripts/setup.py --install-service
Uninstall:        python3 scripts/setup.py --uninstall-service

Everything the wizard writes can also be done by hand — see README "Manual setup".
It writes exactly three things, all outside the repo:
  ~/.aside-relay/token   bearer token (0600)
  ~/.aside-relay/env     KEY=VALUE config (0600)
  service registration   (only if you opt in)
    macOS:   ~/Library/LaunchAgents/com.aside-relay.plist
    Windows: a Task Scheduler entry named "aside-relay" (logon trigger)
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

HOME = Path.home()
REPO = Path(__file__).resolve().parent.parent
TOKEN_FILE = HOME / ".aside-relay/token"
ENV_FILE = HOME / ".aside-relay/env"
PLIST = HOME / "Library/LaunchAgents/com.aside-relay.plist"

if os.name == "nt":
    # Windows consoles default to cp1252, which raises UnicodeEncodeError on
    # the ✓/✗ marks below, and ANSI colors need VT mode enabled explicitly.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass
    try:
        import ctypes as _ctypes
        _k32 = _ctypes.windll.kernel32
        for _cid in (-11, -12):                      # STD_OUTPUT/STD_ERROR_HANDLE
            _h = _k32.GetStdHandle(_cid)
            _mode = _ctypes.c_uint32()
            if _k32.GetConsoleMode(_h, _ctypes.byref(_mode)):
                _k32.SetConsoleMode(_h, _mode.value | 0x4)   # ENABLE_VIRTUAL_TERMINAL_PROCESSING
    except (AttributeError, OSError):
        pass

OK, WARN, BAD = "\033[32m✓\033[0m", "\033[33m!\033[0m", "\033[31m✗\033[0m"


def say(mark: str, msg: str) -> None:
    print(f"  {mark} {msg}")


def ask(prompt: str, default: str = "", assume_yes: bool = False) -> str:
    if assume_yes:
        return default
    tail = f" [{default}]" if default else ""
    try:
        v = input(f"  ? {prompt}{tail}: ").strip()
    except EOFError:
        return default
    return v or default


def yesno(prompt: str, default: bool, assume_yes: bool = False) -> bool:
    if assume_yes:
        return default
    d = "Y/n" if default else "y/N"
    v = ask(f"{prompt} ({d})")
    if not v:
        return default
    return v.lower().startswith("y")


# ---------------------------------------------------------------- checks
def check_prereqs() -> bool:
    print("\n[1/5] Prerequisites")
    ok = True

    if sys.version_info < (3, 10):
        say(BAD, f"Python ≥3.10 required (you have {sys.version.split()[0]})")
        ok = False
    else:
        say(OK, f"Python {sys.version.split()[0]}")

    aside = os.environ.get("ASIDE_BIN") or shutil.which("aside") or shutil.which("aside.exe")
    if not aside and os.name == "nt":
        local = os.environ.get("LOCALAPPDATA")
        if local and (Path(local) / "Aside/CLI/current/aside.exe").exists():
            aside = str(Path(local) / "Aside/CLI/current/aside.exe")
    aside = aside or str(HOME / ".local/bin/aside")
    if Path(aside).exists():
        say(OK, f"aside CLI: {aside}")
    else:
        say(BAD, "aside CLI not found — install the Aside browser first, "
                 "then set ASIDE_BIN if it lives somewhere unusual")
        ok = False

    daemon = os.environ.get("ASIDE_DAEMON_URL", "http://127.0.0.1:21420")
    try:
        with urllib.request.urlopen(f"{daemon}/health", timeout=3) as r:
            say(OK, f"Aside daemon reachable at {daemon}" if r.status == 200
                else f"daemon answered HTTP {r.status}")
    except Exception:
        say(WARN, f"Aside daemon not reachable at {daemon} — "
                  "launch the Aside app once, then re-run (not fatal)")

    try:
        import fastapi, httpx, uvicorn, cryptography  # noqa: F401
        say(OK, "python deps present")
    except ImportError as e:
        say(BAD, f"missing python package: {e.name} — run: pip install -r requirements.txt")
        ok = False
    return ok


# ---------------------------------------------------------------- token
def ensure_token() -> None:
    print("\n[2/5] Bearer token")
    if TOKEN_FILE.exists() and TOKEN_FILE.read_text().strip():
        say(OK, f"exists: {TOKEN_FILE}")
        return
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(secrets.token_urlsafe(32) + "\n")
    TOKEN_FILE.chmod(0o600)
    say(OK, f"generated: {TOKEN_FILE} (0600)")


# ---------------------------------------------------------------- env file
def load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def save_env(env: dict[str, str]) -> None:
    lines = ["# aside-relay config — see README for every key", ""]
    lines += [f"{k}={v}" for k, v in sorted(env.items()) if v]
    ENV_FILE.parent.mkdir(parents=True, exist_ok=True)
    ENV_FILE.write_text("\n".join(lines) + "\n")
    ENV_FILE.chmod(0o600)
    say(OK, f"wrote {ENV_FILE} (0600)")


def configure(assume_yes: bool) -> None:
    env = load_env()

    print("\n[3/5] Remote access (optional)")
    print("      Local-only use needs nothing here. For phone/remote access the")
    print("      recommended front is Cloudflare Tunnel + Access — see README.")
    if yesno("Configure Cloudflare Access verification now?", False, assume_yes):
        env["ASIDE_RELAY_ACCESS_TEAM"] = ask(
            "Access team domain (e.g. yourteam.cloudflareaccess.com)",
            env.get("ASIDE_RELAY_ACCESS_TEAM", ""))
        env["ASIDE_RELAY_ACCESS_AUD"] = ask(
            "Access application AUD tag",
            env.get("ASIDE_RELAY_ACCESS_AUD", ""))
        env["ASIDE_RELAY_ACCESS_EMAILS"] = ask(
            "allowed emails (comma-separated)",
            env.get("ASIDE_RELAY_ACCESS_EMAILS", ""))
    else:
        say(OK, "skipped — bridge stays loopback-only until you front it yourself")

    print("\n[4/5] Push notifications (optional)")
    if yesno("Send a push (ntfy protocol) when a run finishes?", False, assume_yes):
        env["ASIDE_RELAY_NTFY"] = ask("ntfy server URL (e.g. https://ntfy.sh)",
                                      env.get("ASIDE_RELAY_NTFY", "https://ntfy.sh"))
        env["ASIDE_RELAY_NTFY_TOPIC"] = ask("topic", env.get("ASIDE_RELAY_NTFY_TOPIC",
                                            "aside-relay-" + secrets.token_hex(4)))
    save_env(env)


# ---------------------------------------------------------------- service
WINDOWS_LAUNCHER = HOME / ".aside-relay/start-bridge.cmd"


def _windows_pythonw() -> str:
    """pythonw.exe 로 창 없이 돌린다(없으면 python.exe — 콘솔창이 뜬다)."""
    exe = Path(sys.executable)
    w = exe.with_name("pythonw.exe")
    return str(w) if w.exists() else sys.executable


def _write_windows_launcher() -> Path:
    """로그인 시 백그라우드로 브리지를 띄우는 .cmd.

    cmd /c + start /b 리다이렉션 조합이 중요하다:
    - pythonw 만 쓰면 sys.stdout 이 None 이라 uvicorn 로그가 죽는다
      (리다이렉션을 걸면 stdio 가 파일 핸들로 살아난다 — 실측 확인).
    - start /b 로 떼어내면 cmd 가 즉시 종료되어 콘솔창이 남지 않는다.
    """
    (REPO / "logs").mkdir(exist_ok=True)
    out = REPO / "logs/bridge.out.log"
    err = REPO / "logs/bridge.err.log"
    body = (
        "@echo off\r\n"
        f'cd /d "{REPO}"\r\n'
        f'start "" /b "{_windows_pythonw()}" "{REPO / "server.py"}"'
        f' >> "{out}" 2>> "{err}"\r\n'
    )
    WINDOWS_LAUNCHER.parent.mkdir(parents=True, exist_ok=True)
    WINDOWS_LAUNCHER.write_bytes(body.encode("ascii"))
    return WINDOWS_LAUNCHER


def _stop_windows_bridge() -> None:
    """이 체크아웃에서 뜬 브리지를 멈춘다(launchctl bootout 과 대응).

    런처가 pythonw 를 detach 하므로 task 상태만으로는 안 멈춘다 — 명령줄의
    server.py 경로로 해당 프로세스를 찾아서 걷어낸다.
    """
    needle = (str(REPO) + "\\server.py").replace("'", "''")
    ps = (
        "Get-CimInstance Win32_Process -Filter \"Name='pythonw.exe'\" | "
        f"Where-Object {{ $_.CommandLine -and $_.CommandLine.Contains('{needle}') }} | "
        "ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
    )
    subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                   capture_output=True, text=True)


def _install_service_windows() -> None:
    launcher = _write_windows_launcher()
    # schtasks /SC ONLOGON 은 표준 사용자에게 Access denied 를 뱉는다(실측).
    # Register-ScheduledTask -AtLogOn 은 관리자 없이도 된다.
    ps = (
        "$action = New-ScheduledTaskAction -Execute 'cmd.exe' "
        f"-Argument '/c \"{launcher}\"';"
        "$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME; "
        "Register-ScheduledTask -TaskName 'aside-relay' "
        "-Action $action -Trigger $trigger -Force | Out-Null"
    )
    r = subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                       capture_output=True, text=True)
    if r.returncode != 0:
        say(BAD, f"scheduled task creation failed: {(r.stderr or r.stdout).strip()}")
        return
    # 등록이 성공한 뒤에 기존 인스턴스를 재시작해야 새 런처/설정이 반영된다.
    _stop_windows_bridge()
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Start-ScheduledTask -TaskName 'aside-relay'"],
                   capture_output=True, text=True)
    say(OK, "service installed & started (Task Scheduler: aside-relay)")
    say(OK, f"logs: {REPO / 'logs/bridge.err.log'}")


def _uninstall_service_windows() -> None:
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Unregister-ScheduledTask -TaskName 'aside-relay' "
                        "-Confirm:$false"],
                       capture_output=True, text=True)
    # bootout 와 마찬가지로 떠 있는 인스턴스도 같이 걷어낸다.
    _stop_windows_bridge()
    say(OK, "service removed" if r.returncode == 0 else "service was not registered")


def install_service() -> None:
    if os.name == "nt":
        _install_service_windows()
        return
    (REPO / "logs").mkdir(exist_ok=True)      # plist 가 로그를 여기 쓴다
    tmpl = (REPO / "deploy/com.aside-relay.plist.template").read_text()
    plist = (tmpl.replace("__PYTHON__", sys.executable)
                 .replace("__REPO__", str(REPO))
                 .replace("__HOME__", str(HOME)))
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    PLIST.write_text(plist)
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(PLIST)],
                   capture_output=True)
    r = subprocess.run(["launchctl", "bootstrap", f"gui/{uid}", str(PLIST)],
                       capture_output=True, text=True)
    if r.returncode == 0:
        say(OK, f"service installed & started ({PLIST.name})")
        say(OK, "logs: <repo>/logs/bridge.err.log")
    else:
        say(BAD, f"launchctl bootstrap failed: {r.stderr.strip()}")


def uninstall_service() -> None:
    if os.name == "nt":
        _uninstall_service_windows()
        return
    uid = os.getuid()
    subprocess.run(["launchctl", "bootout", f"gui/{uid}", str(PLIST)], capture_output=True)
    if PLIST.exists():
        PLIST.unlink()
    say(OK, "service removed")


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--yes", action="store_true", help="accept defaults, no prompts")
    ap.add_argument("--install-service", action="store_true",
                    help="install auto-start service (launchd on macOS, Task Scheduler on Windows) and exit")
    ap.add_argument("--uninstall-service", action="store_true",
                    help="remove auto-start service and exit")
    a = ap.parse_args()

    if a.uninstall_service:
        uninstall_service(); return 0
    if a.install_service:
        install_service(); return 0

    print("aside-relay setup")
    if not check_prereqs():
        print("\nfix the ✗ items above, then re-run.")
        return 1
    ensure_token()
    configure(a.yes)

    print("\n[5/5] Run it")
    if sys.platform in ("darwin", "win32") and yesno(
            "Install as a service (auto-start at login)?", False, a.yes):
        install_service()
    else:
        py = "python" if os.name == "nt" else "python3"
        say(OK, f"manual start:  {py} {REPO / 'server.py'}")
    print(f"\nDone. Open http://127.0.0.1:8799/ — on localhost the token is picked up "
          f"automatically.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
