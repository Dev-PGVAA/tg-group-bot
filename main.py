#!/usr/bin/env python3
"""
📦 Менеджер Telegram ботов (новая структура проекта)

Использование:
    python3 main.py start   - Запустить всех ботов
    python3 main.py stop    - Остановить всех ботов
    python3 main.py restart - Перезапустить всех ботов
    python3 main.py status  - Проверить статус ботов
    python3 main.py logs    - Показать последние логи
"""

import sys
import os
import subprocess
import signal
import time
from pathlib import Path

# --- Конфигурация проекта ---
PROJECT_DIR = Path(__file__).resolve().parent
PID_DIR = PROJECT_DIR / "data" / "pids"
LOG_DIR = PROJECT_DIR / "data" / "logs"

PID_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# --- Боты и WebPanel ---
BOTS = {
    # "Forwarder": "src.bot.forwarder",
    # "Records": "src.bot.sil_bot",
    "WebPanel": "src.webpanel.webpanel",
}

class BotManager:
    def __init__(self):
        pass

    def _pid_file(self, name): return PID_DIR / f"{name.lower()}.pid"
    def _log_file(self, name): return LOG_DIR / f"{name.lower()}.log"

    def is_running(self, name):
        pid_file = self._pid_file(name)
        if not pid_file.exists():
            return False
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            return True
        except (OSError, ValueError, ProcessLookupError):
            pid_file.unlink(missing_ok=True)
            return False

    def get_pid(self, name):
        pid_file = self._pid_file(name)
        return int(pid_file.read_text().strip()) if pid_file.exists() else None

    def start(self):
        for name, module in BOTS.items():
            if self.is_running(name):
                print(f"⚠️  {name} уже запущен (PID: {self.get_pid(name)})")
                continue

            print(f"🚀 Запуск {name}...")
            log_file = open(self._log_file(name), "a")
            process = subprocess.Popen(
                [sys.executable, "-m", module],
                stdout=log_file,
                stderr=subprocess.STDOUT,
                cwd=PROJECT_DIR,
                start_new_session=True
            )
            self._pid_file(name).write_text(str(process.pid))
            print(f"✅ {name} запущен (PID: {process.pid}) — логи: {self._log_file(name)}")

    def stop(self):
        for name in BOTS.keys():
            if not self.is_running(name):
                print(f"⚠️  {name} не запущен")
                continue
            pid = self.get_pid(name)
            print(f"🛑 Остановка {name} (PID: {pid})...")
            try:
                os.kill(pid, signal.SIGTERM)
                for _ in range(10):
                    if not self.is_running(name):
                        break
                    time.sleep(0.5)
                if self.is_running(name):
                    os.kill(pid, signal.SIGKILL)
                self._pid_file(name).unlink(missing_ok=True)
                print(f"✅ {name} остановлен")
            except Exception as e:
                print(f"❌ Ошибка при остановке {name}: {e}")

    def restart(self):
        print("🔄 Перезапуск всех ботов...")
        self.stop()
        time.sleep(1)
        self.start()

    def status(self):
        print("📊 Статус ботов:\n")
        for name in BOTS.keys():
            if self.is_running(name):
                pid = self.get_pid(name)
                print(f"✅ {name}: запущен (PID {pid})")
            else:
                print(f"⚠️  {name}: не запущен")

    def logs(self, name=None, lines=40):
        if name:
            log_file = self._log_file(name)
            if not log_file.exists():
                print(f"❌ Лог {name} не найден")
                return
            print(f"📜 Последние {lines} строк {name}:\n")
            os.system(f"tail -n {lines} {log_file}")
        else:
            print("📜 Все доступные логи:")
            for name in BOTS.keys():
                print(f"  - {name}: {self._log_file(name)}")

def print_help():
    print("""
🤖 Bot Manager — управление Telegram ботами

Использование:
    python3 main.py <команда> [параметры]

Команды:
    start       — запустить всех ботов
    stop        — остановить всех ботов
    restart     — перезапустить всех ботов
    status      — показать состояние
    logs [bot]  — показать последние строки логов
    help        — помощь
""")

def main():
    manager = BotManager()
    if len(sys.argv) < 2:
        print_help()
        return

    cmd = sys.argv[1].lower()
    args = sys.argv[2:] if len(sys.argv) > 2 else []

    if cmd == "start":
        manager.start()
    elif cmd == "stop":
        manager.stop()
    elif cmd == "restart":
        manager.restart()
    elif cmd == "status":
        manager.status()
    elif cmd == "logs":
        manager.logs(args[0] if args else None)
    else:
        print_help()

if __name__ == "__main__":
    main()
