from flask import Flask, render_template, request, redirect, url_for, flash, send_file
import oracledb
from datetime import datetime
from random import randint
from reports import (
    generate_pdf_report,
    generate_grouped_pdf_report,
    generate_chart_pdf_report
)

app = Flask(__name__)
app.secret_key = "your_secret_key"

db_config = {
    "user": "RESTAURANT_USER",
    "password": "12345",
    "dsn": oracledb.makedsn("localhost", 1521, service_name="ORCLPDB1"),
}

@app.route("/")
def index():
    try:
        conn = oracledb.connect(**db_config)
        cursor = conn.cursor()

        query = """
            SELECT r.reservation_id, c.name, r.table_id, TO_CHAR(r.reservation_date, 'YYYY-MM-DD HH24:MI'), r.guest_count
            FROM Reservation r
            JOIN Customer c ON r.customer_id = c.customer_id
            ORDER BY r.reservation_date
        """
        cursor.execute(query)
        reservations = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template("index.html", reservations=reservations)

    except oracledb.DatabaseError as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for("index"))

@app.route("/manager", methods=["GET", "POST"])
def manager():
    try:
        conn = oracledb.connect(**db_config)
        cursor = conn.cursor()

        if request.method == "POST":
            action = request.form.get("action")

            if action == "add":
                customer_name = request.form.get("customer_name")
                customer_phone = request.form.get("customer_phone")
                reservation_date = request.form.get("reservation_date")
                reservation_time = request.form.get("reservation_time")
                guest_count = request.form.get("guest_count", 2)

                reservation_timestamp = f"{reservation_date} {reservation_time}"

                if not customer_name or not customer_phone or not reservation_date or not reservation_time:
                    flash("All fields are required!", "warning")
                else:
                    cursor.execute("""
                        SELECT customer_id FROM Customer WHERE name = :name AND phone = :phone
                    """, {"name": customer_name, "phone": customer_phone})
                    result = cursor.fetchone()

                    if result:
                        customer_id = result[0]
                    else:
                        cursor.execute("""
                            INSERT INTO Customer (name, phone) VALUES (:name, :phone)
                        """, {"name": customer_name, "phone": customer_phone})
                        conn.commit()
                        cursor.execute("""
                            SELECT customer_id FROM Customer WHERE name = :name AND phone = :phone
                        """, {"name": customer_name, "phone": customer_phone})
                        customer_id = cursor.fetchone()[0]

                    table_id = randint(1, 15)

                    cursor.execute("""
                        INSERT INTO Reservation (customer_id, table_id, reservation_date, guest_count)
                        VALUES (:cid, :tid, TO_TIMESTAMP(:rdatetime, 'YYYY-MM-DD HH24:MI'), :gcount)
                    """, {"cid": customer_id, "tid": table_id, "rdatetime": reservation_timestamp, "gcount": guest_count})
                    conn.commit()
                    flash("Reservation added successfully!", "success")

            elif action == "delete":
                reservation_id = request.form.get("reservation_id")
                cursor.execute("DELETE FROM Reservation WHERE reservation_id = :rid", {"rid": reservation_id})
                conn.commit()
                flash("Reservation deleted successfully!", "success")

            elif action == "update":
                reservation_id = request.form.get("reservation_id")
                new_date = request.form.get("reservation_date")
                new_time = request.form.get("reservation_time")
                new_guest_count = request.form.get("guest_count")

                new_timestamp = f"{new_date} {new_time}"

                cursor.execute("""
                    UPDATE Reservation
                    SET reservation_date = TO_TIMESTAMP(:rdatetime, 'YYYY-MM-DD HH24:MI'),
                        guest_count = :gcount
                    WHERE reservation_id = :rid
                """, {"rdatetime": new_timestamp, "gcount": new_guest_count, "rid": reservation_id})
                conn.commit()
                flash("Reservation updated successfully!", "success")

            return redirect(url_for("manager"))

        search_name = request.args.get("search_name")
        search_phone = request.args.get("search_phone")

        if search_name or search_phone:
            query = """
                SELECT r.reservation_id, c.name, c.phone, r.table_id, 
                       TO_CHAR(r.reservation_date, 'YYYY-MM-DD HH24:MI') AS reservation_date, 
                       r.guest_count
                FROM Reservation r
                JOIN Customer c ON r.customer_id = c.customer_id
                WHERE c.name LIKE :name OR c.phone LIKE :phone
                ORDER BY r.reservation_date
            """
            cursor.execute(query, {"name": f"%{search_name}%", "phone": f"%{search_phone}%"})
        else:
            query = """
                SELECT r.reservation_id, c.name, c.phone, r.table_id, 
                       TO_CHAR(r.reservation_date, 'YYYY-MM-DD HH24:MI') AS reservation_date, 
                       r.guest_count
                FROM Reservation r
                JOIN Customer c ON r.customer_id = c.customer_id
                ORDER BY r.reservation_date
            """
            cursor.execute(query)

        reservations = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template("manager.html", reservations=reservations)

    except oracledb.DatabaseError as e:
        flash(f"Database error: {e}", "danger")
        return redirect(url_for("manager"))

