import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_from_directory, jsonify
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
    # Ensure only Coordinators can access this route (adjust role_id if needed)
    if current_user.role_id != 3: # Assuming Coordinator role_id is 3
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch coordinator details (assuming 'users' table)
    cursor.execute("SELECT user_id, name, email, phone FROM users WHERE user_id = %s", (current_user.user_id,))
    coordinator = cursor.fetchone()

    if not coordinator:
        flash('Coordinator details not found.', 'error')
        # Handle error appropriately, e.g., redirect or render error page
        cursor.close()
        conn.close()
        return redirect(url_for('main.homepage')) # Or some other sensible redirect

    # --- Fetch available years for the dropdown ---
    # Combine years from relevant tables. Adjust table/column names as needed.
    # Using UNION to get distinct years from multiple potential sources.
    # Make sure the 'created_at' column exists and is a DATE, DATETIME, or TIMESTAMP type.
    query_years = """
        (SELECT DISTINCT YEAR(created_at) AS year FROM grantee_details WHERE created_at IS NOT NULL)
        UNION
        (SELECT DISTINCT YEAR(created_at) AS year FROM users WHERE (role_id = 5 OR role_id = 4)  AND created_at IS NOT NULL) /* Assuming role_id 5 is Sponsor */
        UNION
        (SELECT DISTINCT YEAR(created_at) AS year FROM users WHERE role_id = 6 AND created_at IS NOT NULL) /* Assuming role_id 6 is Grantee/Beneficiary */
        ORDER BY year DESC;
    """
    cursor.execute(query_years)
    available_years_result = cursor.fetchall()
    available_years = [row['year'] for row in available_years_result if row['year'] is not None]

    # Get selected year from query parameters, default to current year or most recent if not provided
    selected_year = request.args.get('year', type=int)
    if selected_year is None and available_years:
        selected_year = available_years[0] # Default to the most recent year
    elif selected_year is None: # No data, no years
        selected_year = datetime.now().year # Fallback to current system year

    # --- Fetch stats based on selected_year ---
    year_filter_clause = ""
    params = []

    if selected_year:
        year_filter_clause = " WHERE YEAR(created_at) = %s"
        params.append(selected_year)

    # Fetch total applications (adjust table and columns as needed)
    # Assuming 'grantee_details' stores applications
    cursor.execute(f"SELECT COUNT(*) AS count FROM grantee_details {year_filter_clause}", tuple(params))
    applications_count = cursor.fetchone()['count'] or 0

    # Fetch total sponsors (adjust table, columns, and role_id for sponsors)
    # Assuming 'users' table and role_id = 5 for sponsors
    # If sponsors_convenors means both, adjust the query
    sponsor_filter_clause = f" WHERE role_id = 5 {('AND YEAR(created_at) = %s' if selected_year else '')}"
    sponsor_params = [selected_year] if selected_year else []
    cursor.execute(f"SELECT COUNT(*) AS count FROM users {sponsor_filter_clause}", tuple(sponsor_params))
    sponsors_count = cursor.fetchone()['count'] or 0


    # Fetch total grantees/beneficiaries (adjust table, columns, and role_id for grantees)
    # Assuming 'users' table and role_id = 2 for grantees
    grantee_filter_clause = f" WHERE role_id = 6 {('AND YEAR(created_at) = %s' if selected_year else '')}"
    grantee_params = [selected_year] if selected_year else []
    cursor.execute(f"SELECT COUNT(*) AS count FROM users {grantee_filter_clause}", tuple(grantee_params))
    grantees_count = cursor.fetchone()['count'] or 0

    # --- Data for Charts (Placeholder - you'll make this dynamic too, possibly by year) ---
    # For now, I'll leave the chart data fetching as it might be,
    # but you'd likely want to filter chart data by 'selected_year' as well.
    # Example: applications_by_status, sponsors_by_region

    cursor.close()
    conn.close()

    return render_template(
        'coordinator/dashboard.html', # Ensure path is correct
        coordinator=coordinator,
        applications_count=applications_count,
        sponsors_count=sponsors_count,
        grantees_count=grantees_count,
        available_years=available_years,
        selected_year=selected_year
        # Pass other data needed for charts, etc.
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
        cursor.execute("SELECT user_id, name, email, phone FROM users WHERE user_id = %s", (current_user.user_id,))
        coordinator = cursor.fetchone()
        cursor.close()
        conn.close()

    return redirect(url_for(' coordinator/dashboard.html',coordinator=coordinator))

# Activate/Inactivate Sponsor or Convenor
@coordinator_bp.route('/update_user_status/<string:user_id>/<status>', methods=['GET'])
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

    return redirect(url_for('coordinator.co_manage_sponsors'))

# Map Students to Sponsors
@coordinator_bp.route('/co_map_students_to_sponsors/<string:sponsor_id>', methods=['GET', 'POST'])
@login_required
def co_map_students_to_sponsors(sponsor_id):
    print(f"Current User: {current_user}")
    print(f"Current User Role ID: {current_user.role_id}")
    if current_user.role_id not in [1,2,3, 4]:
        print("I am failing")
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        # Get selected student IDs
        student_ids = request.form.getlist('student_ids')

        # Map students to the sponsor
        for student_id in student_ids:
            cursor.execute("""
                UPDATE grantor_grantees
                SET grantor_id = %s
                WHERE grantee_id = %s
            """, (sponsor_id, student_id))
        conn.commit()

        flash('Students mapped successfully!', 'success')
        return redirect(url_for('coordinator.co_manage_sponsors'))

    # Fetch all students who are not assigned to any sponsor
    cursor.execute("""
        SELECT u.*
        FROM users u
        JOIN grantor_grantees gg ON u.user_id = gg.grantee_id
        WHERE gg.grantor_id = %s
    """, (12,))  # Use convenor's region from the database
    students = cursor.fetchall()

    # Fetch students already mapped to the sponsor (with full details)
    cursor.execute("""
        SELECT u.*
        FROM users u
        JOIN grantor_grantees gg ON u.user_id = gg.grantee_id
        WHERE gg.grantor_id = %s
    """, (sponsor_id,))
    mapped_students = cursor.fetchall()

    # Extract user IDs from mapped_students
    mapped_student_ids = [student['user_id'] for student in mapped_students]

    cursor.execute("SELECT user_id, name, email, phone FROM users WHERE user_id = %s", (current_user.user_id,))
    coordinator = cursor.fetchone()

    cursor.close()
    conn.close()

    return render_template(
        'coordinator/map_students.html',
        coordinator =coordinator ,  # Pass convenor to the template
        students=students,
        mapped_students=mapped_students,  # Pass full details of mapped students
        mapped_student_ids=mapped_student_ids,  # Pass only the IDs for comparison
        sponsor_id=sponsor_id
    )

# Manage Sponsors
@coordinator_bp.route('/co_manage_sponsors', methods=['GET'])
@login_required
def co_manage_sponsors():
    if current_user.role_id != 3:  # Ensure only coordinators can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)


    cursor.execute("SELECT user_id, name, email, phone FROM users WHERE user_id = %s", (current_user.user_id,))
    coordinator = cursor.fetchone()

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
        coordinator=coordinator,
        sponsors_convenors=sponsors_convenors,
        grantees=grantees
    )

