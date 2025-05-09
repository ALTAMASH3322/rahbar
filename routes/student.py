from flask import Blueprint, render_template, request, redirect, url_for, flash
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
@student_bp.route('/student_dashboard', methods=['GET'])
@login_required
def student_dashboard():
    # Debugging: Print current user details
    #print(f"Current User Role ID: {current_user.role_id}")  # Debugging
    #print(f"Current User: {current_user}")  # Debugging
    #print(f"Current User ID: {current_user.user_id}")  # Debugging

    # Ensure only Grantees (Students) can access this route
    if current_user.role_id != 6:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch student details
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    student = cursor.fetchone()

    # Fetch assigned sponsor
    cursor.execute("SELECT * FROM grantor_grantees WHERE grantee_id = %s", (current_user.user_id,))
    grantor_grantee = cursor.fetchone()

    sponsor = None
    if grantor_grantee:
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (grantor_grantee['grantor_id'],))
        sponsor = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('student/dashboard.html', student=student, sponsor=sponsor)

def get_bank_details(user_id):
    """Fetch bank details for a given user."""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
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
    cursor = conn.cursor(dictionary=True)

    # Fetch payments for the student
    cursor.execute("SELECT * FROM payments WHERE grantee_id = %s", (current_user.user_id,))
    payments = cursor.fetchall()

    cursor.close()
    conn.close()

    bank_details = get_bank_details(current_user.user_id)
    

    return render_template('student/payment.html', payments=payments , bank_details=bank_details)

# Student Progress (Upload Marks and Files)
from flask import send_from_directory

@student_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)


from flask import jsonify, request

@student_bp.route('/edit_bank_details', methods=['GET', 'POST'])
@login_required
def edit_bank_details():
    if current_user.role_id != 6:
        return jsonify({'success': False, 'message': 'Unauthorized access'}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Fetch form data
        


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

    else:
        # Return bank details as JSON
        bank_details = get_bank_details(current_user.user_id)
        print(bank_details)
        return jsonify(bank_details if bank_details else {})

    

            


@student_bp.route('/student_progress', methods=['GET', 'POST'])
@login_required
def student_progress():
    if current_user.role_id != 6:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    # Ensure the uploads folder exists
    if not os.path.exists('uploads'):
        os.makedirs('uploads')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Handle file upload and marks submission
        marks = request.form.get('marks')
        file = request.files.get('file')

        if not marks or not file:
            flash('Marks and file are required.', 'error')
            return redirect(url_for('student.student_progress'))

        # Save the file
        filename = secure_filename(file.filename)
        file_path = os.path.join('uploads', filename)
        print(f"Saving file to: {file_path}")  # Debug
        file.save(file_path)

        # Insert progress data into the database
        try:
            cursor.execute(
                "INSERT INTO student_progress (grantee_id, marks, file_path, created_at) VALUES (%s, %s, %s, NOW())",
                (current_user.user_id, marks, file_path)
            )
            conn.commit()
            flash('Progress submitted successfully!', 'success')
        except Exception as e:
            print(f"Database Error: {e}")  # Debug
            conn.rollback()
            flash('An error occurred while submitting progress.', 'error')

        return redirect(url_for('student.student_progress'))

    else:
        # Fetch progress data for the student
        cursor.execute("SELECT * FROM student_progress WHERE grantee_id = %s", (current_user.user_id,))
        progress_data = cursor.fetchall()

        cursor.close()
        conn.close()

        return render_template('student/student_progress.html', progress_data=progress_data)