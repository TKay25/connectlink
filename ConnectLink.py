import uuid
import os

# Prevent Matplotlib from building font cache on startup (blocks Gunicorn port binding on Render)
os.environ.setdefault("MPLCONFIGDIR", "/tmp/.matplotlib")

from db_helper import get_db, execute_query
import numpy as np
from mysql.connector import Error
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_file,flash, make_response, after_this_request
from datetime import datetime, timedelta
import pandas as pd
from xhtml2pdf import pisa
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import seaborn as sns
import psycopg2
from psycopg2 import sql
from db_helper import get_db, execute_query
import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.styles import PatternFill, Font
from werkzeug.utils import secure_filename
import io
import base64
import json
import requests
from weasyprint import HTML
import re
#from paynow import Paynow
import time
import random
#import threading
#from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)
app.secret_key = 'your_secret_key'  
app.secret_key = '011235'
app.permanent_session_lifetime = timedelta(minutes=360)
user_sessions = {}

database = 'connectlinkdata'

# WhatsApp API Credentials (Replace with your actual credentials)
#ACCESS_TOKEN = "EAATESj1oB5YBOyIVfVPEAIZAZA7sgPboDN36Wa2Or11uZCBEZCVWaNAZB0exkYYG6gcIdiYbvPCST9tKjS54ib1NqXbNg7UvJYaZCIZAjxgTBQwvyoWE8cZCMgje1wkrUyb335TMwNwYSTA3rNwppRZAeQGt3M7s5x15nZCbZBtEfZBtSIu3p7ZCHOcF0pMTuLgjQreLz2QZDZD"
#PHONE_NUMBER_ID = "558392750697195"
#VERIFY_TOKEN = "521035180620700"
#WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

def initialize_database_tables():
    """Initialize all required database tables on startup"""
    try:
        with get_db() as (cursor, connection):
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkdetails (
                    address VARCHAR (200),
                    contact1 INT,
                    contact2 INT,
                    email VARCHAR (100)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkusers (
                    id SERIAL PRIMARY KEY,
                    datecreated date,
                    name VARCHAR (200),
                    password varchar (100),
                    email VARCHAR (100)
                );
            """)

            # Create connectlinkadmin table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkadmin (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR (200),
                    contact INT
                );
            """)
            
            # Create connectlinkatabase table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkatabase (
                    id SERIAL PRIMARY KEY,
                    clientname VARCHAR (100),
                    clientidnumber varchar (100),
                    clientaddress VARCHAR (200),
                    clientwanumber INT,
                    clientemail VARCHAR (100),
                    clientnextofkinname VARCHAR (100),
                    clientnextofkinaddress VARCHAR (100),
                    clientnextofkinphone INT,
                    nextofkinrelationship VARCHAR (100),
                    projectname VARCHAR (100),
                    projectlocation VARCHAR (100),
                    projectdescription VARCHAR (500),
                    projectadministratorname VARCHAR (100),
                    projectstartdate date,
                    projectduration INT,
                    contractagreementdate date,
                    totalcontractamount NUMERIC (12, 2),
                    paymentmethod VARCHAR (100),
                    monthstopay INT,
                    depositrequired NUMERIC (12, 2),
                );
            """)
            
            cursor.execute("""
                ALTER TABLE connectlinkatabase
                ADD COLUMN IF NOT EXISTS datecaptured date;
            """)

            cursor.execute("""
                ALTER TABLE connectlinkatabase
                ADD COLUMN IF NOT EXISTS capturer VARCHAR (100);
            """)

            cursor.execute("""
                ALTER TABLE connectlinkatabase
                ADD COLUMN IF NOT EXISTS capturerid INT;
            """)

            # Create cagwatickcustomerdetails table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS clientpayments (
                    id INT,
                    paymentmethod VARCHAR (100),
                    totalcontractamount NUMERIC (12, 2),
                    depositorbullet NUMERIC (12, 2),
                    datedepositorbullet date,
                    monthstopay INT,
                    monthlyinstallment NUMERIC (12, 2),
                    installment1amount NUMERIC (12, 2),
                    installment1duedate date,
                    installment1date date,
                    installment2amount NUMERIC (12, 2),
                    installment2duedate date,
                    installment2date date,
                    installment3amount NUMERIC (12, 2),
                    installment3duedate date,
                    installment3date date,
                    installment4amount NUMERIC (12, 2),
                    installment4duedate date,
                    installment4date date,
                    installment5amount NUMERIC (12, 2),
                    installment5duedate date,
                    installment5date date,
                    installment6amount NUMERIC (12, 2),
                    installment6duedate date,
                    installment6date date,
                );
            """)
            
            connection.commit()
            print("✅ Database tables initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing database tables: {e}")