# Appoint Sponsor as Convenor
@coordinator_bp.route('/appoint_convenor/<string:sponsor_id>', methods=['POST'])
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
@coordinator_bp.route('/change_region/<string:user_id>', methods=['POST'])
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

    return redirect(url_for('coordinator.dashboard'))

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
    if current_user.role_id != 3:  # Ensure only coordinators can access this route
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, name, email, phone FROM users WHERE user_id = %s", (current_user.user_id,))
    coordinator = cursor.fetchone()

    return render_template('coordinator/monitor_payments.html', coordinator=coordinator)

# Monitor Payments Data (for DataTables) - CORRECTED
@coordinator_bp.route('/monitor_payments_data', methods=['GET'])
@login_required
def monitor_payments_data():
    if current_user.role_id != 3:  # Ensure only coordinators can access this route
        return jsonify({"error": "Unauthorized access"}), 403

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("SELECT user_id, name, email, phone FROM users WHERE user_id = %s", (current_user.user_id,))
    coordinator = cursor.fetchone()

    # Fetch DataTables parameters
    draw = request.args.get('draw', default=1, type=int)
    start = request.args.get('start', default=0, type=int)
    length = request.args.get('length', default=10, type=int)
    search_value = request.args.get('search[value]', default='', type=str).strip()
    order_column_index = request.args.get('order[0][column]', default=0, type=int)
    order_dir = request.args.get('order[0][dir]', default='asc', type=str)

    # Map column index to a safe, sortable database field name.
    columns_map = ['grantee_name', 'grantor_name', 'amount', 'status', 'receipt_url']
    order_by_column = columns_map[order_column_index]

    # Base SQL query
    base_query = """
        SELECT u1.name AS grantee_name, u1.user_id AS grantee_id, u1.phone AS grantee_phone, 
               u2.name AS grantor_name, u2.user_id AS grantor_id, u2.phone AS grantor_phone, 
               p.amount, p.status, p.receipt_url, p.payment_id
        FROM payments p
        JOIN users u1 ON p.grantee_id = u1.user_id
        JOIN users u2 ON p.grantor_id = u2.user_id
    """
    
    query_params = ()
    # --- UPDATED SEARCH LOGIC ---
    if search_value:
        search_clauses = [
            "u1.name LIKE %s",
            "u1.user_id LIKE %s",
            "u1.phone LIKE %s",
            "u2.name LIKE %s",
            "u2.user_id LIKE %s",
            "u2.phone LIKE %s",
            "p.status LIKE %s"
        ]
        base_query += " WHERE " + " OR ".join(search_clauses)
        search_param = f"%{search_value}%"
        query_params = (search_param,) * 7
    # --- END OF UPDATED SEARCH LOGIC ---

    # Get total records count (unfiltered)
    # This query runs without the WHERE clause to get the true total.
    cursor.execute("SELECT COUNT(*) AS total FROM payments")
    total_records = cursor.fetchone()['total']
    
    # Get filtered records count
    # This query includes the WHERE clause (if search is used) to get the filtered count.
    count_query = f"SELECT COUNT(*) AS total FROM ({base_query}) AS subquery"
    cursor.execute(count_query, query_params)
    records_filtered = cursor.fetchone()['total']

    # Add sorting and pagination to the main query
    final_query = base_query + f" ORDER BY {order_by_column} {order_dir} LIMIT %s, %s"
    final_params = query_params + (start, length)

    try:
        cursor.execute(final_query, final_params)
        payments = cursor.fetchall()

        response = {
            "draw": draw,
            "recordsTotal": total_records,
            "recordsFiltered": records_filtered,
            "data": payments
        }
        return jsonify(response)

    except Exception as e:
        print(f"Error executing query: {e}") # Log error to console for debugging
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()

# View Uploaded File
@coordinator_bp.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)

# Generate Reports
from flask import send_file
import pandas as pd
from io import BytesIO

@coordinator_bp.route('/generate_reports', methods=['GET', 'POST'])
@login_required
def generate_reports():
    if current_user.role_id != 3:
        flash('You do not have permission to access this page.', 'error')
        return redirect(url_for('auth.login'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT user_id, name, email, phone FROM users WHERE user_id = %s", (current_user.user_id,))
    coordinator = cursor.fetchone()

    # Fetch all applications
    cursor.execute("SELECT * FROM grantee_details g join application_status a on g.grantee_detail_id = a.grantee_detail_id")
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
        'coordinator/generate_reports.html',
        coordinator=coordinator,
        applications=applications,
        payments=payments,
        sponsors_convenors=sponsors_convenors,
        grantees=grantees
    )