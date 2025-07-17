import os
from dotenv import load_dotenv

load_dotenv()

# Telegram settings
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

# File paths
EXCEL_WEEKLY = 'weekly.xlsx'
EXCEL_MONTHLY = 'monthly.xlsx'     # ежемесячный отчет (пример)
BINDINGS_FILE = 'bindings.json'
DB_FILE = 'weekly_results.db'
TEMP_DIR = 'temp'