@app.route('/dashboard')
def Dashboard():

    with get_db() as (cursor, connection):

        user_uuid = session.get('user_uuid')
        if user_uuid:

            try:

                today_date = datetime.now().strftime('%d %B %Y')
                applied_date = datetime.now().strftime('%Y-%m-%d')
                userid = session.get('userid')

                companyname = table_name.replace("main", "")
                company_name = companyname.replace('_', ' ')

                results = run1(table_name, userid)  

                print("Back from adventures")
                if results["role"] == 'Administrator':
                    role_narr = "LMS ADMINISTRATOR"

                    return render_template('adminpage.html', **results, id= userid, company_name=company_name, role_narr = role_narr)

                if results["role"] == 'Ordinary User':

                    query = f"SELECT id FROM {table_name} WHERE leaveapproverid = {userid};"
                    cursor.execute(query)
                    rows = cursor.fetchall()

                    df_employeesempapp = pd.DataFrame(rows, columns=["id"])

                    if len(df_employeesempapp) > 0:

                        role_narr = "LMS LEAVE APPLICATIONS APPROVER"
                        hide_element = True
                        return render_template('adminpage.html', **results, id= userid, company_name=company_name, hide_element=hide_element, role_narr = role_narr)

                    elif len(df_employeesempapp) == 0:
                        
                        role_narr = "LMS USER"
                        hide_element = True
                        hide_element2 = True
                        return render_template('adminpage.html', **results, id= userid, company_name=company_name, hide_element=hide_element, hide_element2 = hide_element2, role_narr = role_narr)
                    
            except Error as e:

                print(e)

                return redirect(url_for('landingpage'))


        
        else:
                return redirect(url_for('landingpage'))

@app.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
            
        try:
                
            with get_db() as (cursor, connection):

                today_date = datetime.now().strftime('%d %B %Y')
                applied_date = datetime.now().strftime('%Y-%m-%d')

                # Retrieve form data
                email = request.form.get('emaillogin').strip()
                password = request.form.get('passwordlogin').strip()

                # Check for missing input
                if not email or not password:
                    return jsonify({'success': False, 'message': 'Email and password are required.'}), 400

                for (table_name,) in tables_with_email:
                    search_query = f"SELECT * FROM {table_name} WHERE email = %s;"
                    cursor.execute(search_query, (email,))
                    rows = cursor.fetchall()
                    if rows:
                        results.append((table_name, rows))

                if results:
                    table_name, rows = results[0]
                    print(f"Table Found: {table_name}")
                    print(rows)
                    sliced_rows = [row[:15] for row in rows]
                    print(sliced_rows)

                    table_df = pd.DataFrame(sliced_rows, columns=['id', 'firstname', 'surname', 'whatsapp', 'address', 'email', 'password', 'department', 'role', 'leaveapprovername', 'leaveapproverid', 'leaveapproveremail','leaveapproverwhatsapp','currentleavedaysbalance', 'monthlyaccumulation'])

                    if table_df.iat[0, 6] == password:
                        user_uuid = uuid.uuid4()
                        session['user_uuid'] = str(user_uuid)
                        session.permanent = True
                        user_sessions[email] = {'uuid': str(user_uuid), 'email': email}

                        userid = table_df.iat[0, 0]
                        session['table_name'] = table_name
                        session['userid'] = int(np.int64(userid))  # Ensure Python int

                        # Redirect to dashboard
                        return redirect(url_for('Dashboard'))

                    else:
                        print('Incorrect password')
                        return jsonify({'success': False, 'message': 'Incorrect password.'}), 401

                else:
                    print(f"No rows found with email '{email}' in any table.")
                    return jsonify({'success': False, 'message': 'Email not found.'}), 404

        except Exception as e:
            print("Error while connecting to the database:", e)
            return jsonify({'success': False, 'message': str(e)}), 500

        finally:
            print("Done")

    return jsonify({'success': False, 'message': 'Invalid request method.'}), 405

