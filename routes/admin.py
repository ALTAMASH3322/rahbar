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
        hashed_password = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (user_id, name, email,phone, role_id, status, password_hash, created_at, updated_at, region)
            VALUES (%s, %s, %s,%s, %s, %s,%s, NOW(), NOW(),%s)
        """, (user_id, name, email,contact, role_id, status, hashed_password,region))

        print(user_id, name, email, role_id, status, hashed_password, region)

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
    if current_user.role_id not in [1, 2]:  # Ensure only Admins can access this route
        flash('You do not have permission to access this page.', 'error')
        # print("Permission issue hit") # For debugging if needed
        return redirect(url_for('auth.login'))

    # --- Data Fetching for page load and report generation ---
    # It's better to fetch data once. If POST, this data is used.
    # If GET, this data is passed to the template for previews.

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch all applications (Original query)
    cursor.execute("SELECT * FROM grantee_details")
    applications_data = cursor.fetchall() # Use a different variable name to avoid confusion

    # Fetch all payments (MODIFIED QUERY to include names)
    cursor.execute("""
        SELECT
            p.payment_id,
            p.amount,
            p.status AS payment_status,
            p.payment_date,
            p.receipt_url, 
            p.grantee_id,
            grantee_user.name AS grantee_name,
            p.grantor_id,
            grantor_user.name AS grantor_name,
            p.created_at, 
            p.updated_at
        FROM payments p
        LEFT JOIN users grantee_user ON p.grantee_id = grantee_user.user_id
        LEFT JOIN users grantor_user ON p.grantor_id = grantor_user.user_id
       
    """)
    payments_data = cursor.fetchall() # Use a different variable name

    # Fetch all sponsors and convenors (Original query)
    cursor.execute("SELECT * FROM users WHERE role_id IN (4, 5)")  # Role ID 4 = Convenor, 5 = Sponsor
    sponsors_convenors_data = cursor.fetchall() # Use a different variable name

    # Fetch all grantees (students) (Original query)
    cursor.execute("SELECT * FROM users WHERE role_id = 6")  # Role ID 6 = Grantee (Student)
    grantees_data = cursor.fetchall() # Use a different variable name

    cursor.close()
    conn.close()

    if request.method == 'POST':
        report_type = request.form.get('reportType')
        report_format = request.form.get('format') # Renamed from 'format' for clarity

        data_for_df = [] # Data to be converted to DataFrame
        filename_prefix = 'report'
        columns_for_report = [] # To control columns in the report

        if report_type == 'applications':
            data_for_df = applications_data
            filename_prefix = 'applications_report'
            # Define specific columns for applications if you don't want SELECT *
            # For example: columns_for_report = ['grantee_detail_id', 'name', 'status', ...]
        elif report_type == 'payments':
            data_for_df = payments_data # This now includes the names
            filename_prefix = 'payments_report'
            columns_for_report = [ # Define the columns you want in the payment report
                'payment_id', 'grantee_name', 'grantor_name', 'amount', 
                'payment_status', 'payment_date', 'receipt_url', 
                'updated_by_name', 'notes', 'created_at', 'updated_at',
                # Optionally include original IDs if needed:
                # 'grantee_id', 'grantor_id', 'updated_by' 
            ]
        elif report_type == 'sponsors_convenors':
            data_for_df = sponsors_convenors_data
            filename_prefix = 'sponsors_convenors_report'
            # Define specific columns: columns_for_report = ['user_id', 'name', 'email', 'role_id', ...]
        elif report_type == 'grantees':
            data_for_df = grantees_data
            filename_prefix = 'grantees_report'
            # Define specific columns: columns_for_report = ['user_id', 'name', 'email', ...]
        else:
            flash('Invalid report type selected.', 'error')
            return redirect(url_for('admin.admin_generate_reports'))

        if not data_for_df:
            flash(f'No data available for {report_type.replace("_", " ")} report.', 'info')
            return redirect(url_for('admin.admin_generate_reports'))

        # Convert data to a DataFrame
        df = pd.DataFrame(data_for_df)

        # If specific columns are defined, use them. Otherwise, use all columns from df.
        if columns_for_report:
            # Filter to include only existing columns from the defined list, preserving order
            df = df[[col for col in columns_for_report if col in df.columns]]
        elif df.empty: # If df is empty after all, no point proceeding
             flash(f'No data to generate for {report_type.replace("_", " ")} report.', 'info')
             return redirect(url_for('admin.admin_generate_reports'))


        # Generate the report in the selected format
        if report_format == 'csv':
            output = BytesIO()
            df.to_csv(output, index=False, encoding='utf-8')
            output.seek(0)
            return send_file(output, as_attachment=True, download_name=f"{filename_prefix}.csv", mimetype='text/csv')

        elif report_format == 'excel':
            output = BytesIO()
            # Use pd.ExcelWriter for more control if needed in the future (e.g., multiple sheets)
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Report')
            output.seek(0)
            return send_file(output, as_attachment=True, download_name=f"{filename_prefix}.xlsx", mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        elif report_format == 'pdf':
            # Placeholder for PDF generation - use a library like WeasyPrint or ReportLab
            try:
                from weasyprint import HTML # Make sure WeasyPrint is installed: pip install WeasyPrint
                # Create a basic HTML string from the DataFrame
                html_content = df.to_html(index=False, border=1, classes="table table-striped")
                # Add some minimal styling for better PDF output
                styled_html = f"""
                <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            body {{ font-family: Arial, sans-serif; font-size: 10pt; }}
                            table {{ border-collapse: collapse; width: 100%; }}
                            th, td {{ border: 1px solid #ccc; padding: 5px; text-align: left; }}
                            th {{ background-color: #f2f2f2; }}
                            .table-striped tbody tr:nth-of-type(odd) {{ background-color: rgba(0,0,0,.05); }}
                        </style>
                    </head>
                    <body>
                        <h2>{filename_prefix.replace("_", " ").title()}</h2>
                        {html_content}
                    </body>
                </html>
                """
                output = BytesIO()
                HTML(string=styled_html).write_pdf(output)
                output.seek(0)
                return send_file(output, as_attachment=True, download_name=f"{filename_prefix}.pdf", mimetype='application/pdf')
            except ImportError:
                flash("PDF generation library (WeasyPrint) is not installed. Please install it.", "error")
                return redirect(url_for('admin.admin_generate_reports'))
            except Exception as e:
                flash(f"An error occurred during PDF generation: {str(e)}", "error")
                current_app.logger.error(f"PDF Generation Error: {e}", exc_info=True)
                return redirect(url_for('admin.admin_generate_reports'))
        else:
            flash("Invalid report format selected.", "error")
            return redirect(url_for('admin.admin_generate_reports'))


    # This data is passed to the template for the initial page load (e.g., for previews if any)
    return render_template(
        'admin/generate_reports.html',
        applications=applications_data,
        payments=payments_data, # This now includes names
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
    print(current_user.user_id )
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
            valid_statuses = ['draft', 'submitted', 'interviewing', 'accepted', 'rejected','on hold', 'provisional admission letter', 'admitted']
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