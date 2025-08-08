import sqlite3
from datetime import datetime
from config import DB_FILE

DB_PATH = DB_FILE

# ──────────────────────── Подключение и инициализация ────────────────────────


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Для доступа к колонкам по имени
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # Таблица еженедельных результатов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS weekly_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            subject TEXT NOT NULL,
            mark TEXT,
            date TEXT NOT NULL
        )
    """)

    # Таблица ежемесячных результатов
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


# ──────────────────────── Сохранение данных ────────────────────────


def save_weekly_results(student_name, results: dict, date_str: str):
    if not results:
        return

    conn = get_connection()
    cur = conn.cursor()
    student_name_clean = student_name.strip().lower()

    for subject, mark in results.items():
        subject_clean = subject.strip().lower()

        # Проверка на дубликат
        cur.execute(
            """
            SELECT COUNT(*) FROM weekly_results
            WHERE student_name = ? AND subject = ? AND date = ?
        """, (student_name_clean, subject_clean, date_str))
        exists = cur.fetchone()[0]

        if exists:
            print(
                f"⚠️ Уже есть: {student_name_clean} — {subject_clean} — {date_str}"
            )
            continue

        # Вставка
        cur.execute(
            """
            INSERT INTO weekly_results (student_name, subject, mark, date)
            VALUES (?, ?, ?, ?)
        """, (student_name_clean, subject_clean, mark, date_str))

        print(f"✅ Добавлено: {student_name_clean} — {subject_clean} — {mark}")

    conn.commit()
    conn.close()


def save_monthly_results(student_name, results: dict, date_str: str):
    if not results:
        return

    conn = get_connection()
    cur = conn.cursor()
    name_clean = student_name.strip().lower()

    for subject, mark in results.items():
        subject_clean = subject.strip().lower()

        cur.execute(
            """
            SELECT COUNT(*) FROM results
            WHERE name = ? AND subject = ? AND date = ?
        """, (name_clean, subject_clean, date_str))
        exists = cur.fetchone()[0]

        if exists:
            print(
                f"⚠️ Уже есть (MONTHLY): {name_clean} — {subject_clean} — {date_str}"
            )
            continue

        cur.execute(
            """
            INSERT INTO results (name, subject, score, date)
            VALUES (?, ?, ?, ?)
        """, (name_clean, subject_clean, mark, date_str))

        print(
            f"✅ Добавлено (MONTHLY): {name_clean} — {subject_clean} — {mark}")

    conn.commit()
    conn.close()


# ──────────────────────── Получение данных ────────────────────────


def get_last_weekly_results(student_name):
    """Результаты за последнюю (самую свежую) неделю"""
    conn = get_connection()
    cur = conn.cursor()
    name_clean = student_name.strip().lower()

    # Получаем последнюю дату
    cur.execute(
        """
        SELECT MAX(date) AS last_date FROM weekly_results
        WHERE student_name = ?
    """, (name_clean, ))
    row = cur.fetchone()

    if not row or not row['last_date']:
        conn.close()
        return []

    last_date = row['last_date']

    # Получаем все предметы по этой дате
    cur.execute(
        """
        SELECT subject, mark, date FROM weekly_results
        WHERE student_name = ? AND date = ?
        ORDER BY subject ASC
    """, (name_clean, last_date))
    rows = cur.fetchall()
    conn.close()
    return [(r['subject'], r['mark'], r['date']) for r in rows]


def get_all_weekly_results(student_name):
    """Все еженедельные результаты ученика"""
    conn = get_connection()
    cur = conn.cursor()
    name_clean = student_name.strip().lower()
    cur.execute(
        """
        SELECT subject, mark, date FROM weekly_results
        WHERE student_name = ?
        ORDER BY date ASC
    """, (name_clean, ))
    rows = cur.fetchall()
    conn.close()
    return [(r['subject'], r['mark'], r['date']) for r in rows]


def get_all_monthly_results(student_name):
    """Все ежемесячные результаты ученика"""
    conn = get_connection()
    cur = conn.cursor()
    name_clean = student_name.strip().lower()
    cur.execute(
        """
        SELECT subject, score, date FROM results
        WHERE name = ?
        ORDER BY date ASC
    """, (name_clean, ))
    rows = cur.fetchall()
    conn.close()
    return [(r['subject'], r['score'], r['date']) for r in rows]


