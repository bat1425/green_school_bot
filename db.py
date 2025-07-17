import sqlite3
from datetime import datetime

DB_PATH = 'school_data.db'  # Путь к файлу базы, поменяй под себя

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Для удобного доступа к колонкам по имени
    return conn

def init_db():
    conn = get_connection()
    cur = conn.cursor()
    # Создание таблицы weekly_results, если её нет
    cur.execute("""
    CREATE TABLE IF NOT EXISTS weekly_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_name TEXT NOT NULL,
        subject TEXT NOT NULL,
        mark TEXT,
        date TEXT NOT NULL
    )
    """)
    # Создание таблицы results, если нужна
    cur.execute("""
    CREATE TABLE IF NOT EXISTS results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        subject TEXT NOT NULL,
        score TEXT,
        date TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def get_last_weekly_date(conn):
    cur = conn.cursor()
    cur.execute("SELECT date FROM weekly_results ORDER BY date DESC LIMIT 1")
    row = cur.fetchone()
    if row is None:
        return None
    return datetime.strptime(row['date'], "%Y-%m-%d")

def clear_weekly_results(conn):
    cur = conn.cursor()
    cur.execute("DELETE FROM weekly_results")
    conn.commit()

def save_weekly_results(student_name, results: dict, date_str: str):
    """
    results: dict с ключами — предметы, значениями — оценки
    date_str: строка даты в формате 'YYYY-MM-DD'
    """
    conn = get_connection()
    new_date = datetime.strptime(date_str, "%Y-%m-%d")
    last_date = get_last_weekly_date(conn)

    # Если месяц изменился — очищаем старые данные
    if last_date and last_date.month != new_date.month:
        clear_weekly_results(conn)

    cur = conn.cursor()

    # Удаляем старые записи для этого студента и даты
    cur.execute(
        "DELETE FROM weekly_results WHERE student_name = ? AND date = ?",
        (student_name, date_str)
    )

    # Вставляем новые данные
    for subject, mark in results.items():
        cur.execute(
            "INSERT INTO weekly_results (student_name, subject, mark, date) VALUES (?, ?, ?, ?)",
            (student_name, subject, mark, date_str)
        )
    conn.commit()
    conn.close()

def get_monthly_results(student_name):
    """
    Возвращает список кортежей (subject, mark, date) за текущий месяц для данного студента
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT subject, mark, date FROM weekly_results
        WHERE student_name = ?
        AND strftime('%Y-%m', date) = strftime('%Y-%m', 'now')
        ORDER BY date ASC
    """, (student_name,))
    rows = cur.fetchall()
    conn.close()
    return [(row['subject'], row['mark'], row['date']) for row in rows]