@app.route("/edit_reservation", methods=["GET", "POST"])
def edit_reservation():
    try:
        conn = oracledb.connect(**db_config)
        cursor = conn.cursor()

        if request.method == "POST":
            reservation_id = request.form.get("reservation_id")
            new_name = request.form.get("customer_name")
            new_phone = request.form.get("customer_phone")
            new_date = request.form.get("reservation_date")
            new_time = request.form.get("reservation_time")
            new_guest_count = request.form.get("guest_count")

            try:
                combined_datetime = datetime.strptime(f"{new_date} {new_time}", "%Y-%m-%d %H:%M")
            except ValueError:
                return "Invalid date or time format. Please use 'YYYY-MM-DD' for date and 'HH:MM' for time."

            cursor.execute("""
                SELECT customer_id FROM Reservation WHERE reservation_id = :rid
            """, {"rid": reservation_id})
            result = cursor.fetchone()

            if not result:
                return "Reservation not found."
            
            customer_id = result[0]

            cursor.execute("""
                UPDATE Customer
                SET name = :name, phone = :phone
                WHERE customer_id = :cid
            """, {"name": new_name, "phone": new_phone, "cid": customer_id})

            cursor.execute("""
                UPDATE Reservation
                SET reservation_date = :rdate,
                    guest_count = :gcount
                WHERE reservation_id = :rid
            """, {"rdate": combined_datetime, "gcount": new_guest_count, "rid": reservation_id})

            conn.commit()

            cursor.close()
            conn.close()

            return redirect(url_for("manager"))

        else: 
            reservation_id = request.args.get("reservation_id")

            cursor.execute("""
                SELECT r.reservation_id, c.name, c.phone, 
                       TO_CHAR(r.reservation_date, 'YYYY-MM-DD'),
                       TO_CHAR(r.reservation_date, 'HH24:MI'),
                       r.guest_count
                FROM Reservation r
                JOIN Customer c ON r.customer_id = c.customer_id
                WHERE r.reservation_id = :rid
            """, {"rid": reservation_id})
            reservation = cursor.fetchone()

            if not reservation:
                return "Reservation not found."

            cursor.close()
            conn.close()

            return render_template("edit_reservation.html", reservation=reservation)

    except oracledb.DatabaseError as e:
        return f"Database error: {e}"

@app.route("/pdf_report/<int:report_type>")
def pdf_report(report_type):
    output_path = f"static/reports/report_{report_type}.pdf"

    try:
        if report_type == 1:
            generate_pdf_report(output_path, db_config)
        elif report_type == 2:
            generate_grouped_pdf_report(output_path, db_config)
        elif report_type == 3:
            generate_chart_pdf_report(output_path, db_config)
        else:
            flash("Invalid report type selected.", "danger")
            return redirect(url_for("choose_report"))

        return send_file(output_path, as_attachment=True)

    except Exception as e:
        flash(f"Error while generating report: {e}", "danger")
        return redirect(url_for("choose_report"))

@app.route("/choose_report")
def choose_report():
    return render_template("choose_report.html")

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
