import json
import os
import pandas as pd
from config import EXCEL_WEEKLY, BINDINGS_FILE


def load_bindings():
    if os.path.exists(BINDINGS_FILE):
        try:
            with open(BINDINGS_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}


def save_bindings(bindings):
    with open(BINDINGS_FILE, 'w') as f:
        json.dump(bindings, f)


def get_student_data(phone):
    """
    Загружает weekly Excel и возвращает полный DataFrame и строки по точному номеру телефона.
    """
    if not os.path.exists(EXCEL_WEEKLY):
        return None, None

    df = pd.read_excel(EXCEL_WEEKLY, dtype={'Телефон родителя': str})
    # очистка номера
    df['Телефон родителя'] = (
        df['Телефон родителя']
        .astype(str)
        .str.strip()
        .str.replace(' ', '', regex=False)
        .str.replace('\u200b', '', regex=False)
    )
    phone_clean = phone.strip().replace(' ', '').replace('\u200b', '')

    # отладочный вывод
    print(f"Телефоны из файла после очистки: {df['Телефон родителя'].tolist()}")
    print(f"Ищем номер: {phone_clean}")

    rows = df[df['Телефон родителя'] == phone_clean]
    return df, rows


def format_results(name, data, emoji="🔹"):
    results = data.drop(['Имя ученика', 'Телефон родителя'], errors='ignore')
    text = f"*Результаты для {name}:*\n"
    for subject, mark in results.items():
        text += f"{emoji} {subject}: {mark}\n"
    return text


def load_monthly_data(path=None):
    """
    Загружает ежемесячный отчет из Excel (B5, E5, H5, K5, N5, O5, P5 и далее).
    """
    path = path or EXCEL_MONTHLY
    df = pd.read_excel(path, header=None)
    data = {
        'Имя ученика': df.loc[4:, 1],
        'Таджикский': df.loc[4:, 4],
        'Биология': df.loc[4:, 7],
        'Химия': df.loc[4:, 10],
        'Физика': df.loc[4:, 13],
        'Общий балл': df.loc[4:, 14],
        'Процент': df.loc[4:, 15],
    }
    r = pd.DataFrame(data)
    r = r.dropna(subset=['Имя ученика']).reset_index(drop=True)
    return r


def find_chat_id_by_name(name, bindings, student_df):
    """
    Находит chat_id по имени ученика через bindings и student_df.
    student_df должен содержать 'Имя ученика' и 'Телефон родителя'.
    """
    matches = student_df[student_df['Имя ученика'].str.lower() == name.lower()]
    if matches.empty:
        return None
    phone = matches.iloc[0]['Телефон родителя']
    for cid, p in bindings.items():
        if p.strip() == phone.strip():
            return cid
    return None