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



@app.route('contract_log', methods=['POST'])
def contract_log():
        
    with get_db() as (cursor, connection):

        today_date = datetime.now().strftime('%d %B %Y')
        applied_date = datetime.now().strftime('%Y-%m-%d')

        user_uuid = session.get('user_uuid')
        table_name = session.get('table_name')
        empid = session.get('empid')

        if not user_uuid or not table_name or not empid:
            return "Session data is missing", 400
        
        if request.method == 'POST':

            company_name = table_name.replace("main", "")
            companyxx = company_name.replace("_"," ").title()
            employee_number = request.form.get('employee_number')
            first_name = request.form.get('first_name_app')
            surname = request.form.get('surname')
            department = request.form.get('department')
            date_applied = request.form.get('dateapplied')
            approver_name = request.form.get('approvername')
            approver_id = int(np.float64(request.form.get('approverid')))
            approver_email = request.form.get('approveremailapp')
            approver_whatsapp = int(np.float64(request.form.get('approverwhatsappapp')))
            leave_days_balance = float(np.float64(request.form.get('leavedays-bf')))
            unicode = request.form.get('unicode')
            leave_type = request.form.get('leaveType')
            leave_specify = request.form.get('leaveSpecify')  # Optional field
            start_date = request.form.get('startDate')
            end_date = request.form.get('endDate')

            try:

                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                end_date = datetime.strptime(end_date, '%Y-%m-%d')

                # Initialize count for non-Sundays
                leave_days = 0
                current_date = start_date

                # Iterate through the range of dates
                while current_date <= end_date:
                    #if current_date.weekday() != 6:  # Exclude Sundays (6 is Sunday in Python's `weekday()` function)
                    leave_days += 1
                    current_date += timedelta(days=1)

                # Debug: Print the result
                print(f"Number of leave days (excluding Sundays): {leave_days}")

            except ValueError:
                    # Handle invalid date format
                    return jsonify({'status': 'error', 'message': 'Invalid date format. Use YYYY-MM-DD.'}), 400

            # Debug: Print received data (remove this in production)
            print(f"Employee Number: {employee_number}")
            print(f"First Name: {first_name}")
            print(f"Surname: {surname}")
            print(f"Date Applied: {date_applied}")
            print(f"Approver Name: {approver_name}")
            print(f"Approver ID: {approver_id}")
            print(f"Leave Days Balance: {leave_days_balance}")
            print(f"Unicode: {unicode}")
            print(f"Leave Type: {leave_type}")
            print(f"Leave Specify: {leave_specify}")
            print(f"Start Date: {start_date}")
            print(f"End Date: {end_date}")
            print(f"Department: {department}")

            if leave_type == "Annual":

                leavedaysbalancebf = float(leave_days_balance) - float(leave_days)

            else:

                leavedaysbalancebf = float(leave_days_balance)

            table_name_apps_pending_approval = f"{company_name}appspendingapproval"
            table_name_apps_approved = f"{company_name}appsapproved"

            query = f"SELECT id FROM {table_name_apps_pending_approval} WHERE id = {empid};"
            cursor.execute(query)
            rows = cursor.fetchall()

            df_employeesappspendingcheck = pd.DataFrame(rows, columns=["id"])    

            if len(df_employeesappspendingcheck) == 0:

                query = f"""SELECT appid, id, leavestartdate, leaveenddate FROM {table_name_apps_approved} WHERE id = %s AND leavestartdate <= %s AND leaveenddate >= %s"""

                cursor.execute(query, (employee_number, end_date, start_date))
                results = cursor.fetchall()

                # Process results
                if results:
                    print("Overlapping records found:")

                    try:

                        overlap_messages = []

                        for row in results:

                            formatted_date_start = row[2].strftime("%d %B %Y")
                            formatted_date_end = row[3].strftime("%d %B %Y")

                            overlap_messages.append(f"appID: {row[0]}, Starting Date: {formatted_date_start}, Ending Date: {formatted_date_end}")

                        # Combine into one single string (newline-separated)
                        overlap_info = "\n".join(overlap_messages)

                        response = {'status': 'error', 'message': f'One of your previously approved leave applications include days within the period that you are currently applying for leave; {overlap_info}.'}
                        return jsonify(response), 400  
                    
                    except Exception as e:

                        response = {'status': 'error', 'message': {e}}
                        return jsonify(response), 400                        

                else:
                    print("No overlapping records found.")

                    status = "Pending"

                    insert_query = f"""
                    INSERT INTO {table_name_apps_pending_approval} (id, firstname, surname, department, leavetype, reasonifother, leaveapprovername, leaveapproverid, leaveapproveremail, leaveapproverwhatsapp, currentleavedaysbalance, dateapplied, leavestartdate, leaveenddate, leavedaysappliedfor, leavedaysbalancebf, approvalstatus)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
                    """
                    cursor.execute(insert_query, (employee_number, first_name, surname, department, leave_type, leave_specify, approver_name, approver_id, approver_email, approver_whatsapp, leave_days_balance, date_applied, start_date, end_date, leave_days, float(leavedaysbalancebf), status))
                    connection.commit()


                    query = f"SELECT id, firstname, surname, whatsapp, email, address, role, department, leaveapprovername, leaveapproverid, leaveapproveremail, leaveapproverwhatsapp, currentleavedaysbalance, monthlyaccumulation FROM {table_name};"
                    cursor.execute(query)
                    rows = cursor.fetchall()

                    df_employees = pd.DataFrame(rows, columns=["id","firstname", "surname", "whatsapp","Email", "Address", "Role","Department","Leave Approver Name","Leave Approver ID","Leave Approver Email", "Leave Approver WhatsAapp", "Leave Days Balance","Days Accumulated per Month"])
                    print(df_employees)
                    userdf = df_employees[df_employees['id'] == int(np.int64(employee_number))].reset_index()
                    print("yeaarrrrr")
                    print(userdf)
                    firstname = userdf.iat[0,2]
                    surname = userdf.iat[0,3]
                    whatsapp = userdf.iat[0,4]
                    address = userdf.iat[0,6]
                    email = userdf.iat[0,5]
                    fullnamedisp = firstname + ' ' + surname
                    leaveapprovername = userdf.iat[0,9]
                    leaveapproverid = userdf.iat[0,9]
                    leaveapproveremail = userdf.iat[0, 10]
                    leaveapproverwhatsapp = int(userdf.iat[0,12])
                    role = userdf.iat[0,7]
                    leavedaysbalance = userdf.iat[0,12]
                    print('check')
                    approovvver = leaveapprovername.title()


                    departmentdf = df_employees[df_employees['Department'] == department].reset_index()
                    numberindepartment = len(departmentdf)

                    startdatex = pd.Timestamp(start_date)
                    enddatex = pd.Timestamp(end_date)

                    leave_dates = pd.date_range(startdatex, enddatex)

                    query = f"""
                        SELECT appid, id, leavetype, leaveapprovername, dateapplied, leavestartdate,
                            leaveenddate, leavedaysappliedfor, approvalstatus, statusdate,
                            leavedaysbalancebf, department
                        FROM {table_name_apps_approved}
                        WHERE department = %s;
                    """
                    cursor.execute(query, (department,))
                    rows = cursor.fetchall()

                    df_employeesappsapprovedcheck = pd.DataFrame(rows, columns=["appid","id", "leavetype", "leaveapprovername", "dateapplied", "leavestartdate", "leaveenddate", "leavedaysappliedfor","approvalstatus","statusdate", "leavedaysbalancebf","department"]) 

                    # Create daily impact report
                    df_employeesappsapprovedcheck["leavestartdate"] = pd.to_datetime(df_employeesappsapprovedcheck["leavestartdate"])
                    df_employeesappsapprovedcheck["leaveenddate"] = pd.to_datetime(df_employeesappsapprovedcheck["leaveenddate"])
                    df_employeesappsapprovedcheck.dropna(subset=["leavestartdate", "leaveenddate"], inplace=True)


                    impact_report = []

                    for date in leave_dates:
        
                        date = pd.Timestamp(date)

                        print(type(date))  # Should be pandas._libs.tslibs.timestamps.Timestamp or datetime.datetime
                        print(df_employeesappsapprovedcheck.dtypes)  # Check all datetime columns

                        on_leave = ((df_employeesappsapprovedcheck["leavestartdate"] <= date) & (df_employeesappsapprovedcheck["leaveenddate"] >= date)).sum()
                        remaining = numberindepartment - on_leave - 1  # subtract 1 for the new leave
                        impact_report.append({
                            "date": date.strftime("%Y-%m-%d"),
                            "on leave": on_leave + 1,
                            "employees remaining": remaining
                        })

                    # Convert to DataFrame for display
                    impact_df = pd.DataFrame(impact_report)
                    print("IMPAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACT")
                    print(impact_df)
                    print(numberindepartment)

                    impact_df["date"] = pd.to_datetime(impact_df["date"], dayfirst=True)
                    #impact_df = impact_df[impact_df["date"].dt.weekday != 6].copy()

                    impact_df["group"] = (impact_df[["on leave", "employees remaining"]] != impact_df[["on leave", "employees remaining"]].shift()).any(axis=1).cumsum()

                    statements = []
                    for _, group_df in impact_df.groupby("group"):
                        start = group_df["date"].iloc[0].strftime("%d %B %Y")
                        end = group_df["date"].iloc[-1].strftime("%d %B %Y")
                        on_leave = group_df["on leave"].iloc[0]
                        remaining = group_df["employees remaining"].iloc[0]
                        
                        if start == end:
                            statements.append(f"On {start}, the {department} department will have {remaining} employee(s) remaining at work and {on_leave} employee(s) on leave.")
                        else:
                            statements.append(f"From {start} to {end}, the {department} department will have {remaining} employee(s) remaining at work and {on_leave} employee(s) on leave.")
                    # Combine all statements into a single variable
                    final_summary = "\n".join(statements)
                    # Print output
                    for s in statements:
                        print(s)

                    query = f"SELECT appid, id FROM {table_name_apps_pending_approval} WHERE id = {str(employee_number)} ;"
                    cursor.execute(query, )
                    rows = cursor.fetchall()

                    df_employees = pd.DataFrame(rows, columns=["appid","id"])
                    leaveappid = df_employees.iat[0,0]


                    """send_whatsapp_message(f"263{whatsapp}", f"✅ Great News {first_name} from {companyxx}'s {department} department! \n\n Your `{leave_type} Leave Application` for `{leave_days} days` from `{start_date.strftime('%d %B %Y')}` to `{end_date.strftime('%d %B %Y')}` has been submitted successfully!\n\n"
                        f"Your Leave Application ID is `{leaveappid}`.\n\n"
                        f"A Notification has been sent to `{approovvver}`  on `+263{leaveapproverwhatsapp}` to decide on  your application.\n\n"
                        "To Check the approval status of your leave application, type `Hello` then select `Track Application`.")
                    
                    if leaveapproverwhatsapp:

                        buttons = [
                            {"type": "reply", "reply": {"id": f"Approve5appwa_{leaveappid}", "title": "Approve"}},
                            {"type": "reply", "reply": {"id": f"Disapproveappwa_{leaveappid}", "title": "Disapprove"}},
                        ]
                        send_whatsapp_message(
                            f"263{leaveapproverwhatsapp}", 
                            f"Hey {approovvver}! 😊. New `{leave_type}` Leave Application from `{first_name} {surname}` in {department} department for `{leave_days} days` from `{start_date.strftime('%d %B %Y')}` to `{end_date.strftime('%d %B %Y')}`.\n\n" 
                            f"If you approve this leave application, {final_summary}\n\n"  
                            f"Select an option below to either approve or disapprove the application."         
                            , 
                            buttons
                        )"""

                    results = run1(table_name, empid)
                    return render_template('adminpage.html', **results)

            else:
                response = {'status': 'error', 'message': 'Leave application not submitted successfully.'}
                return jsonify(response), 400  




@app.teardown_appcontext
def close_db(error):
    """Close any remaining connections on app shutdown"""
    pass  # No-op now since you're using context managers everywhere   

if __name__ == "__main__":
    app.run(host="0.0.0.0", port = 55, debug = True)