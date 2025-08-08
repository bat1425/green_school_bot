import os
from datetime import datetime
import pandas as pd
import telebot
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler

from config import BOT_TOKEN, ADMIN_ID, EXCEL_WEEKLY, EXCEL_MONTHLY
from background import keep_alive
from utils import (
    load_bindings, save_bindings,
    get_student_data, format_results,
    load_monthly_data, find_chat_id_by_name
)
from db import (
    init_db, save_weekly_results,
    save_monthly_results, get_all_weekly_results, get_all_monthly_results
)
from report import generate_progress_pdf
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

bot = telebot.TeleBot(BOT_TOKEN)
init_db()
os.makedirs('temp', exist_ok=True)

# ───────────────────────────── Еженедельная рассылка ─────────────────────────────

def weekly_broadcast():
    bindings = load_bindings()
    count = 0
    date_str = datetime.now().strftime("%Y-%m-%d")

    for cid, phone in bindings.items():
        _, rows = get_student_data(phone)
        if rows is None or rows.empty:
            print(f"📭 Нет данных для chat_id {cid} ({phone})")
            continue

        for _, row in rows.iterrows():
            name = row['Имя ученика']
            try:
                results = row.drop(['Имя ученика', 'Телефон родителя'], errors='ignore').astype(float).to_dict()
            except Exception as e:
                print(f"⚠️ Ошибка в данных ученика {name}: {e}")
                continue

            results_percent = {k: round(v * 100) for k, v in results.items()}
            save_weekly_results(name, results, date_str)

            text_lines = [f"🧪 {subject.strip()}: {score}%" for subject, score in results_percent.items()]
            text = f"📅 Итоги недели для *{name}*:\n\n" + "\n".join(text_lines)

            try:
                bot.send_message(cid, text, parse_mode='Markdown')
                print(f"✅ Отправлено {name} → {cid}")
                count += 1
            except Exception as e:
                print(f"❌ Ошибка отправки для chat_id {cid}: {e}")
    return count


# ───────────────────────────── Команды ─────────────────────────────


# Команда /start
@bot.message_handler(commands=['start'])
def handle_start(message):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📝 Зарегистрироваться", callback_data='register'))
    markup.add(InlineKeyboardButton("📊 Результаты недели", callback_data='results'))
    markup.add(InlineKeyboardButton("📈 Прогресс ", callback_data='progress'))

    text = (
        "👋 Добро пожаловать!\n\n"
        "Я помогу вам получать результаты вашего ребёнка.\n\n"
        "👇 Выберите действие:"
    )
    bot.send_message(message.chat.id, text, reply_markup=markup)

# Обработка нажатий кнопок
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    chat_id = call.message.chat.id
    if call.data == 'register':
        msg = bot.send_message(chat_id, "📱 Введите новый номер телефона (9 цифр):")
        bot.register_next_step_handler(msg, register_phone)
    elif call.data == 'results':
        handle_results(call.message)
    elif call.data == 'progress':
        handle_progress(call.message)

# Команда /register (если кто-то всё же введёт вручную)
@bot.message_handler(commands=['register'])
def handle_register(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "📱 Введите новый номер телефона (9 цифр):")
    bot.register_next_step_handler(msg, register_phone)


# Обработка номера
def register_phone(message):
    phone = message.text.strip()
    chat_id = str(message.chat.id)

    if not phone.isdigit() or len(phone) != 9:
        bot.send_message(chat_id, "❗️ Неверный номер. Введите ровно 9 цифр. Начните заново с /register.")
        return

    bindings = load_bindings()
    bindings[chat_id] = phone
    save_bindings(bindings)
    bot.send_message(chat_id, "✅ Вы успешно зарегистрированы!")


@bot.message_handler(commands=['results'])
def handle_results(message):
    chat_id = str(message.chat.id)
    bindings = load_bindings()
    if chat_id not in bindings:
        bot.send_message(chat_id, "❗️ Сначала зарегистрируйтесь: /register")
        return
    phone = bindings[chat_id]
    _, rows = get_student_data(phone)
    if rows is None or rows.empty:
        bot.send_message(chat_id, "😞 Нет данных.")
        return
    for _, row in rows.iterrows():
        text = format_results(row['Имя ученика'], row)
        bot.send_message(chat_id, text, parse_mode='Markdown')


