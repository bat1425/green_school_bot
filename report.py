import os
from fpdf import FPDF
from datetime import datetime
from config import TEMP_DIR

class PDFReport(FPDF):
    def header(self):
        self.set_font("DejaVu", "B", 16)
        self.cell(0, 10, "Прогресс ученика", ln=True, align="C")
        self.ln(10)

    def add_student_results(self, student_name, records):
        self.set_font("DejaVu", "B", 12)
        self.cell(0, 10, f"Имя: {student_name}", ln=True)
        self.ln(5)

        headers = ["Дата", "Таджикский язык", "Биология", "Физика", "Химия", "Общий процент"]
        col_widths = [30, 42, 25, 25, 25, 37]  # Поправил ширину, чтобы вместилось

        for i, header in enumerate(headers):
            self.cell(col_widths[i], 10, header, 1, 0, "C")
        self.ln()

        self.set_font("DejaVu", "", 11)

        def fmt(value):
            try:
                fval = float(value)
                # Если значение уже в процентах, например >1, просто добавить "%"
                if fval > 1:
                    return f"{int(fval)}%"
                else:
                    return f"{int(fval * 100)}%"
            except Exception:
                return str(value).strip()

        for rec in records:
            date_str = datetime.strptime(rec['date'], "%Y-%m-%d").strftime("%d.%m.%Y")
            subj = rec['subjects']

            # Берем значения, ключи обрезаем по пробелам
            tadj = subj.get('таджикский язык', '') or subj.get('таджикский язык '.strip(), '')
            bio = subj.get('биология', '')
            phys = subj.get('физика', '')
            chem = subj.get('химия', '')
            perc = subj.get('общий процент', '') or subj.get('общий процент ', '')

            row = [
                date_str,
                fmt(tadj),
                fmt(bio),
                fmt(phys),
                fmt(chem),
                fmt(perc),
            ]

            for i, item in enumerate(row):
                self.cell(col_widths[i], 10, item, 1, 0, "C")
            self.ln()



def generate_progress_pdf(student_name, records):
    if not os.path.exists(TEMP_DIR):
        os.makedirs(TEMP_DIR)

    pdf = PDFReport()
    # Зарегистрировать шрифт DejaVuSans.ttf (укажи правильный путь к файлу шрифта)
    pdf.add_font('DejaVu', '', 'fonts/DejaVuSans.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'fonts/DejaVuSans.ttf', uni=True)

    pdf.add_page()
    pdf.add_student_results(student_name, records)

    filename = f"{student_name.replace(' ', '_')}_progress.pdf"
    filepath = os.path.join(TEMP_DIR, filename)
    pdf.output(filepath)
    return filepath
