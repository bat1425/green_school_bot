import os
from fpdf import FPDF
from datetime import datetime
from config import TEMP_DIR

# ────────────────────── Константы ──────────────────────
FONT_PATH = 'fonts/DejaVuSans.ttf'  # Убедись, что файл существует
FONT_NAME = 'DejaVu'

# ────────────────────── Класс PDF ──────────────────────

class PDFReport(FPDF):
    def __init__(self, report_type='weekly'):
        super().__init__()
        self.report_type = report_type

    def header(self):
        self.set_font(FONT_NAME, 'B', 16)
        title = 'Еженедельный прогресс ученика' if self.report_type == 'weekly' else 'Ежемесячный прогресс ученика'
        self.cell(0, 10, title, ln=True, align='C')
        self.ln(10)

    def add_student_results(self, student_name, records):
        self.set_font(FONT_NAME, 'B', 12)
        self.cell(0, 10, f"Имя: {student_name}", ln=True)
        self.ln(5)

        if not records:
            self.set_font(FONT_NAME, '', 12)
            self.cell(0, 10, "Нет данных для отображения.", ln=True)
            return

        if self.report_type == 'weekly':
            headers = ["Дата", "Таджикский язык", "Биология", "Физика", "Химия", "Общий процент"]
            col_widths = [30, 42, 25, 25, 25, 37]
        else:
            headers = ["Дата", "Таджикский язык", "Биология", "Химия", "Физика", "Общий балл", "Процент"]
            col_widths = [27, 42, 25, 23, 23, 32, 21]

        for i, header in enumerate(headers):
            self.cell(col_widths[i], 10, header, 1, 0, "C")
        self.ln()

        self.set_font(FONT_NAME, '', 11)

        def fmt(val):
            try:
                fval = float(val)
                return f"{int(fval)}%" if fval > 1 else f"{int(fval * 100)}%"
            except Exception:
                return str(val).strip()

        for rec in records:
            date_str = datetime.strptime(rec['date'], "%Y-%m-%d").strftime("%d.%m.%Y")
            subj = {k.strip().lower(): v for k, v in rec['subjects'].items()}

            if self.report_type == 'weekly':
                row = [
                    date_str,
                    fmt(subj.get('таджикский язык', '')),
                    fmt(subj.get('биология', '')),
                    fmt(subj.get('физика', '')),
                    fmt(subj.get('химия', '')),
                    fmt(subj.get('общий процент', ''))
                ]
            else:
                row = [
                    date_str,
                    str(subj.get('таджикский язык', '')),
                    str(subj.get('биология', '')),
                    str(subj.get('химия', '')),
                    str(subj.get('физика', '')),
                    str(subj.get('общий балл', '')),
                    fmt(subj.get('общий процент', subj.get('общий процент', '')))
                ]

            for i, item in enumerate(row):
                self.cell(col_widths[i], 10, item, 1, 0, 'C')
            self.ln()

# ────────────────────── Генерация PDF ──────────────────────

def generate_progress_pdf(student_name, records, report_type='weekly'):
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    if not os.path.exists(FONT_PATH):
        raise FileNotFoundError(f"❌ Не найден шрифт: {FONT_PATH}")

    pdf = PDFReport(report_type=report_type)
    pdf.add_font(FONT_NAME, '', FONT_PATH, uni=True)
    pdf.add_font(FONT_NAME, 'B', FONT_PATH, uni=True)

    pdf.add_page()
    pdf.add_student_results(student_name, records)

    safe_name = ''.join(c for c in student_name if c.isalnum() or c in (' ', '_')).strip().replace(' ', '_')
    filename = f"{safe_name}_progress_{report_type}.pdf"
    filepath = os.path.join(TEMP_DIR, filename)

    pdf.output(filepath)
    return filepath