@bot.message_handler(commands=['broadcast'])
def handle_broadcast(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Только админ может.")
        return
    count = weekly_broadcast()
    bot.reply_to(message, f"✅ Рассылка завершена. Отправлено: {count}")


@bot.message_handler(commands=['monthly_report'])
def handle_monthly_report(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Только админ может.")
        return
    try:
        monthly_df = load_monthly_data()
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
                f"📅 *Месячный отчёт для {name}*:\n\n"
                f"📚 Таджикский язык: {row['Таджикский язык']} из 75\n"
                f"🌱 Биология: {row['Биология']} из 150\n"
                f"🧪 Химия: {row['Химия']} из 175\n"
                f"⚡️ Физика: {row['Физика']} из 100\n"
                f"📊 Общий балл: {row['Общий балл']} из 500\n"
                f"✅ Процент: {row['Общий процент']}%"
            )
            results_dict = {
                'таджикский язык': row['Таджикский язык'],
                'биология': row['Биология'],
                'химия': row['Химия'],
                'физика': row['Физика'],
                'общий балл': row['Общий балл'],  
                'общий процент': row['Общий процент'],
            }
            #save_monthly_results(name, results_dict, datetime.now().strftime("%Y-%m-%d"))
            bot.send_message(cid, text, parse_mode='Markdown')
            sent += 1

        bot.reply_to(message, f"✅ Месячный отчёт отправлен: {sent}")
    except Exception as e:
        bot.reply_to(message, f"⚠️ Ошибка: {e}")


@bot.message_handler(commands=['progress'])
def handle_progress(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📄 Недельный прогресс", "📄 Месячный прогресс", "📄 Оба файла")
    bot.send_message(message.chat.id, "📊 Какой отчёт хотите получить?", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text in ["📄 Недельный прогресс", "📄 Месячный прогресс", "📄 Оба файла"])
def handle_progress_choice(message):
    if message.text == "📄 Недельный прогресс":
        handle_progress_weekly(message)
    elif message.text == "📄 Месячный прогресс":
        handle_progress_monthly(message)
    elif message.text == "📄 Оба файла":
        handle_progress_combined(message)


def handle_progress_weekly(message):
    chat_id = str(message.chat.id)
    bindings = load_bindings()
    if chat_id not in bindings:
        bot.send_message(chat_id, "❗ Сначала зарегистрируйтесь: /register")
        return

    phone = bindings[chat_id]
    _, rows = get_student_data(phone)
    if rows is None or rows.empty:
        bot.send_message(chat_id, "😞 Данных не найдено.")
        return

    for _, row in rows.iterrows():
        name = row['Имя ученика']
        records = get_all_weekly_results(name)
        if not records:
            bot.send_message(chat_id, f"📭 Нет еженедельных данных для {name}.")
            continue

        data = {}
        for subj, mark, date in records:
            data.setdefault(date, {})[subj] = mark

        structured = [{'date': d, 'subjects': s} for d, s in sorted(data.items())]
        try:
            pdf_path = generate_progress_pdf(name, structured, report_type="weekly")
            with open(pdf_path, 'rb') as f:
                bot.send_document(chat_id, f, caption=f"📄 Еженедельный прогресс для {name}")
        except Exception as e:
            bot.send_message(chat_id, f"⚠ Ошибка PDF: {e}")


def handle_progress_monthly(message):
    chat_id = str(message.chat.id)
    bindings = load_bindings()
    if chat_id not in bindings:
        bot.send_message(chat_id, "❗ Сначала зарегистрируйтесь: /register")
        return

    phone = bindings[chat_id]
    _, rows = get_student_data(phone)
    if rows is None or rows.empty:
        bot.send_message(chat_id, "😞 Данных не найдено.")
        return

    for _, row in rows.iterrows():
        name = row['Имя ученика']
        records = get_all_monthly_results(name)
        if not records:
            bot.send_message(chat_id, f"📭 Нет ежемесячных данных для {name}.")
            continue

        data = {}
        for subj, score, date in records:
            data.setdefault(date, {})[subj] = score

        structured = [{'date': d, 'subjects': s} for d, s in sorted(data.items())]
        try:
            pdf_path = generate_progress_pdf(name, structured, report_type="monthly")
            with open(pdf_path, 'rb') as f:
                bot.send_document(chat_id, f, caption=f"📄 Ежемесячный прогресс для {name}")
        except Exception as e:
            bot.send_message(chat_id, f"⚠ Ошибка PDF: {e}")


def handle_progress_combined(message):
    chat_id = str(message.chat.id)
    bindings = load_bindings()
    if chat_id not in bindings:
        bot.send_message(chat_id, "❗ Сначала зарегистрируйтесь: /register")
        return

    phone = bindings[chat_id]
    _, rows = get_student_data(phone)
    if rows is None or rows.empty:
        bot.send_message(chat_id, "😞 Данных не найдено.")
        return

    for _, row in rows.iterrows():
        name = row['Имя ученика']
        has_data = False

        weekly = get_all_weekly_results(name)
        if weekly:
            weekly_data = {}
            for subj, mark, date in weekly:
                weekly_data.setdefault(date, {})[subj] = mark
            structured_weekly = [{'date': d, 'subjects': s} for d, s in sorted(weekly_data.items())]
            try:
                path = generate_progress_pdf(name + "_weekly", structured_weekly, report_type="weekly")
                with open(path, 'rb') as f:
                    bot.send_document(chat_id, f, caption=f"📄 Еженедельный прогресс: {name}")
                has_data = True
            except Exception as e:
                bot.send_message(chat_id, f"⚠ PDF ошибка (weekly): {e}")

        monthly = get_all_monthly_results(name)
        if monthly:
            monthly_data = {}
            for subj, score, date in monthly:
                monthly_data.setdefault(date, {})[subj] = score
            structured_monthly = [{'date': d, 'subjects': s} for d, s in sorted(monthly_data.items())]
            try:
                path = generate_progress_pdf(name + "_monthly", structured_monthly, report_type="monthly")
                with open(path, 'rb') as f:
                    bot.send_document(chat_id, f, caption=f"📄 Ежемесячный прогресс: {name}")
                has_data = True
            except Exception as e:
                bot.send_message(chat_id, f"⚠ PDF ошибка (monthly): {e}")

        if not has_data:
            bot.send_message(chat_id, f"📭 Нет данных для {name}.")




@bot.message_handler(content_types=['document'])
def handle_file_upload(message):
    if message.from_user.id != ADMIN_ID:
        bot.reply_to(message, "⛔ Только админ может загружать файлы.")
        return

    file_name = message.document.file_name.lower()
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
        bot.reply_to(message, f"✅ Файл сохранён как *{label}* (`{path}`).", parse_mode='Markdown')

        if label == 'еженедельный':
            df = pd.read_excel(path, dtype=str)
            date_str = datetime.now().strftime("%Y-%m-%d")
            for _, row in df.iterrows():
                name = row.get('Имя ученика')
                if not name:
                    continue
                results = row.drop(labels=['Имя ученика', 'Телефон родителя'], errors='ignore').to_dict()
                save_weekly_results(name, results, date_str)
        elif label == 'ежемесячный':
            from utils import load_monthly_data

            df = load_monthly_data(path)

            date_str = datetime.now().strftime("%Y-%m-%d")
            for _, row in df.iterrows():
                name = row.get('Имя ученика')
                if not name:
                    continue
                try:
                    results_dict = {
                        'таджикский язык': float(row.get('Таджикский язык', 0)),
                        'биология': float(row.get('Биология', 0)),
                        'химия': float(row.get('Химия', 0)),
                        'физика': float(row.get('Физика', 0)),
                        'общий балл': float(row.get('Общий балл', 0)),
                        'общий процент': float(row.get('Общий процент', 0)),
                    }
                    save_monthly_results(name, results_dict, date_str)
                except Exception as e:
                    print(f"⚠ Ошибка при сохранении месячных данных для {name}: {e}")


    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка при загрузке: {e}")



@bot.message_handler(commands=['get_excel'])
def handle_get_excel(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("📤 Weekly", "📤 Monthly")
    bot.send_message(message.chat.id, "📁 Какой файл отправить?", reply_markup=markup)


@bot.message_handler(func=lambda message: message.text in ["📤 Weekly", "📤 Monthly"])
def send_excel_file(message):
    if message.text == "📤 Weekly":
        path = EXCEL_WEEKLY
        label = "Weekly"
    else:
        path = EXCEL_MONTHLY
        label = "Monthly"

    if not os.path.exists(path):
        bot.send_message(message.chat.id, f"❌ Файл {label} ещё не загружен.")
        return

    try:
        with open(path, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"📄 Excel-файл: {label}")
    except Exception as e:
        bot.send_message(message.chat.id, f"⚠ Ошибка при отправке: {e}")


# ───────────────────────────── Планировщик и запуск ─────────────────────────────

scheduler = BackgroundScheduler()
scheduler.add_job(weekly_broadcast, 'cron', day_of_week='sun', hour=10, minute=0)
scheduler.start()

keep_alive()
print("🤖 Бот запущен...")
bot.polling(none_stop=True)
