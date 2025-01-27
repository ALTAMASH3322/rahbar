from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory
from flask_login import login_required, current_user
import mysql.connector
from config import Config as c  # Import config values
from werkzeug.utils import secure_filename
import os

# Create Blueprint for coordinator routes
coordinator_bp = Blueprint('coordinator', __name__)

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

# Coordinator Dashboard
@coordinator_bp.route('/coordinator_dashboard', methods=['GET'])
@login_required
def coordinator_dashboard():
    # Ensure only Coordinators can access this route
    if current_user.role_id != 3:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch coordinator details
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    coordinator = cursor.fetchone()

    # Debugging: Print coordinator details
    print(f"Coordinator Details: {coordinator}")

    # Fetch all applications
    cursor.execute("""
        SELECT gd.*, u.name AS applicant_name
        FROM grantee_details gd
        JOIN users u ON gd.user_id = u.user_id
    """)
    applications = cursor.fetchall()

    # Fetch all sponsors and convenors
    cursor.execute("""
        SELECT u.*, r.role_name, r.description
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE u.role_id IN (4, 5)  
    """)
    sponsors_convenors = cursor.fetchall()

    # Fetch all grantees (students)
    cursor.execute("SELECT * FROM users WHERE role_id = 6")  # Role ID 6 = Grantee (Student)
    grantees = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'coordinator/dashboard.html',
        coordinator=coordinator,
        applications=applications,
        sponsors_convenors=sponsors_convenors,
        grantees=grantees
    )

# View Applications Route
@coordinator_bp.route('/co_view_applications', methods=['GET'])
@login_required
def co_view_applications():
    if current_user.role_id != 3:  # Ensure only coordinators can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all applications
    cursor.execute("""
        SELECT gd.*, u.name AS applicant_name
        FROM grantee_details gd
        JOIN users u ON gd.user_id = u.user_id
    """)
    applications = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('coordinator/view_applications.html', applications=applications)

# Assign Sponsor to Student
@coordinator_bp.route('/assign_sponsor', methods=['POST'])
@login_required
def assign_sponsor():
    if current_user.role_id != 3:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    grantee_id = request.form.get('grantee_id')
    grantor_id = request.form.get('grantor_id')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if the student is already assigned to a sponsor (grantor_id != 12)
        cursor.execute("SELECT * FROM grantor_grantees WHERE grantee_id = %s AND grantor_id != 12", (grantee_id,))
        existing_assignment = cursor.fetchone()

        if existing_assignment:
            # Update the existing assignment (status should not be Pending)
            cursor.execute("""
                UPDATE grantor_grantees
                SET grantor_id = %s, status = 'Assigned', updated_at = NOW()
                WHERE grantee_id = %s
            """, (grantor_id, grantee_id))
        else:
            # Insert new assignment (status should not be Pending)
            cursor.execute("""
                INSERT INTO grantor_grantees (grantor_id, grantee_id, status, created_at, updated_at)
                VALUES (%s, %s, 'Assigned', NOW(), NOW())
            """, (grantor_id, grantee_id))

        conn.commit()
        flash('Sponsor assigned successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('coordinator.coordinator_dashboard'))

# Activate/Inactivate Sponsor or Convenor
@coordinator_bp.route('/update_user_status/<int:user_id>/<status>', methods=['GET'])
@login_required
def update_user_status(user_id, status):
    if current_user.role_id != 3:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update user status
        cursor.execute("""
            UPDATE users
            SET status = %s
            WHERE user_id = %s
        """, (status, user_id))
        conn.commit()

        # If the user is a sponsor or convenor and is being deactivated, reassign their grantees to grantor 12
        if status == 'Inactive':
            cursor.execute("""
                UPDATE grantor_grantees
                SET grantor_id = 12, status = 'Unassigned'
                WHERE grantor_id = %s
            """, (user_id,))
            conn.commit()

        flash(f'User status updated to {status}, and grantees reassigned to default grantor (ID: 12).', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('coordinator.coordinator_dashboard'))

# Manage Sponsors
@coordinator_bp.route('/co_manage_sponsors', methods=['GET'])
@login_required
def co_manage_sponsors():
    print(current_user)
    if current_user.role_id != 3:  # Ensure only coordinators can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all sponsors and convenors
    cursor.execute("""
        SELECT u.*, r.role_name, r.description
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE u.role_id IN (4, 5)  # Role ID 4 = Convenor, 5 = Sponsor
    """)
    sponsors_convenors = cursor.fetchall()

    # Fetch all grantees (students)
    cursor.execute("SELECT * FROM users WHERE role_id = 6")  # Role ID 6 = Grantee (Student)
    grantees = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'coordinator/manage_sponsors.html',
        sponsors_convenors=sponsors_convenors,
        grantees=grantees
    )




