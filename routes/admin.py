from flask import Blueprint, current_app, render_template, request, redirect, url_for, flash, jsonify, send_file, send_from_directory
from flask_login import login_required, current_user
import mysql.connector
from config import Config as c  # Import config values
from werkzeug.security import generate_password_hash, check_password_hash
import os
import pandas as pd
from io import BytesIO
from datetime import datetime
import datetime
from werkzeug.utils import secure_filename


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
    if current_user.role_id not in [1, 2]:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Get selected year from query parameters, default to None (all years)
    selected_year = request.args.get('year', None)
    if selected_year == "": # Handle case where "All Years" (empty value) is selected
        selected_year = None
    
    # --- Fetch available years for the dropdown ---
    # We'll query each relevant table and combine the years
    all_years_set = set()

    # Years from users table (assuming 'created_at' column exists)
    # Replace 'created_at' with your actual column name if different
    cursor.execute("SELECT DISTINCT YEAR(created_at) as year FROM users WHERE created_at IS NOT NULL")
    for row in cursor.fetchall():
        if row['year']:
            all_years_set.add(row['year'])

    # Years from grantee_details table (assuming 'created_at' or a relevant date column exists)
    # Replace 'application_date' or 'created_at' with your actual column name
    # For grantee_details, let's assume a submission date like 'application_date' or a generic 'created_at'
    # If it doesn't have a created_at, you might need to choose a relevant date field or skip it for year filtering
    cursor.execute("SELECT DISTINCT YEAR(created_at) as year FROM grantee_details WHERE created_at IS NOT NULL") # Assuming created_at
    for row in cursor.fetchall():
        if row['year']:
            all_years_set.add(row['year'])
    
    # Years from payments table (assuming 'payment_date' or 'created_at' column exists)
    # Replace 'payment_date' with your actual column name
    cursor.execute("SELECT DISTINCT YEAR(payment_date) as year FROM payments WHERE payment_date IS NOT NULL") # Assuming payment_date
    for row in cursor.fetchall():
        if row['year']:
            all_years_set.add(row['year'])

    # Sponsors/Convenors are from the users table, so their years are already covered by the first query.

    available_years = sorted(list(all_years_set), reverse=True) # Sort descending

    # --- Build WHERE clauses for year filtering ---
    year_filter_users = ""
    year_filter_applications = ""
    year_filter_payments = ""

    params_users = []
    params_applications = []
    params_payments = []

    if selected_year:
        try:
            # Validate selected_year is an integer
            year_int = int(selected_year)
            year_filter_users = "WHERE YEAR(created_at) = %s"
            params_users.append(year_int)
            
            # Adjust column name for grantee_details if different
            year_filter_applications = "WHERE YEAR(created_at) = %s" # Assuming created_at
            params_applications.append(year_int)

            # Adjust column name for payments if different
            year_filter_payments = "WHERE YEAR(payment_date) = %s" # Assuming payment_date
            params_payments.append(year_int)

        except ValueError:
            flash('Invalid year selected.', 'error')
            selected_year = None # Fallback to all years if invalid
            # Reset filters if year is invalid
            year_filter_users = ""
            year_filter_applications = ""
            year_filter_payments = ""
            params_users = []
            params_applications = []
            params_payments = []


    # --- Fetch data with year filtering ---
    cursor.execute(f"SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
    admin = cursor.fetchone()

    # Fetch users count
    cursor.execute(f"SELECT COUNT(*) as count FROM users {year_filter_users}", tuple(params_users))
    users_count = cursor.fetchone()['count']

    # Fetch applications count
    cursor.execute(f"SELECT COUNT(*) as count FROM grantee_details {year_filter_applications}", tuple(params_applications))
    applications_count = cursor.fetchone()['count']

    # Fetch payments count
    cursor.execute(f"SELECT COUNT(*) as count FROM payments {year_filter_payments}", tuple(params_payments))
    payments_count = cursor.fetchone()['count']

    # Fetch sponsors and convenors count
    # Sponsors/Convenors are also users, so their created_at is tied to the users table.
    # We need to combine the year filter with the role and status filter.
    sponsors_convenors_base_query = "SELECT COUNT(*) as count FROM users WHERE role_id IN (4, 5) AND status LIKE 'Active'"
    sponsors_params = []
    if selected_year:
        sponsors_convenors_query = f"{sponsors_convenors_base_query} AND YEAR(created_at) = %s"
        sponsors_params.append(int(selected_year)) # Assuming selected_year is validated
    else:
        sponsors_convenors_query = sponsors_convenors_base_query
        
    cursor.execute(sponsors_convenors_query, tuple(sponsors_params))
    sponsors_convenors_count = cursor.fetchone()['count']

    # Fetch all grantees (students) - Not directly filtered by year for summary card in original request
    # If you want to filter grantees by year as well, apply similar logic.
    cursor.execute("SELECT * FROM users WHERE role_id = 6")
    grantees = cursor.fetchall() # For now, keep fetching all grantees if not used in a year-filtered card

    # Fetch application period status
    cursor.execute("SELECT * FROM application_period WHERE id = 1 AND is_active = 1")
    application_period = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'admin/dashboard.html',
        admin=admin,
        users_count=users_count,
        applications_count=applications_count,
        payments_count=payments_count,
        sponsors_convenors_count=sponsors_convenors_count,
        grantees=grantees, # Pass grantees if still needed elsewhere on the page
        application_period=application_period,
        available_years=available_years,
        selected_year=selected_year
    )