def run1(userid):

    with get_db() as (cursor, connection):

        print(userid)
        today_date = datetime.now().strftime('%d %B %Y')
        applied_date = datetime.now().strftime('%Y-%m-%d')

        ######### payroll
        querypayroll = f"SELECT id, firstname, surname, leaveapprovername, department, designation, datejoined, bank FROM {table_name};"
        cursor.execute(querypayroll)
        rowspayroll = cursor.fetchall()





        df_employees_payroll = pd.DataFrame(rowspayroll, columns=["id","Firstname", "Surname","Manager_Supervisor", "Department", "Designation","Date Joined","Bank"])
        df_employees_payroll['Action'] = df_employees_payroll.apply(
            lambda row: f'''<div style="display: flex; gap: 10px;font-size: 12px;"><button class="btn btn-primary3 edit-emp-details-comp-btn-payroll" data-id="{row['id']}" data-firstname="{row['Firstname']}" data-surname="{row['Surname']}" data-manager="{row['Manager_Supervisor']}" data-department="{row['Department']}" data-designation="{row['Designation']}"  data-datejoined="{row['Date Joined']}"  data-bank="{row['Bank']}">Edit Information</button></div>''', axis=1
        )

        df_employees_payroll = df_employees_payroll[["id", "Firstname", "Surname","Manager_Supervisor", "Department", "Designation","Date Joined","Bank", "Action"]]

        table_employees_payroll_html = df_employees_payroll.to_html(classes="table table-bordered table-theme", table_id="employeespayrollTable", index=False,  escape=False,)















        ############################

        query = f"SELECT id, firstname, surname, whatsapp, email, address, role, leaveapprovername, leaveapproverid, leaveapproveremail, leaveapproverwhatsapp, currentleavedaysbalance, monthlyaccumulation, department FROM {table_name};"
        cursor.execute(query)
        rows = cursor.fetchall()

        df_employees = pd.DataFrame(rows, columns=["id","firstname", "surname", "whatsapp","Email", "Address", "Role","Leave Approver Name","Leave Approver ID","Leave Approver Email", "Leave Approver WhatsAapp", "Leave Days Balance","Days Accumulated per Month","Department"])
        
        
        
        print(df_employees)
        employee_personal_details = df_employees[["id","firstname", "surname", "whatsapp","Email","Address"]]

        employee_personal_details['Action'] = employee_personal_details.apply(
            lambda row: f'''<div style="display: flex; gap: 10px;font-size: 12px;"><button class="btn btn-primary3 edit-emp-details-comp-btn" data-id="{row['id']}" data-firstname="{row['firstname']}" data-surname="{row['surname']}" data-whatsapp="{row['whatsapp']}" data-email="{row['Email']}" data-address="{row['Address']}">Edit Information</button></div>''', axis=1
        )

        employee_personal_details.columns = ["ID","FIRST NAME","SURNAME","WHATSAPP","EMAIL","ADDRESS","ACTION"]
        employee_personal_details_html = employee_personal_details.to_html(classes="table table-bordered table-theme", table_id="employeespersonalTable", index=False,  escape=False,)

        total_days_available = df_employees["Leave Days Balance"].sum()

        total_employees = len(df_employees)
        userdf = df_employees[df_employees['id'] == empid].reset_index()
        print("yeaarrrrr")
        print(userdf)
        firstname = userdf.iat[0,2]
        surname = userdf.iat[0,3]
        whatsapp = userdf.iat[0,4]
        address = userdf.iat[0,6]
        email = userdf.iat[0,5]
        fullnamedisp = firstname + ' ' + surname
        leaveapprovername = userdf.iat[0,8]
        leaveapproverid = userdf.iat[0,9]
        leaveapproveremail = userdf.iat[0, 10]

        if userdf.iat[0,11]:
            if not pd.isna(userdf.iat[0,11]):
                leaveapproverwhatsapp = int(userdf.iat[0,11])
            else:
                leaveapproverwhatsapp = ""   # or None, depending on what you need

        else:
            leaveapproverwhatsapp = ""


        role = userdf.iat[0,7]
        leavedaysbalance = userdf.iat[0,12]
        department = userdf.iat[0,14]

        print('check')

        df_employees['Employee Name'] = df_employees['firstname'] + ' ' + df_employees['surname']

        df_employees['Action'] = df_employees['id'].apply(
            lambda x: f'''<div style="display: flex; gap: 10px;font-size: 12px;"> <button class="btn btn-primary3 edit-priv-btn" data-bs-toggle="modal" data-bs-target="#editModalpriv" data-name="{x}"  data-ID="{x}">Edit Role</button> <button class="btn btn-primary3 edit-department-btn" data-bs-toggle="modal" data-bs-target="#editModaldepartment" data-name="{x}"  data-ID="{x}">Change Department</button>  <button class="btn btn-primary3 change-approver-btn" data-bs-toggle="modal" data-bs-target="#editModalapprover" data-name="{x}" data-ID="{x}">Change Approver</button>  <button class="btn btn-primary3 edit-balance-btn" data-bs-toggle="modal" data-bs-target="#editModalbalance" data-name="{x}" data-ID="{x}">Edit Balance</button> </div>'''
        )

        selected_columns = df_employees[['id','Employee Name', "Role", "Department", "Leave Approver Name", "Leave Days Balance", "Action"]]
        selected_columns.columns = ['ID','EMPLOYEE NAME','ROLE','DEPARTMENT','APPROVER','DAYS BALANCE','ACTION']

        table_employees_html = selected_columns.to_html(classes="table table-bordered table-theme", table_id="employeesTable", index=False,  escape=False,)

        selected_columns['Combined'] = selected_columns.apply(
            lambda row: f"{row['ID']}--{row['EMPLOYEE NAME']}", axis=1
        )

        employees_list = selected_columns['Combined'].tolist()

        selected_columns_accumulators = df_employees[['id','Employee Name', "Days Accumulated per Month"]]
        selected_columns_accumulators.columns = ['ID','EMPLOYEE NAME','DAYS ACCUMULATED PER MONTH']
        selected_columns_accumulators.loc[:, 'LEAVE DAYS ACCUMULATED PER MONTH'] = selected_columns_accumulators.apply(
            lambda row: f'<input type="number" step="0.5" class="editable-field" value="{row["DAYS ACCUMULATED PER MONTH"]:.1f}" data-id="{row["ID"]}" style="width: 100%;"/>'
            if row["DAYS ACCUMULATED PER MONTH"] is not None
            else f'<input type="number" step="0.5" class="editable-field" value="0.0" data-id="{row["ID"]}" style="width: 100%;"/>',
            axis=1
        )


        seacc = selected_columns_accumulators[['ID','EMPLOYEE NAME','LEAVE DAYS ACCUMULATED PER MONTH']]

        table_employees_accumulators_html = seacc.to_html(classes="table table-bordered table-theme", table_id="employeesaccumulatorsTable", index=False,  escape=False,)

        rememployees = selected_columns_accumulators[['ID','EMPLOYEE NAME']]
        rememployees.loc[:, 'SELECTION'] = rememployees.apply(
            lambda row: f'<input type="checkbox" class="custom-checkbox employee-checkbox" name="employee_ids" value="{row["ID"]}" data-employee-name="{row["EMPLOYEE NAME"]}">',
            axis=1
        )

        table_rememployees_html = rememployees.to_html(classes="table table-bordered table-theme", table_id="removeemployeesTable", index=False,  escape=False,)

        rememployees1 = selected_columns_accumulators[['ID','EMPLOYEE NAME']]
        rememployees1.loc[:, 'SELECTION'] = rememployees1.apply(
            lambda row: f'<input type="checkbox" class="custom-checkbox employee-checkbox-bulk-approver" name="employee_ids" value="{row["ID"]}" data-employee-name="{row["EMPLOYEE NAME"]}">',
            axis=1
        )
        table_rememployees_bulk1_html = rememployees1.to_html(classes="table table-bordered table-theme", table_id="employeesbulk1Table", index=False,  escape=False,)

        rememployees2 = selected_columns_accumulators[['ID','EMPLOYEE NAME']]
        rememployees2.loc[:, 'SELECTION'] = rememployees2.apply(
            lambda row: f'<input type="checkbox" class="custom-checkbox employee-checkbox-bulk-balances" name="employee_ids" value="{row["ID"]}" data-employee-name="{row["EMPLOYEE NAME"]}">',
            axis=1
        )
        table_rememployees_bulk_balances_html = rememployees2.to_html(classes="table table-bordered table-theme", table_id="employeesbulkbalancesTable", index=False,  escape=False,)

        rememployees3 = selected_columns_accumulators[['ID','EMPLOYEE NAME']]
        rememployees3.loc[:, 'SELECTION'] = rememployees3.apply(
            lambda row: f'<input type="checkbox" class="custom-checkbox employee-checkbox-bulk-accumulators" name="employee_ids" value="{row["ID"]}" data-employee-name="{row["EMPLOYEE NAME"]}">',
            axis=1
        )
        table_rememployees_bulk_accumulators_html = rememployees3.to_html(classes="table table-bordered table-theme", table_id="bulkemployeesbulkaccumulatorsTable", index=False,  escape=False,)

        company_name = table_name.replace("main", "")


















