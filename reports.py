import matplotlib.pyplot as plt
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
import oracledb

def generate_pdf_report(output_path, db_config):
    """
    Generate a PDF report with improved design (date under the title).
    """
    try:
        conn = oracledb.connect(**db_config)
        cursor = conn.cursor()

        # SQL query to fetch data
        cursor.execute("""
            SELECT r.reservation_id, c.name, r.table_id, r.reservation_date, r.guest_count
            FROM Reservation r
            JOIN Customer c ON r.customer_id = c.customer_id
            ORDER BY r.reservation_date
        """)
        data = cursor.fetchall()

        # Table headers
        table_data = [["Reservation ID", "Customer Name", "Table", "Date", "Guests"]]

        # Add rows of data
        for row in data:
            table_data.append([
                row[0],
                row[1],
                row[2],
                row[3].strftime("%Y-%m-%d %H:%M") if row[3] else "",
                row[4]
            ])

        # ---------- 1. Styles for PDF ----------
        styles = getSampleStyleSheet()

        # Customize title style
        title_style = styles['Title']
        title_style.textColor = colors.HexColor("#303f9f")  # Dark blue
        title_style.fontSize = 24

        # Style for date
        subtitle_style = ParagraphStyle(
            name='Subtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.gray,
            alignment=1  # Center align
        )

        # ---------- 2. Create PDF document and elements ----------
        pdf = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []

        # ---------- 3. Create header ----------
        title_para = Paragraph("Restaurant Reservation Report", title_style)
        elements.append(title_para)

        # Add date line under the title
        date_str = f"Generated on {datetime.now():%Y-%m-%d %H:%M:%S}"
        date_para = Paragraph(date_str, subtitle_style)
        elements.append(Spacer(1, 10))  # Space between title and date
        elements.append(date_para)

        elements.append(Spacer(1, 20))  # Space between date and table

        # ---------- 4. Create data table ----------
        data_table = Table(table_data)

        data_table_style = TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#455a64")),
            ('TEXTCOLOR',  (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN',      (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME',   (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE',   (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),

            # Remaining cells
            ('ALIGN',     (0, 1), (-1, -1), 'CENTER'),
            ('FONTNAME',  (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE',  (0, 1), (-1, -1), 10),

            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1),
             [colors.whitesmoke, colors.lightgrey]),

            # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ])
        data_table.setStyle(data_table_style)

        elements.append(data_table)

        # ---------- 5. Save PDF ----------
        pdf.build(elements)
        print("PDF created!")

    except oracledb.DatabaseError as e:
        print(f"Error: {e}")

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

def generate_grouped_pdf_report(output_path, db_config):
    """
    Generate a PDF report with grouped reservations by date.
    """
    try:
        conn = oracledb.connect(**db_config)
        cursor = conn.cursor()

        # SQL query to fetch data
        cursor.execute("""
            SELECT TO_CHAR(r.reservation_date, 'YYYY-MM-DD') AS reservation_date, 
                   c.name, r.table_id, r.guest_count
            FROM Reservation r
            JOIN Customer c ON r.customer_id = c.customer_id
            ORDER BY reservation_date
        """)
        data = cursor.fetchall()

        # Group data
        grouped_data = {}
        for row in data:
            date = row[0]
            if date not in grouped_data:
                grouped_data[date] = []
            grouped_data[date].append(row[1:])

        # ---------- Create PDF ----------
        pdf = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []

        # Title
        styles = getSampleStyleSheet()
        title_style = styles['Title']
        title_style.textColor = colors.HexColor("#303f9f")
        title_style.fontSize = 20

        elements.append(Paragraph("Grouped Reservation Report", title_style))
        elements.append(Spacer(1, 20))

        # Create tables for each group
        for date, reservations in grouped_data.items():
            # Group header (date)
            elements.append(Paragraph(f"Date: {date}", styles['Heading2']))
            elements.append(Spacer(1, 10))

            # Data table
            table_data = [["Customer Name", "Table", "Guests"]]
            for res in reservations:
                table_data.append(list(res))

            table = Table(table_data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#455a64")),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.whitesmoke, colors.lightgrey])
            ]))
            elements.append(table)
            elements.append(Spacer(1, 20))

        pdf.build(elements)
        print("Grouped PDF report created successfully!")

    except oracledb.DatabaseError as e:
        print(f"Database error: {e}")

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()

def generate_chart_pdf_report(output_path, db_config):
    """
    Generate a PDF report with a chart (reservations by month).
    """
    try:
        import matplotlib
        matplotlib.use('Agg') 
        conn = oracledb.connect(**db_config)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT TO_CHAR(reservation_date, 'YYYY-MM') AS month, COUNT(*)
            FROM Reservation
            GROUP BY TO_CHAR(reservation_date, 'YYYY-MM')
            ORDER BY month
        """)
        data = cursor.fetchall()

        months = [row[0] for row in data]
        counts = [row[1] for row in data]

        # Create chart
        plt.figure(figsize=(10, 6))
        plt.bar(months, counts, color='skyblue', edgecolor='black')
        plt.title("Reservations per Month", fontsize=16)
        plt.xlabel("Month", fontsize=12)
        plt.ylabel("Number of Reservations", fontsize=12)
        plt.xticks(rotation=45)
        plt.tight_layout()

        buffer = BytesIO()
        plt.savefig(buffer, format="png")
        buffer.seek(0)

        pdf = SimpleDocTemplate(output_path, pagesize=letter)
        elements = []

        styles = getSampleStyleSheet()
        title_style = styles['Title']
        elements.append(Paragraph("Reservation Chart Report", title_style))
        elements.append(Spacer(1, 20))

        # Add chart to PDF
        from reportlab.platypus import Image
        img = Image(buffer, 500, 300)  # Ensure dimensions fit the PDF
        elements.append(img)

        pdf.build(elements)
        print("Chart PDF report created successfully!")

        buffer.close()

    except oracledb.DatabaseError as e:
        print(f"Database error: {e}")

    finally:
        if 'cursor' in locals() and cursor:
            cursor.close()
        if 'conn' in locals() and conn:
            conn.close()