# Start or End Application Period
@admin_bp.route('/manage_application_period', methods=['GET', 'POST'])
@login_required
def manage_application_period():
    if current_user.role_id not in [1, 2]:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = None 
    cursor = None 

    if request.method == 'POST':
        action = request.form.get('action')
        start_date_str = request.form.get('start_date')
        end_date_str = request.form.get('end_date')
        user_id = current_user.user_id

        try:
            conn = get_db_connection()
            # Use a buffered cursor for POST operations as well, just in case
            cursor = conn.cursor(dictionary=True, buffered=True) 

            if action == 'start':
                if not start_date_str or not end_date_str:
                    flash('Start date and end date are required to start a new period.', 'error')
                else:
                    try:
                        start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
                        end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()

                        if end_date < start_date:
                            flash('End date cannot be before the start date.', 'error')
                        else:
                            
                            
                            cursor.execute("""
                                INSERT INTO application_period (start_date, end_date, is_active)
                                VALUES (%s, %s, 1)
                            """, (start_date, end_date)) 
                            
                            conn.commit()
                            flash('New application period started successfully! All previous active periods have been ended.', 'success')
                    except ValueError:
                        flash('Invalid date format. Please use YYYY-MM-DD.', 'error')
            
            elif action == 'end':
                cursor.execute("""
                    UPDATE application_period 
                    SET is_active = 0
                    WHERE is_active = 1; 
                """)
                
                if cursor.rowcount > 0: 
                    conn.commit()
                    flash(f'{cursor.rowcount} application period(s) ended successfully!', 'success')
                else:
                    flash('No active application period found to end.', 'info')
            else:
                flash('Invalid action specified.', 'error')

        except Exception as e:
            if conn and conn.is_connected(): conn.rollback()
            flash(f'An error occurred: {str(e)}', 'error')
            current_app.logger.error(f"Error in manage_application_period POST: {e}", exc_info=True)
        finally:
            if cursor: cursor.close()
            if conn: conn.close()

        return redirect(url_for('admin.manage_application_period'))

    # --- For GET requests, fetch the CURRENTLY ACTIVE period (if any) ---
    application_period_data = None
    try:
        conn = get_db_connection()
        # Use a buffered cursor for GET requests
        cursor = conn.cursor(dictionary=True, buffered=True) 
        
        cursor.execute("SELECT id, start_date, end_date, is_active FROM application_period WHERE is_active = 1 ORDER BY start_date DESC LIMIT 1")
        application_period_data = cursor.fetchone() # Consume the result

        # If no active period, and you want to show the last created one (optional)
        # The "pass" in your original code meant the second query's results might not have been consumed if it ran.
        if not application_period_data:
            # Example: Fetch last entered period if none active (optional display logic)
            # cursor.execute("SELECT id, start_date, end_date, is_active FROM application_period ORDER BY id DESC LIMIT 1")
            # last_period = cursor.fetchone() # MUST consume result if query is run
            # if last_period:
            #    application_period_data = last_period # Or just use it to display "Last period was..."
            pass # Current logic: if no active period, application_period_data remains None

    except Exception as e:
        flash(f'Error fetching application period: {str(e)}', 'error')
        current_app.logger.error(f"Error in manage_application_period GET: {e}", exc_info=True)
    finally:
        if cursor: cursor.close() # This is where the error was happening
        if conn: conn.close()
        
    return render_template('admin/manage_application_period.html', application_period=application_period_data)
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
        contact = request.form.get('contact')
        email = request.form.get('email')
        role_id = request.form.get('role_id')
        status = request.form.get('status')
        region = request.form.get('region')
        password = request.form.get('password')
        hashed_password = password
        cursor.execute("""
            INSERT INTO users (user_id, name, email,phone, role_id, status, password_hash, created_at, updated_at, region)
            VALUES (%s, %s, %s,%s, %s, %s,%s, NOW(), NOW(),%s)
        """, (user_id, name, email,contact, role_id, status, hashed_password,region))

        #print(user_id, name, email, role_id, status, hashed_password, region)

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
@admin_bp.route('/edit_user/<user_id>', methods=['GET', 'POST'])
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
@admin_bp.route('/delete_user/<user_id>', methods=['GET'])
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

    conn = None
    cursor = None
    
    # Generate a list of years for the dropdown, e.g., last 5 years to next 5 years
    current_system_year = datetime.datetime.now().year
    available_years_for_dropdown = [str(y) for y in range(current_system_year - 5, current_system_year + 6)]

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        if request.method == 'POST':
            user_id = current_user.user_id
            selected_year_str = request.form.get('selected_year')
            amount_str = request.form.get('amount')

            if not selected_year_str or not amount_str:
                flash('Year and Amount are required.', 'error')
            else:
                try:
                    selected_year = int(selected_year_str)
                    amount = float(amount_str)
                    if amount < 0:
                         raise ValueError("Amount cannot be negative.")

                    # ON DUPLICATE KEY UPDATE will work if 'year' is a UNIQUE key
                    cursor.execute("""
                        INSERT INTO payment_schedules (
                            amount,
                            year,
                            status, -- Assuming status is still 1 or to be set
                            updated_by
                        )
                        VALUES (%s, %s, 1, %s) -- 3 Python placeholders
                        ON DUPLICATE KEY UPDATE
                            amount = VALUES(amount),
                            status = VALUES(status), -- Or remove if status is not managed here
                            updated_at = NOW(),
                            updated_by = VALUES(updated_by);
                    """, (amount, selected_year, user_id))
                    conn.commit()
                    flash(f'Payment amount for year {selected_year} saved successfully.', 'success')
                except ValueError:
                    flash('Invalid year or amount format. Amount cannot be negative.', 'error')
                    if conn.is_connected(): conn.rollback()
                except Exception as e:
                    flash(f'An error occurred: {str(e)}', 'error')
                    if conn.is_connected(): conn.rollback()
                    current_app.logger.error(f"Error in POST system_configuration: {e}", exc_info=True)
            
            # Redirect to the same page, possibly with the year pre-selected if desired
            # Or just redirect to the base config page.
            # To pre-select, add ?selected_year=selected_year to the redirect URL.
            return redirect(url_for('admin.system_configuration'))

        # --- GET request - load all existing payment schedules ---
        # And also get data for a potentially pre-selected year for the form
        
        # Fetch all schedules for display in the table
        cursor.execute("""
            SELECT ps.schedule_id, ps.amount, ps.year, ps.updated_at, u.name as updated_by_name
            FROM payment_schedules ps
            LEFT JOIN users u ON ps.updated_by = u.user_id
            ORDER BY ps.year DESC
        """)
        all_schedules = cursor.fetchall()

        # For the form: if a year is selected via GET param (e.g., after an error or for editing)
        # Or default to the current year for the form
        year_for_form_str = request.args.get('selected_year', str(current_system_year))
        try:
            year_for_form = int(year_for_form_str)
        except ValueError:
            year_for_form = current_system_year # Fallback

        form_data = {'amount': '', 'selected_year_for_form': year_for_form}

        cursor.execute("""
            SELECT amount FROM payment_schedules WHERE year = %s
        """, (year_for_form,))
        schedule_for_form_year = cursor.fetchone()
        if schedule_for_form_year:
            form_data['amount'] = schedule_for_form_year['amount']
        

        return render_template(
            'admin/system_configuration.html',
            all_schedules=all_schedules, # For the display table
            form_data=form_data, # For pre-filling the add/edit form
            available_years=available_years_for_dropdown, # For the year selection dropdown
            current_system_year=current_system_year # For general display if needed
        )

    except Exception as e:
        flash(f'An unexpected error occurred: {str(e)}', 'error')
        current_app.logger.error(f"Error in system_configuration: {e}", exc_info=True)
        # Fallback rendering in case of major error
        return render_template(
            'admin/system_configuration.html',
            all_schedules=[],
            form_data={'amount': '', 'selected_year_for_form': current_system_year},
            available_years=available_years_for_dropdown,
            current_system_year=current_system_year
        )
    finally:
        if cursor: cursor.close()
        if conn: conn.close()
