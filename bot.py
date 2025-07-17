import os
import json
import pandas as pd
import telebot
from telebot import types
from datetime import datetime
from config import BOT_TOKEN, ADMIN_ID, EXCEL_WEEKLY, EXCEL_MONTHLY
from utils import (
    load_bindings, save_bindings,
    get_student_data, format_results,
    load_monthly_data, find_chat_id_by_name
)
from db import init_db, save_weekly_results, get_monthly_results
from report import generate_progress_pdf
from apscheduler.schedulers.background import BackgroundScheduler

# Инициализация
bot = telebot.TeleBot(BOT_TOKEN)
init_db()
if not os.path.exists('temp'):
    os.makedirs('temp')

# Еженедельная рассылка
def weekly_broadcast():
    bindings = load_bindings()
    df, _ = get_student_data("")
    if df is None:
        return 0
    count = 0
    for cid, phone in bindings.items():
        _, rows = get_student_data(phone)
        if rows.empty:
            continue
        for _, row in rows.iterrows():
            name = row['Имя ученика']
            results = row.drop(['Имя ученика', 'Телефон родителя']).to_dict()
            save_weekly_results(name, results)
            text = f"📅 Итоги недели для *{name}*:\n" + format_results(name, row, emoji='🧪')
            try:
                bot.send_message(cid, text, parse_mode='Markdown')
                count += 1
            except:
                pass
    return count

# Команды бота
@bot.message_handler(commands=['start'])
def handle_start(message):
    text = (
        "👋 Добро пожаловать!\n\n"
        "Я помогу вам получать результаты вашего ребёнка.\n\n"
        "Доступные команды:\n"
        "/register — Зарегистрироваться\n"
        "/results — Получить результаты за текущую неделю\n"
        "/progress — PDF-прогресс за месяц\n"
        "(для админа) /broadcast, /monthly_report\n"
    )
    bot.send_message(message.chat.id, text)

@bot.message_handler(commands=['register'])
def handle_register(message):
    msg = bot.send_message(message.chat.id, "📱 Введите номер телефона (+992...):")
    bot.register_next_step_handler(msg, register_phone)

def register_phone(message):
    phone = message.text.strip()
    chat_id = str(message.chat.id)
    if not phone.startswith('+992'):
        bot.send_message(chat_id, "❗ Неверный формат. Начните заново с /register.")
        return
    bindings = load_bindings()
    bindings[chat_id] = phone
    save_bindings(bindings)
    bot.send_message(chat_id, "✅ Вы зарегистрированы!")

@bot.message_handler(commands=['results'])
def handle_results(message):
    chat_id = str(message.chat.id)
    bindings = load_bindings()
    if chat_id not in bindings:
        bot.send_message(chat_id, "❗ Сначала зарегистрируйтесь: /register")
        return
    phone = bindings[chat_id]
    df, rows = get_student_data(phone)
    if df is None:
        bot.send_message(chat_id, "⚠️ Нет weekly данных. Админ еще не загрузил файл.")
        return
    if rows.empty:
        bot.send_message(chat_id, "🙁 Ученик не найден.")
        return
    for _, row in rows.iterrows():
        bot.send_message(
            chat_id,
            format_results(row['Имя ученика'], row),
            parse_mode='Markdown'
        )

@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Только админ может.")
        return
    count = weekly_broadcast()
    bot.reply_to(message, f"✅ Еженедельная рассылка завершена. Отправлено: {count}")

@bot.message_handler(commands=['monthly_report'])
def handle_monthly_report(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Только админ может.")
        return
    try:
        monthly_df = load_monthly_data(EXCEL_MONTHLY)
        student_df = pd.read_excel(EXCEL_WEEKLY, dtype={'Телефон родителя': str})
        student_df['Имя ученика'] = student_df['Имя ученика'].str.strip()
        student_df['Телефон родителя'] = student_df['Телефон родителя'].str.strip()
        bindings = load_bindings()
        sent = 0
        for _, row in monthly_df.iterrows():
            name = str(row['Имя ученика']).strip()
            cid = find_chat_id_by_name(name, bindings, student_df)
            if not cid:
                continue
            text = (
                f"📅 Месячный отчёт для *{name}*:\n"
                f"📚 Таджикский: {row['Таджикский']}\n"
                f"🌱 Биология: {row['Биология']}\n"
                f"🧪 Химия: {row['Химия']}\n"
                f"⚡️ Физика: {row['Физика']}\n"
                f"📊 Общий балл: {row['Общий балл']}\n"
                f"✅ Процент: {row['Процент']}"
            )
            bot.send_message(cid, text, parse_mode='Markdown')
            sent += 1
        bot.reply_to(message, f"✅ Месячный отчёт отправлен: {sent}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка: {e}")

@bot.message_handler(commands=['progress'])
def handle_progress(message):
    chat_id = str(message.chat.id)
    bindings = load_bindings()
    if chat_id not in bindings:
        bot.send_message(chat_id, "❗ Сначала зарегистрируйтесь: /register")
        return
    phone = bindings[chat_id]
    _, rows = get_student_data(phone)
    if rows.empty:
        bot.send_message(chat_id, "🙁 Ученик не найден.")
        return
    for _, row in rows.iterrows():
        name = row['Имя ученика']
        raw = get_monthly_results(name)
        
        print(get_monthly_results(name))

        if not raw:
            bot.send_message(chat_id, "🔍 Нет данных за месяц.")
            return
        recs = []
        curr = None
        group = {}
        for subj, mark, date in raw:
            if date != curr:
                if group:
                    recs.append({'date': curr, 'subjects': group.copy()})
                curr = date
                group = {}
            group[subj] = mark
        if group:
            recs.append({'date': curr, 'subjects': group.copy()})
        pdf_path = generate_progress_pdf(name, recs)
        with open(pdf_path, 'rb') as f:
            bot.send_document(chat_id, f)

def process_weekly_file(file_path):
    df = pd.read_excel(file_path, dtype=str)
    date_str = datetime.now().strftime("%Y-%m-%d")
    for _, row in df.iterrows():
        name = row.get('Имя ученика')
        if not name:
            continue
        results = row.drop(labels=['Имя ученика', 'Телефон родителя'], errors='ignore').to_dict()
        save_weekly_results(name, results, date_str)

@bot.message_handler(content_types=['document'])
def handle_file_upload(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Только админ может загружать файлы.")
        return

    file_name = message.document.file_name.lower()
    print("📥 Получен файл:", file_name)

    if 'week' in file_name or 'неделя' in file_name:
        path = EXCEL_WEEKLY
        label = 'еженедельный'
    elif 'month' in file_name or 'месяц' in file_name or 'итог' in file_name:
        path = EXCEL_MONTHLY
        label = 'ежемесячный'
    else:
        bot.reply_to(message, "⚠️ Имя файла должно содержать 'week'/'неделя' или 'month'/'месяц'/'итог'.")
        return

    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info.file_path)
        with open(path, 'wb') as f:
            f.write(downloaded)
        bot.reply_to(message, f"✅ Файл успешно сохранён как *{label}* (`{path}`).", parse_mode='Markdown')

        # Если это еженедельный файл, вызываем обработку и запись в базу
        if label == 'еженедельный':
            process_weekly_file(path)

    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при загрузке: {e}")


# Планировщик
scheduler = BackgroundScheduler()
scheduler.add_job(weekly_broadcast, 'cron', day_of_week='sun', hour=10, minute=0)
scheduler.start()

print("🤖 Бот запущен...")
bot.polling(none_stop=True)
