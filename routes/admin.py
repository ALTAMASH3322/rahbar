from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory
from flask_login import login_required, current_user
import mysql.connector
from config import Config as c  # Import config values
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pandas as pd
from io import BytesIO
from datetime import datetime

# Create Blueprint for admin routes
admin_bp = Blueprint('admin', __name__)

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

# Ensure the uploads folder exists
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Admin Dashboard
@admin_bp.route('/admin_dashboard', methods=['GET'])
@login_required
def admin_dashboard():
    # Ensure only Admins (Super Admin or Application Admin) can access this route
    if current_user.role_id not in [1, 2]:  # Role ID 1 = Super Admin, 2 = Application Admin
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch admin details
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    admin = cursor.fetchone()

    # Fetch all users
    cursor.execute("SELECT * FROM users")
    users = cursor.fetchall()

    # Fetch all applications
    cursor.execute("SELECT * FROM grantee_details")
    applications = cursor.fetchall()

    # Fetch all payments
    cursor.execute("SELECT * FROM payments")
    payments = cursor.fetchall()

    # Fetch all sponsors and convenors
    cursor.execute("SELECT * FROM users WHERE role_id IN (4, 5)")  # Role ID 4 = Convenor, 5 = Sponsor
    sponsors_convenors = cursor.fetchall()

    # Fetch all grantees (students)
    cursor.execute("SELECT * FROM users WHERE role_id = 6")  # Role ID 6 = Grantee (Student)
    grantees = cursor.fetchall()

    # Fetch application period status
    cursor.execute("SELECT * FROM application_period WHERE id = 1")
    application_period = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'admin/dashboard.html',
        admin=admin,
        users=users,
        applications=applications,
        payments=payments,
        sponsors_convenors=sponsors_convenors,
        grantees=grantees,
        application_period=application_period
    )

# Start or End Application Period
@admin_bp.route('/manage_application_period', methods=['POST'])
@login_required
def manage_application_period():
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    action = request.form.get('action')  # 'start' or 'end'
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if action == 'start':
            # Validate start and end dates
            if not start_date or not end_date:
                flash('Start date and end date are required to start the application period.', 'error')
                return redirect(url_for('admin.admin_dashboard'))

            # Convert dates to datetime objects
            start_date = datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.strptime(end_date, '%Y-%m-%d')

            # Check if the application period is already active
            cursor.execute("SELECT * FROM application_period WHERE id = 1")
            existing_period = cursor.fetchone()

            if existing_period and existing_period['is_active']:
                flash('An application period is already active.', 'error')
                return redirect(url_for('admin.admin_dashboard'))

            # Start the application period
            cursor.execute("""
                INSERT INTO application_period (id, start_date, end_date, is_active)
                VALUES (1, %s, %s, 1)
                ON DUPLICATE KEY UPDATE start_date = %s, end_date = %s, is_active = 1
            """, (start_date, end_date, start_date, end_date))
            conn.commit()
            flash('Application period started successfully!', 'success')

        elif action == 'end':
            # End the application period
            cursor.execute("UPDATE application_period SET is_active = 0 WHERE id = 1")
            conn.commit()
            flash('Application period ended successfully!', 'success')

    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin.admin_dashboard'))

# Manage Users
@admin_bp.route('/manage_users', methods=['GET', 'POST'])
@login_required
def manage_users():
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Handle user creation or update
        user_id = request.form.get('user_id')
        name = request.form.get('name')
        email = request.form.get('email')
        role_id = request.form.get('role_id')
        status = request.form.get('status')

        if user_id:  # Update existing user
            cursor.execute("""
                UPDATE users
                SET name = %s, email = %s, role_id = %s, status = %s
                WHERE user_id = %s
            """, (name, email, role_id, status, user_id))
        else:  # Create new user
            password = request.form.get('password')
            hashed_password = generate_password_hash(password)
            cursor.execute("""
                INSERT INTO users (name, email, role_id, status, password_hash, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            """, (name, email, role_id, status, hashed_password))

        conn.commit()
        flash('User saved successfully!', 'success')
        return redirect(url_for('admin.manage_users'))

    # Fetch all users with their roles
    cursor.execute("""
        SELECT u.*, r.role_name
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
    """)
    users = cursor.fetchall()

    # Fetch all roles
    cursor.execute("SELECT * FROM roles")
    roles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/manage_users.html', users=users, roles=roles)

# Delete User
@admin_bp.route('/delete_user/<int:user_id>', methods=['GET'])
@login_required
def delete_user(user_id):
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete user
        cursor.execute("DELETE FROM users WHERE user_id = %s", (user_id,))
        conn.commit()
        flash('User deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin.manage_users'))

# System Configuration (e.g., fee schedules, deadlines)
@admin_bp.route('/system_configuration', methods=['GET', 'POST'])
@login_required
def system_configuration():
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Handle configuration updates
        fee_schedule = request.form.get('fee_schedule')
        deadline = request.form.get('deadline')

        # Update system configuration (example)
        cursor.execute("""
            UPDATE system_config
            SET fee_schedule = %s, deadline = %s
            WHERE config_id = 1
        """, (fee_schedule, deadline))
        conn.commit()
        flash('System configuration updated successfully!', 'success')
        return redirect(url_for('admin.system_configuration'))

    # Fetch current system configuration
    cursor.execute("SELECT * FROM system_config WHERE config_id = 1")
    config = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('admin/system_configuration.html', config=config)

# Generate Reports
@admin_bp.route('/generate_reports', methods=['GET', 'POST'])
@login_required
def generate_reports():
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all applications
    cursor.execute("SELECT * FROM grantee_details")
    applications = cursor.fetchall()

    # Fetch all payments
    cursor.execute("SELECT * FROM payments")
    payments = cursor.fetchall()

    # Fetch all sponsors and convenors
    cursor.execute("SELECT * FROM users WHERE role_id IN (4, 5)")  # Role ID 4 = Convenor, 5 = Sponsor
    sponsors_convenors = cursor.fetchall()

    # Fetch all grantees (students)
    cursor.execute("SELECT * FROM users WHERE role_id = 6")  # Role ID 6 = Grantee (Student)
    grantees = cursor.fetchall()

    cursor.close()
    conn.close()

    if request.method == 'POST':
        report_type = request.form.get('reportType')
        format = request.form.get('format')

        # Prepare data based on report type
        if report_type == 'applications':
            data = applications
            filename = 'applications_report'
        elif report_type == 'payments':
            data = payments
            filename = 'payments_report'
        elif report_type == 'sponsors_convenors':
            data = sponsors_convenors
            filename = 'sponsors_convenors_report'
        elif report_type == 'grantees':
            data = grantees
            filename = 'grantees_report'

        # Convert data to a DataFrame
        df = pd.DataFrame(data)

        # Generate the report in the selected format
        if format == 'csv':
            output = BytesIO()
            df.to_csv(output, index=False)
            output.seek(0)
            return send_file(output, as_attachment=True, download_name=f"{filename}.csv", mimetype='text/csv')

        elif format == 'excel':
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False)
            output.seek(0)
            return send_file(output, as_attachment=True, download_name=f"{filename}.xlsx", mimetype='application/vnd.ms-excel')

        elif format == 'pdf':
            # Use a library like ReportLab or WeasyPrint to generate PDFs
            pass

    return render_template(
        'admin/generate_reports.html',
        applications=applications,
        payments=payments,
        sponsors_convenors=sponsors_convenors,
        grantees=grantees
    )

# Serve Uploaded Files
@admin_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)