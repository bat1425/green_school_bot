import json
import os
import pandas as pd
from typing import Tuple, Optional
from config import EXCEL_WEEKLY, EXCEL_MONTHLY, BINDINGS_FILE

# ──────────────────────── Утилита для очистки номера ────────────────────────

def clean_phone(phone: str) -> str:
    """Удаляет пробелы, скрытые символы и приводит номер к нормальной форме."""
    return phone.strip().replace(' ', '').replace('\u200b', '')

# ──────────────────────── Работа с привязками ────────────────────────

def load_bindings() -> dict:
    """Загружает словарь привязок chat_id → телефон из JSON."""
    if os.path.exists(BINDINGS_FILE):
        try:
            with open(BINDINGS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_bindings(bindings: dict) -> None:
    """Сохраняет привязки chat_id → телефон в JSON."""
    with open(BINDINGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(bindings, f, ensure_ascii=False, indent=2)

# ──────────────────────── Получение данных ученика из Excel ────────────────────────

def get_student_data(phone: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
    """
    Загружает Excel-файл и находит строки с указанным номером.
    Возвращает (весь DataFrame, только строки с нужным номером).
    """
    if not phone or not os.path.exists(EXCEL_WEEKLY):
        return None, None

    df = pd.read_excel(EXCEL_WEEKLY, dtype={'Телефон родителя': str})

    if 'Телефон родителя' not in df.columns:
        return df, None

    df['Телефон родителя'] = df['Телефон родителя'].astype(str).apply(clean_phone)
    phone_clean = clean_phone(phone)

    matched_rows = df[df['Телефон родителя'] == phone_clean]
    return df, matched_rows

# ──────────────────────── Форматирование текста результата ────────────────────────

def format_results(name: str, data: pd.Series) -> str:
    """
    Формирует текст для Telegram с результатами ученика.
    """
    subject_emojis = {
        'таджикский язык': '📚',
        'биология': '🌱',
        'химия': '🧪',
        'физика': '⚡️',
        'общий процент': '📊'
    }

    results = data.drop(['Имя ученика', 'Телефон родителя'], errors='ignore')
    results_percent = {}

    for subject, mark in results.items():
        subject_clean = subject.strip().lower()
        try:
            percent = float(mark)
            results_percent[subject_clean] = (
                f"{round(percent * 100)}%" if percent <= 1 else f"{round(percent)}%"
            )
        except (ValueError, TypeError):
            results_percent[subject_clean] = str(mark)

    text = f"*Результаты прошедшей недели для {name}:*\n\n"
    for subject, mark in results_percent.items():
        emoji = subject_emojis.get(subject, '🔹')
        text += f"{emoji} {subject.capitalize()}: {mark}\n"

    return text

# ──────────────────────── Загрузка ежемесячных данных из Excel ────────────────────────

def load_monthly_data(path: Optional[str] = None) -> pd.DataFrame:
    """
    Загружает ежемесячный Excel-файл и преобразует его в DataFrame.
    """
    path = path or EXCEL_MONTHLY
    if not os.path.exists(path):
        return pd.DataFrame()

    df = pd.read_excel(path, header=None)

    data = {
        'Имя ученика': df.loc[4:, 1],
        'Таджикский язык': df.loc[4:, 4],
        'Биология': df.loc[4:, 7],
        'Химия': df.loc[4:, 10],
        'Физика': df.loc[4:, 13],
        'Общий балл': df.loc[4:, 14],
        'Общий процент': df.loc[4:, 15],
    }

    result_df = pd.DataFrame(data)
    result_df = result_df.dropna(subset=['Имя ученика']).reset_index(drop=True)
    return result_df

# ──────────────────────── Поиск chat_id по имени ученика ────────────────────────

def find_chat_id_by_name(name: str, bindings: dict, student_df: pd.DataFrame) -> Optional[str]:
    """
    Находит chat_id по имени ученика, используя привязки и телефон.
    """
    matches = student_df[student_df['Имя ученика'].str.lower() == name.lower()]
    if matches.empty:
        return None

    phone = matches.iloc[0]['Телефон родителя']
    phone_clean = clean_phone(phone)

    for chat_id, bound_phone in bindings.items():
        if clean_phone(bound_phone) == phone_clean:
            return chat_id
    return None
