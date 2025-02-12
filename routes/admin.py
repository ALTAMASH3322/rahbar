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
@admin_bp.route('/manage_application_period', methods=['GET', 'POST'])
@login_required
def manage_application_period():
    if current_user.role_id not in [1, 2]:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch current application period status
    cursor.execute("SELECT * FROM application_period WHERE id = 1")
    application_period = cursor.fetchone()

    if request.method == 'POST':
        action = request.form.get('action')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')

        try:
            if action == 'start':
                if not start_date or not end_date:
                    flash('Start and end dates are required.', 'error')
                    return redirect(url_for('admin.manage_application_period'))

                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                end_date = datetime.strptime(end_date, '%Y-%m-%d')

                cursor.execute("""
                    INSERT INTO application_period (id, start_date, end_date, is_active)
                    VALUES (1, %s, %s, 1)
                    ON DUPLICATE KEY UPDATE
                        start_date = VALUES(start_date),
                        end_date = VALUES(end_date),
                        is_active = VALUES(is_active)
                """, (start_date, end_date))
                conn.commit()
                flash('Application period started successfully!', 'success')

            elif action == 'end':
                cursor.execute("UPDATE application_period SET is_active = 0 WHERE id = 1")
                conn.commit()
                flash('Application period ended successfully!', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin.manage_application_period'))

    # For GET requests, render the template
    cursor.close()
    conn.close()
    return render_template('admin/manage_application_period.html', application_period=application_period)

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
                INSERT INTO users (user_id, name, email, role_id, status, password_hash, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
            """, (user_id, name, email, role_id, status, hashed_password))

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



# Edit User
@admin_bp.route('/edit_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Handle user update

        name = request.form.get('name')
        email = request.form.get('email')
        role_id = request.form.get('role_id')
        status = request.form.get('status')

        cursor.execute("""
            UPDATE users
            SET name = %s, email = %s, role_id = %s, status = %s
            WHERE user_id = %s
        """, (name, email, role_id, status, user_id))
        conn.commit()
        flash('User updated successfully!', 'success')
        return redirect(url_for('admin.manage_users'))

    # Fetch user details
    cursor.execute("SELECT * FROM users WHERE user_id = %s", (user_id,))
    user = cursor.fetchone()

    # Fetch all roles
    cursor.execute("SELECT * FROM roles")
    roles = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/edit_user.html', user=user, roles=roles)




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
    if current_user.role_id not in [1, 2]:
        flash('Permission denied', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    frequencies = ['yearly', 'half-yearly', 'quarterly', 'monthly']

    if request.method == 'POST':
        try:
            # Process all frequencies
            for freq in frequencies:
                amount = request.form.get(f'amount_{freq}')
                deadline = request.form.get(f'deadline_{freq}')

                if amount and deadline:
                    cursor.execute("""
                        INSERT INTO payment_schedules (frequency, amount, deadline_date)
                        VALUES (%s, %s, %s)
                        ON DUPLICATE KEY UPDATE
                            amount = VALUES(amount),
                            deadline_date = VALUES(deadline_date),
                            updated_at = NOW()
                    """, (freq, float(amount), deadline))

            conn.commit()
            flash('Payment schedules updated successfully', 'success')

        except ValueError:
            flash('Invalid amount format', 'error')
            conn.rollback()
        except Exception as e:
            flash(f'Database error: {str(e)}', 'error')
            conn.rollback()
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin.system_configuration'))

    # GET request - load existing data
    cursor.execute("SELECT * FROM payment_schedules")
    existing_data = {row['frequency']: row for row in cursor.fetchall()}

    # Prepare data structure for template
    payment_data = []
    for freq in frequencies:
        payment_data.append({
            'frequency': freq,
            'amount': existing_data.get(freq, {}).get('amount', ''),
            'deadline': existing_data.get(freq, {}).get('deadline_date', '')
        })

    cursor.close()
    conn.close()

    return render_template(
        'admin/system_configuration.html',
        payment_data=payment_data,
        frequencies=frequencies
    )
# Generate Reports
@admin_bp.route('/admin_generate_reports', methods=['GET', 'POST'])
@login_required
def admin_generate_reports():
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        print("This is creating the issue")
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


# Public Application Form
@admin_bp.route('/apply', methods=['GET', 'POST'])
def public_application():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Check application period
    cursor.execute(
        "SELECT * FROM application_period WHERE is_active = 1 AND start_date <= CURDATE() AND end_date >= CURDATE()")
    period = cursor.fetchone()
    cursor.execute("SELECT * FROM rcc_centers")
    rcc_centers = cursor.fetchall()

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    if not period:
        cursor.close()
        conn.close()
        return render_template('application_closed.html')

    if request.method == 'POST':
        try:
            # Get mobile numbers
            father_mobile = request.form['father_mobile']
            mother_mobile = request.form['mother_mobile']
            student_mobile = request.form['student_mobile']

            # Server-side validation
            mobiles = [father_mobile, mother_mobile, student_mobile]

            # Check uniqueness
            if len(set(mobiles)) != 3:
                flash('All three mobile numbers must be different', 'error')
                return redirect(url_for('admin.public_application'))

            # Check valid 10-digit numbers
            if not all(num.isdigit() and len(num) == 10 for num in mobiles):
                flash('Invalid mobile numbers. Must be 10 digits', 'error')
                return redirect(url_for('admin.public_application'))

            form_data = {
                'father_name': request.form['father_name'],
                'mother_name': request.form['mother_name'],
                'father_profession': request.form['father_profession'],
                'mother_profession': request.form['mother_profession'],
                'address': request.form['address'],
                'average_annual_salary': request.form['average_annual_salary'],
                'rahbar_alumnus': 1 if request.form.get('rahbar_alumnus') else 0,
                'rcc_name': request.form['rcc_name'],
                'course_applied': request.form['course_applied'],
                'father_mobile': father_mobile,
                'mother_mobile': mother_mobile,
                'student_mobile': student_mobile
            }

            # Insert into grantee_details
            cursor.execute("""
                INSERT INTO grantee_details 
                (user_id, father_name, mother_name, father_profession, mother_profession, 
                 address, average_annual_salary, rahbar_alumnus, rcc_name, course_applied,
                 father_mobile, mother_mobile, student_mobile, created_at, updated_at)
                VALUES (NULL, %(father_name)s, %(mother_name)s, %(father_profession)s, 
                        %(mother_profession)s, %(address)s, %(average_annual_salary)s, 
                        %(rahbar_alumnus)s, %(rcc_name)s, %(course_applied)s,
                        %(father_mobile)s, %(mother_mobile)s, %(student_mobile)s, NOW(), NOW())
            """, form_data)

            grantee_detail_id = cursor.lastrowid

            # Create initial application status
            cursor.execute("""
                INSERT INTO application_status (grantee_detail_id, status, comments, updated_by)
                VALUES (%s, 'submitted', 'Application submitted', %s)
            """, (grantee_detail_id, None))

            conn.commit()
            flash('Application submitted successfully!', 'success')
            return redirect(url_for('admin.application_status', application_id=grantee_detail_id))

        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Database error: {err.msg}', 'error')
        except Exception as e:
            conn.rollback()
            flash(f'Error submitting application: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

    return render_template('public/apply.html',rcc_centers=rcc_centers,
                         courses=courses)


# Application Status Check
@admin_bp.route('/application_status', methods=['GET', 'POST'])
def check_application_status():
    if request.method == 'POST':
        mobile = request.form.get('mobile')

        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        # Check if mobile exists in any of the contact numbers
        cursor.execute("""
            SELECT grantee_detail_id 
            FROM grantee_details 
            WHERE student_mobile = %s 
               OR father_mobile = %s 
               OR mother_mobile = %s
        """, (mobile, mobile, mobile))

        application = cursor.fetchone()
        cursor.close()
        conn.close()

        if application:
            return redirect(url_for('admin.application_status',
                                    application_id=application['grantee_detail_id']))
        else:
            flash('No application found with this mobile number', 'error')
            return redirect(url_for('admin.check_application_status'))

    return render_template('public/check_status.html')


@admin_bp.route('/application_status/<int:application_id>')
def application_status(application_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT gd.*, s.status, s.comments, s.created_at as status_date
        FROM grantee_details gd
        LEFT JOIN application_status s ON gd.grantee_detail_id = s.grantee_detail_id
        WHERE gd.grantee_detail_id = %s
        ORDER BY s.created_at DESC
    """, (application_id,))

    application = cursor.fetchone()
    cursor.close()
    conn.close()

    if not application:
        flash('Invalid application ID', 'error')
        return redirect(url_for('admin.check_application_status'))

    return render_template('public/application_status.html', application=application)


# Admin Management of Applications
@admin_bp.route('/admin/manage_applications')
@login_required
def manage_applications():
    if current_user.role_id not in [1, 2, 4]:  # Admin and Convenors
        flash('Permission denied', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get applications with latest status
    cursor.execute("""
        SELECT gd.*, s.status, s.comments, s.created_at as status_date
        FROM grantee_details gd
        LEFT JOIN (
            SELECT grantee_detail_id, MAX(created_at) as latest
            FROM application_status
            GROUP BY grantee_detail_id
        ) latest_status ON gd.grantee_detail_id = latest_status.grantee_detail_id
        LEFT JOIN application_status s ON s.grantee_detail_id = latest_status.grantee_detail_id 
            AND s.created_at = latest_status.latest
    """)

    applications = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template('admin/manage_applications.html', applications=applications)


# Update Application Status
@admin_bp.route('/admin/update_application_status/<int:grantee_detail_id>', methods=['GET', 'POST'])
@login_required
def update_application_status(grantee_detail_id):
    if current_user.role_id not in [1, 2, 4]:  # Admin and Convenors
        flash('Permission denied', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        status = request.form['status']
        comments = request.form['comments']

        try:
            cursor.execute("""
                INSERT INTO application_status (grantee_detail_id, status, comments, updated_by)
                VALUES (%s, %s, %s, %s)
            """, (grantee_detail_id, status, comments, current_user.user_id))

            conn.commit()
            flash('Status updated successfully', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error updating status: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin.manage_applications'))

    # GET request - load current status
    cursor.execute("""
        SELECT * FROM application_status 
        WHERE grantee_detail_id = %s
        ORDER BY created_at DESC LIMIT 1
    """, (grantee_detail_id,))

    current_status = cursor.fetchone()
    cursor.close()
    conn.close()

    return render_template('admin/update_application_status.html',
                           application_id=grantee_detail_id,
                           current_status=current_status)



# Manage RCC Centers
@admin_bp.route('/manage_rcc_centers', methods=['GET', 'POST'])
@login_required
def manage_rcc_centers():
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Handle RCC center creation or update
        rcc_center_id = request.form.get('rcc_center_id')
        center_name = request.form.get('center_name')
        incharge_name = request.form.get('incharge_name')
        contact_number = request.form.get('contact_number')
        location = request.form.get('location')

        if rcc_center_id:  # Update existing RCC center
            cursor.execute("""
                UPDATE rcc_centers
                SET center_name = %s, incharge_name = %s, contact_number = %s, location = %s
                WHERE rcc_center_id = %s
            """, (center_name, incharge_name, contact_number, location, rcc_center_id))
        else:  # Create new RCC center
            cursor.execute("""
                INSERT INTO rcc_centers (center_name, incharge_name, contact_number, location)
                VALUES (%s, %s, %s, %s)
            """, (center_name, incharge_name, contact_number, location))

        conn.commit()
        flash('RCC Center saved successfully!', 'success')
        return redirect(url_for('admin.manage_rcc_centers'))

    # Fetch all RCC centers
    cursor.execute("SELECT * FROM rcc_centers")
    rcc_centers = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/manage_rcc_centers.html', rcc_centers=rcc_centers)


# Edit RCC Center
@admin_bp.route('/edit_rcc_center/<int:rcc_center_id>', methods=['GET', 'POST'])
@admin_bp.route('/edit_rcc_center', methods=['GET', 'POST'])  # Add this line to handle "Add New"
@login_required
def edit_rcc_center(rcc_center_id=None):  # Make rcc_center_id optional
    if current_user.role_id not in [1, 2]:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Handle form submission
        center_name = request.form.get('center_name')
        incharge_name = request.form.get('incharge_name')
        contact_number = request.form.get('contact_number')
        location = request.form.get('location')

        if rcc_center_id:  # Update existing RCC center
            cursor.execute("""
                UPDATE rcc_centers
                SET center_name = %s, incharge_name = %s, contact_number = %s, location = %s
                WHERE rcc_center_id = %s
            """, (center_name, incharge_name, contact_number, location, rcc_center_id))
        else:  # Create new RCC center
            cursor.execute("""
                INSERT INTO rcc_centers (center_name, incharge_name, contact_number, location)
                VALUES (%s, %s, %s, %s)
            """, (center_name, incharge_name, contact_number, location))

        conn.commit()
        flash('RCC Center saved successfully!', 'success')
        return redirect(url_for('admin.manage_rcc_centers'))

    # Fetch RCC center details (if editing)
    rcc_center = None
    if rcc_center_id:
        cursor.execute("SELECT * FROM rcc_centers WHERE rcc_center_id = %s", (rcc_center_id,))
        rcc_center = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('admin/edit_rcc_center.html', rcc_center=rcc_center)

    # Fetch RCC center details
    cursor.execute("SELECT * FROM rcc_centers WHERE rcc_center_id = %s", (rcc_center_id,))
    rcc_center = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template('admin/edit_rcc_center.html', rcc_center=rcc_center)


# Delete RCC Center
@admin_bp.route('/delete_rcc_center/<int:rcc_center_id>', methods=['GET'])
@login_required
def delete_rcc_center(rcc_center_id):
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete RCC center
        cursor.execute("DELETE FROM rcc_centers WHERE rcc_center_id = %s", (rcc_center_id,))
        conn.commit()
        flash('RCC Center deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin.manage_rcc_centers'))


# Manage Courses
@admin_bp.route('/manage_courses', methods=['GET', 'POST'])
@login_required
def manage_courses():
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Handle course creation or update
        course_id = request.form.get('course_id')
        institution_id = request.form.get('institution_id')
        course_name = request.form.get('course_name')
        course_description = request.form.get('course_description')
        fees_per_semester = request.form.get('fees_per_semester')
        number_of_semesters = request.form.get('number_of_semesters')

        if course_id:  # Update existing course
            cursor.execute("""
                UPDATE courses
                SET institution_id = %s, course_name = %s, course_description = %s,
                    fees_per_semester = %s, number_of_semesters = %s
                WHERE course_id = %s
            """, (institution_id, course_name, course_description, fees_per_semester, number_of_semesters, course_id))
        else:  # Create new course
            cursor.execute("""
                INSERT INTO courses (institution_id, course_name, course_description, fees_per_semester, number_of_semesters)
                VALUES (%s, %s, %s, %s, %s)
            """, (institution_id, course_name, course_description, fees_per_semester, number_of_semesters))

        conn.commit()
        flash('Course saved successfully!', 'success')
        return redirect(url_for('admin.manage_courses'))

    # Fetch all courses with institution names
    cursor.execute("""
        SELECT c.*, i.institution_name 
        FROM courses c
        JOIN institutions i ON c.institution_id = i.institution_id
    """)
    courses = cursor.fetchall()

    # Fetch all institutions (if applicable)
    cursor.execute("SELECT * FROM institutions")
    institutions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/manage_courses.html', courses=courses, institutions=institutions)


# Edit Course
@admin_bp.route('/edit_course/<int:course_id>', methods=['GET', 'POST'])
@admin_bp.route('/edit_course', methods=['GET', 'POST'])  # Add this line to handle "Add New"
@login_required
def edit_course(course_id=None):  # Make course_id optional
    if current_user.role_id not in [1, 2]:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Handle form submission
        institution_id = request.form.get('institution_id')
        course_name = request.form.get('course_name')
        course_description = request.form.get('course_description')
        fees_per_semester = request.form.get('fees_per_semester')
        number_of_semesters = request.form.get('number_of_semesters')

        if course_id:  # Update existing course
            cursor.execute("""
                UPDATE courses
                SET institution_id = %s, course_name = %s, course_description = %s,
                    fees_per_semester = %s, number_of_semesters = %s
                WHERE course_id = %s
            """, (institution_id, course_name, course_description, fees_per_semester, number_of_semesters, course_id))
        else:  # Create new course
            cursor.execute("""
                INSERT INTO courses (institution_id, course_name, course_description, fees_per_semester, number_of_semesters)
                VALUES (%s, %s, %s, %s, %s)
            """, (institution_id, course_name, course_description, fees_per_semester, number_of_semesters))

        conn.commit()
        flash('Course saved successfully!', 'success')
        return redirect(url_for('admin.manage_courses'))

    # Fetch course details (if editing)
    course = None
    if course_id:
        cursor.execute("SELECT * FROM courses WHERE course_id = %s", (course_id,))
        course = cursor.fetchone()

    # Fetch all institutions
    cursor.execute("SELECT * FROM institutions")
    institutions = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/edit_course.html', course=course, institutions=institutions)


# Delete Course
@admin_bp.route('/delete_course/<int:course_id>', methods=['GET'])
@login_required
def delete_course(course_id):
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete course
        cursor.execute("DELETE FROM courses WHERE course_id = %s", (course_id,))
        conn.commit()
        flash('Course deleted successfully!', 'success')
    except Exception as e:
        conn.rollback()
        flash(f'An error occurred: {str(e)}', 'error')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('admin.manage_courses'))


# Add Institution Route
@admin_bp.route('/add_institution', methods=['GET', 'POST'])
@login_required
def add_institution():
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        try:
            # Get form data
            institution_id = request.form.get('institution_id')
            institution_name = request.form.get('institution_name')
            address = request.form.get('address')
            contact_number = request.form.get('contact_number')
            email = request.form.get('email')

            # Insert into institutions table
            cursor.execute("""
                INSERT INTO institutions (institution_id, institution_name, address, contact_number, email)
                VALUES (%s, %s, %s, %s, %s)
            """, (institution_id, institution_name, address, contact_number, email))

            conn.commit()
            flash('Institution added successfully!', 'success')
            return redirect(url_for('admin.manage_courses'))

        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Database error: {err.msg}', 'error')
        except Exception as e:
            conn.rollback()
            flash(f'Error adding institution: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

    # For GET requests, render the form
    return render_template('admin/add_institution.html')


# View Applications List
@admin_bp.route('/applications', methods=['GET'])
def view_applications():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT g.grantee_detail_id, g.father_name, g.mother_name, g.rcc_name, a.status 
        FROM grantee_details g
        LEFT JOIN application_status a ON g.grantee_detail_id = a.grantee_detail_id
    """)
    applications = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('applications.html', applications=applications)


# View and Update Application
@admin_bp.route('/application/<int:application_id>', methods=['GET', 'POST'])
def view_application(application_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch application details
    cursor.execute("""
        SELECT g.*, a.status, a.comments 
        FROM grantee_details g
        LEFT JOIN application_status a ON g.grantee_detail_id = a.grantee_detail_id
        WHERE g.grantee_detail_id = %s
    """, (application_id,))
    print(application_id)
    application = cursor.fetchone()

    if not application:
        flash("Application not found!", "error")
        return redirect(url_for('admin.view_applications'))

    if request.method == 'POST':
        try:
            new_status = request.form['status']
            comments = request.form['comments']

            # Ensure valid status
            valid_statuses = ['draft', 'submitted', 'interviewing', 'accepted', 'rejected']
            if new_status not in valid_statuses:
                flash("Invalid status selected!", "error")
                return redirect(url_for('admin.view_application', application_id=application_id))

            # Update application status
            #print(f"This is the issue in the code{application_id}")
            cursor.execute("""
                UPDATE application_status
                SET status = %s, comments = %s, updated_at = NOW()
                WHERE grantee_detail_id = %s
            """, (new_status, comments, application_id))
            # Replace None with user ID if authentication exists

            conn.commit()
            flash("Application status updated successfully!", "success")
            return redirect(url_for('admin.view_application', application_id=application_id))
        except mysql.connector.Error as err:
            conn.rollback()
            flash(f'Database error: {err.msg}', 'error')
        except Exception as e:
            conn.rollback()
            flash(f'Error updating application: {str(e)}', 'error')

    cursor.close()
    conn.close()

    return render_template('application_details.html', application=application,
                           statuses=['draft', 'submitted', 'interviewing', 'accepted', 'rejected'])
