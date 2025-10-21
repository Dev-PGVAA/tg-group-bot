import os
import sys
import time
import shutil
import signal
import logging
import subprocess

# Настраиваем логгер
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class TmuxBotManager:
    def __init__(self):
        self.session_name = "tg-bots"
        self.bot_pane = "bot"
        self.forwarder_pane = "forwarder"
        
    def check_tmux(self):
        """Проверяем наличие tmux"""
        if not shutil.which("tmux"):
            logger.error("❌ tmux не установлен. Установите: sudo apt install tmux (или brew install tmux)")
            return False
        return True
        
    def create_session(self):
        """Создаем tmux сессию с двумя окнами"""
        try:
            # Удаляем существующую сессию, если есть
            subprocess.run(["tmux", "kill-session", "-t", self.session_name], 
                         capture_output=True, check=False)
            
            # Создаем новую сессию с первым окном
            subprocess.run([
                "tmux", "new-session", "-d", "-s", self.session_name,
                "-n", self.bot_pane, "bash"
            ], check=True)
            
            # Создаем второе окно
            subprocess.run([
                "tmux", "new-window", "-t", self.session_name,
                "-n", self.forwarder_pane, "bash"
            ], check=True)
            
            # Разделяем окна на панели
            subprocess.run([
                "tmux", "split-window", "-h", "-t", f"{self.session_name}:{self.bot_pane}",
                "bash"
            ], check=True)
            
            subprocess.run([
                "tmux", "split-window", "-h", "-t", f"{self.session_name}:{self.forwarder_pane}",
                "bash"
            ], check=True)
            
            # Настраиваем панели
            subprocess.run([
                "tmux", "select-layout", "-t", f"{self.session_name}:{self.bot_pane}", "tiled"
            ], check=True)
            
            subprocess.run([
                "tmux", "select-layout", "-t", f"{self.session_name}:{self.forwarder_pane}", "tiled"
            ], check=True)
            
            logger.info("✅ Tmux сессия создана с двумя окнами")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Ошибка создания tmux сессии: {e}")
            return False
            
    def start_bot(self):
        """Запускаем Telegram бота в первой панели"""
        try:
            bot_cmd = f"cd {os.getcwd()} && python3 src/bot.py"
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.session_name}:bot",
                f"echo '🚀 Запускаю DiedOnSteroidsBot...'", "Enter"
            ], check=True)
            time.sleep(1)
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.session_name}:bot",
                bot_cmd, "Enter"
            ], check=True)
            logger.info("✅ DiedOnSteroidsBot запущен в первой панели")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Ошибка запуска бота: {e}")
            
    def start_forwarder(self):
        """Запускаем Forwarder во втором окне"""
        try:
            forwarder_cmd = f"cd {os.getcwd()} && python3 src/forwarder.py"
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.session_name}:{self.forwarder_pane}",
                f"echo '🚀 Запускаю Forwarder...'", "Enter"
            ], check=True)
            time.sleep(1)
            subprocess.run([
                "tmux", "send-keys", "-t", f"{self.session_name}:{self.forwarder_pane}",
                forwarder_cmd, "Enter"
            ], check=True)
            logger.info("✅ Forwarder запущен во втором окне")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Ошибка запуска forwarder: {e}")
            
    def attach_session(self):
        """Подключаемся к tmux сессии"""
        try:
            logger.info("🔗 Подключаюсь к tmux сессии...")
            logger.info("💡 Управление:")
            logger.info("   - Ctrl+B, затем 0/1 - переключение между окнами")
            logger.info("   - Ctrl+B, затем стрелки - переключение между панелями")
            logger.info("   - Ctrl+B, затем D - отключиться (боты продолжат работать)")
            logger.info("   - Ctrl+C - остановить текущий бот")
            logger.info("   - exit - закрыть панель")
            
            subprocess.run(["tmux", "attach-session", "-t", self.session_name])
            
        except subprocess.CalledProcessError as e:
            logger.error(f"❌ Ошибка подключения к сессии: {e}")
        except KeyboardInterrupt:
            logger.info("📡 Отключение от сессии...")
            
    def start_bots(self):
        """Запуск обоих ботов в tmux"""
        if not self.check_tmux():
            return False
            
        if not self.create_session():
            return False
            
        # Запускаем ботов
        self.start_bot()
        time.sleep(2)
        self.start_forwarder()
        
        logger.info("✅ Оба бота запущены в отдельных панелях!")
        
        # Подключаемся к сессии
        self.attach_session()
        
        return True
        
    def stop_bots(self):
        """Останавливаем все боты"""
        try:
            logger.info("🛑 Останавливаю ботов...")
            subprocess.run(["tmux", "kill-session", "-t", self.session_name], 
                         capture_output=True, check=False)
            logger.info("✅ Боты остановлены")
        except Exception as e:
            logger.error(f"❌ Ошибка остановки: {e}")
            
    def show_status(self):
        """Показываем статус сессии"""
        try:
            result = subprocess.run([
                "tmux", "list-sessions", "-F", "#{session_name}: #{session_windows} windows"
            ], capture_output=True, text=True, check=True)
            
            if self.session_name in result.stdout:
                logger.info(f"📊 Статус: {result.stdout.strip()}")
            else:
                logger.info("📊 Сессия не активна")
                
        except subprocess.CalledProcessError:
            logger.info("📊 tmux не запущен")

def signal_handler(signum, frame):
    """Обработчик сигналов для корректного завершения"""
    logger.info(f"📡 Получен сигнал {signum}, завершаю работу...")
    sys.exit(0)

def main():
    """Главная функция"""
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    manager = TmuxBotManager()
    
    # Проверяем аргументы командной строки
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "stop":
            manager.stop_bots()
            return
        elif command == "status":
            manager.show_status()
            return
        elif command == "attach":
            try:
                subprocess.run(["tmux", "attach-session", "-t", manager.session_name])
            except KeyboardInterrupt:
                logger.info("📡 Отключение от сессии...")
            return
        elif command == "help":
            print("""
🤖 Telegram Bot Manager

Использование:
  python3 main.py          - Запустить ботов в tmux
  python3 main.py stop     - Остановить всех ботов
  python3 main.py status   - Показать статус
  python3 main.py attach   - Подключиться к сессии
  python3 main.py help     - Показать эту справку

Управление в tmux:
  Ctrl+B, затем стрелки    - Переключение между панелями
  Ctrl+B, затем D          - Отключиться (боты продолжат работать)
  Ctrl+C                   - Остановить текущий бот
  exit                     - Закрыть панель
            """)
            return
    
    try:
        if not manager.start_bots():
            logger.error("❌ Не удалось запустить ботов")
            sys.exit(1)
    except KeyboardInterrupt:
        logger.info("📡 Получен Ctrl+C, завершаю работу...")
        manager.stop_bots()
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        manager.stop_bots()
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 До свидания!")
    except Exception as e:
        logger.error(f"💥 Фатальная ошибка: {e}")
        sys.exit(1)

