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

            def get_table_columns(table_name):
                try:
                    with get_db() as (cursor, connection):
                        cursor.execute("""
                            SELECT column_name
                            FROM information_schema.columns
                            WHERE table_name = %s
                            ORDER BY ordinal_position;
                        """, (table_name,))

                        columns = [row[0] for row in cursor.fetchall()]
                        return columns

                except Exception as e:
                    print(f"Error fetching columns: {e}")
                    return []
            columns = get_table_columns("connectlinkdatabase")
            print(columns)



            cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)

            tables = cursor.fetchall()

            print("Tables in database:")
            for table in tables:
                print(table[0])

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkdetails (
                    address VARCHAR (200),
                    contact1 INT,
                    contact2 INT,
                    email VARCHAR (100)
                );
            """)

            comp_details_alters = [
                "ALTER TABLE connectlinkdetails ADD COLUMN IF NOT EXISTS companyname VARCHAR(200);",
                "ALTER TABLE connectlinkdetails ADD COLUMN IF NOT EXISTS tinnumber VARCHAR(100);"
            ]

            for sql_stmt in comp_details_alters:
                cursor.execute(sql_stmt) 


            '''cursor.execute("""
                INSERT INTO connectlinkdetails (address, contact1, contact2, email, companyname, tinnumber)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                "38A Coronation Avenue Greendale Harare",
                773368558 ,
                718047602,
                "info@connectlinkproperties.co.zw",
                "ConnectLink Properties",
                ""
            ))'''          

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkusers (
                    id SERIAL PRIMARY KEY,
                    datecreated date,
                    name VARCHAR (200),
                    password varchar (100),
                    email VARCHAR (100)
                );
            """)
            current_date = datetime.now().strftime('%Y-%m-%d')

            '''cursor.execute("""
                INSERT INTO connectlinkusers (datecreated, name, password, email)
                VALUES (%s, %s, %s, %s);
            """, (current_date, "ConnectLinkAdmin01", "ConnectLinkAdmin01", "Admin01@connectlinkproperties.co.zw"))

            '''
            # Create connectlinkadmin table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkadmin (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR (200),
                    contact INT
                );
            """)

            '''cursor.execute("""
                ALTER TABLE connectlinkdatabase DROP COLUMN depositrequired;
            """)'''
            
            # Create connectlinkdatabase table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkdatabase (
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
                    datecaptured date,
                    capturer VARCHAR (100),
                    capturerid INT
                );
            """)

            payment_alters = [
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS depositorbullet NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS datedepositorbullet date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS monthlyinstallment NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment1amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment1duedate date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment1date date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment2amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment2duedate date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment2date date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment3amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment3duedate date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment3date date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment4amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment4duedate date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment4date date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment5amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment5duedate date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment5date date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment6amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment6duedate date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment6date date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS projectcompletionstatus varchar(100);"
            ]

            for sql_stmt in payment_alters:
                cursor.execute(sql_stmt)
            
            connection.commit()
            print("✅ Database tables initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing database tables: {e}")

initialize_database_tables()

@app.route('/dashboard')
def Dashboard():

    with get_db() as (cursor, connection):

        user_uuid = session.get('user_uuid')
        user_name = session.get('user_name')
        userid = session.get('userid')

        if user_uuid:

            try:

                today_date = datetime.now().strftime('%d %B %Y')
                applied_date = datetime.now().strftime('%Y-%m-%d')

                results = run1(userid)  

                print("Back from adventures")

                return render_template('adminpage.html', **results, userid = userid, user_name=user_name)
                    
            except Error as e:

                print(e)

                return redirect(url_for('userlogin'))

        else:
                return redirect(url_for('userlogin'))

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

                search_query = "SELECT * FROM connectlinkusers WHERE email = %s;"
                cursor.execute(search_query, (email,))
                rows = cursor.fetchall()

                if rows: 
                    user_row = rows[0]

                    table_df = pd.DataFrame([user_row], columns=[
                        'id', 'datecreated', 'name', 'password', 'email'
                    ])

                    if table_df.iat[0, 3] == password:
                        user_uuid = uuid.uuid4()
                        session['user_uuid'] = str(user_uuid)
                        session.permanent = True
                        user_sessions[email] = {'uuid': str(user_uuid), 'email': email}

                        userid = table_df.iat[0, 0]
                        user_name = table_df.iat[0,2]
                        session['userid'] = int(np.int64(userid))  # Ensure Python int
                        session['user_name'] = user_name

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

@app.route('/download_contract/<project_id>')
def download_contract(project_id):

    with get_db() as (cursor, connection):
        try:
            # Fetch project data
            cursor.execute("SELECT * FROM connectlinkdatabase WHERE id = %s", (project_id,))
            row = cursor.fetchone()
            if not row:
                return "Project not found", 404

            agreement_date = row[16] 
            formatted_agreement_date = agreement_date.strftime("%d %B %Y")

            detailscompquery = f"SELECT * FROM connectlinkdetails;"
            cursor.execute(detailscompquery)
            detailscompdata = cursor.fetchall()
            print(detailscompdata)

            detailscompdata = pd.DataFrame(detailscompdata, columns= ['address', 'contact1', 'contact2', 'email', 'companyname', 'tinnumber'])
            companyname = detailscompdata.iat[0,4] if not detailscompdata.empty else "ConnectLink Properties"
            address = detailscompdata.iat[0,0] if not detailscompdata.empty else ""
            contact1 = detailscompdata.iat[0,1] if not detailscompdata.empty else ""
            contact2 = detailscompdata.iat[0,2] if not detailscompdata.empty else ""
            compemail = detailscompdata.iat[0,3] if not detailscompdata.empty else ""
            tinnumber = detailscompdata.iat[0,5] if not detailscompdata.empty else ""

            nameclient = row[0]
            locationclientprojectnum = row[11]

            # Map row to dictionary
            project = {
                'id': row[0],
                'client_name': row[1],
                'client_idnumber': row[2],
                'client_address': row[3],
                'client_whatsapp': row[4],
                'client_email': row[5],
                'next_of_kin_name': row[6],
                'next_of_kin_address': row[7],
                'next_of_kin_phone': row[8],
                'relationship': row[9],
                'project_name': row[10],
                'project_location': row[11],
                'project_description': row[12],
                'project_administrator': row[13],
                'project_start_date': row[14],
                'project_duration': row[15],
                'agreement_date': formatted_agreement_date,
                'total_contract_price': row[17],
                'payment_method': row[18],
                'months_to_pay': row[19],
                'date_captured': row[20],
                'capturer': row[21],
                'capturerid': row[22],
                'depositorbullet': row[23] if len(row) > 23 else None,
                'datedepositorbullet': row[24] if len(row) > 24 else None,
                'monthlyinstallment': row[25] if len(row) > 25 else None,
                'installment1amount': row[26] if len(row) > 26 else None,
                'installment1duedate': row[27] if len(row) > 27 else None,
                'installment1date': row[28] if len(row) > 28 else None,
                'installment2amount': row[29] if len(row) > 29 else None,
                'installment2duedate': row[30] if len(row) > 30 else None,
                'installment2date': row[31] if len(row) > 31 else None,
                'installment3amount': row[32] if len(row) > 32 else None,
                'installment3duedate': row[33] if len(row) > 33 else None,
                'installment3date': row[34] if len(row) > 34 else None,
                'installment4amount': row[35] if len(row) > 35 else None,
                'installment4duedate': row[36] if len(row) > 36 else None,
                'installment4date': row[37] if len(row) > 37 else None,
                'installment5amount': row[38] if len(row) > 38 else None,
                'installment5duedate': row[39] if len(row) > 39 else None,
                'installment5date': row[40] if len(row) > 40 else None,
                'installment6amount': row[41] if len(row) > 41 else None,
                'installment6duedate': row[42] if len(row) > 42 else None,
                'installment6date': row[43] if len(row) > 43 else None,
                'companyname': companyname,
                'companyaddress': address,
                'companycontact1': contact1,
                'companycontact2': contact2,
                'companyemail': compemail,
            }

            # Get logo as base64 for embedding in PDF
            def get_logo_base64():
                logo_path = os.path.join(app.static_folder, 'images', 'web-logo.png')
                with open(logo_path, "rb") as img_file:
                    return "data:image/png;base64," + base64.b64encode(img_file.read()).decode('utf-8')

            project['company_logo'] = get_logo_base64()
            project['generated_on'] = datetime.now().strftime('%d %B %Y')

            # Render HTML template with project data
            html = render_template('contracttemplate.html', project=project)

            # Generate PDF
            pdf = HTML(string=html).write_pdf()

            # Return PDF as response
            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename={nameclient}_{locationclientprojectnum}_contract_{project_id}_{companyname}.pdf'
            return response

        except Exception as e:
            return str(e), 500


@app.route('/addadmin', methods=['POST'])
def add_admin():
    data = request.get_json()

    adminName = data.get("adminName")
    adminPhone = data.get("adminPhone")

    with get_db() as (cursor, connection):

        try:
            cursor.execute("""
                INSERT INTO connectlinkadmin (name, contact)
                VALUES (%s, %s)
            """, (adminName, adminPhone))
            connection.commit()
            return jsonify({"status": "success"})

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})

@app.route('/removeadmin', methods=['POST'])
def remove_admin():
    data = request.get_json()
    admin_id = data.get('id')

    if not admin_id:
        return jsonify({"status": "error", "message": "No ID provided"})

    with get_db() as (cursor, connection):

        try:
            cursor.execute("DELETE FROM connectlinkadmin WHERE id=%s", (admin_id,))
            connection.commit()
            return jsonify({"status": "success"})
        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})



def run1(userid):

    with get_db() as (cursor, connection):

        print(userid)
        today_date = datetime.now().strftime('%d %B %Y')
        applied_date = datetime.now().strftime('%Y-%m-%d')

        ####### admins

        adminsdataquery = f"SELECT * FROM connectlinkadmin;"
        cursor.execute(adminsdataquery)
        adminsdata = cursor.fetchall()
        print(adminsdata)

        adminsdatamain = pd.DataFrame(adminsdata, columns= ['id', 'name', 'contact'])
        adminsdatamain['Action'] = adminsdatamain['id'].apply(lambda x: f'''<div style="display: flex; gap: 10px;"><button class="btn btn-primary edit-admin-details-btn" style="width:max-content;" data-bs-toggle="modal" data-bs-target="#viewprojectModal" data-ID="{x}">Edit Details</button>    <button class="btn btn-danger-2 remove-admin-btn" data-ID="{x}">Remove</button></div>''')
        adminsdatamain = adminsdatamain[['id', 'name', 'contact', 'Action']]
        table_datamain_admins_html = adminsdatamain.to_html(classes="table table-bordered table-theme", table_id="alladminsTable", index=False,  escape=False,)

        admin_options = adminsdatamain.apply(lambda row: f"{row['id']}--{row['name']}", axis=1).tolist()


        ######### maindata
        maindataquery = f"SELECT * FROM connectlinkdatabase;"
        cursor.execute(maindataquery)
        maindata = cursor.fetchall()
        print(maindata)
        num_projects = len(maindata)
        print(f"Number of projects: {num_projects}")


        datamain = pd.DataFrame(maindata, columns= ['id', 'clientname', 'clientidnumber', 'clientaddress', 'clientwanumber', 'clientemail', 'clientnextofkinname', 'clientnextofkinaddress', 'clientnextofkinphone', 'nextofkinrelationship', 'projectname', 'projectlocation', 'projectdescription', 'projectadministratorname', 'projectstartdate', 'projectduration', 'contractagreementdate', 'totalcontractamount', 'paymentmethod', 'monthstopay', 'datecaptured', 'capturer', 'capturerid', 'depositorbullet', 'datedepositorbullet', 'monthlyinstallment', 'installment1amount', 'installment1duedate', 'installment1date', 'installment2amount', 'installment2duedate', 'installment2date', 'installment3amount', 'installment3duedate', 'installment3date', 'installment4amount', 'installment4duedate', 'installment4date', 'installment5amount', 'installment5duedate', 'installment5date', 'installment6amount', 'installment6duedate', 'installment6date','projectcompletionstatus'])
        datamain['Action'] = datamain['id'].apply(lambda x: f'''<div style="display: flex; gap: 10px;"><a href="/download_contract/{x}" class="btn btn-primary3">Download Contract</a>    <button class="btn btn-primary3 view-project-btn" data-bs-toggle="modal" data-bs-target="#viewprojectModal" data-id="{x}">View Project</button><button class="btn btn-primary3 log-payment-btn" data-bs-toggle="modal" data-bs-target="#logpaymentModal" data-ID="{x}">Log a Payment</button></div>''')
        datamain = datamain[['id', 'clientname', 'clientidnumber', 'clientaddress', 'clientwanumber', 'clientemail', 'clientnextofkinname', 'clientnextofkinaddress', 'clientnextofkinphone', 'nextofkinrelationship', 'projectname', 'projectlocation', 'projectdescription', 'projectadministratorname', 'projectstartdate', 'projectduration', 'contractagreementdate', 'totalcontractamount', 'paymentmethod', 'monthstopay', 'datecaptured', 'capturer', 'capturerid', 'depositorbullet', 'datedepositorbullet', 'monthlyinstallment', 'installment1amount', 'installment1duedate', 'installment1date', 'installment2amount', 'installment2duedate', 'installment2date', 'installment3amount', 'installment3duedate', 'installment3date', 'installment4amount', 'installment4duedate', 'installment4date', 'installment5amount', 'installment5duedate', 'installment5date', 'installment6amount', 'installment6duedate', 'installment6date','projectcompletionstatus', 'Action']]

        table_datamain_html = datamain.to_html(classes="table table-bordered table-theme", table_id="allprojectsTable", index=False,  escape=False,)

        detailscompquery = f"SELECT * FROM connectlinkdetails;"
        cursor.execute(detailscompquery)
        detailscompdata = cursor.fetchall()
        print(detailscompdata)

        detailscompdata = pd.DataFrame(detailscompdata, columns= ['address', 'contact1', 'contact2', 'email', 'companyname', 'tinnumber'])
        companyname = detailscompdata.iat[0,4] if not detailscompdata.empty else "ConnectLink Properties"
        address = detailscompdata.iat[0,0] if not detailscompdata.empty else ""
        contact1 = detailscompdata.iat[0,1] if not detailscompdata.empty else ""
        contact2 = detailscompdata.iat[0,2] if not detailscompdata.empty else ""
        compemail = detailscompdata.iat[0,3] if not detailscompdata.empty else ""
        tinnumber = detailscompdata.iat[0,5] if not detailscompdata.empty else ""
        
        return {
            "table_datamain_html": table_datamain_html,
            'table_datamain_admins_html': table_datamain_admins_html,
            "companyname": companyname,
            "address": address,
            "contact1": contact1,
            "contact2": contact2,
            "compemail": compemail,
            "tinnumber": tinnumber,
            'today_date': today_date,
            'num_projects': num_projects,
            'admin_options': admin_options
            }

@app.route('/')
def userlogin():
    return render_template('login.html') 

@app.route('/get_project/<int:project_id>')
def get_project(project_id):

    with get_db() as (cursor, connection):

        try:
            cursor.execute("SELECT * FROM connectlinkdatabase WHERE id=%s", (project_id,))
            row = cursor.fetchone()
            cursor.close()

            if not row:
                return jsonify({})

            # Map columns to dict
            columns = ['id', 'clientname', 'clientidnumber', 'clientaddress', 'clientwanumber', 'clientemail',
                    'clientnextofkinname', 'clientnextofkinaddress', 'clientnextofkinphone', 'nextofkinrelationship',
                    'projectname', 'projectlocation', 'projectdescription', 'projectadministratorname',
                    'projectstartdate', 'projectduration', 'contractagreementdate', 'totalcontractamount',
                    'paymentmethod', 'monthstopay', 'datecaptured', 'capturer', 'capturerid', 'depositorbullet',
                    'datedepositorbullet', 'monthlyinstallment', 'installment1amount', 'installment1duedate',
                    'installment1date', 'installment2amount', 'installment2duedate', 'installment2date',
                    'installment3amount', 'installment3duedate', 'installment3date', 'installment4amount',
                    'installment4duedate', 'installment4date', 'installment5amount', 'installment5duedate',
                    'installment5date', 'installment6amount', 'installment6duedate', 'installment6date',
                    'projectcompletionstatus']

            project_dict = dict(zip(columns, row))
            return jsonify(project_dict)

        except Exception as e:
            return jsonify({"error": str(e)})

@app.route('/contract_log', methods=['POST'])
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

                project_administrator = request.form.get('projectadministrator')

                project_name = request.form.get('project_name')
                project_location = request.form.get('project_location')
                project_start_date = request.form.get('project_start_date')
                months_to_completion = request.form.get('months_to_completion')
                project_description = request.form.get('project_description') or ""


                agreement_date = request.form.get('agreement_date')
                total_contract_price = request.form.get('total_contract_price')
                payment_method = request.form.get('payment_method')
                months_to_pay = request.form.get('months_to_pay')

                if payment_method == "Bullet":
                    depostorbullet = request.form.get('total_contract_price')
                    deposit_payment_date = request.form.get('bullet_payment_date')


                elif payment_method == "Installments":
                    depostorbullet = request.form.get('deposit_required')
                    deposit_payment_date = request.form.get('deposit_payment_date')

                monthlyinstallment = (float(total_contract_price) - float(depostorbullet))/int(months_to_pay)
                project_completion_status = "Ongoing"

                if int(months_to_pay) == 1:
                    installment1amount = float(monthlyinstallment)
                    installment2amount = 0
                    installment3amount = 0
                    installment4amount = 0
                    installment5amount = 0
                    installment6amount = 0

                elif int(months_to_pay) == 2:
                    installment1amount = float(monthlyinstallment)
                    installment2amount = float(monthlyinstallment)
                    installment3amount = 0
                    installment4amount = 0
                    installment5amount = 0
                    installment6amount = 0
                
                elif int(months_to_pay) == 3:
                    installment1amount = float(monthlyinstallment)
                    installment2amount = float(monthlyinstallment)
                    installment3amount = float(monthlyinstallment)
                    installment4amount = 0
                    installment5amount = 0
                    installment6amount = 0

                elif int(months_to_pay) == 4:
                    installment1amount = float(monthlyinstallment)
                    installment2amount = float(monthlyinstallment)
                    installment3amount = float(monthlyinstallment)
                    installment4amount = float(monthlyinstallment)
                    installment5amount = 0
                    installment6amount = 0

                elif int(months_to_pay) == 5:
                    installment1amount = float(monthlyinstallment)
                    installment2amount = float(monthlyinstallment)
                    installment3amount = float(monthlyinstallment)
                    installment4amount = float(monthlyinstallment)
                    installment5amount = float(monthlyinstallment)
                    installment6amount = 0

                elif int(months_to_pay) == 6:
                    installment1amount = float(monthlyinstallment)
                    installment2amount = float(monthlyinstallment)
                    installment3amount = float(monthlyinstallment)
                    installment4amount = float(monthlyinstallment)
                    installment5amount = float(monthlyinstallment)
                    installment6amount = float(monthlyinstallment)


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

                print(f"Administrator: {project_administrator}")

                print(f"Project Name: {project_name}")
                print(f"Project Location: {project_location}")
                print(f"Project Start Date: {project_start_date}")
                print(f"Project Duration (Months): {months_to_completion}")

                print(f"Agreement Date: {agreement_date}")
                print(f"Total Contract Price: {total_contract_price}")
                print(f"Payment Method: {payment_method}")

                print(f"Bullet/Deposit Payment Date: {deposit_payment_date}")

                print(f"Months to Pay: {months_to_pay}")
                print(f"Deposit Payment Date: {deposit_payment_date}")
                print(f"First Installment Due Date: {first_installment_due_date}")
        

                # --- Insert into database (connectlinkdatabase) ---
                def safe_int(v):
                    try:
                        return int(v) if v not in (None, "") else None
                    except Exception:
                        return None

                def safe_float(v):
                    try:
                        return float(v) if v not in (None, "") else None
                    except Exception:
                        return None

                def safe_date(v):
                    try:
                        return datetime.strptime(v, "%Y-%m-%d").date() if v not in (None, "") else None
                    except Exception:
                        return None

                capturer = session.get('user_name', '')
                capturerid = session.get('userid')

                try:

                    insert_query = """
                        INSERT INTO connectlinkdatabase (
                            clientname, clientidnumber, clientaddress, clientwanumber, clientemail,
                            clientnextofkinname, clientnextofkinaddress, clientnextofkinphone, nextofkinrelationship,
                            projectname, projectlocation, projectdescription, projectadministratorname,
                            projectstartdate, projectduration, contractagreementdate, totalcontractamount,
                            paymentmethod, monthstopay, depositorbullet, datedepositorbullet, monthlyinstallment, 
                            installment1duedate, datecaptured, capturer, capturerid, projectcompletionstatus, installment1amount, installment2amount, installment3amount, installment4amount, installment5amount, installment6amount
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        );
                    """

                    params = (
                        client_name,
                        client_national_id,
                        client_address,
                        safe_int(client_whatsapp_number),
                        client_email,
                        next_of_kin_name,
                        next_of_kin_address,
                        safe_int(next_of_kin_contact_number),
                        relationship,
                        project_name,
                        project_location,
                        project_description,
                        project_administrator,
                        safe_date(project_start_date),
                        safe_int(months_to_completion),
                        safe_date(agreement_date),
                        safe_float(total_contract_price),
                        payment_method,
                        safe_int(months_to_pay),
                        safe_float(depostorbullet),
                        safe_date(deposit_payment_date),
                        safe_float(monthlyinstallment),
                        safe_date(first_installment_due_date),
                        today_date,
                        capturer,
                        capturerid,
                        project_completion_status,
                        installment1amount,
                        installment2amount,
                        installment3amount,
                        installment4amount,
                        installment5amount,
                        installment6amount
                    )

        
                    cursor.execute(insert_query, params)
                    connection.commit()
                    print("✅ Project inserted into connectlinkdatabase")


                except Exception as e:
                    connection.rollback()
                    print("❌ Failed to insert project:", e)
                    response = {'status': 'error', 'message': 'Failed to save project.'}
                    return jsonify(response), 500


                results = run1(userid)
                return render_template('adminpage.html', **results)

            except Exception as e:
                response = {'status': 'error', 'message': 'Leave application not submitted successfully.'}
                return jsonify(response), 400  


@app.route('/logout')
def logout():
    # Clear the session data to log the user out
    session.clear()

    # Redirect to the landing page or login page after logout
    return redirect(url_for('userlogin'))

@app.teardown_appcontext
def close_db(error):
    """Close any remaining connections on app shutdown"""
    pass  # No-op now since you're using context managers everywhere   

if __name__ == "__main__":
    app.run(host="0.0.0.0", port = 55, debug = True)