# Generate Reports
@admin_bp.route('/admin_generate_reports', methods=['GET', 'POST'])
@login_required
def admin_generate_reports():
    if current_user.role_id not in [1, 2]:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Fetch Applications (Modified to include the assigned Human Sponsor)
    cursor.execute("""
        SELECT gd.*, 
               sr.reference_id AS assigned_reference_id,
               sponsor_user.name AS assigned_sponsor_name
        FROM grantee_details gd
        LEFT JOIN grantor_grantees gg ON gd.user_id = gg.grantee_id
        LEFT JOIN sponsor_references sr ON gg.grantor_id COLLATE utf8mb4_general_ci = sr.reference_id COLLATE utf8mb4_general_ci
        LEFT JOIN users sponsor_user ON sr.user_id COLLATE utf8mb4_general_ci = sponsor_user.user_id COLLATE utf8mb4_general_ci
    """)
    applications_data = cursor.fetchall()

    # 2. Fetch Payments (Modified to correctly find Grantor Name via Reference ID)
    cursor.execute("""
        SELECT
            p.payment_id, p.amount, p.status AS payment_status, p.payment_date,
            p.receipt_url, p.grantee_id,
            grantee_user.name AS grantee_name,
            p.grantor_id AS grantor_reference_id,
            sponsor_user.name AS grantor_name,
            p.created_at, p.updated_at
        FROM payments p
        LEFT JOIN users grantee_user ON p.grantee_id = grantee_user.user_id
        -- We join through sponsor_references to find which human made this payment
        LEFT JOIN sponsor_references sr ON p.grantor_id COLLATE utf8mb4_general_ci = sr.reference_id COLLATE utf8mb4_general_ci
        LEFT JOIN users sponsor_user ON sr.user_id COLLATE utf8mb4_general_ci = sponsor_user.user_id COLLATE utf8mb4_general_ci
    """)
    payments_data = cursor.fetchall()

    # 3. Fetch all sponsors and convenors
    cursor.execute("SELECT * FROM users WHERE role_id IN (4, 5)")
    sponsors_convenors_data = cursor.fetchall()

    # 4. Fetch all grantees (students)
    cursor.execute("SELECT * FROM users WHERE role_id = 6")
    grantees_data = cursor.fetchall()

    cursor.close()
    conn.close()

    if request.method == 'POST':
        report_type = request.form.get('reportType')
        report_format = request.form.get('format')

        data_for_df = []
        filename_prefix = 'report'
        columns_for_report = []

        if report_type == 'applications':
            data_for_df = applications_data
            filename_prefix = 'applications_report'
            columns_for_report = [
                'grantee_detail_id', 'name', 'father_name', 'rcc_name', 
                'course_applied', 'assigned_sponsor_name', 'assigned_reference_id'
            ]
        elif report_type == 'payments':
            data_for_df = payments_data
            filename_prefix = 'payments_report'
            columns_for_report = [
                'payment_id', 'grantee_name', 'grantor_name', 'grantor_reference_id', 
                'amount', 'payment_status', 'payment_date'
            ]
        elif report_type == 'sponsors_convenors':
            data_for_df = sponsors_convenors_data
            filename_prefix = 'sponsors_convenors_report'
        elif report_type == 'grantees':
            data_for_df = grantees_data
            filename_prefix = 'grantees_report'
        else:
            flash('Invalid report type selected.', 'error')
            return redirect(url_for('admin.admin_generate_reports'))

        if not data_for_df:
            flash(f'No data available for {report_type} report.', 'info')
            return redirect(url_for('admin.admin_generate_reports'))

        df = pd.DataFrame(data_for_df)

        if columns_for_report:
            df = df[[col for col in columns_for_report if col in df.columns]]

        if report_format == 'csv':
            output = BytesIO()
            df.to_csv(output, index=False, encoding='utf-8')
            output.seek(0)
            return send_file(output, as_attachment=True, download_name=f"{filename_prefix}.csv", mimetype='text/csv')

        elif report_format == 'excel':
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Report')
            output.seek(0)
            return send_file(output, as_attachment=True, download_name=f"{filename_prefix}.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        elif report_format == 'pdf':
            try:
                from weasyprint import HTML
                html_content = df.to_html(index=False, border=1, classes="table table-striped")
                styled_html = f"<html><body><h2>{filename_prefix.replace('_', ' ').title()}</h2>{html_content}</body></html>"
                output = BytesIO()
                HTML(string=styled_html).write_pdf(output)
                output.seek(0)
                return send_file(output, as_attachment=True, download_name=f"{filename_prefix}.pdf", mimetype='application/pdf')
            except ImportError:
                flash("PDF library not installed.", "error")
                return redirect(url_for('admin.admin_generate_reports'))

    return render_template(
        'admin/generate_reports.html',
        applications=applications_data,
        payments=payments_data,
        sponsors_convenors=sponsors_convenors_data,
        grantees=grantees_data
    )

# Serve Uploaded Files
@admin_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(UPLOAD_FOLDER, filename)


# Public Application Form

@admin_bp.route('/apply', methods=['GET', 'POST'])
@login_required
def public_application():
    #print(current_user.user_id )
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
                'student_mobile': student_mobile,
                'name': request.form['name']
            }

            # Insert into grantee_details
            cursor.execute("""
                INSERT INTO grantee_details 
                (user_id,name, father_name, mother_name, father_profession, mother_profession, 
                 address, average_annual_salary, rahbar_alumnus, rcc_name, course_applied,
                 father_mobile, mother_mobile, student_mobile, created_at, updated_at)
                VALUES (NULL, %(name)s , %(father_name)s, %(mother_name)s, %(father_profession)s, 
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

            print(current_user.user_id)

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
        SELECT g.grantee_detail_id,g.name, g.father_name, g.mother_name, g.rcc_name, a.status 
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
    #print(application_id)
    application = cursor.fetchone()

    if not application:
        flash("Application not found!", "error")
        return redirect(url_for('admin.view_applications'))

    if request.method == 'POST':
        try:
            new_status = request.form['status']
            comments = request.form['comments']

            # Ensure valid status
            valid_statuses = ['draft', 'submitted', 'interviewing', 'accepted', 'rejected','on hold', 'provisional admission letter', 'admitted']
            if new_status not in valid_statuses:
                flash("Invalid status selected!", "error")
                return redirect(url_for('admin.view_application', application_id=application_id))

            # Update application status
            #print(f"This is the issue in the code{application_id}")
            cursor.execute("""
                UPDATE application_status
                SET status = %s, comments = %s, updated_by = %s , updated_at = NOW()
                WHERE grantee_detail_id = %s
            """, (new_status, comments, application_id , current_user.user_id))
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




@admin_bp.route('/manage_students', methods=['GET', 'POST'])
@login_required
def manage_students():
    if current_user.role_id not in [1, 2]:  # Only Admins
        flash('Permission denied', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all active students with their sponsors and current assignments
    cursor.execute("""
        SELECT 
            u.user_id, 
            u.name AS student_name,
            u.email AS student_email,
            u.phone AS student_phone,
            u.region,
            sponsor.name AS sponsor_name,
            inst.institution_name,
            c.course_name,
            sic.institution_id,
            sic.course_id
        FROM users u
        LEFT JOIN grantor_grantees gg ON u.user_id = gg.grantee_id
        LEFT JOIN users sponsor ON gg.grantor_id = sponsor.user_id
        LEFT JOIN student_institution_courses sic ON u.user_id = sic.user_id
        LEFT JOIN institutions inst ON sic.institution_id = inst.institution_id
        LEFT JOIN courses c ON sic.course_id = c.course_id
        WHERE u.role_id = 6 AND u.status = 'active'
    """)
    students = cursor.fetchall()

    # Fetch all institutions for dropdown
    cursor.execute("SELECT * FROM institutions")
    institutions = cursor.fetchall()

    # Fetch all courses for dropdown

    cursor.execute("SELECT * FROM courses")
    courses = cursor.fetchall()

    if request.method == 'POST':
        try:
            user_id = request.form['user_id']
            institution_id = request.form['institution_id']
            course_id = request.form['course_id']

            # Validate course belongs to institution
            cursor.execute("""
                SELECT course_id 
                FROM courses 
                WHERE institution_id = %s AND course_id = %s
            """, (institution_id, course_id))
            if not cursor.fetchone():
                flash('Invalid course-institution combination', 'error')
                return redirect(url_for('admin.manage_students'))

            # Insert or update assignment
            cursor.execute("""
                INSERT INTO student_institution_courses 
                    (user_id, institution_id, course_id, assigned_by)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    institution_id = VALUES(institution_id),
                    course_id = VALUES(course_id),
                    assigned_by = VALUES(assigned_by),
                    assigned_at = NOW()
            """, (user_id, institution_id, course_id, current_user.user_id))

            conn.commit()
            flash('Assignment updated successfully!', 'success')

        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'error')
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('admin.manage_students'))
    
    

    cursor.close()
    conn.close()

    return render_template('admin/manage_students.html',students=students,institutions=institutions, courses=courses)



@admin_bp.route('/admin_map_students_to_sponsors/<string:user_id>', methods=['GET', 'POST'])
@login_required
def admin_map_students_to_sponsors(user_id):
    if current_user.role_id not in [1, 2]:
        flash('Permission denied', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Fetch Human Sponsor Details
    cursor.execute("SELECT user_id, name, email, region FROM users WHERE user_id = %s", (user_id,))
    sponsor = cursor.fetchone()

    if not sponsor:
        flash('Sponsor not found.', 'error')
        conn.close()
        return redirect(url_for('admin.manage_sponsorships'))

    # 2. Fetch all Reference IDs belonging to this human
    cursor.execute("SELECT reference_id, sponsor_year, chapter FROM sponsor_references WHERE user_id = %s", (user_id,))
    available_references = cursor.fetchall()
    ref_id_list = [r['reference_id'] for r in available_references]

    # 3. Handle POST (Saving changes)
    if request.method == 'POST':
        try:
            student_ids = request.form.getlist('student_ids')
            target_ref_id = request.form.get('target_reference_id')

            if not target_ref_id:
                flash('Please select a Reference ID for assignment.', 'error')
            else:
                query = """
                    INSERT INTO grantor_grantees (grantee_id, grantor_id, status, created_at) 
                    VALUES (%s, %s, 'Accepted', NOW())
                    ON DUPLICATE KEY UPDATE grantor_id = VALUES(grantor_id), updated_at = NOW()
                """
                for student_id in student_ids:
                    cursor.execute(query, (student_id, target_ref_id))
                
                conn.commit()
                flash(f'Students successfully mapped to Reference {target_ref_id}!', 'success')
            
            return redirect(url_for('admin.admin_map_students_to_sponsors', user_id=user_id))
        except Exception as e:
            conn.rollback()
            flash(f'Error: {str(e)}', 'error')

    # 4. Handle GET (Fetching Data)
    
    # A. Mapped Students (Right Side) - Added GROUP BY to prevent duplicates
    mapped_students = []
    if ref_id_list:
        format_strings = ','.join(['%s'] * len(ref_id_list))
        cursor.execute(f"""
            SELECT u.user_id, u.name, u.email, u.phone, u.region, 
                   MAX(gg.grantor_id) AS linked_ref_id
            FROM users u
            JOIN grantor_grantees gg ON u.user_id = gg.grantee_id
            WHERE gg.grantor_id IN ({format_strings}) AND u.status = 'active'
            GROUP BY u.user_id
            ORDER BY u.name ASC
        """, tuple(ref_id_list))
        mapped_students = cursor.fetchall()

    # B. Available Students (Left Side) - Added GROUP BY and MAX() to prevent duplicates
    # This prevents the repeating "Rashid Qamar" rows shown in your screenshot
    format_strings_sub = ','.join(['%s'] * len(ref_id_list)) if ref_id_list else "''"
    
    available_students_query = f"""
        SELECT u.user_id, u.name, u.email, u.phone, u.region, 
               MAX(actual_sponsor.name) as current_sponsor_name,
               MAX(gg.grantor_id) as current_ref_id
        FROM users u
        LEFT JOIN grantor_grantees gg ON u.user_id = gg.grantee_id
        LEFT JOIN sponsor_references sr ON gg.grantor_id COLLATE utf8mb4_general_ci = sr.reference_id COLLATE utf8mb4_general_ci
        LEFT JOIN users actual_sponsor ON sr.user_id COLLATE utf8mb4_general_ci = actual_sponsor.user_id COLLATE utf8mb4_general_ci
        WHERE u.role_id = 6 
        AND u.status = 'active'
        AND (u.user_id NOT IN (SELECT grantee_id FROM grantor_grantees WHERE grantor_id IN ({format_strings_sub})))
        GROUP BY u.user_id
        ORDER BY u.name ASC
    """
    
    cursor.execute(available_students_query, tuple(ref_id_list) if ref_id_list else ())
    available_students = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template(
        'admin/map_students_to_sponsor.html',
        sponsor=sponsor,
        references=available_references,
        students=available_students,
        mapped_students=mapped_students,
        mapped_student_ids=[s['user_id'] for s in mapped_students]
    )

@admin_bp.route('/manage_sponsorships', methods=['GET'])
@login_required
def manage_sponsorships():
    # Permission Check
    if current_user.role_id not in [1, 2]:
        flash('Permission denied', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch Sponsors, Convenors, and Coordinators (Roles 3, 4, 5)
    cursor.execute("""
        SELECT u.user_id, u.name, u.email, u.phone, u.status, u.region, r.role_name
        FROM users u
        JOIN roles r ON u.role_id = r.role_id
        WHERE u.role_id IN (3, 4, 5) AND u.status = 'active'
        ORDER BY u.name ASC
    """)
    sponsors = cursor.fetchall()

    cursor.close()
    conn.close()

    return render_template('admin/manage_sponsorships.html', sponsors=sponsors)

@admin_bp.route('/get_courses/<int:institution_id>')
@login_required
def get_courses(institution_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT course_id, course_name 
        FROM courses 
        WHERE institution_id = %s
    """, (institution_id,))
    
    courses = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return jsonify(courses)








