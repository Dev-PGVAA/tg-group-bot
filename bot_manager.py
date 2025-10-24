#!/usr/bin/env python3
"""
Менеджер для управления Telegram ботами
Использование:
    python3 bot_manager.py start   - Запустить всех ботов в фоне
    python3 bot_manager.py stop    - Остановить всех ботов
    python3 bot_manager.py restart - Перезапустить всех ботов
    python3 bot_manager.py status  - Проверить статус ботов
    python3 bot_manager.py logs    - Показать последние логи
"""

import sys
import os
import subprocess
import signal
import time
from pathlib import Path

# Конфигурация
PROJECT_DIR = Path(__file__).parent
PID_DIR = PROJECT_DIR / "data" / "pids"
LOG_DIR = PROJECT_DIR / "data" / "logs"
MAIN_SCRIPT = PROJECT_DIR / "src" / "main.py"

# Создаем необходимые директории
PID_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

class BotManager:
    def __init__(self):
        self.pid_file = PID_DIR / "bot.pid"
        self.log_file = LOG_DIR / "bot_manager.log"
        
    def is_running(self):
        """Проверяет, запущен ли бот"""
        if not self.pid_file.exists():
            return False
        
        try:
            with open(self.pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Проверяем существование процесса
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, ValueError, OSError):
            # Процесс не существует, удаляем устаревший PID файл
            if self.pid_file.exists():
                self.pid_file.unlink()
            return False
    
    def get_pid(self):
        """Получает PID запущенного бота"""
        if self.pid_file.exists():
            try:
                with open(self.pid_file, 'r') as f:
                    return int(f.read().strip())
            except (ValueError, OSError):
                return None
        return None
    
    def start(self):
        """Запускает бота в фоновом режиме"""
        if self.is_running():
            print("❌ Бот уже запущен!")
            print(f"   PID: {self.get_pid()}")
            return False
        
        print("🚀 Запуск бота в фоновом режиме...")
        
        # Запускаем процесс в фоне с перенаправлением вывода
        process = subprocess.Popen(
            [sys.executable, str(MAIN_SCRIPT)],
            stdout=open(self.log_file, 'a'),
            stderr=subprocess.STDOUT,
            start_new_session=True,  # Отделяем от текущей сессии
            cwd=PROJECT_DIR
        )
        
        # Сохраняем PID
        with open(self.pid_file, 'w') as f:
            f.write(str(process.pid))
        
        # Даем время на запуск
        time.sleep(2)
        
        if self.is_running():
            print(f"✅ Бот успешно запущен! PID: {process.pid}")
            print(f"   Логи: {self.log_file}")
            print(f"   Для просмотра логов: python3 bot_manager.py logs")
            return True
        else:
            print("❌ Не удалось запустить бота. Проверьте логи:")
            print(f"   tail -f {self.log_file}")
            return False
    
    def stop(self):
        """Останавливает бота"""
        if not self.is_running():
            print("⚠️  Бот не запущен")
            return False
        
        pid = self.get_pid()
        print(f"🛑 Остановка бота (PID: {pid})...")
        
        try:
            # Отправляем SIGTERM для корректного завершения
            os.kill(pid, signal.SIGTERM)
            
            # Ждем завершения
            for i in range(10):
                if not self.is_running():
                    break
                time.sleep(0.5)
            
            # Если не завершился, используем SIGKILL
            if self.is_running():
                print("   Принудительное завершение...")
                os.kill(pid, signal.SIGKILL)
                time.sleep(1)
            
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            print("✅ Бот остановлен")
            return True
            
        except ProcessLookupError:
            print("⚠️  Процесс уже завершен")
            if self.pid_file.exists():
                self.pid_file.unlink()
            return True
        except Exception as e:
            print(f"❌ Ошибка при остановке: {e}")
            return False
    
    def restart(self):
        """Перезапускает бота"""
        print("🔄 Перезапуск бота...")
        self.stop()
        time.sleep(1)
        return self.start()
    
    def status(self):
        """Показывает статус бота"""
        if self.is_running():
            pid = self.get_pid()
            print(f"✅ Бот запущен")
            print(f"   PID: {pid}")
            print(f"   Лог файл: {self.log_file}")
            
            # Показываем использование памяти
            try:
                with open(f'/proc/{pid}/status', 'r') as f:
                    for line in f:
                        if line.startswith('VmRSS:'):
                            print(f"   Память: {line.split()[1]} KB")
                            break
            except:
                pass
        else:
            print("⚠️  Бот не запущен")
    
    def show_logs(self, lines=50):
        """Показывает последние строки логов"""
        if not self.log_file.exists():
            print("⚠️  Лог файл не найден")
            return
        
        print(f"📋 Последние {lines} строк логов:\n")
        try:
            result = subprocess.run(
                ['tail', '-n', str(lines), str(self.log_file)],
                capture_output=True,
                text=True
            )
            print(result.stdout)
        except Exception as e:
            # Если tail не доступен, читаем файл напрямую
            with open(self.log_file, 'r') as f:
                all_lines = f.readlines()
                for line in all_lines[-lines:]:
                    print(line, end='')

def print_help():
    """Выводит справку"""
    print("""
🤖 Менеджер Telegram ботов

Использование:
    python3 bot_manager.py <команда>

Команды:
    start    - Запустить бота в фоновом режиме
    stop     - Остановить бота
    restart  - Перезапустить бота
    status   - Проверить статус бота
    logs     - Показать последние логи (по умолчанию 50 строк)
    help     - Показать эту справку

Примеры:
    python3 bot_manager.py start
    python3 bot_manager.py logs
    """)

def main():
    manager = BotManager()
    
    if len(sys.argv) < 2:
        print_help()
        return
    
    command = sys.argv[1].lower()
    
    commands = {
        'start': manager.start,
        'stop': manager.stop,
        'restart': manager.restart,
        'status': manager.status,
        'logs': lambda: manager.show_logs(int(sys.argv[2]) if len(sys.argv) > 2 else 50),
        'help': print_help
    }
    
    if command in commands:
        commands[command]()
    else:
        print(f"❌ Неизвестная команда: {command}")
        print_help()
        sys.exit(1)

if __name__ == "__main__":
    main()