@app.route('/')
def userlogin():
    return render_template('login.html') 



@app.route('contract_log', methods=['POST'])
def contract_log():
        
    with get_db() as (cursor, connection):

        today_date = datetime.now().strftime('%d %B %Y')
        applied_date = datetime.now().strftime('%Y-%m-%d')

        user_uuid = session.get('user_uuid')
        userid = session.get('userid')

        if not user_uuid or not userid:
            return "Session data is missing", 400
        
        if request.method == 'POST':

            try:

                client_name = request.form.get('client_name')
                client_national_id = request.form.get('client_national_id')
                client_address = request.form.get('client_address')
                client_whatsapp_number = request.form.get('client_whatsapp_number')
                client_email = request.form.get('client_email')

                next_of_kin_name = request.form.get('next_of_kin_name')
                next_of_kin_address = request.form.get('next_of_kin_address')
                next_of_kin_contact_number = request.form.get('next_of_kin_contact_number')
                relationship = request.form.get('relationship')

                administrator = request.form.get('administrator')

                project_name = request.form.get('project_name')
                project_location = request.form.get('project_location')
                project_start_date = request.form.get('project_start_date')
                months_to_completion = request.form.get('months_to_completion')

                agreement_date = request.form.get('agreement_date')
                total_contract_price = request.form.get('total_contract_price')
                payment_method = request.form.get('payment_method')

                bullet_payment_date = request.form.get('bullet_payment_date')

                months_to_pay = request.form.get('months_to_pay')
                deposit_required = request.form.get('deposit_required')
                deposit_paid = request.form.get('deposit_paid')
                deposit_payment_date = request.form.get('deposit_payment_date')
                first_installment_due_date = request.form.get('first_installment_due_date')

                # Debug: Print received data (remove this in production)
                print(f"Client Name: {client_name}")
                print(f"Client National ID: {client_national_id}")
                print(f"Client Address: {client_address}")
                print(f"Client Whatsapp Number: {client_whatsapp_number}")
                print(f"Client Email: {client_email}")

                print(f"Next of Kin Name: {next_of_kin_name}")
                print(f"Next of Kin Address: {next_of_kin_address}")
                print(f"Next of Kin Contact Number: {next_of_kin_contact_number}")
                print(f"Next of Kin Relationship: {relationship}")

                print(f"Administrator: {administrator}")

                print(f"Project Name: {project_name}")
                print(f"Project Location: {project_location}")
                print(f"Project Start Date: {project_start_date}")
                print(f"Project Duration (Months): {months_to_completion}")

                print(f"Agreement Date: {agreement_date}")
                print(f"Total Contract Price: {total_contract_price}")
                print(f"Payment Method: {payment_method}")

                print(f"Bullet Payment Date: {bullet_payment_date}")

                print(f"Months to Pay: {months_to_pay}")
                print(f"Deposit Required: {deposit_required}")
                print(f"Deposit Paid: {deposit_paid}")
                print(f"Deposit Payment Date: {deposit_payment_date}")
                print(f"First Installment Due Date: {first_installment_due_date}")


                if leave_type == "Annual":

                    leavedaysbalancebf = float(leave_days_balance) - float(leave_days)

                else:

                    leavedaysbalancebf = float(leave_days_balance)


                    insert_query = f"""
                    INSERT INTO {table_name_apps_pending_approval} (id, firstname, surname, department, leavetype, reasonifother, leaveapprovername, leaveapproverid, leaveapproveremail, leaveapproverwhatsapp, currentleavedaysbalance, dateapplied, leavestartdate, leaveenddate, leavedaysappliedfor, leavedaysbalancebf, approvalstatus)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """
                    cursor.execute(insert_query, (employee_number, first_name, surname, department, leave_type, leave_specify, approver_name, approver_id, approver_email, approver_whatsapp, leave_days_balance, date_applied, start_date, end_date, leave_days, float(leavedaysbalancebf), status))
                    connection.commit()

                    results = run1(userid)
                    return render_template('adminpage.html', **results)

            except Exception as e:
                response = {'status': 'error', 'message': 'Leave application not submitted successfully.'}
                return jsonify(response), 400  




@app.teardown_appcontext
def close_db(error):
    """Close any remaining connections on app shutdown"""
    pass  # No-op now since you're using context managers everywhere   

if __name__ == "__main__":
    app.run(host="0.0.0.0", port = 55, debug = True)