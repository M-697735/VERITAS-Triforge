import os
import sys
import argparse
import socket
import subprocess
import webbrowser
import threading
import time
import uvicorn

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.storage import reset_history_file

def get_pid_on_port(port: int = 8000) -> str:
    """Finds the PID of the process listening on the specified port."""
    try:
        if sys.platform == "win32":
            output = subprocess.check_output("netstat -ano -p tcp", shell=True, text=True, stderr=subprocess.DEVNULL)
            for line in output.splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0].upper() == "TCP":
                    local_addr = parts[1]
                    state = parts[3].upper() if len(parts) == 5 else parts[-2].upper()
                    pid = parts[-1]
                    if (local_addr.endswith(f":{port}") or f":{port}" in local_addr) and state == "LISTENING":
                        return pid
        else:
            output = subprocess.check_output(["lsof", "-ti", f":{port}"], text=True, stderr=subprocess.DEVNULL)
            pids = output.strip().split()
            if pids:
                return pids[0]
    except Exception:
        pass
    return "<pid>"

def check_port_free(port: int = 8000, host: str = "127.0.0.1") -> bool:
    """Checks whether the given port is available for binding."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((host, port))
            return True
        except OSError:
            return False

def open_browser():
    time.sleep(1.5)
    target_url = os.environ.get("VERITAS_URL")
    if not target_url:
        try:
            for p in (3001, 3002, 3003):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.3)
                    if s.connect_ex(("127.0.0.1", p)) == 0:
                        target_url = f"http://localhost:{p}"
                        break
            if not target_url:
                target_url = "http://127.0.0.1:8000"
        except Exception:
            target_url = "http://127.0.0.1:8000"

    try:
        webbrowser.open(target_url)
    except Exception:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VERITAS Email Forensics Backend")
    parser.add_argument("--reset-history", action="store_true", help="Reset history.json to empty on startup")
    args, unknown = parser.parse_known_args()

    # Check whether port 8000 is free before starting
    if not check_port_free(8000):
        pid = get_pid_on_port(8000)
        print(f"Port 8000 is already in use - close the other VERITAS window or run: Stop-Process -Id {pid}")
        sys.exit(1)

    if args.reset_history:
        reset_history_file()
        print("[VERITAS] Persistent case history has been reset to empty.")

    print("VERITAS running at http://127.0.0.1:8000")
    threading.Thread(target=open_browser, daemon=True).start()
    try:
        uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
    except OSError:
        pid = get_pid_on_port(8000)
        print(f"Port 8000 is already in use - close the other VERITAS window or run: Stop-Process -Id {pid}")
        sys.exit(1)


