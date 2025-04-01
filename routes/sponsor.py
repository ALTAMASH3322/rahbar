from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user
import mysql.connector
from config import Config as c
import os
from werkzeug.utils import secure_filename

# Create Blueprint for sponsor routes
sponsor_bp = Blueprint('sponsor', __name__)

# Database configuration
db_config = {
    'host': c.MYSQL_HOST,
    'user': c.MYSQL_USER,
    'password': c.MYSQL_PASSWORD,
    'database': c.MYSQL_DB
}

# Helper function to get a database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Ensure the uploads folder exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Sponsor Dashboard
@sponsor_bp.route('/sponsor_dashboard', methods=['GET'])
@login_required
def sponsor_dashboard():
    # Only allow sponsors (role_id 5) to access this route.
    if current_user.role_id != 5:
        return render_template('sponsor/error.html', error="You do not have permission to access this page."), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch sponsor details
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    sponsor = cursor.fetchone()

    # Fetch assigned grantees (students) for the sponsor
    cursor.execute("SELECT * FROM grantor_grantees WHERE grantor_id = %s", (current_user.user_id,))
    grantor_grantees = cursor.fetchall()

    grantees = []
    # Loop through each assigned grantee and fetch all related details
    for gg in grantor_grantees:
        grantee_id = gg['grantee_id']

        # Get grantee details from the users table
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (grantee_id,))
        grantee = cursor.fetchone()

        # Get bank details for the grantee
        cursor.execute("SELECT * FROM bank_details WHERE user_id = %s", (grantee_id,))
        bank_details = cursor.fetchone()

        # Get the latest payment record for the grantee based on created_at timestamp
        cursor.execute(
            "SELECT * FROM payments WHERE grantee_id = %s ORDER BY created_at DESC LIMIT 1", 
            (grantee_id,)
        )
        latest_payment = cursor.fetchone()

        # Combine all details into one dictionary
        grantee_details = {
            'user': grantee,
            'bank_details': bank_details,
            'latest_payment': latest_payment
        }
        grantees.append(grantee_details)

    cursor.close()
    conn.close()

    # Pass the sponsor and grantees data to the template
    return render_template('sponsor/dashboard.html', sponsor=sponsor, grantees=grantees)


# Sponsor Payments
@sponsor_bp.route('/payments', methods=['GET', 'POST'])
@login_required
def sponsor_payments():
    if current_user.role_id != 5:  # Ensure only sponsors can access this route
        return render_template('sponsor/error.html', error="You do not have permission to access this page."), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        action = request.form.get('action')
        grantee_id = request.form.get('grantee_id')
        amount = request.form.get('amount')
        receipt = request.files.get('receipt')

        if action == 'pay':
            if not grantee_id or not amount or not receipt:
                flash('Grantee ID, amount, and receipt are required.', 'error')
                return redirect(url_for('sponsor.sponsor_payments'))

            # Save the receipt file
            filename = secure_filename(receipt.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            receipt.save(filepath)

            # Insert payment record
            try:
                cursor.execute(
                    """
                    INSERT INTO payments (grantor_id, grantee_id, amount, payment_date, receipt_url, status)
                    VALUES (%s, %s, %s, NOW(), %s, 'paid')
                    """,
                    (current_user.user_id, grantee_id, amount, filepath)
                )
                conn.commit()
                flash('Payment recorded and receipt uploaded successfully!', 'success')
            except Exception as e:
                print(f"Database Error: {e}")
                conn.rollback()
                flash('An error occurred while processing the payment.', 'error')

        return redirect(url_for('sponsor.sponsor_payments'))

    # ----------------------
    # GET method processing
    # ----------------------

    # Get all payment schedules once
    cursor.execute("SELECT * FROM payment_schedules")
    payment_schedules = cursor.fetchall()

    # Fetch assigned grantees for the current sponsor
    cursor.execute("SELECT * FROM grantor_grantees WHERE grantor_id = %s", (current_user.user_id,))
    grantor_grantees = cursor.fetchall()

    payment_details = []
    from datetime import datetime, timedelta
    current_date = datetime.now()

    for gg in grantor_grantees:
        # Get grantee user details
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (gg['grantee_id'],))
        grantee = cursor.fetchone()

        # Get grantee bank details
        cursor.execute("SELECT * FROM bank_details WHERE user_id = %s", (gg['grantee_id'],))
        bank_details = cursor.fetchone()

        # Get the latest payment record (if any)
        cursor.execute(
            "SELECT * FROM payments WHERE grantee_id = %s ORDER BY payment_date DESC LIMIT 1", 
            (gg['grantee_id'],)
        )
        payment_record = cursor.fetchone()

        # Determine payment frequency and status (default is unpaid)
        status = "unpaid"
        frequency = 1  # default frequency
        if payment_record:
            # Find the matching payment schedule based on amount
            for schedule in payment_schedules:
                if payment_record["amount"] == schedule["amount"]:
                    frequency = schedule["schedule_id"]
                    break

            # Compute status based on frequency
            if frequency == 1:
                one_year_ago = current_date - timedelta(days=365)
                if payment_record["payment_date"] >= one_year_ago:
                    status = "paid"
            elif frequency == 2:
                six_months_ago = current_date - timedelta(days=180)
                if payment_record["payment_date"] >= six_months_ago:
                    status = "paid"
            elif frequency == 3:
                three_months_ago = current_date - timedelta(days=90)
                if payment_record["payment_date"] >= three_months_ago:
                    status = "paid"
            elif frequency == 4:
                one_month_ago = current_date - timedelta(days=30)
                # Assuming payment_schedules[3] exists; adjust accordingly if not
                if payment_record["payment_date"] >= one_month_ago and payment_record["payment_date"] >= payment_schedules[3].get("updated_at", one_month_ago):
                    status = "paid"

        # Build the payment details dictionary
        payment_details.append({
            "grantee": grantee,
            "bank_details": bank_details,
            "payments": [payment_record] if payment_record else [],
            "due_date": status  # used as current status in template
        })

    # Fetch past payments for display
    cursor.execute("""
        SELECT p.*, u.name AS grantee_name
        FROM payments p
        JOIN users u ON p.grantee_id = u.user_id
        WHERE p.grantee_id IN (
            SELECT grantee_id FROM grantor_grantees WHERE grantor_id = %s and p.status = 'paid'
        )
    """, (current_user.user_id,))
    past_payments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('sponsor/payment.html', payment_details=payment_details, past_payments=past_payments)


# Sponsor Student Progress
@sponsor_bp.route('/sponsor_student_progress', methods=['GET'])
@login_required
def sponsor_student_progress():
    if current_user.role_id != 5:  # Ensure only sponsors can access this route
        return render_template('sponsor/error.html', error="You do not have permission to access this page."), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch progress data for all grantees
    cursor.execute("""
        SELECT sp.*, u.name AS grantee_name
        FROM student_progress sp
        JOIN users u ON sp.grantee_id = u.user_id
        WHERE sp.grantee_id IN (
            SELECT grantee_id FROM grantor_grantees WHERE grantor_id = %s
        )
    """, (current_user.user_id,))
    progress_data = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('sponsor/student_progress.html', progress_data=progress_data)

# Serve uploaded files
@sponsor_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)