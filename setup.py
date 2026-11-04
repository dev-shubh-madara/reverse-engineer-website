"""One-command setup: checks Ollama, offers to install it, pulls the model, starts the scanner."""
import os
import platform
import shutil
import subprocess
import sys
import webbrowser

MODEL = os.getenv("RE_MODEL", "qwen2.5-coder:7b")


def ask(q: str) -> bool:
    return input(f"{q} [y/N] ").strip().lower() in ("y", "yes")


def ensure_ollama():
    if shutil.which("ollama"):
        print("Ollama found.")
        return
    print("Ollama is not installed (it runs the local AI model).")
    system = platform.system()
    if system == "Linux" and ask("Install it now with the official script (curl ollama.com/install.sh | sh)?"):
        subprocess.run("curl -fsSL https://ollama.com/install.sh | sh", shell=True, check=True)
    else:
        print("Download it from https://ollama.com/download, install it, then run this script again.")
        if system in ("Windows", "Darwin") and ask("Open the download page?"):
            webbrowser.open("https://ollama.com/download")
        sys.exit(0)


def ensure_model():
    have = subprocess.run(["ollama", "list"], capture_output=True, text=True).stdout
    if MODEL.split(":")[0] in have:
        print(f"Model {MODEL} found.")
        return
    if ask(f"Download model {MODEL} (several GB)?"):
        subprocess.run(["ollama", "pull", MODEL], check=True)
    else:
        print("Skipping. The scan still works, but without the local AI summary.")


def main():
    ensure_ollama()
    ensure_model()
    from scanner.server import main as serve
    serve()


if __name__ == "__main__":
    main()