# ==============================================================================
# ADMIN STUDENT MANAGEMENT API (Search, View Details, Edit, Actions)
# ==============================================================================


@admin_bp.route('/api/students/list', methods=['GET'])
@login_required
def get_all_students_data():
    if current_user.role_id not in [1, 2]:
        return jsonify({'error': 'Unauthorized'}), 403

    draw = request.args.get('draw', 1, type=int)
    start = request.args.get('start', 0, type=int)
    length = request.args.get('length', 10, type=int)
    search_value = request.args.get('search[value]', '', type=str).strip()
    inst_filter = request.args.get('institution_id')
    course_filter = request.args.get('course_id')

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # UPDATED JOIN CHAIN with Collation Bridge:
    # We force both sides of the join to use utf8mb4_general_ci to prevent the 1267 error
    query_body = """
        FROM users u
        LEFT JOIN grantee_details gd ON u.user_id = gd.user_id
        LEFT JOIN grantor_grantees gg ON u.user_id = gg.grantee_id
        
        -- Collation Fix for Sponsor References
        LEFT JOIN sponsor_references sr ON gg.grantor_id COLLATE utf8mb4_general_ci = sr.reference_id COLLATE utf8mb4_general_ci
        
        -- Collation Fix for Sponsor User link
        LEFT JOIN users sponsor ON sr.user_id COLLATE utf8mb4_general_ci = sponsor.user_id COLLATE utf8mb4_general_ci
        
        LEFT JOIN student_institution_courses sic ON u.user_id = sic.user_id
        LEFT JOIN institutions inst ON sic.institution_id = inst.institution_id
        LEFT JOIN courses c ON sic.course_id = c.course_id
        WHERE u.role_id = 6
    """
    params = []
    
    if inst_filter:
        query_body += " AND sic.institution_id = %s"
        params.append(inst_filter)
    if course_filter:
        query_body += " AND sic.course_id = %s"
        params.append(course_filter)
    if search_value:
        query_body += " AND (u.name LIKE %s OR u.email LIKE %s OR u.user_id LIKE %s OR sponsor.name LIKE %s OR sr.reference_id LIKE %s)"
        wildcard = f"%{search_value}%"
        params.extend([wildcard, wildcard, wildcard, wildcard, wildcard])

    # 1. Count unique students
    cursor.execute(f"SELECT COUNT(DISTINCT u.user_id) as count {query_body}", tuple(params))
    records_filtered = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM users WHERE role_id = 6")
    records_total = cursor.fetchone()['count']

    # 2. Final query
    final_query = f"""
        SELECT u.user_id, u.name, u.email, u.phone, u.region, u.status,
               MAX(sr.reference_id) AS sponsor_id, 
               MAX(sponsor.name) AS sponsor_name,
               MAX(inst.institution_name) AS institution_name, 
               MAX(c.course_name) AS course_name
        {query_body}
        GROUP BY u.user_id
        ORDER BY u.user_id DESC LIMIT %s, %s
    """
    params.extend([start, length])
    
    try:
        cursor.execute(final_query, tuple(params))
        data = cursor.fetchall()
    except Exception as e:
        print(f"SQL Error: {e}")
        return jsonify({"error": str(e)}), 500

    cursor.close()
    conn.close()
    return jsonify({
        "draw": draw, 
        "recordsTotal": records_total, 
        "recordsFiltered": records_filtered, 
        "data": data
    })