# Appoint Sponsor as Convenor
@coordinator_bp.route('/appoint_convenor/<int:sponsor_id>', methods=['POST'])
@login_required
def appoint_convenor(sponsor_id):
    if current_user.role_id != 3:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    region = request.form.get('region')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update user role to Convenor (Role ID 4) and set region
        cursor.execute("""
            UPDATE users
            SET role_id = 4, region = %s
            WHERE user_id = %s
        """, (region, sponsor_id))
        conn.commit()

        flash('Sponsor appointed as Convenor successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('coordinator.coordinator_dashboard'))

# Change Region of Sponsor or Convenor
@coordinator_bp.route('/change_region/<int:user_id>', methods=['POST'])
@login_required
def change_region(user_id):
    if current_user.role_id != 3:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    region = request.form.get('region')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update user region
        cursor.execute("""
            UPDATE users
            SET region = %s
            WHERE user_id = %s
        """, (region, user_id))
        conn.commit()

        flash('Region updated successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('coordinator.coordinator_dashboard'))

# Assign Students to Sponsors (Bulk Assignment)
@coordinator_bp.route('/assign_students_to_sponsors', methods=['POST'])
@login_required
def assign_students_to_sponsors():
    if current_user.role_id != 3:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    student_ids = request.form.getlist('student_ids')
    sponsor_id = request.form.get('sponsor_id')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Assign students to the selected sponsor
        for student_id in student_ids:
            # Check if the student is already assigned to a sponsor (grantor_id != 12)
            cursor.execute("SELECT * FROM grantor_grantees WHERE grantee_id = %s AND grantor_id != 12", (student_id,))
            existing_assignment = cursor.fetchone()

            if existing_assignment:
                # Update the existing assignment (status should not be Pending)
                cursor.execute("""
                    UPDATE grantor_grantees
                    SET grantor_id = %s, status = 'Assigned', updated_at = NOW()
                    WHERE grantee_id = %s
                """, (sponsor_id, student_id))
            else:
                # Insert new assignment (status should not be Pending)
                cursor.execute("""
                    INSERT INTO grantor_grantees (grantor_id, grantee_id, status, created_at, updated_at)
                    VALUES (%s, %s, 'Assigned', NOW(), NOW())
                """, (sponsor_id, student_id))

        conn.commit()
        flash('Students assigned to sponsor successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('coordinator.coordinator_dashboard'))

# View All Sponsors and Convenors with Roles and Regions
@coordinator_bp.route('/view_sponsors_convenors', methods=['GET'])
@login_required
def view_sponsors_convenors():
    if current_user.role_id != 3:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all sponsors and convenors with their roles and regions
    cursor.execute("""
        SELECT u.*, r.role_name, r.description
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE u.role_id IN (4, 5)  # Role ID 4 = Convenor, 5 = Sponsor
    """)
    sponsors_convenors = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'coordinator/view_sponsors_convenors.html',
        sponsors_convenors=sponsors_convenors
    )

# Monitor Payments
@coordinator_bp.route('/monitor_payments', methods=['GET'])
@login_required
def monitor_payments():
    if current_user.role_id != 3:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all payments with grantee and grantor details
    cursor.execute("""
        SELECT p.*, u1.name AS grantee_name, u2.name AS grantor_name
        FROM payments p
        JOIN users u1 ON p.grantee_id = u1.user_id
        JOIN users u2 ON p.grantor_id = u2.user_id
    """)
    payments = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('coordinator/monitor_payments.html', payments=payments)

# Change Payment Status
@coordinator_bp.route('/update_payment_status/<int:payment_id>', methods=['POST'])
@login_required
def update_payment_status(payment_id):
    if current_user.role_id != 3:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    status = request.form.get('status')
    comments = request.form.get('comments')

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update payment status and comments
        cursor.execute("""
            UPDATE payments
            SET status = %s, comments = %s
            WHERE payment_id = %s
        """, (status, comments, payment_id))
        conn.commit()

        flash('Payment status updated successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('coordinator.monitor_payments'))

# View Uploaded File
@coordinator_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

# Generate Reports
@coordinator_bp.route('/generate_reports', methods=['GET'])
@login_required
def generate_reports():
    if current_user.role_id != 3:
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

    return render_template(
        'coordinator/generate_reports.html',
        applications=applications,
        payments=payments,
        sponsors_convenors=sponsors_convenors,
        grantees=grantees
    )