"""One-command setup: checks Ollama (optional), installs the headless browser, launches the collector UI."""
from __future__ import annotations

import platform
import shutil
import subprocess
import sys
import webbrowser

MODEL = "qwen2.5-coder:7b"


def ask(q: str) -> bool:
    return input(f"{q} [y/N] ").strip().lower() in ("y", "yes")


def ensure_python_deps() -> None:
    try:
        import playwright  # noqa: F401
        import PIL  # noqa: F401
    except ImportError:
        print("Installing Python dependencies...")
        subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)


def ensure_browser() -> None:
    print("Making sure the headless browser is installed (used by the verify loop)...")
    try:
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
    except Exception as e:  # noqa: BLE001
        print(f"Could not auto-install the browser ({e}).")
        print("Run this yourself when you need the verify loop:  python -m playwright install chromium")


def ensure_ollama() -> None:
    """Ollama is optional: it only powers the local 'what looks unfinished' summary during a scan."""
    if shutil.which("ollama"):
        print("Ollama found.")
        have = subprocess.run(["ollama", "list"], capture_output=True, text=True).stdout
        if MODEL.split(":")[0] not in have and ask(f"Download local model {MODEL} (several GB)?"):
            subprocess.run(["ollama", "pull", MODEL], check=True)
        return
    print("\nOllama is optional (local scan summary only). The rebuild + verify loop work without it.")
    if not ask("Set up Ollama now?"):
        return
    if platform.system() == "Linux" and ask("Install with the official script (curl ollama.com/install.sh | sh)?"):
        subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=True)
        if ask(f"Download model {MODEL} (several GB)?"):
            subprocess.run(["ollama", "pull", MODEL], check=True)
    else:
        print("Get it from https://ollama.com/download, then re-run this script.")
        if ask("Open the download page?"):
            webbrowser.open("https://ollama.com/download")


def main() -> None:
    ensure_python_deps()
    ensure_browser()
    ensure_ollama()
    print("\nStarting the collector UI...")
    from scanner.server import main as serve
    serve()


if __name__ == "__main__":
    main()