import json

import json

@admin_bp.route('/api/student/details/<user_id>', methods=['GET'])
@login_required

def get_student_full_details(user_id):
    if current_user.role_id not in [1, 2]:
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True, buffered=True)

    try:
        # 1. Fetch Profile
        cursor.execute("""
            SELECT u.user_id, u.name AS user_real_name, u.email, u.phone, u.status, u.region, u.year,
                   gd.* 
            FROM users u
            LEFT JOIN grantee_details gd ON u.user_id = gd.user_id
            WHERE u.user_id = %s
        """, (user_id,))
        profile = cursor.fetchone()

        if not profile:
             return jsonify({'error': 'Student not found'}), 404
        
        profile['name'] = profile['user_real_name']

        # 2. Fetch Year-Specific Amount
        cursor.execute("""
            SELECT amount as schedule_amount 
            FROM payment_schedules 
            WHERE year = %s AND status = 1 
            LIMIT 1
        """, (profile['year'],))
        schedule_info = cursor.fetchone()
        profile['annual_schedule_amount'] = schedule_info['schedule_amount'] if schedule_info else 0

        # 3. Bank Details
        cursor.execute("SELECT * FROM bank_details WHERE user_id = %s", (user_id,))
        bank = cursor.fetchone()

        # 4. Course Assignment
        cursor.execute("""
            SELECT sic.assigned_at, sic.institution_id, sic.course_id, 
                   c.course_name, c.number_of_semesters, i.institution_name
            FROM student_institution_courses sic
            JOIN courses c ON sic.course_id = c.course_id
            JOIN institutions i ON sic.institution_id = i.institution_id
            WHERE sic.user_id = %s
        """, (user_id,))
        course_info = cursor.fetchone()

        # 5. UPDATED SPONSOR INFO Logic
        # Join: Mapping (gg) -> Reference (sr) -> Human (u)
        cursor.execute("""
            SELECT u.user_id, u.name, u.email, sr.reference_id 
            FROM grantor_grantees gg
            JOIN sponsor_references sr ON gg.grantor_id COLLATE utf8mb4_general_ci = sr.reference_id COLLATE utf8mb4_general_ci
            JOIN users u ON sr.user_id COLLATE utf8mb4_general_ci = u.user_id COLLATE utf8mb4_general_ci
            WHERE gg.grantee_id = %s
        """, (user_id,))
        sponsor = cursor.fetchone()

        # 6. Payment History
        cursor.execute("""
            SELECT p.*, u.name as grantor_name FROM payments p
            LEFT JOIN users u ON p.grantor_id = u.user_id
            WHERE p.grantee_id = %s ORDER BY p.payment_date DESC
        """, (user_id,))
        payments = cursor.fetchall()

        # 7. Documents
        cursor.execute("SELECT * FROM student_progress WHERE grantee_id = %s ORDER BY created_at DESC", (user_id,))
        documents = cursor.fetchall()

        response_data = {
            "profile": profile,
            "bank": bank,
            "course": course_info,
            "sponsor": sponsor,
            "payments": payments,
            "documents": documents
        }

        # Safe Date Conversion
        def default_converter(o):
            if isinstance(o, (datetime.date, datetime.datetime)):
                return o.isoformat()
            return str(o)

        return current_app.response_class(json.dumps(response_data, default=default_converter), mimetype='application/json')

    except Exception as e:
        print(f"Error in detail fetch: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/api/student/update', methods=['POST'])
@login_required
def update_student_full_details():
    if current_user.role_id not in [1, 2]:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    user_id = data.get('user_id')
    if not user_id:
        return jsonify({'error': 'User ID missing'}), 400

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # --- 1. UPDATE USERS TABLE ---
        # We only update the fields that are actually in the 'data' package
        user_updates = []
        user_params = []
        for field in ['name', 'email', 'phone', 'region', 'status']:
            if field in data and data[field] is not None:
                user_updates.append(f"{field} = %s")
                user_params.append(data[field])
        
        if user_updates:
            user_sql = f"UPDATE users SET {', '.join(user_updates)}, updated_at = NOW() WHERE user_id = %s"
            user_params.append(user_id)
            cursor.execute(user_sql, tuple(user_params))

        # --- 2. UPDATE GRANTEE_DETAILS ---
        grantee_updates = []
        grantee_params = []
        for field in ['father_name', 'mother_name', 'address', 'father_mobile', 'mother_mobile']:
            if field in data and data[field] is not None:
                grantee_updates.append(f"{field} = %s")
                grantee_params.append(data[field])
        
        if grantee_updates:
            grantee_sql = f"UPDATE grantee_details SET {', '.join(grantee_updates)}, updated_at = NOW() WHERE user_id = %s"
            grantee_params.append(user_id)
            cursor.execute(grantee_sql, tuple(grantee_params))

        # --- 3. BANK DETAILS (The error fix) ---
        cursor.execute("SELECT * FROM bank_details WHERE user_id = %s", (user_id,))
        exists = cursor.fetchone()

        bank_fields = {
            'bank_name': data.get('bank_name'),
            'account_number': data.get('account_number'),
            'ifsc_code': data.get('ifsc_code'),
            'account_name': data.get('account_name')
        }

        if exists:
            # Update existing
            cursor.execute("""
                UPDATE bank_details SET bank_name=%s, account_number=%s, ifsc_code=%s, account_name=%s 
                WHERE user_id=%s
            """, (bank_fields['bank_name'], bank_fields['account_number'], 
                  bank_fields['ifsc_code'], bank_fields['account_name'], user_id))
        else:
            # Create new - FIXING Error 1364 by manually finding the next ID
            if bank_fields['account_number']:
                cursor.execute("SELECT COALESCE(MAX(bank_detail_id), 0) + 1 AS next_id FROM bank_details")
                new_id = cursor.fetchone()['next_id']
                cursor.execute("""
                    INSERT INTO bank_details (bank_detail_id, user_id, bank_name, account_number, ifsc_code, account_name)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (new_id, user_id, bank_fields['bank_name'], bank_fields['account_number'], 
                      bank_fields['ifsc_code'], bank_fields['account_name']))

        # --- 4. COURSE ASSIGNMENT ---
        if data.get('institution_id') and data.get('course_id'):
            cursor.execute("""
                INSERT INTO student_institution_courses (user_id, institution_id, course_id, assigned_by, assigned_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE institution_id=VALUES(institution_id), course_id=VALUES(course_id)
            """, (user_id, data['institution_id'], data['course_id'], current_user.user_id))

        conn.commit()
        return jsonify({'success': True, 'message': 'Successfully updated student record.'})

    except Exception as e:
        conn.rollback()
        print(f"Update Error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()


@admin_bp.route('/api/student/action', methods=['POST'])
@login_required
def perform_student_action():
    """
    API to perform specific actions like Deactivate, Activate, or Unmap Sponsor.
    """
    if current_user.role_id not in [1, 2]:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    user_id = data.get('user_id') # This is the Student's Reference ID
    action = data.get('action') # 'activate', 'deactivate', 'unassign_sponsor'

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        if action == 'deactivate':
            cursor.execute("UPDATE users SET status = 'Inactive' WHERE user_id = %s", (user_id,))
            msg = "Student deactivated successfully."
        
        elif action == 'activate':
            cursor.execute("UPDATE users SET status = 'Active' WHERE user_id = %s", (user_id,))
            msg = "Student activated successfully."
        
        elif action == 'unassign_sponsor':
            # Logic Update: Since we link Students to Sponsor Reference IDs,
            # we simply delete the mapping row to make them "Unassigned"
            cursor.execute("DELETE FROM grantor_grantees WHERE grantee_id = %s", (user_id,))
            msg = "Student unassigned from sponsor reference successfully."
            
        else:
            return jsonify({'error': 'Invalid action'}), 400

        conn.commit()
        return jsonify({'success': True, 'message': msg})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()



# Route for the NEW Student Directory/Edit Page
@admin_bp.route('/student_directory', methods=['GET'])
@login_required
def student_directory():
    # 1. Permission Check
    if current_user.role_id not in [1, 2]:
        flash('Permission denied', 'error')
        return redirect(url_for('auth.login'))
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 2. Fetch admin details for the sidebar name display
        cursor.execute("SELECT * FROM users WHERE user_id = %s", (current_user.user_id,))
        admin = cursor.fetchone()

        # 3. Fetch all Institutions (For top filters and Assignment modal)
        cursor.execute("SELECT institution_id, institution_name FROM institutions ORDER BY institution_name ASC")
        institutions = cursor.fetchall()

        # 4. Fetch all Courses (For top filters and Assignment modal)
        # We include institution_id here so the JavaScript can filter courses based on the selected college
        cursor.execute("SELECT course_id, course_name, institution_id FROM courses ORDER BY course_name ASC")
        courses = cursor.fetchall()

    except Exception as e:
        flash(f"Error loading directory: {str(e)}", "error")
        admin = None
        institutions = []
        courses = []
    finally:
        cursor.close()
        conn.close()

    # 5. Return template with all required data
    return render_template('admin/student_directory.html', 
                           admin=admin, 
                           institutions=institutions, 
                           courses=courses)



@admin_bp.route('/upload_students_csv', methods=['GET'])
@login_required
def upload_students_csv():
    if current_user.role_id not in [1, 2]:
        flash('Permission denied', 'error')
        return redirect(url_for('auth.login'))
    


    return render_template('admin/upload_students_csv.html')


# ==============================================================================
# ADMIN PAYMENT ACTION API (Record New Payment)
# ==============================================================================

@admin_bp.route('/api/payment/record_action', methods=['POST'])
@login_required

def admin_record_payment():
    if current_user.role_id not in [1, 2]:
        return jsonify({'error': 'Unauthorized'}), 403

    from datetime import datetime 

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # 1. Get Form Data
        action_type = request.form.get('action_type') # 'create' or 'edit'
        payment_id = request.form.get('payment_id') 
        grantee_id = request.form.get('grantee_id') # The Student ID
        amount = request.form.get('amount')
        payment_date = request.form.get('payment_date') 
        status = request.form.get('status', 'Paid')
        
        # 2. Handle File Upload
        receipt_file = request.files.get('receipt')
        receipt_path = None
        if receipt_file and receipt_file.filename != '':
            timestamp = datetime.now().timestamp()
            filename = secure_filename(f"admin_pay_{grantee_id}_{timestamp}_{receipt_file.filename}")
            filepath = os.path.join(UPLOAD_FOLDER, filename)
            receipt_file.save(filepath)
            receipt_path = filename 

        # 3. Database Logic
        if action_type == 'create':
            if not grantee_id or not amount:
                return jsonify({'error': 'Missing student or amount'}), 400
            
            # --- NEW STEP: Find the Sponsor Reference ID for this student ---
            # We look in grantor_grantees to find WHICH reference is supporting this student
            cursor.execute("""
                SELECT grantor_id FROM grantor_grantees 
                WHERE grantee_id = %s LIMIT 1
            """, (grantee_id,))
            mapping = cursor.fetchone()
            
            # If student isn't mapped, we can't link the payment to a sponsor reference
            if not mapping:
                return jsonify({'error': 'This student is not assigned to any Sponsor Reference. Mapping required first.'}), 400
            
            target_reference_id = mapping['grantor_id']
            final_date = payment_date if payment_date else datetime.now().strftime('%Y-%m-%d')

            # We insert the Reference ID as the grantor_id
            cursor.execute("""
                INSERT INTO payments (grantor_id, grantee_id, amount, payment_date, status, receipt_url, created_at, updated_by)
                VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (target_reference_id, grantee_id, amount, final_date, status, receipt_path, current_user.user_id))
            
            msg = "Payment recorded and linked to Sponsor Reference successfully."

        elif action_type == 'edit':
            if not payment_id:
                return jsonify({'error': 'Payment ID missing'}), 400
            
            query = "UPDATE payments SET amount=%s, payment_date=%s, status=%s, updated_at=NOW(), updated_by=%s"
            params = [amount, payment_date, status, current_user.user_id]
            
            if receipt_path:
                query += ", receipt_url=%s"
                params.append(receipt_path)
            
            query += " WHERE payment_id=%s"
            params.append(payment_id)
            
            cursor.execute(query, tuple(params))
            msg = "Payment updated successfully."

        conn.commit()
        return jsonify({'success': True, 'message': msg})

    except Exception as e:
        if conn: conn.rollback()
        print(f"Payment Error: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()




import re
import pandas as pd
from flask import request, redirect, url_for, flash
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

@admin_bp.route('/api/students/bulk_upload', methods=['POST'])
@login_required
def bulk_upload_students():
    if current_user.role_id not in [1, 2]:
        return redirect(url_for('admin.student_directory'))

    file = request.files.get('file')
    if not file: return redirect(url_for('admin.student_directory'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        try:
            df = pd.read_csv(file)
        except:
            file.seek(0)
            df = pd.read_csv(file, encoding='latin-1')

        # Cleanup headers: lowercase and remove spaces
        df.columns = [str(c).strip().lower().replace(" ", "") for c in df.columns]
        df = df.astype(object).where(pd.notnull(df), None)

        hashed_pw = generate_password_hash("hello")
        STUDENT_ROLE_ID = 6
        success_count = 0

        for index, row in df.iterrows():
            try:
                u_id = str(row.get('studentreference', '')).strip()
                name = str(row.get('studentname', '')).strip()
                
                if not u_id or u_id in ['None', '']: continue

                # --- STEP A: USERS (Prevent duplication manually if DB unique constraint missing) ---
                email_val = row.get('email') or f"{u_id}@rahbar.com"
                phone_val = str(row.get('mobilestudent') or '')
                year_adm = row.get('yearadmission')

                cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (u_id,))
                user_exists = cursor.fetchone()

                if user_exists:
                    cursor.execute("""
                        UPDATE users SET name=%s, email=%s, phone=%s, year=%s, updated_at=NOW() 
                        WHERE user_id=%s
                    """, (name, email_val, phone_val, year_adm, u_id))
                else:
                    cursor.execute("""
                        INSERT INTO users (user_id, name, email, sex, phone, role_id, status, password_hash, year, created_at, updated_at)
                        VALUES (%s, %s, %s, 'M', %s, %s, 'Active', %s, %s, NOW(), NOW())
                    """, (u_id, name, email_val, phone_val, STUDENT_ROLE_ID, hashed_pw, year_adm))

                # --- STEP B: GRANTEE_DETAILS ---
                cursor.execute("""
                    INSERT INTO grantee_details (user_id, name, father_name, address, course_applied, rcc_name, father_mobile, mother_mobile, student_mobile, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                    ON DUPLICATE KEY UPDATE name=VALUES(name), father_name=VALUES(father_name), address=VALUES(address), course_applied=VALUES(course_applied), updated_at=NOW()
                """, (u_id, name, row.get('fathername'), row.get('address'), row.get('course(branch)'), row.get('rccnon-rcc'), row.get('mobile-1'), row.get('mobile-2'), phone_val))

                # --- STEP C: BANK DETAILS (New Ultra-Forgiving Parser) ---
                bank_raw = str(row.get('bank') or '').strip()
                acc_no, bnk_nm, ifsc = None, None, None

                if bank_raw and bank_raw not in ['None', '']:
                    # Try Format 1: A/c Number...
                    if "A/c Number" in bank_raw:
                        acc_m = re.search(r"A/c Number:\s*([^,]+)", bank_raw)
                        bnk_m = re.search(r"Bank:\s*([^,]+)", bank_raw)
                        ifs_m = re.search(r"IFSC Code:\s*(\w+)", bank_raw)
                        acc_no = acc_m.group(1).strip().replace('*','') if acc_m else None
                        bnk_nm = bnk_m.group(1).strip() if bnk_m else None
                        ifsc = ifs_m.group(1).strip() if ifs_m else None
                    
                    # Try Format 2: Bank & Branch...
                    elif "Bank & Branch" in bank_raw:
                        bnk_m = re.search(r"Bank & Branch:\s*(.*)", bank_raw)
                        bnk_nm = bnk_m.group(1).strip() if bnk_m else bank_raw
                    
                    # Fallback: Just take the whole string
                    if not bnk_nm:
                        bnk_nm = bank_raw

                    cursor.execute("SELECT bank_detail_id FROM bank_details WHERE user_id = %s", (u_id,))
                    if cursor.fetchone():
                        cursor.execute("UPDATE bank_details SET account_number=%s, bank_name=%s, ifsc_code=%s, account_name=%s WHERE user_id=%s", (acc_no, bnk_nm, ifsc, name, u_id))
                    else:
                        cursor.execute("SELECT COALESCE(MAX(bank_detail_id), 0) + 1 as n_id FROM bank_details")
                        new_bank_id = cursor.fetchone()['n_id']
                        cursor.execute("INSERT INTO bank_details (bank_detail_id, user_id, bank_name, account_number, ifsc_code, account_name) VALUES (%s, %s, %s, %s, %s, %s)", (new_bank_id, u_id, bnk_nm, acc_no, ifsc, name))

                # --- STEP D: INSTITUTIONS & COURSES ---
                coll_name = row.get('college')
                course_name = row.get('course(branch)')
                if coll_name and course_name:
                    cursor.execute("SELECT institution_id FROM institutions WHERE institution_name = %s", (coll_name,))
                    inst_res = cursor.fetchone()
                    if inst_res: inst_id = inst_res['institution_id']
                    else:
                        cursor.execute("SELECT COALESCE(MAX(institution_id), 0) + 1 as n_inst FROM institutions")
                        inst_id = cursor.fetchone()['n_inst']
                        cursor.execute("INSERT INTO institutions (institution_id, institution_name, address, created_at, updated_at) VALUES (%s, %s, 'Bulk Upload', NOW(), NOW())", (inst_id, coll_name))

                    cursor.execute("SELECT course_id FROM courses WHERE course_name = %s AND institution_id = %s", (course_name, inst_id))
                    crs_res = cursor.fetchone()
                    if crs_res: course_id = crs_res['course_id']
                    else:
                        cursor.execute("INSERT INTO courses (institution_id, course_name, fees_per_semester, number_of_semesters) VALUES (%s, %s, 0, 8)", (inst_id, course_name))
                        course_id = cursor.lastrowid

                    cursor.execute("""
                        INSERT INTO student_institution_courses (user_id, institution_id, course_id, assigned_by, assigned_at)
                        VALUES (%s, %s, %s, %s, NOW())
                        ON DUPLICATE KEY UPDATE institution_id=VALUES(institution_id), course_id=VALUES(course_id)
                    """, (u_id, inst_id, course_id, current_user.user_id))

                success_count += 1
            except Exception as e:
                print(f"Error at {u_id}: {e}")
                continue

        conn.commit()
        flash(f'Success! Processed {success_count} unique students.', 'success')

    except Exception as e:
        if conn: conn.rollback()
        flash(f"Error: {e}", 'error')
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return redirect(url_for('admin.student_directory'))




@admin_bp.route('/api/students/manual_add', methods=['POST'])
@login_required
def manual_add_student():
    if current_user.role_id not in [1, 2]:
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        # --- 1. Get Data from Form ---
        u_id = request.form.get('user_id')
        name = request.form.get('name')
        
        # --- 2. USERS TABLE ---
        hashed_pw = generate_password_hash("hello")
        email = request.form.get('email') or f"{u_id}@rahbar.com"
        
        cursor.execute("""
            INSERT INTO users (user_id, name, email, sex, phone, role_id, status, password_hash, year, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 6, 'Active', %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE name=VALUES(name), email=VALUES(email), phone=VALUES(phone), year=VALUES(year), updated_at=NOW()
        """, (u_id, name, email, request.form.get('sex'), request.form.get('phone'), hashed_pw, request.form.get('year')))

        # --- 3. GRANTEE_DETAILS ---
        cursor.execute("""
            INSERT INTO grantee_details (
                user_id, name, father_name, mother_name, address, course_applied, 
                rcc_name, father_mobile, mother_mobile, student_mobile, created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            ON DUPLICATE KEY UPDATE 
                father_name=VALUES(father_name), mother_name=VALUES(mother_name), address=VALUES(address),
                course_applied=VALUES(course_applied), rcc_name=VALUES(rcc_name), updated_at=NOW()
        """, (u_id, name, request.form.get('father_name'), request.form.get('mother_name'), 
              request.form.get('address'), request.form.get('course_name'), request.form.get('rcc_name'),
              request.form.get('father_mobile'), request.form.get('mother_mobile'), request.form.get('phone')))

        # --- 4. BANK DETAILS ---
        bnk_nm = request.form.get('bank_name')
        if bnk_nm:
            cursor.execute("SELECT bank_detail_id FROM bank_details WHERE user_id = %s", (u_id,))
            if cursor.fetchone():
                cursor.execute("""
                    UPDATE bank_details SET bank_name=%s, account_number=%s, ifsc_code=%s, account_name=%s 
                    WHERE user_id=%s
                """, (bnk_nm, request.form.get('acc_no'), request.form.get('ifsc'), name, u_id))
            else:
                cursor.execute("SELECT COALESCE(MAX(bank_detail_id), 0) + 1 as n_id FROM bank_details")
                new_bid = cursor.fetchone()['n_id']
                cursor.execute("""
                    INSERT INTO bank_details (bank_detail_id, user_id, bank_name, account_number, ifsc_code, account_name) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (new_bid, u_id, bnk_nm, request.form.get('acc_no'), request.form.get('ifsc'), name))

        # --- 5. INSTITUTION & COURSE MAPPING ---
        inst_id = request.form.get('institution_id')
        crs_id = request.form.get('course_id')
        if inst_id and crs_id:
            cursor.execute("""
                INSERT INTO student_institution_courses (user_id, institution_id, course_id, assigned_by, assigned_at)
                VALUES (%s, %s, %s, %s, NOW())
                ON DUPLICATE KEY UPDATE institution_id=VALUES(institution_id), course_id=VALUES(course_id)
            """, (u_id, inst_id, crs_id, current_user.user_id))

        conn.commit()
        flash(f'Student {u_id} registered successfully!', 'success')
        return redirect(url_for('admin.student_directory'))

    except Exception as e:
        if conn: conn.rollback()
        flash(f'Error: {str(e)}', 'error')
        return redirect(url_for('admin.student_directory'))
    finally:
        cursor.close()
        conn.close()









# API to get full sponsor details and all their references
@admin_bp.route('/api/sponsor/details/<user_id>', methods=['GET'])
@login_required
def get_sponsor_full_details(user_id):
    if current_user.role_id not in [1, 2]:
        return jsonify({'error': 'Unauthorized'}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # 1. Fetch User Profile
    cursor.execute("SELECT user_id, name, email, phone, region, status FROM users WHERE user_id = %s", (user_id,))
    profile = cursor.fetchone()

    if not profile:
        return jsonify({'error': 'Sponsor not found'}), 404

    # 2. Fetch all References for this User
    cursor.execute("SELECT * FROM sponsor_references WHERE user_id = %s", (user_id,))
    references = cursor.fetchall()

    # Helper to convert dates for JSON
    def date_handler(obj):
        return obj.isoformat() if hasattr(obj, 'isoformat') else obj

    return current_app.response_class(
        json.dumps({'profile': profile, 'references': references}, default=date_handler),
        mimetype='application/json'
    )

# API to update Sponsor Profile
@admin_bp.route('/api/sponsor/update', methods=['POST'])
@login_required
def update_sponsor_details():
    if current_user.role_id not in [1, 2]:
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.json
    user_id = data.get('user_id')
    
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Update Users Table
        cursor.execute("""
            UPDATE users 
            SET name=%s, email=%s, phone=%s, region=%s 
            WHERE user_id=%s
        """, (data['name'], data['email'], data['phone'], data['region'], user_id))

        conn.commit()
        return jsonify({'success': True, 'message': 'Sponsor profile updated!'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cursor.close()
        conn.close()



@admin_bp.route('/api/sponsors/bulk_upload', methods=['POST'])
@login_required
def bulk_upload_sponsors():
    if current_user.role_id not in [1, 2]:
        return redirect(url_for('admin.student_directory'))

    file = request.files.get('file')
    if not file: return redirect(url_for('admin.student_directory'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    def safe_date(val):
        if not val or pd.isna(val) or str(val).strip().lower() in ['nan', 'none', '']: return None
        try: return pd.to_datetime(val).strftime('%Y-%m-%d')
        except: return None

    try:
        try:
            df = pd.read_csv(file)
        except:
            file.seek(0)
            df = pd.read_csv(file, encoding='latin-1')

        # Clean headers
        df.columns = [str(c).strip().lower().replace(" ", "").replace("_", "") for c in df.columns]
        df = df.astype(object).where(pd.notnull(df), None)

        SPONSOR_ROLE_ID = 5
        hashed_pw = generate_password_hash("hello")
        success_count = 0

        for index, row in df.iterrows():
            try:
                # Basic Mapping
                ref_id = str(row.get('sponsorreference', '')).strip()
                name = str(row.get('sponsorname', '')).strip()
                email = str(row.get('sponsoremail', '')).strip() if row.get('sponsoremail') else None
                mobile1 = str(row.get('sponsormobile1', '')).strip() if row.get('sponsormobile1') else None
                chapter = str(row.get('sponsorchapter', '')).strip() or "General"
                
                if not ref_id or ref_id == 'None': continue

                # --- STEP 1: IDENTITY MERGING (Find Existing Person) ---
                user_id = None
                if email and email not in ['None', '', 'nan']:
                    cursor.execute("SELECT user_id FROM users WHERE email = %s AND role_id IN (3,4,5) LIMIT 1", (email,))
                    res = cursor.fetchone()
                    if res: user_id = res['user_id']

                if not user_id and mobile1 and mobile1 not in ['None', '', 'nan']:
                    cursor.execute("SELECT user_id FROM users WHERE phone = %s AND role_id IN (3,4,5) LIMIT 1", (mobile1,))
                    res = cursor.fetchone()
                    if res: user_id = res['user_id']

                if not user_id and name and chapter:
                    cursor.execute("SELECT user_id FROM users WHERE name = %s AND region = %s AND role_id IN (3,4,5) LIMIT 1", (name, chapter))
                    res = cursor.fetchone()
                    if res: user_id = res['user_id']

                # --- STEP 2: CREATE OR UPDATE USER ACCOUNT ---
                if not user_id:
                    user_id = f"USR-{ref_id}" 
                    cursor.execute("""
                        INSERT INTO users (user_id, name, email, phone, role_id, status, password_hash, region, created_at, updated_at)
                        VALUES (%s, %s, %s, %s, %s, 'active', %s, %s, NOW(), NOW())
                    """, (user_id, name, email, mobile1, SPONSOR_ROLE_ID, hashed_pw, chapter))
                else:
                    cursor.execute("UPDATE users SET updated_at=NOW() WHERE user_id=%s", (user_id,))

                # --- STEP 3: FILL SPONSOR REFERENCES ---
                cursor.execute("""
                    REPLACE INTO sponsor_references (
                        reference_id, user_id, sponsor_year, chapter, referral, 
                        installment_date, payment_months, confirm_credit_date, 
                        special_demand, remarks, mobile_1, mobile_2, created_at, updated_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                """, (
                    ref_id, user_id, row.get('sponsoryear'), chapter, row.get('sponsorreferal'),
                    safe_date(row.get('datetransf1stinstallment')),
                    row.get('paymentnumberofmonths') or 0,
                    safe_date(row.get('confirmcreditdate')),
                    row.get('specialdemand'), row.get('remarks'), mobile1, row.get('sponsormobile2')
                ))

                # --- STEP 4: MAP STUDENTS (GRANTOR_GRANTEES) ---
                # We use row.get('studentassigned') from your CSV
                student_data = str(row.get('studentassigned') or '').strip()
                if student_data and student_data.lower() not in ['none', 'nan', '']:
                    # Support multiple student IDs in one cell (e.g. M001, M002)
                    stu_list = [s.strip() for s in student_data.split(',')]
                    for stu_id in stu_list:
                        if stu_id:
                            cursor.execute("""
                                INSERT INTO grantor_grantees (grantor_id, grantee_id, status, created_at)
                                VALUES (%s, %s, 'Accepted', NOW())
                                ON DUPLICATE KEY UPDATE updated_at = NOW()
                            """, (ref_id, stu_id)) # Link Student to Reference ID

                success_count += 1
            except Exception as e_row:
                print(f"Row {index} failed: {e_row}")
                continue

        conn.commit()
        flash(f'Success! Processed {success_count} rows. Sponsors merged and students mapped.', 'success')

    except Exception as e:
        if conn: conn.rollback()
        flash(f"System Error: {str(e)}", 'error')
    finally:
        if cursor: cursor.close()
        if conn: conn.close()

    return redirect(url_for('admin.manage_sponsorships'))