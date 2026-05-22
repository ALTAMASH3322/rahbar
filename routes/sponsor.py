from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, current_app
from flask_login import login_required, current_user
import mysql.connector
from config import Config as c
import os
from werkzeug.utils import secure_filename
import calendar
from datetime import datetime, timedelta
import json

# Create Blueprint for sponsor routes
sponsor_bp = Blueprint('sponsor', __name__)

# Database configuration
db_config = {
    'host': c.MYSQL_HOST,
    'user': c.MYSQL_USER,
    'password': c.MYSQL_PASSWORD,
    'database': c.MYSQL_DB
}

def get_db_connection():
    return mysql.connector.connect(**db_config)

UPLOAD_FOLDER = 'uploads'

# --- HELPER: GET ALL REFERENCE IDs FOR CURRENT SPONSOR ---
def get_sponsor_ref_ids(cursor, user_id):
    cursor.execute("SELECT reference_id FROM sponsor_references WHERE user_id = %s", (user_id,))
    return [row['reference_id'] for row in cursor.fetchall()]

# 1. SPONSOR DASHBOARD
@sponsor_bp.route('/sponsor_dashboard', methods=['GET'])
@login_required
def sponsor_dashboard():
    if current_user.role_id != 5:
        return render_template('sponsor/error.html', error="Unauthorized."), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    sponsor_id = current_user.user_id

    # --- NEW: Explicitly fetch the Sponsor's own details to ensure Name is loaded ---
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (sponsor_id,))
    sponsor_full_details = cursor.fetchone()

    # Fetch students mapped to ANY of this sponsor's Reference IDs
    cursor.execute("""
        SELECT gg.*, sr.reference_id as linked_ref_id
        FROM grantor_grantees gg
        JOIN sponsor_references sr ON gg.grantor_id COLLATE utf8mb4_general_ci = sr.reference_id COLLATE utf8mb4_general_ci
        WHERE sr.user_id = %s
    """, (sponsor_id,))
    grantor_grantees = cursor.fetchall()

    grantees = []
    for gg in grantor_grantees:
        grantee_id = gg['grantee_id']
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (grantee_id,))
        grantee = cursor.fetchone()
        cursor.execute("SELECT * FROM bank_details WHERE user_id = %s", (grantee_id,))
        bank_details = cursor.fetchone()
        cursor.execute("SELECT * FROM payments WHERE grantee_id = %s ORDER BY created_at DESC LIMIT 1", (grantee_id,))
        latest_payment = cursor.fetchone()

        cursor.execute("""
            SELECT sic.assigned_at, c.number_of_semesters
            FROM student_institution_courses sic
            JOIN courses c ON sic.course_id = c.course_id
            WHERE sic.user_id = %s
        """, (grantee_id,))
        course_info = cursor.fetchone()

        payment_status = "Pending"
        if course_info and course_info.get('assigned_at'):
            payment_status = "On Schedule"

        grantees.append({
            'user': grantee,
            'bank_details': bank_details,
            'latest_payment': latest_payment,
            'payment_status': payment_status,
            'reference_id': gg['linked_ref_id']
        })

    cursor.close()
    conn.close()
    
    # Pass the explicitly fetched 'sponsor_full_details' as 'sponsor'
    return render_template('sponsor/dashboard.html', sponsor=sponsor_full_details, grantees=grantees)


