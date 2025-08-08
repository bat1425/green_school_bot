import os
from dotenv import load_dotenv

# ──────────────────────── Загрузка переменных окружения (если используются) ────────────────────────
load_dotenv()

# ──────────────────────── Настройки Telegram ────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# ──────────────────────── Пути к файлам ────────────────────────
EXCEL_WEEKLY = 'weekly.xlsx'       # 📄 Еженедельный Excel-файл
EXCEL_MONTHLY = 'monthly.xlsx'     # 📄 Ежемесячный Excel-файл
BINDINGS_FILE = 'bindings.json'    # 👤 Привязки chat_id → телефон
DB_FILE = 'weekly_results.db'      # 🗃️ Основная база данных SQLite
TEMP_DIR = 'temp'                  # 📁 Каталог для временных PDF/файлов
