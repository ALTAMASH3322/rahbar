import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
from flask_login import login_required, current_user
import mysql.connector
from config import Config as c  # Import config values
from werkzeug.utils import secure_filename
import os

# Create Blueprint for student routes
student_bp = Blueprint('student', __name__)

# Database configuration using config file values
db_config = {
    'host': c.MYSQL_HOST,
    'user': c.MYSQL_USER,
    'password': c.MYSQL_PASSWORD,
    'database': c.MYSQL_DB
}

# Helper function to get a database connection
def get_db_connection():
    return mysql.connector.connect(**db_config)

# Student Dashboard
# Student Dashboard
@student_bp.route('/student_dashboard', methods=['GET'])
@login_required
def student_dashboard():
    # Ensure only Grantees (Students) can access this route
    if current_user.role_id != 6:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    # Using buffered=True to avoid unread result errors
    cursor = conn.cursor(dictionary=True, buffered=True)

    # 1. Fetch student details
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    student = cursor.fetchone()

    # 2. Fetch assigned sponsor via the NEW join path
    # Join: Mapping (gg) -> Reference (sr) -> Human Sponsor (u)
    cursor.execute("""
        SELECT u.*, sr.reference_id 
        FROM grantor_grantees gg
        JOIN sponsor_references sr ON gg.grantor_id COLLATE utf8mb4_general_ci = sr.reference_id COLLATE utf8mb4_general_ci
        JOIN users u ON sr.user_id COLLATE utf8mb4_general_ci = u.user_id COLLATE utf8mb4_general_ci
        WHERE gg.grantee_id = %s
    """, (current_user.user_id,))
    sponsor = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('student/dashboard.html', student=student, sponsor=sponsor)