# 2. SPONSOR PAYMENTS
@sponsor_bp.route('/payments', methods=['GET', 'POST'])
@login_required
def sponsor_payments():
    # Ensure only Sponsors (role_id 5) can access
    if current_user.role_id != 5:
        return render_template('sponsor/error.html', error="Unauthorized."), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    sponsor_id = current_user.user_id

    # --- 1. HANDLE POST REQUEST (RECORDING A PAYMENT) ---
    if request.method == 'POST':
        action = request.form.get('action')
        grantee_id = request.form.get('grantee_id')
        amount = request.form.get('amount')
        payment_date = request.form.get('payment_date') # Captures the date from the modal
        receipt = request.files.get('receipt')

        if action == 'pay':
            # Identify which Reference ID fund this student belongs to
            cursor.execute("SELECT grantor_id FROM grantor_grantees WHERE grantee_id = %s LIMIT 1", (grantee_id,))
            mapping = cursor.fetchone()
            ref_id = mapping['grantor_id'] if mapping else None

            if not ref_id:
                flash('Error: Student is not linked to a valid sponsorship reference.', 'error')
                return redirect(url_for('sponsor.sponsor_payments'))

            # Save the Foundation Receipt file
            filename = secure_filename(receipt.filename)
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            receipt.save(filepath)

            try:
                # Insert payment using the manual date provided by the sponsor
                cursor.execute("""
                    INSERT INTO payments (grantor_id, grantee_id, amount, payment_date, receipt_url, status, created_at, updated_by)
                    VALUES (%s, %s, %s, %s, %s, 'Paid', NOW(), %s)
                """, (ref_id, grantee_id, amount, payment_date, filename, current_user.user_id))
                
                conn.commit()
                flash('Payment recorded successfully!', 'success')
            except Exception as e:
                conn.rollback()
                flash(f'Database Error: {str(e)}', 'error')

        return redirect(url_for('sponsor.sponsor_payments'))

    # --- 2. HANDLE GET REQUEST (DISPLAYING DATA) ---
    
    # Capture grantee_id from URL if redirecting from Dashboard (e.g., ?grantee_id=M001)
    selected_grantee_id = request.args.get('grantee_id')

    # Fetch all students assigned to this human sponsor across all their Reference IDs
    cursor.execute("""
        SELECT u.*, gg.grantor_id as linked_ref_id
        FROM users u
        JOIN grantor_grantees gg ON u.user_id = gg.grantee_id
        JOIN sponsor_references sr ON gg.grantor_id COLLATE utf8mb4_general_ci = sr.reference_id COLLATE utf8mb4_general_ci
        WHERE sr.user_id = %s
    """, (sponsor_id,))
    assigned_students = cursor.fetchall()

    payment_details = []
    student_data_map = {}

    for student in assigned_students:
        s_id = student['user_id']
        
        # A. Fetch the scheduled scholarship amount based on student's batch year
        cursor.execute("""
            SELECT amount FROM payment_schedules 
            WHERE year = %s AND status = 1 LIMIT 1
        """, (student['year'],))
        sched_res = cursor.fetchone()
        student['annual_schedule_amount'] = sched_res['amount'] if sched_res else 0

        # B. Fetch bank details for the student
        cursor.execute("SELECT * FROM bank_details WHERE user_id = %s", (s_id,))
        bank = cursor.fetchone()

        # C. Fetch all successful payments and generate links for foundation and student receipts
        cursor.execute("SELECT * FROM payments WHERE grantee_id = %s AND status = 'Paid' ORDER BY payment_date DESC", (s_id,))
        all_payments = cursor.fetchall()
        for p in all_payments:
            p['foundation_receipt'] = url_for('sponsor.uploaded_file', filename=p['receipt_url']) if p['receipt_url'] else None
            p['student_expenditure_proof'] = url_for('sponsor.uploaded_file', filename=p['student_proof_url']) if p['student_proof_url'] else None

        # D. Fetch course and enrollment date for schedule generation
        cursor.execute("""
            SELECT sic.assigned_at, c.number_of_semesters, c.fees_per_semester
            FROM student_institution_courses sic
            JOIN courses c ON sic.course_id = c.course_id
            WHERE sic.user_id = %s
        """, (s_id,))
        course = cursor.fetchone()

        detail = {
            "grantee": student,
            "bank_details": bank,
            "payments": all_payments,
            "course_info": course,
            "reference_id": student['linked_ref_id']
        }
        payment_details.append(detail)
        student_data_map[s_id] = detail

    # --- 3. FETCH RECENT HISTORY (LATEST 5 PAYMENTS) ---
    cursor.execute("""
        SELECT p.*, u.name AS grantee_name
        FROM payments p
        JOIN users u ON p.grantee_id = u.user_id
        JOIN sponsor_references sr ON p.grantor_id COLLATE utf8mb4_general_ci = sr.reference_id COLLATE utf8mb4_general_ci
        WHERE sr.user_id = %s AND p.status = 'Paid'
        ORDER BY p.payment_date DESC LIMIT 5
    """, (sponsor_id,))
    past_payments = cursor.fetchall()

    for pp in past_payments:
        pp['foundation_receipt'] = url_for('sponsor.uploaded_file', filename=pp['receipt_url']) if pp['receipt_url'] else None
        pp['student_proof'] = url_for('sponsor.uploaded_file', filename=pp['student_proof_url']) if pp['student_proof_url'] else None

    cursor.close()
    conn.close()

    return render_template('sponsor/payment.html', 
        payment_details=payment_details, 
        past_payments=past_payments, 
        sponsor=current_user,
        student_data_map=student_data_map,
        selected_grantee_id=selected_grantee_id, # Passed to JS for auto-selection
        students_for_dropdown=[d['grantee'] for d in payment_details])


# 3. STUDENT PROGRESS
@sponsor_bp.route('/sponsor_student_progress', methods=['GET'])
@login_required
def sponsor_student_progress():
    if current_user.role_id != 5:
        return render_template('sponsor/error.html', error="Unauthorized."), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    # Updated query to link through sponsor_references
    cursor.execute("""
        SELECT sp.*, u.name AS grantee_name
        FROM student_progress sp
        JOIN users u ON sp.grantee_id = u.user_id
        JOIN grantor_grantees gg ON u.user_id = gg.grantee_id
        JOIN sponsor_references sr ON gg.grantor_id COLLATE utf8mb4_general_ci = sr.reference_id COLLATE utf8mb4_general_ci
        WHERE sr.user_id = %s
    """, (current_user.user_id,))
    progress_data = cursor.fetchall()

    cursor.close()
    conn.close()
    return render_template('sponsor/student_progress.html', progress_data=progress_data, sponsor=current_user)

@sponsor_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)