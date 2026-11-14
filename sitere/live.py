"""The live view: one status line per agent, repainted in place.

Each agent keeps its own line (its own "cursor"), so you watch the whole crew work at
once instead of a single scrolling log. Falls back to plain lines when there is no TTY
(CI, piped output), and to silence when asked.
"""
from __future__ import annotations

import sys
import threading
import time

SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
HIDE, SHOW = "\033[?25l", "\033[?25h"
DIM, RESET, GREEN, CYAN, RED = "\033[2m", "\033[0m", "\033[32m", "\033[36m", "\033[31m"


def shorten(text: str, width: int = 68) -> str:
    text = text.replace("\n", " ").strip()
    return text if len(text) <= width else text[: width - 1] + "…"


class Dashboard:
    """Thread-safe board the agents write their current action to."""

    def __init__(self, n_agents: int, *, mode: str = "auto", stream=None):
        self.stream = stream or sys.stdout
        tty = hasattr(self.stream, "isatty") and self.stream.isatty()
        if mode == "auto":
            mode = "live" if tty else "plain"
        self.mode = mode  # "live" | "plain" | "quiet"
        self.n = n_agents
        self.states = ["idle"] * n_agents
        self.done = 0
        self.total = 0
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._painter = None
        self._frame = 0

    # -- agent-facing updates -------------------------------------------------
    def set(self, agent_id: int, verb: str, detail: str = "") -> None:
        line = verb if not detail else f"{verb} {detail}"
        with self._lock:
            if 0 <= agent_id < self.n:
                self.states[agent_id] = line
            if self.mode == "plain":
                print(f"  agent {agent_id:02d}  {shorten(line)}", file=self.stream, flush=True)

    def tick(self, done: int, total: int) -> None:
        with self._lock:
            self.done, self.total = done, total

    # -- lifecycle ------------------------------------------------------------
    def start(self) -> None:
        if self.mode != "live":
            return
        self.stream.write(HIDE)
        self.stream.write("\n" * (self.n + 1))
        self._painter = threading.Thread(target=self._loop, daemon=True)
        self._painter.start()

    def _loop(self) -> None:
        while not self._stop.is_set():
            self._paint()
            time.sleep(0.12)
        self._paint()

    def _paint(self) -> None:
        with self._lock:
            frame = SPIN[self._frame % len(SPIN)]
            self._frame += 1
            lines = []
            for i, state in enumerate(self.states):
                if state in ("idle", "done"):
                    mark = f"{DIM}•{RESET}"
                    body = f"{DIM}{state}{RESET}"
                else:
                    mark = f"{CYAN}{frame}{RESET}"
                    body = shorten(state)
                lines.append(f"  {mark} agent {i:02d}  {body}")
            bar = f"{GREEN}rebuilt {self.done}/{self.total}{RESET}" if self.total else "starting…"
            block = "\n".join(lines) + f"\n  {bar}"
        up = f"\033[{self.n + 1}A"
        self.stream.write("\r" + up + "\033[J" + block + "\n")
        self.stream.flush()

    def stop(self) -> None:
        if self.mode == "live":
            self._stop.set()
            if self._painter:
                self._painter.join(timeout=1)
            self.stream.write(SHOW)
            self.stream.flush()