def get_bank_details(user_id):
    """Fetch bank details for a given user."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)
    
    cursor.execute("SELECT * FROM bank_details WHERE user_id = %s", (user_id,))
    bank_details = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    return bank_details if bank_details else {}


# Student Payment History
@student_bp.route('/student_payments', methods=['GET'])
@login_required
def student_payments():
    # Ensure only Grantees (Students) can access this route
    if current_user.role_id != 6:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    # 1. Fetch payments for the student
    cursor.execute("SELECT * FROM payments WHERE grantee_id = %s ORDER BY payment_date ASC", (current_user.user_id,))
    payments = cursor.fetchall()

    # --- NEW LOGIC: Pre-generate receipt URLs in the backend ---
    for payment in payments:
        # Check if a receipt_url exists for this payment record
        if payment.get('receipt_url'):
            # Use os.path.basename to safely get just the filename from the path
            filename = os.path.basename(payment['receipt_url'])
            # Use url_for to generate the secure link and add it to the dictionary
            payment['receipt_link'] = url_for('student.uploaded_file', filename=filename)
        else:
            # If no receipt exists, set the link to None
            payment['receipt_link'] = None
    # --- END OF NEW LOGIC ---

    # Fetch student details
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    student = cursor.fetchone()

    # Fetch course details for schedule generation
    cursor.execute("""
        SELECT 
            sic.assigned_at, 
            c.number_of_semesters,
            c.fees_per_semester
        FROM student_institution_courses sic
        JOIN courses c ON sic.course_id = c.course_id
        WHERE sic.user_id = %s
    """, (current_user.user_id,))
    course_info = cursor.fetchone()

    # Fetch bank details
    cursor.execute("SELECT * FROM bank_details WHERE user_id = %s", (current_user.user_id,))
    bank_details = cursor.fetchone()

    cursor.close()
    conn.close()
    
    # The 'payments' list now contains the extra 'receipt_link' key for each payment
    return render_template(
        'student/payment.html', 
        payments=payments, 
        bank_details=bank_details, 
        student=student,
        course_info=course_info
    )

# Serve uploaded files from the 'uploads' directory
@student_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)


@student_bp.route('/edit_bank_details', methods=['GET', 'POST'])
@login_required
def edit_bank_details():
    if current_user.role_id != 6:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    if request.method == 'POST':
        bank_name = request.json.get('bank_name')
        account_number = request.json.get('account_number')
        ifsc_code = request.json.get('ifsc_code')
        account_name = request.json.get('account_name')

        try:
            bank_details = get_bank_details(current_user.user_id)

            if bank_details:
                cursor.execute(
                    "UPDATE bank_details SET bank_name = %s, account_number = %s, ifsc_code = %s, account_name = %s WHERE user_id = %s",
                    (bank_name, account_number, ifsc_code, account_name, current_user.user_id)
                )
            else:
                cursor.execute(
                    "INSERT INTO bank_details (user_id, bank_name, account_number, ifsc_code, account_name) VALUES (%s, %s, %s, %s, %s)",
                    (current_user.user_id, bank_name, account_number, ifsc_code, account_name)
                )

            conn.commit()
            return jsonify({'success': True, 'message': 'Bank details updated successfully!'})

        except Exception as e:
            print(f"Database Error: {e}")
            conn.rollback()
            return jsonify({'success': False, 'message': 'An error occurred while updating bank details'})
        finally:
            cursor.close()
            conn.close()
    else:
        # GET request returns current bank details as JSON
        bank_details = get_bank_details(current_user.user_id)
        return jsonify(bank_details if bank_details else {})


@student_bp.route('/student_progress', methods=['GET', 'POST'])
@login_required
def student_progress():
    if current_user.role_id != 6:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    if request.method == 'POST':
        # 1. Retrieve data from form
        marks = request.form.get('marks')
        year = request.form.get('year')
        session = request.form.get('session') 
        file = request.files.get('file')

        # 2. Basic validation
        if not marks or not file or not year or not session:
            flash('All fields are required.', 'error')
            return redirect(url_for('student.student_progress'))

        try:
            # 3. MANUALLY CALCULATE NEXT ID (Fixes 'progress_id' default value error)
            cursor.execute("SELECT COALESCE(MAX(progress_id), 0) + 1 AS next_id FROM student_progress")
            new_id = cursor.fetchone()['next_id']

            # 4. SECURE FILENAME GENERATION
            original_filename = secure_filename(file.filename)
            file_ext = os.path.splitext(original_filename)[1]
            timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
            
            # Clean session string for filename (replace slashes with dashes)
            clean_session = session.replace('/', '-')
            custom_filename = f"{current_user.user_id}_{clean_session}_{timestamp}{file_ext}"
            
            # 5. DISK OPERATION: Save file with folder prefix
            file_save_path = os.path.join('uploads', custom_filename)
            file.save(file_save_path)

            # 6. DATABASE OPERATION: Save ONLY the filename (no 'uploads\' prefix)
            sql = """
                INSERT INTO student_progress 
                (progress_id, grantee_id, marks, file_path, created_at, updated_at, session, year, updated_by) 
                VALUES (%s, %s, %s, %s, NOW(), NOW(), %s, %s, %s)
            """
            
            # Note: custom_filename is used for the file_path column
            params = (new_id, current_user.user_id, marks, custom_filename, session, year, current_user.user_id)
            
            cursor.execute(sql, params)
            conn.commit()
            
            flash('Progress submitted successfully!', 'success')
            return redirect(url_for('student.student_progress'))

        except mysql.connector.Error as err:
            if conn: conn.rollback()
            flash(f'Database Error: {err.msg}', 'error')
        except Exception as e:
            if conn: conn.rollback()
            flash(f'System Error: {str(e)}', 'error')
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return redirect(url_for('student.student_progress'))

    else:
        # GET request: Fetch submission history for display
        cursor.execute("SELECT * FROM student_progress WHERE grantee_id = %s ORDER BY created_at DESC", (current_user.user_id,))
        progress_data = cursor.fetchall()
        
        cursor.close()
        conn.close()
        
        return render_template('student/student_progress.html', progress_data=progress_data, student=current_user)
    



@student_bp.route('/upload_payment_proof', methods=['POST'])
@login_required
def upload_payment_proof():
    if current_user.role_id != 6:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403

    payment_id = request.form.get('payment_id')
    file = request.files.get('proof_file')

    if not file or not payment_id:
        return jsonify({'success': False, 'message': 'File and Payment ID required'}), 400

    try:
        # Secure and save the file
        filename = secure_filename(f"proof_{payment_id}_{file.filename}")
        file_path = os.path.join('uploads', filename)
        file.save(file_path)

        # Update database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE payments SET student_proof_url = %s WHERE payment_id = %s AND grantee_id = %s",
            (filename, payment_id, current_user.user_id)
        )
        conn.commit()
        cursor.close()
        conn.close()

        return jsonify({'success': True, 'message': 'Proof uploaded successfully!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500