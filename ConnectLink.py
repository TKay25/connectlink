import uuid
import os
import html

# Prevent Matplotlib from building font cache on startup (blocks Gunicorn port binding on Render)
os.environ.setdefault("MPLCONFIGDIR", "/tmp/.matplotlib")
import bleach
from db_helper import get_db, execute_query
import numpy as np
from mysql.connector import Error
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_file,flash, make_response, after_this_request
from datetime import datetime, timedelta, date
import calendar
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
from openpyxl import Workbook
from weasyprint import HTML, CSS
import re
import traceback
from collections import Counter
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

            '''cursor.execute("""UPDATE connectlinkusers SET whatsapp = 774822568 WHERE id = 3""")'''

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
                "ALTER TABLE connectlinkusers ADD COLUMN IF NOT EXISTS whatsapp INT;",
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

            '''cursor.execute("""DROP TABLE connectlinkdatabasedeleted;""")'''        

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinknotes (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP,
                    capturer VARCHAR (100),
                    capturerid INT,
                    projectid INT,
                    note VARCHAR (1000)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appenqtemp (
                    id SERIAL PRIMARY KEY,
                    wanumber INT,
                    enqtype VARCHAR (100)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkenquiries (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMP,
                    clientwhatsapp INT,
                    enqcategory VARCHAR (100),
                    enq VARCHAR (1000),
                    plan BYTEA
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

            cursor.execute("""DELETE FROM connectlinkdatabase WHERE id BETWEEN 37 AND 39;""")
            '''cursor.execute("""DELETE FROM connectlinkadmin WHERE id BETWEEN 1 AND 6;""")
            cursor.execute("""TRUNCATE TABLE connectlinknotes;""")'''




            tables = ['connectlinkdatabase', 'connectlinknotes', 'connectlinkadmin']
            for table in tables:
                cursor.execute(f"SELECT pg_get_serial_sequence('{table}', 'id');")
                seq_name = cursor.fetchone()[0]  # fetch the first column of the first row
                print(f"Sequence for {table}: {seq_name}")


            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkdatabasedeletedprojects (
                    id INTEGER PRIMARY KEY,  -- Use INTEGER instead of SERIAL
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
                    capturerid INT,
                    deletedby VARCHAR (100),
                    deleterid INT,
                    depositorbullet NUMERIC(12,2),
                    datedepositorbullet date,
                    monthlyinstallment NUMERIC(12,2),
                    installment1amount NUMERIC(12,2),
                    installment1duedate date,
                    installment1date date,
                    installment2amount NUMERIC(12,2),
                    installment2duedate date,
                    installment2date date,
                    installment3amount NUMERIC(12,2),
                    installment3duedate date,
                    installment3date date,
                    installment4amount NUMERIC(12,2),
                    installment4duedate date,
                    installment4date date,
                    installment5amount NUMERIC(12,2),
                    installment5duedate date,
                    installment5date date,
                    installment6amount NUMERIC(12,2),
                    installment6duedate date,
                    installment6date date,
                    projectcompletionstatus varchar(100),
                    latepaymentinterest INT
                );
            """)

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
                "ALTER TABLE connectlinkenquiries ADD COLUMN IF NOT EXISTS status VARCHAR (100);",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS momid INT;",
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
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS projectcompletionstatus varchar(100);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS latepaymentinterest INT;",
                "ALTER TABLE connectlinknotes ADD COLUMN IF NOT EXISTS projectname varchar(100);",
                "ALTER TABLE connectlinknotes ADD COLUMN IF NOT EXISTS clientname varchar(100);",
                "ALTER TABLE connectlinknotes ADD COLUMN IF NOT EXISTS clientwanumber INT;",
                "ALTER TABLE connectlinknotes ADD COLUMN IF NOT EXISTS clientnextofkinnumber INT;"

            ]

            for sql_stmt in payment_alters:
                cursor.execute(sql_stmt)
            
            connection.commit()
            print("✅ Database tables initialized successfully!")
    except Exception as e:
        print(f"❌ Error initializing database tables: {e}")

initialize_database_tables()

@app.route("/webhook", methods=["GET", "POST"])
def webhook():

    with get_db() as (cursor, connection):

        if request.method == "GET":
            print("ouch")
            VERIFY_TOKEN = "2012753506232550"
            if request.args.get("hub.verify_token") == VERIFY_TOKEN:
                return request.args.get("hub.challenge")
            return "Verification failed", 403

        if request.method == "POST":
            today_date = datetime.now().strftime('%d %B %Y')
            applied_date = datetime.now().strftime('%Y-%m-%d')
            data = request.get_json()

            #global ACCESS_TOKEN
            #global PHONE_NUMBER_ID

            try:
                # Navigate the JSON structure to get the display_phone_number
                display_phone_number = data["entry"][0]["changes"][0]["value"]["metadata"]["display_phone_number"]

                if display_phone_number == "263781959700":

                    ACCESS_TOKEN = "EAAMk5Wj6ZBLABQZAZBaIfs9V338WQbkpZB5KfVQ58fUcjrX4nZCJm9SqSWsG6ouZCl9ZAIXGZCDo7xzitOUO5AgsPwtIaUMqpHj9iZCsJI4irPjcryKpeAchBf0ASjNPazQRrwBeL3dMs3tu4jbmlg3B2fYiZCEJhQQO4ZB4WSH8oHh07CCRKR2N2ZBWKMxVbLeyO8fA3gZDZD"
                    PHONE_NUMBER_ID = "977519838770637"
                    VERIFY_TOKEN = "2012753506232550"
                    WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
                    power = "Echelon Equipment Pvt Ltd"
                    bot = "ConnectLink Properties"



                def send_whatsapp_button_image_message(recipient, text, image_url, buttons, footer_text=None):
                    headers = {
                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                        "Content-Type": "application/json"
                    }

                    payload = {
                        "messaging_product": "whatsapp",
                        "to": recipient,
                        "type": "interactive",
                        "interactive": {
                            "type": "button",
                            "header": {
                                "type": "image",
                                "image": {
                                    "link": "https://connectlink-wbax.onrender.com/static/images/reqlogo.jpg"
                                }
                            },
                            "body": {
                                "text": text
                            },
                            "action": {
                                "buttons": buttons
                            }
                        }
                    }

                    if footer_text:
                        payload["interactive"]["footer"] = {
                            "text": footer_text
                        }

                    response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
                    print("📡 Button message response:", response.json())
                    return response

                def send_whatsapp_message(to, text, buttons=None, footer_text = None):

                    print("send mess initialised")

                    """Function to send a WhatsApp message using Meta API, with optional buttons."""
                    headers = {
                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                        "Content-Type": "application/json"
                    }

                    # If buttons are provided, send an interactive message
                    if buttons:
                        data = {
                            "messaging_product": "whatsapp",
                            "to": to,
                            "type": "interactive",
                            "interactive": {
                                "type": "button",
                                "body": {"text": text},
                                "action": {
                                    "buttons": buttons
                                }
                            }
                        }

                    if footer_text:
                        data["interactive"]["footer"] = {
                            "text": footer_text
                        }

                    else:
                        # Send a normal text message
                        print("inside else")

                        data = {
                            "messaging_product": "whatsapp",
                            "to": to,
                            "type": "text",
                            "text": {"body": text}
                        }
                    
                    # Debugging logs
                    print("✅ Sending message to:", to)
                    print("📩 Message body:", text)

                    """try:
                        response_json = response.json()
                        print("📝 WhatsApp API Response Data:", response_json)
                    except Exception as e:
                        print("❌ Error parsing response JSON:", e)"""

                    try:
                        print("trying in def")

                        response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
                        print("📡 WhatsApp API Response Status:", response.status_code)
                        print("📡 WhatsApp API Response Text:", response.text)

                        response.raise_for_status()  # will throw if not 2xx

                        print("✅ Message sent successfully.")
                        print("📝 Response JSON:", response.json())

                        print("done trying")
                        return response.json()
                    
                    except requests.exceptions.RequestException as e:
                        print("❌ WhatsApp API Error:", e)
                        return {"error": str(e)}

                def send_whatsapp_button_message(recipient, text, buttons, footer_text=None):
                    """Send WhatsApp interactive button message with footer"""
                    try:
                        headers = {
                            "Authorization": f"Bearer {ACCESS_TOKEN}",
                            "Content-Type": "application/json"
                        }
                        
                        payload = {
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": recipient,
                            "type": "interactive",
                            "interactive": {
                                "type": "button",
                                "body": {
                                    "text": text
                                },
                                "action": {
                                    "buttons": buttons
                                }
                            }
                        }
                        
                        # Add footer text if provided
                        if footer_text:
                            payload["interactive"]["footer"] = {"text": footer_text}
                        
                        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)

                        print("✅ Sending button message to:", recipient)
                        print("📩 Message body:", text)
                        print("📌 Footer:", footer_text)
                        print("📡 WhatsApp API Response Status:", response.status_code)
                        
                        if response.status_code != 200:
                            print("❌ Error response:", response.json())
                        
                        return response
                        
                    except Exception as e:
                        print(f"❌ Error sending WhatsApp button message: {str(e)}")
                        return None
                    
                def send_whatsapp_list_message(recipient, text, header_text, sections, footer_text=None):
                    """Send WhatsApp interactive list message"""
                    try:
                        headers = {
                            "Authorization": f"Bearer {ACCESS_TOKEN}",
                            "Content-Type": "application/json"
                        }
                        
                        payload = {
                            "messaging_product": "whatsapp",
                            "recipient_type": "individual",
                            "to": recipient,
                            "type": "interactive",
                            "interactive": {
                                "type": "list",
                                "header": {
                                    "type": "text",
                                    "text": header_text[:60]  # Max 60 chars
                                },
                                "body": {
                                    "text": text[:1024]  # Max 1024 chars
                                },
                                "action": {
                                    "button": "Select Option",
                                    "sections": sections
                                }
                            }
                        }
                        
                        # Add footer text if provided
                        if footer_text:
                            payload["interactive"]["footer"] = {"text": footer_text[:60]}  # Max 60 chars
                        
                        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
                        
                        print("✅ Sending list message to:", recipient)
                        print("📩 Message body:", text)
                        print("📌 Footer:", footer_text)
                        print("📡 WhatsApp API Response Status:", response.status_code)
                        
                        return response
                        
                    except Exception as e:
                        print(f"❌ Error sending WhatsApp list message: {str(e)}")
                        return None


                print("📥 Full incoming data:", json.dumps(data, indent=2))

                if data and "entry" in data:

                    profile_name = None

                    try:
                        profile_name = (
                            data.get("entry", [{}])[0]
                                .get("changes", [{}])[0]
                                .get("value", {})
                                .get("contacts", [{}])[0]
                                .get("profile", {})
                                .get("name")
                        )
                    except Exception as e:
                        print("❌ Error extracting profile name:", e)

                    print("👤 Contact profile name:", profile_name)


                    for entry in data["entry"]:
                        for change in entry["changes"]:
                            if "messages" in change["value"]:
                                for message in change["value"]["messages"]:

                                    conversation_id = str(uuid.uuid4())
                                    session['conversation_id'] = conversation_id
                                

                                    sender_id = message["from"]
                                    sender_number = sender_id[-9:]
                                    print(f"📱 Conversation {conversation_id}: Sender's WhatsApp number: {sender_number}")
                                    session['client'] = str(sender_number)

                                    #external_database_url = "postgresql://lmsdatabase_8ag3_user:6WD9lOnHkiU7utlUUjT88m4XgEYQMTLb@dpg-ctp9h0aj1k6c739h9di0-a.oregon-postgres.render.com/lmsdatabase_8ag3"

                                    with get_db() as (cursor, connection):

                                        try:
                                            
                                            query = """
                                                SELECT *
                                                FROM connectlinkusers
                                                WHERE whatsapp::TEXT LIKE %s
                                            """

                                            cursor.execute(query, (f"%{sender_number}%",))
                                            result = cursor.fetchone()

                                            print(result)

                                            if result:

                                                found = True 

                                                id_user = result[0]  
                                                admin_name = result[2]  

                                                print(id_user)
                                                print(admin_name)

                                                try:
                                                
                                                    if message.get("type") == "interactive":
                                                        interactive = message.get("interactive", {})


                                                        if interactive.get("type") == "list_reply":
                                                            selected_option = interactive.get("list_reply", {}).get("id")
                                                            print(f"📋 User selected: {selected_option}")
                                                            button_id = ""

                                                        elif interactive.get("type") == "button_reply":
                                                            button_id = interactive.get("button_reply", {}).get("id")
                                                            print(f"🔘 Button clicked: {button_id}")
                                                            selected_option = ""


                                                        elif interactive.get("type") == "nfm_reply":

                                                            url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                            headers = {
                                                                "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                "Content-Type": "application/json"
                                                            }


                                                            response_str = interactive.get("nfm_reply", {}).get("response_json", "{}")
                                                            selected_option = ""
                                                            button_id = ""
                                                            
                                                            try:
                                                                form_response = json.loads(response_str)  # convert string → dict
                                                            except Exception as e:
                                                                print("❌ Error parsing nfm_reply response_json:", e)
                                                                form_response = {}

                                                            print("📋 User submitted flow response:", form_response)


                                                        if button_id == "portfolio":

                                                            buttons = [
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "getportfolio",
                                                                        "title": "🏗️ Get Master File"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "getnotes",
                                                                        "title": "Get Notes"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "main_menu",
                                                                        "title": " Main Menu"
                                                                    }
                                                                }
                                                            ]


                                                            send_whatsapp_message(
                                                                sender_id, 
                                                                "Kindly select a portfolio option below.",
                                                                buttons,
                                                                footer_text="ConnectLink Properties • Admin Panel"

                                                            )

                                                            continue

                                                        elif selected_option == "getportfolio":

                                                            try:
                                                                
                                                                # Get today's date for filtering
                                                                today = date.today()
                                                                today_str = today.strftime('%d %B %Y')
                                                                
                                                                with get_db() as (cursor, connection):
                                                                    # Query for ALL installment projects (not just pending)
                                                                    query = """
                                                                    SELECT 
                                                                        id,
                                                                        clientname,
                                                                        projectname,
                                                                        projectstartdate,
                                                                        projectadministratorname,
                                                                        totalcontractamount,
                                                                        depositorbullet,
                                                                        clientwanumber,
                                                                        momid,
                                                                        monthstopay,
                                                                        installment1amount, installment1duedate, installment1date,
                                                                        installment2amount, installment2duedate, installment2date,
                                                                        installment3amount, installment3duedate, installment3date,
                                                                        installment4amount, installment4duedate, installment4date,
                                                                        installment5amount, installment5duedate, installment5date,
                                                                        installment6amount, installment6duedate, installment6date
                                                                    FROM connectlinkdatabase 
                                                                    WHERE paymentmethod = 'Installments'
                                                                    ORDER BY 
                                                                        clientname ASC,
                                                                        projectstartdate DESC,
                                                                        momid ASC;
                                                                    """
                                                                    
                                                                    cursor.execute(query)
                                                                    rows = cursor.fetchall()
                                                                    
                                                                    if not rows:
                                                                        return jsonify({'status': 'error', 'message': 'No installment projects found in portfolio'}), 404
                                                                    
                                                                    # Get column names
                                                                    colnames = [desc[0] for desc in cursor.description]
                                                                    
                                                                # Convert to DataFrame
                                                                df = pd.DataFrame(rows, columns=colnames)
                                                                
                                                                # ================================================
                                                                # PROCESS DATA FOR PROJECTS PORTFOLIO
                                                                # ================================================
                                                                projects_data = []
                                                                summary_data = {
                                                                    'total_projects': 0,
                                                                    'total_contract_value': 0.0,
                                                                    'total_paid': 0.0,
                                                                    'total_pending': 0.0,
                                                                    'total_overdue': 0.0,
                                                                    'total_future': 0.0,
                                                                    'clients_by_status': {
                                                                        'all_paid': 0,
                                                                        'partially_paid': 0,
                                                                        'all_pending': 0,
                                                                        'has_overdue': 0
                                                                    }
                                                                }
                                                                
                                                                # Track unique clients and their statuses
                                                                client_statuses = {}
                                                                
                                                                for _, row in df.iterrows():
                                                                    project_start = row.get('projectstartdate')
                                                                    start_date_str = project_start.strftime('%d %b %Y') if pd.notna(project_start) else 'Not Started'
                                                                    
                                                                    client_name = str(row.get('clientname', '')).strip()
                                                                    
                                                                    # Calculate installment details
                                                                    installments = []
                                                                    total_pending = 0.0
                                                                    total_paid = 0.0
                                                                    overdue_amount = 0.0
                                                                    future_amount = 0.0
                                                                    installment_count = 0
                                                                    paid_count = 0
                                                                    pending_count = 0
                                                                    overdue_count = 0
                                                                    
                                                                    for i in range(1, 7):
                                                                        amount = row.get(f'installment{i}amount')
                                                                        due_date = row.get(f'installment{i}duedate')
                                                                        payment_date = row.get(f'installment{i}date')
                                                                        
                                                                        if amount and float(amount) > 0:
                                                                            installment_count += 1
                                                                            if pd.isna(payment_date):  # Pending
                                                                                due_str = due_date.strftime('%d %b %Y') if pd.notna(due_date) else 'No Due Date'
                                                                                due_month = due_date.strftime('%B %Y') if pd.notna(due_date) else 'No Month'
                                                                                
                                                                                # Check if overdue
                                                                                is_overdue = False
                                                                                if pd.notna(due_date):
                                                                                    is_overdue = due_date < today
                                                                                
                                                                                status = 'OVERDUE' if is_overdue else 'PENDING'
                                                                                status_color = 'red' if is_overdue else 'orange'
                                                                                
                                                                                installment_data = {
                                                                                    'number': i,
                                                                                    'due_date': due_str,
                                                                                    'amount': float(amount),
                                                                                    'status': status,
                                                                                    'status_color': status_color,
                                                                                    'due_month': due_month
                                                                                }
                                                                                
                                                                                installments.append(installment_data)
                                                                                total_pending += float(amount)
                                                                                pending_count += 1
                                                                                
                                                                                if is_overdue:
                                                                                    overdue_amount += float(amount)
                                                                                    overdue_count += 1
                                                                                else:
                                                                                    future_amount += float(amount)
                                                                            else:  # Paid
                                                                                installments.append({
                                                                                    'number': i,
                                                                                    'due_date': payment_date.strftime('%d %b %Y') if pd.notna(payment_date) else 'Paid',
                                                                                    'amount': float(amount),
                                                                                    'status': 'PAID',
                                                                                    'status_color': 'green',
                                                                                    'due_month': 'Completed'
                                                                                })
                                                                                total_paid += float(amount)
                                                                                paid_count += 1
                                                                    
                                                                    # Sort installments by number
                                                                    installments.sort(key=lambda x: x['number'])
                                                                    
                                                                    # Determine project status
                                                                    if paid_count == installment_count and installment_count > 0:
                                                                        project_status = 'COMPLETED'
                                                                        status_color = 'green'
                                                                    elif paid_count > 0 and pending_count > 0:
                                                                        project_status = 'IN PROGRESS'
                                                                        status_color = 'orange'
                                                                    elif pending_count > 0 and overdue_count > 0:
                                                                        project_status = 'OVERDUE'
                                                                        status_color = 'red'
                                                                    elif pending_count > 0:
                                                                        project_status = 'PENDING'
                                                                        status_color = 'orange'
                                                                    else:
                                                                        project_status = 'NO INSTALLMENTS'
                                                                        status_color = 'gray'
                                                                    
                                                                    # Prepare project data for PDF
                                                                    project_data = {
                                                                        'client_name': client_name,
                                                                        'project_name': str(row.get('projectname', '')),
                                                                        'mom_id': int(row.get('momid', 0)) if pd.notna(row.get('momid')) else 0,
                                                                        'start_date': start_date_str,
                                                                        'administrator': str(row.get('projectadministratorname', '')),
                                                                        'total_contract': float(row.get('totalcontractamount', 0)) if pd.notna(row.get('totalcontractamount')) else 0.0,
                                                                        'deposit_paid': float(row.get('depositorbullet', 0)) if pd.notna(row.get('depositorbullet')) else 0.0,
                                                                        'client_phone': str(row.get('clientwanumber', '')),
                                                                        'months_to_pay': int(row.get('monthstopay', 0)) if pd.notna(row.get('monthstopay')) else 0,
                                                                        'installments': installments,
                                                                        'total_pending': total_pending,
                                                                        'total_paid': total_paid,
                                                                        'overdue_amount': overdue_amount,
                                                                        'future_amount': future_amount,
                                                                        'balance_due': float(row.get('totalcontractamount', 0) or 0) - total_paid - float(row.get('depositorbullet', 0) or 0),
                                                                        'project_status': project_status,
                                                                        'status_color': status_color,
                                                                        'completion_percentage': (total_paid / float(row.get('totalcontractamount', 1) or 1)) * 100 if float(row.get('totalcontractamount', 0)) > 0 else 0
                                                                    }
                                                                    
                                                                    projects_data.append(project_data)
                                                                    
                                                                    # Update client status tracking
                                                                    if client_name not in client_statuses:
                                                                        client_statuses[client_name] = {
                                                                            'projects': 0,
                                                                            'completed': 0,
                                                                            'in_progress': 0,
                                                                            'overdue': 0,
                                                                            'pending': 0
                                                                        }
                                                                    
                                                                    client_statuses[client_name]['projects'] += 1
                                                                    if project_status == 'COMPLETED':
                                                                        client_statuses[client_name]['completed'] += 1
                                                                    elif project_status == 'IN PROGRESS':
                                                                        client_statuses[client_name]['in_progress'] += 1
                                                                    elif project_status == 'OVERDUE':
                                                                        client_statuses[client_name]['overdue'] += 1
                                                                    elif project_status == 'PENDING':
                                                                        client_statuses[client_name]['pending'] += 1
                                                                    
                                                                    # Update summary totals
                                                                    summary_data['total_projects'] += 1
                                                                    summary_data['total_contract_value'] += float(row.get('totalcontractamount', 0) or 0)
                                                                    summary_data['total_paid'] += total_paid
                                                                    summary_data['total_pending'] += total_pending
                                                                    summary_data['total_overdue'] += overdue_amount
                                                                    summary_data['total_future'] += future_amount
                                                                
                                                                # Calculate client status summary
                                                                for client, status in client_statuses.items():
                                                                    if status['completed'] == status['projects']:
                                                                        summary_data['clients_by_status']['all_paid'] += 1
                                                                    elif status['overdue'] > 0:
                                                                        summary_data['clients_by_status']['has_overdue'] += 1
                                                                    elif status['in_progress'] > 0:
                                                                        summary_data['clients_by_status']['partially_paid'] += 1
                                                                    elif status['pending'] == status['projects']:
                                                                        summary_data['clients_by_status']['all_pending'] += 1
                                                                
                                                                # Sort projects by client name, then by status
                                                                projects_data.sort(key=lambda x: (x['client_name'], x['project_status'] != 'COMPLETED', x['project_status'] != 'OVERDUE', x['project_name']))
                                                                
                                                                # Prepare final PDF data
                                                                pdf_data = {
                                                                    'report_date': today_str,
                                                                    'generated_on': datetime.now().strftime('%d %B %Y %H:%M:%S'),
                                                                    'company_name': 'ConnectLink Properties',  # Replace with actual
                                                                    'company_logo': '',  # Add logo if available
                                                                    'report_title': 'INSTALLMENT PROJECTS PORTFOLIO',
                                                                    'summary': summary_data,
                                                                    'projects': projects_data,
                                                                    'total_clients': len(client_statuses)
                                                                }
                                                                
                                                                # Generate PDF
                                                                def generate_portfolio_pdf():

                                                                    from weasyprint import HTML
                                                                    import io

                                                                    
                                                                    """Generate PDF with project-by-project portfolio"""
                                                                    html_template = """
                                                                    <!DOCTYPE html>
                                                                    <html>
                                                                    <head>
                                                                        <meta charset="UTF-8">
                                                                        <style>
                                                                            @page {
                                                                                size: A4;
                                                                                margin: 1.5cm;

                                                                                @bottom-center {
                                                                                    content: "Page " counter(page) " of " counter(pages);
                                                                                    font-size: 10px;
                                                                                    color: #7f8c8d;
                                                                                }
                                                                            }
                                                                            
                                                                            body {
                                                                                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                                                                line-height: 1.6;
                                                                                color: #333;
                                                                                margin: 0;
                                                                                padding: 0;
                                                                            }
                                                                            
                                                                            .header {
                                                                                text-align: center;
                                                                                margin-bottom: 25px;
                                                                                padding-bottom: 20px;
                                                                                border-bottom: 3px solid #3498db;
                                                                            }
                                                                            
                                                                            .company-name {
                                                                                font-size: 24px;
                                                                                font-weight: bold;
                                                                                color: #2c3e50;
                                                                                margin-bottom: 5px;
                                                                            }
                                                                            
                                                                            .report-title {
                                                                                font-size: 20px;
                                                                                color: #3498db;
                                                                                margin-bottom: 10px;
                                                                                text-transform: uppercase;
                                                                                letter-spacing: 2px;
                                                                            }
                                                                            
                                                                            .report-date {
                                                                                font-size: 14px;
                                                                                color: #7f8c8d;
                                                                                margin-bottom: 20px;
                                                                            }
                                                                            
                                                                            .summary-section {
                                                                                background: #f8f9fa;
                                                                                padding: 20px;
                                                                                border-radius: 8px;
                                                                                margin-bottom: 30px;
                                                                                border-left: 4px solid #3498db;
                                                                            }
                                                                            
                                                                            .summary-grid {
                                                                                display: grid;
                                                                                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                                                                                gap: 15px;
                                                                                margin-top: 15px;
                                                                            }
                                                                            
                                                                            .summary-item {
                                                                                background: white;
                                                                                padding: 15px;
                                                                                border-radius: 6px;
                                                                                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                                                                                text-align: center;
                                                                            }
                                                                            
                                                                            .summary-label {
                                                                                font-size: 11px;
                                                                                color: #7f8c8d;
                                                                                text-transform: uppercase;
                                                                                letter-spacing: 0.5px;
                                                                                margin-bottom: 5px;
                                                                            }
                                                                            
                                                                            .summary-value {
                                                                                font-size: 20px;
                                                                                font-weight: bold;
                                                                                color: #2c3e50;
                                                                            }
                                                                            
                                                                            .summary-value.red {
                                                                                color: #e74c3c;
                                                                            }
                                                                            
                                                                            .summary-value.green {
                                                                                color: #27ae60;
                                                                            }
                                                                            
                                                                            .summary-value.blue {
                                                                                color: #3498db;
                                                                            }
                                                                            
                                                                            .summary-value.orange {
                                                                                color: #f39c12;
                                                                            }
                                                                            
                                                                            .project-section {
                                                                                margin-bottom: 40px;
                                                                                page-break-inside: avoid;
                                                                                border: 1px solid #dee2e6;
                                                                                border-radius: 8px;
                                                                                overflow: hidden;
                                                                            }
                                                                            
                                                                            .project-header {
                                                                                padding: 15px;
                                                                                margin-bottom: 0;
                                                                                font-size: 16px;
                                                                                display: flex;
                                                                                justify-content: space-between;
                                                                                align-items: center;
                                                                            }
                                                                            
                                                                            .project-details {
                                                                                padding: 20px;
                                                                                background: white;
                                                                            }
                                                                            
                                                                            .project-grid {
                                                                                display: grid;
                                                                                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                                                                                gap: 15px;
                                                                                margin-bottom: 20px;
                                                                            }
                                                                            
                                                                            .project-field {
                                                                                margin-bottom: 8px;
                                                                            }
                                                                            
                                                                            .field-label {
                                                                                font-size: 11px;
                                                                                color: #7f8c8d;
                                                                                text-transform: uppercase;
                                                                                margin-bottom: 3px;
                                                                            }
                                                                            
                                                                            .field-value {
                                                                                font-size: 14px;
                                                                                font-weight: 500;
                                                                                color: #2c3e50;
                                                                            }
                                                                            
                                                                            .installments-table {
                                                                                width: 100%;
                                                                                border-collapse: collapse;
                                                                                margin-top: 20px;
                                                                                font-size: 11px;
                                                                            }
                                                                            
                                                                            .installments-table th {
                                                                                background: #2c3e50;
                                                                                color: white;
                                                                                padding: 10px;
                                                                                text-align: left;
                                                                                font-weight: 600;
                                                                                text-transform: uppercase;
                                                                            }
                                                                            
                                                                            .installments-table td {
                                                                                padding: 8px;
                                                                                border-bottom: 1px solid #dee2e6;
                                                                            }
                                                                            
                                                                            .installments-table tr:nth-child(even) {
                                                                                background: #f8f9fa;
                                                                            }
                                                                            
                                                                            .status-badge {
                                                                                display: inline-block;
                                                                                padding: 3px 10px;
                                                                                border-radius: 20px;
                                                                                font-size: 10px;
                                                                                font-weight: 600;
                                                                                text-transform: uppercase;
                                                                                letter-spacing: 0.5px;
                                                                            }
                                                                            
                                                                            .status-overdue {
                                                                                background: #ffebee;
                                                                                color: #e74c3c;
                                                                                border: 1px solid #e74c3c;
                                                                            }
                                                                            
                                                                            .status-pending {
                                                                                background: #fff3e0;
                                                                                color: #f39c12;
                                                                                border: 1px solid #f39c12;
                                                                            }
                                                                            
                                                                            .status-paid {
                                                                                background: #e8f5e9;
                                                                                color: #27ae60;
                                                                                border: 1px solid #27ae60;
                                                                            }
                                                                            
                                                                            .status-completed {
                                                                                background: #e8f5e9;
                                                                                color: #27ae60;
                                                                                border: 1px solid #27ae60;
                                                                            }
                                                                            
                                                                            .status-in-progress {
                                                                                background: #fff3e0;
                                                                                color: #f39c12;
                                                                                border: 1px solid #f39c12;
                                                                            }
                                                                            
                                                                            .amount {
                                                                                font-family: 'Courier New', monospace;
                                                                                font-weight: bold;
                                                                                font-size: 12px;
                                                                            }
                                                                            
                                                                            .footer {
                                                                                margin-top: 40px;
                                                                                padding-top: 15px;
                                                                                border-top: 2px solid #ecf0f1;
                                                                                text-align: center;
                                                                                font-size: 11px;
                                                                                color: #7f8c8d;
                                                                            }
                                                                            
                                                                            .note {
                                                                                font-size: 11px;
                                                                                color: #7f8c8d;
                                                                                font-style: italic;
                                                                                margin-top: 5px;
                                                                            }
                                                                            
                                                                            h2 {
                                                                                color: #2c3e50;
                                                                                border-bottom: 2px solid #3498db;
                                                                                padding-bottom: 8px;
                                                                                margin-top: 40px;
                                                                                font-size: 18px;
                                                                            }
                                                                            
                                                                            h3 {
                                                                                color: #34495e;
                                                                                margin: 25px 0 15px 0;
                                                                                font-size: 16px;
                                                                            }
                                                                            
                                                                            .section-title {
                                                                                color: #2c3e50;
                                                                                background: #f8f9fa;
                                                                                padding: 12px 15px;
                                                                                border-left: 4px solid #3498db;
                                                                                margin: 30px 0 20px 0;
                                                                                font-size: 16px;
                                                                                font-weight: 600;
                                                                            }
                                                                            
                                                                            .client-name {
                                                                                font-weight: bold;
                                                                                color: #2c3e50;
                                                                            }
                                                                            
                                                                            .project-name {
                                                                                font-style: italic;
                                                                                color: #7f8c8d;
                                                                            }
                                                                            
                                                                            .completion-bar {
                                                                                height: 8px;
                                                                                background: #ecf0f1;
                                                                                border-radius: 4px;
                                                                                margin-top: 5px;
                                                                                overflow: hidden;
                                                                            }
                                                                            
                                                                            .completion-fill {
                                                                                height: 100%;
                                                                                background: #27ae60;
                                                                                border-radius: 4px;
                                                                            }
                                                                            
                                                                            .progress-text {
                                                                                font-size: 10px;
                                                                                color: #7f8c8d;
                                                                                margin-top: 3px;
                                                                            }
                                                                            
                                                                            .client-summary-table {
                                                                                width: 100%;
                                                                                border-collapse: collapse;
                                                                                margin-top: 20px;
                                                                                font-size: 12px;
                                                                            }
                                                                            
                                                                            .client-summary-table th {
                                                                                background: #3498db;
                                                                                color: white;
                                                                                padding: 12px;
                                                                                text-align: left;
                                                                                font-weight: 600;
                                                                            }
                                                                            
                                                                            .client-summary-table td {
                                                                                padding: 10px;
                                                                                border-bottom: 1px solid #dee2e6;
                                                                            }
                                                                            
                                                                            .client-summary-table tr:nth-child(even) {
                                                                                background: #f8f9fa;
                                                                            }
                                                                        </style>
                                                                    </head>
                                                                    <body>
                                                                        <div class="header">
                                                                            <div class="company-name">{{ company_name }}</div>
                                                                            <div class="report-title">{{ report_title }}</div>
                                                                            <div class="report-date">Generated on: {{ generated_on }}</div>
                                                                        </div>
                                                                        
                                                                        <div class="summary-section">
                                                                            <h3>PORTFOLIO OVERVIEW</h3>
                                                                            <div class="summary-grid">
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Total Projects</div>
                                                                                    <div class="summary-value blue">{{ summary.total_projects }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Total Clients</div>
                                                                                    <div class="summary-value blue">{{ total_clients }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Contract Value</div>
                                                                                    <div class="summary-value">${{ "%.2f"|format(summary.total_contract_value) }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Amount Paid</div>
                                                                                    <div class="summary-value green">${{ "%.2f"|format(summary.total_paid) }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Pending Amount</div>
                                                                                    <div class="summary-value orange">${{ "%.2f"|format(summary.total_pending) }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Overdue Amount</div>
                                                                                    <div class="summary-value red">${{ "%.2f"|format(summary.total_overdue) }}</div>
                                                                                </div>
                                                                            </div>
                                                                            
                                                                            <div class="summary-grid" style="margin-top: 20px;">
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Clients - All Paid</div>
                                                                                    <div class="summary-value green">{{ summary.clients_by_status.all_paid }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Clients - Partially Paid</div>
                                                                                    <div class="summary-value orange">{{ summary.clients_by_status.partially_paid }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Clients - All Pending</div>
                                                                                    <div class="summary-value">{{ summary.clients_by_status.all_pending }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Clients - Has Overdue</div>
                                                                                    <div class="summary-value red">{{ summary.clients_by_status.has_overdue }}</div>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                        
                                                                        <div class="section-title">PROJECT DETAILS</div>
                                                                        
                                                                        {% for project in projects %}
                                                                        <div class="project-section">
                                                                            <div class="project-header" style="background: {{ project.status_color }}; color: white;">
                                                                                <div>
                                                                                    <span class="client-name">{{ project.client_name }}</span>
                                                                                    <span class="project-name"> - {{ project.project_name }}</span>
                                                                                </div>
                                                                                <div style="display: flex; align-items: center; gap: 15px;">
                                                                                    <span>MOM ID: {{ project.mom_id }}</span>
                                                                                    <span class="status-badge status-{{ project.project_status|lower|replace(' ', '-') }}">
                                                                                        {{ project.project_status }}
                                                                                    </span>
                                                                                </div>
                                                                            </div>
                                                                            
                                                                            <div class="project-details">
                                                                                <div class="project-grid">
                                                                                    <div>
                                                                                        <div class="project-field">
                                                                                            <div class="field-label">Administrator</div>
                                                                                            <div class="field-value">{{ project.administrator }}</div>
                                                                                        </div>
                                                                                        <div class="project-field">
                                                                                            <div class="field-label">Start Date</div>
                                                                                            <div class="field-value">{{ project.start_date }}</div>
                                                                                        </div>
                                                                                        <div class="project-field">
                                                                                            <div class="field-label">Client Phone</div>
                                                                                            <div class="field-value">{{ project.client_phone }}</div>
                                                                                        </div>
                                                                                    </div>
                                                                                    <div>
                                                                                        <div class="project-field">
                                                                                            <div class="field-label">Total Contract</div>
                                                                                            <div class="field-value amount">${{ "%.2f"|format(project.total_contract) }}</div>
                                                                                        </div>
                                                                                        <div class="project-field">
                                                                                            <div class="field-label">Deposit Paid</div>
                                                                                            <div class="field-value amount">${{ "%.2f"|format(project.deposit_paid) }}</div>
                                                                                        </div>
                                                                                        <div class="project-field">
                                                                                            <div class="field-label">Months to Pay</div>
                                                                                            <div class="field-value">{{ project.months_to_pay }}</div>
                                                                                        </div>
                                                                                    </div>
                                                                                    <div>
                                                                                        <div class="project-field">
                                                                                            <div class="field-label">Total Paid</div>
                                                                                            <div class="field-value amount green">${{ "%.2f"|format(project.total_paid) }}</div>
                                                                                        </div>
                                                                                        <div class="project-field">
                                                                                            <div class="field-label">Balance Due</div>
                                                                                            <div class="field-value amount">${{ "%.2f"|format(project.balance_due) }}</div>
                                                                                        </div>
                                                                                        <div class="project-field">
                                                                                            <div class="field-label">Pending Amount</div>
                                                                                            <div class="field-value amount orange">${{ "%.2f"|format(project.total_pending) }}</div>
                                                                                        </div>
                                                                                    </div>
                                                                                </div>
                                                                                
                                                                                <!-- Progress Bar -->
                                                                                <div style="margin: 15px 0;">
                                                                                    <div class="field-label">Payment Progress</div>
                                                                                    <div class="completion-bar">
                                                                                        <div class="completion-fill" style="width: {{ project.completion_percentage }}%;"></div>
                                                                                    </div>
                                                                                    <div class="progress-text">
                                                                                        {{ "%.1f"|format(project.completion_percentage) }}% Complete
                                                                                        (${{ "%.2f"|format(project.total_paid) }} of ${{ "%.2f"|format(project.total_contract) }})
                                                                                    </div>
                                                                                </div>
                                                                                
                                                                                <h3>Installment Schedule</h3>
                                                                                <table class="installments-table">
                                                                                    <thead>
                                                                                        <tr>
                                                                                            <th>#</th>
                                                                                            <th>Due Date</th>
                                                                                            <th>Amount</th>
                                                                                            <th>Status</th>
                                                                                            <th>Month</th>
                                                                                        </tr>
                                                                                    </thead>
                                                                                    <tbody>
                                                                                        {% for installment in project.installments %}
                                                                                        <tr>
                                                                                            <td>{{ installment.number }}</td>
                                                                                            <td>{{ installment.due_date }}</td>
                                                                                            <td class="amount">${{ "%.2f"|format(installment.amount) }}</td>
                                                                                            <td>
                                                                                                <span class="status-badge status-{{ installment.status|lower }}">
                                                                                                    {{ installment.status }}
                                                                                                </span>
                                                                                            </td>
                                                                                            <td>{{ installment.due_month }}</td>
                                                                                        </tr>
                                                                                        {% endfor %}
                                                                                    </tbody>
                                                                                </table>
                                                                                
                                                                                <div class="project-grid" style="margin-top: 20px;">
                                                                                    <div class="summary-item" style="padding: 10px;">
                                                                                        <div class="summary-label">Overdue Amount</div>
                                                                                        <div class="summary-value red">${{ "%.2f"|format(project.overdue_amount) }}</div>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                        {% endfor %}
                                                                        
                                                                        <div class="section-title">CLIENT SUMMARY</div>
                                                                        
                                                                        <table class="client-summary-table">
                                                                            <thead>
                                                                                <tr>
                                                                                    <th>Client Name</th>
                                                                                    <th>Total Projects</th>
                                                                                    <th>Completed</th>
                                                                                    <th>In Progress</th>
                                                                                    <th>Overdue</th>
                                                                                    <th>Pending</th>
                                                                                    <th>Total Contract</th>
                                                                                </tr>
                                                                            </thead>
                                                                            <tbody>
                                                                                {% set ns = namespace(clients_processed=0) %}
                                                                                {% for client, status in client_statuses.items() if ns.clients_processed < 10 %}
                                                                                {% set ns.clients_processed = ns.clients_processed + 1 %}
                                                                                <tr>
                                                                                    <td><strong>{{ client }}</strong></td>
                                                                                    <td>{{ status.projects }}</td>
                                                                                    <td><span style="color: #27ae60;">{{ status.completed }}</span></td>
                                                                                    <td><span style="color: #f39c12;">{{ status.in_progress }}</span></td>
                                                                                    <td><span style="color: #e74c3c;">{{ status.overdue }}</span></td>
                                                                                    <td>{{ status.pending }}</td>
                                                                                    <td class="amount">
                                                                                        {% set client_total = 0 %}
                                                                                        {% for project in projects %}
                                                                                            {% if project.client_name == client %}
                                                                                                {% set client_total = client_total + project.total_contract %}
                                                                                            {% endif %}
                                                                                        {% endfor %}
                                                                                        ${{ "%.2f"|format(client_total) }}
                                                                                    </td>
                                                                                </tr>
                                                                                {% endfor %}
                                                                            </tbody>
                                                                        </table>
                                                                        
                                                                        {% if total_clients > 10 %}
                                                                        <p class="note" style="text-align: center; margin-top: 10px;">
                                                                            ... and {{ total_clients - 10 }} more clients
                                                                        </p>
                                                                        {% endif %}
                                                                        
                                                                        <div class="footer">
                                                                            <p>Generated by ConnectLink System • {{ report_date }}</p>
                                                                            <p class="note">This portfolio report includes all installment projects with detailed payment progress and status.</p>
                                                                        </div>
                                                                    </body>
                                                                    </html>
                                                                    """
                                                                    
                                                                    # Render template with data
                                                                    from jinja2 import Template
                                                                    template = Template(html_template)
                                                                    html_content = template.render(**pdf_data, client_statuses=client_statuses)
                                                                    
                                                                    # Generate PDF
                                                                    pdf_bytes = HTML(string=html_content).write_pdf()
                                                                    return pdf_bytes
                                                                
                                                                def upload_pdf_to_whatsapp(pdf_bytes, phone_number):
                                                                    import io
                                                                    """Upload PDF to WhatsApp Cloud API"""
                                                                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                                                    filename = f'installment_portfolio_{timestamp}.pdf'
                                                                    
                                                                    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
                                                                    headers = {
                                                                        "Authorization": f"Bearer {ACCESS_TOKEN}"
                                                                    }
                                                                    
                                                                    files = {
                                                                        "file": (filename, io.BytesIO(pdf_bytes), "application/pdf"),
                                                                        "type": (None, "application/pdf"),
                                                                        "messaging_product": (None, "whatsapp")
                                                                    }
                                                                    
                                                                    response = requests.post(url, headers=headers, files=files)
                                                                    response.raise_for_status()
                                                                    return response.json()["id"]
                                                                
                                                                def send_whatsapp_pdf_by_media_id(recipient_number, media_id):
                                                                    """Send PDF via WhatsApp using media ID"""
                                                                    filename = 'Installment_Projects_Portfolio.pdf'
                                                                    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                    headers = {
                                                                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                        "Content-Type": "application/json"
                                                                    }
                                                                    
                                                                    # First send a text message
                                                                    text_payload = {
                                                                        "messaging_product": "whatsapp",
                                                                        "to": recipient_number,
                                                                        "type": "text",
                                                                        "text": {
                                                                            "body": f"📋 *INSTALLMENT PROJECTS PORTFOLIO REPORT*\n\n"
                                                                                f"📅 Report Date: {today_str}\n"
                                                                                f"🏗️ Total Projects: {summary_data['total_projects']}\n"
                                                                                f"👥 Total Clients: {pdf_data['total_clients']}\n"
                                                                                f"💰 Total Contract Value: ${summary_data['total_contract_value']:,.2f}\n"
                                                                                f"✅ Amount Paid: ${summary_data['total_paid']:,.2f}\n"
                                                                                f"⏳ Pending Amount: ${summary_data['total_pending']:,.2f}\n"
                                                                                f"🔴 Overdue Amount: ${summary_data['total_overdue']:,.2f}\n\n"
                                                                                f"📊 *CLIENT STATUS SUMMARY:*\n"
                                                                                f"• All Paid: {summary_data['clients_by_status']['all_paid']} clients\n"
                                                                                f"• Partially Paid: {summary_data['clients_by_status']['partially_paid']} clients\n"
                                                                                f"• All Pending: {summary_data['clients_by_status']['all_pending']} clients\n"
                                                                                f"• Has Overdue: {summary_data['clients_by_status']['has_overdue']} clients\n\n"
                                                                                f"📑 *REPORT INCLUDES:*\n"
                                                                                f"• Detailed project-by-project analysis\n"
                                                                                f"• Payment progress bars\n"
                                                                                f"• Installment schedules\n"
                                                                                f"• Client summary table\n"
                                                                                f"• Status categorization\n\n"
                                                                                f"Please find the complete portfolio report attached.\n"
                                                                                f"_Generated by ConnectLink System_"
                                                                        }
                                                                    }
                                                                    
                                                                    # Send text message
                                                                    response = requests.post(url, headers=headers, json=text_payload)
                                                                    response.raise_for_status()
                                                                    
                                                                    # Then send the PDF
                                                                    pdf_payload = {
                                                                        "messaging_product": "whatsapp",
                                                                        "to": recipient_number,
                                                                        "type": "document",
                                                                        "document": {
                                                                            "id": media_id,
                                                                            "filename": filename,
                                                                            "caption": f"Installment Projects Portfolio - {today_str}\n"
                                                                                    f"Projects: {summary_data['total_projects']} | "
                                                                                    f"Clients: {pdf_data['total_clients']} | "
                                                                                    f"Value: ${summary_data['total_contract_value']:,.2f}"
                                                                        }
                                                                    }
                                                                    
                                                                    response = requests.post(url, headers=headers, json=pdf_payload)
                                                                    response.raise_for_status()
                                                                    return response.json()
                                                                
                                                                # Generate PDF
                                                                pdf_bytes = generate_portfolio_pdf()
                                                                
                                                                # Get recipient phone number (you need to implement this based on your needs)
                                                                # For example, you might want to send to an administrator or get from request                                                                
                                                                # Upload and send via WhatsApp
                                                                media_id = upload_pdf_to_whatsapp(pdf_bytes, sender_id)
                                                                whatsapp_response = send_whatsapp_pdf_by_media_id(sender_id, media_id)
                                                                

                                                                sections = [
                                                                    {
                                                                        "title": "Portfolio Options",
                                                                        "rows": [
                                                                            {
                                                                                "id": "getportfolio",
                                                                                "title": "Get Master File",
                                                                                "description": "Download full portfolio"
                                                                            },
                                                                            {
                                                                                "id": "getnotes",
                                                                                "title": "Get Notes",
                                                                                "description": "Access project notes"
                                                                            },
                                                                            {
                                                                                "id": "payments_schedule",
                                                                                "title": "Get Payments Schedule",
                                                                                "description": "Access Installments schedule report"
                                                                            },
                                                                            {
                                                                                "id": "main_menu",
                                                                                "title": "Main Menu",
                                                                                "description": "Return to main menu"
                                                                            }
                                                                        ]
                                                                    }
                                                                ]

                                                                send_whatsapp_list_message(
                                                                    sender_id,
                                                                    "Kindly select a portfolio option below.",
                                                                    "ConnectLink Admin",
                                                                    sections,
                                                                    footer_text="ConnectLink Properties • Admin Panel"
                                                                )

                                                                return jsonify({
                                                                    'status': 'success',
                                                                    'message': 'Installment portfolio PDF generated and sent successfully',
                                                                    'whatsapp_response': whatsapp_response,
                                                                    'summary': {
                                                                        'total_projects': summary_data['total_projects'],
                                                                        'total_clients': pdf_data['total_clients'],
                                                                        'total_contract_value': f"${summary_data['total_contract_value']:,.2f}",
                                                                        'total_paid': f"${summary_data['total_paid']:,.2f}",
                                                                        'total_pending': f"${summary_data['total_pending']:,.2f}",
                                                                        'total_overdue': f"${summary_data['total_overdue']:,.2f}"
                                                                    }
                                                                })
                                                                
                                                            except Exception as e:
                                                                print(f"Error generating portfolio PDF: {str(e)}")
                                                                traceback.print_exc()
                                                                return jsonify({'status': 'error', 'message': f'Failed to generate portfolio: {str(e)}'}), 500

                                                        elif selected_option == "getnotes":

                                                            def generate_notes_pdf(project_id=None, client_id=None):
                                                                """Generate PDF of project notes"""
                                                                try:
                                                                    from weasyprint import HTML
                                                                    import io
                                                                    
                                                                    with get_db() as (cursor, connection):
                                                                        # Build query based on filters
                                                                        query = """
                                                                            SELECT 
                                                                                n.id,
                                                                                n.timestamp,
                                                                                n.capturer,
                                                                                n.capturerid,
                                                                                n.projectid,
                                                                                n.note,
                                                                                n.projectname,
                                                                                n.clientname,
                                                                                n.clientwanumber,
                                                                                n.clientnextofkinnumber,
                                                                                p.projectname as full_project_name,
                                                                                p.clientname as full_client_name
                                                                            FROM connectlinknotes n
                                                                            LEFT JOIN connectlinkdatabase p ON n.projectid = p.id
                                                                            WHERE 1=1
                                                                        """
                                                                        params = []
                                                                        
                                                                        if project_id:
                                                                            query += " AND n.projectid = %s"
                                                                            params.append(project_id)
                                                                        
                                                                        if client_id:
                                                                            query += " AND n.clientwanumber = %s"
                                                                            params.append(client_id)
                                                                        
                                                                        query += " ORDER BY n.timestamp DESC"
                                                                        
                                                                        cursor.execute(query, params)
                                                                        rows = cursor.fetchall()
                                                                        
                                                                        if not rows:
                                                                            return None
                                                                        
                                                                        # Get statistics
                                                                        cursor.execute("""
                                                                            SELECT 
                                                                                COUNT(*) as total_notes,
                                                                                COUNT(DISTINCT projectid) as projects_with_notes,
                                                                                COUNT(DISTINCT clientname) as clients_with_notes,
                                                                                MIN(timestamp) as earliest_note,
                                                                                MAX(timestamp) as latest_note
                                                                            FROM connectlinknotes
                                                                            WHERE 1=1
                                                                        """)
                                                                        stats = cursor.fetchone()
                                                                        
                                                                        # Generate HTML
                                                                        html_content = f"""
                                                                        <!DOCTYPE html>
                                                                        <html>
                                                                        <head>
                                                                            <meta charset="UTF-8">
                                                                            <style>
                                                                                @page {{
                                                                                    size: A4;
                                                                                    margin: 2cm;
                                                                                    @top-center {{
                                                                                        content: "PROJECT NOTES REPORT";
                                                                                        font-size: 16px;
                                                                                        font-weight: bold;
                                                                                        color: #1E2A56;
                                                                                    }}
                                                                                    @bottom-center {{
                                                                                        content: "Page " counter(page) " of " counter(pages);
                                                                                        font-size: 10px;
                                                                                        color: #666;
                                                                                    }}
                                                                                }}
                                                                                
                                                                                body {{
                                                                                    font-family: 'Helvetica', 'Arial', sans-serif;
                                                                                    line-height: 1.6;
                                                                                    color: #333;
                                                                                    margin: 0;
                                                                                    padding: 0;
                                                                                }}
                                                                                
                                                                                .header {{
                                                                                    text-align: center;
                                                                                    margin-bottom: 30px;
                                                                                    padding-bottom: 20px;
                                                                                    border-bottom: 3px solid #1E2A56;
                                                                                }}
                                                                                
                                                                                .report-title {{
                                                                                    font-size: 24px;
                                                                                    font-weight: bold;
                                                                                    color: #1E2A56;
                                                                                    margin-bottom: 5px;
                                                                                }}
                                                                                
                                                                                .report-date {{
                                                                                    font-size: 14px;
                                                                                    color: #666;
                                                                                    margin-bottom: 10px;
                                                                                }}
                                                                                
                                                                                .stats-grid {{
                                                                                    display: grid;
                                                                                    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
                                                                                    gap: 15px;
                                                                                    margin: 20px 0;
                                                                                }}
                                                                                
                                                                                .stat-card {{
                                                                                    background: #f8f9fa;
                                                                                    padding: 15px;
                                                                                    border-radius: 6px;
                                                                                    text-align: center;
                                                                                    border-left: 4px solid #1E2A56;
                                                                                }}
                                                                                
                                                                                .stat-value {{
                                                                                    font-size: 20px;
                                                                                    font-weight: bold;
                                                                                    color: #1E2A56;
                                                                                }}
                                                                                
                                                                                .stat-label {{
                                                                                    font-size: 12px;
                                                                                    color: #666;
                                                                                    margin-top: 5px;
                                                                                }}
                                                                                
                                                                                .note-card {{
                                                                                    margin-bottom: 20px;
                                                                                    padding: 15px;
                                                                                    border: 1px solid #dee2e6;
                                                                                    border-radius: 8px;
                                                                                    background: #fff;
                                                                                    page-break-inside: avoid;
                                                                                }}
                                                                                
                                                                                .note-header {{
                                                                                    display: flex;
                                                                                    justify-content: space-between;
                                                                                    margin-bottom: 10px;
                                                                                    padding-bottom: 8px;
                                                                                    border-bottom: 1px solid #eee;
                                                                                }}
                                                                                
                                                                                .note-id {{
                                                                                    font-weight: bold;
                                                                                    color: #1E2A56;
                                                                                }}
                                                                                
                                                                                .note-date {{
                                                                                    color: #666;
                                                                                    font-size: 12px;
                                                                                }}
                                                                                
                                                                                .note-project {{
                                                                                    background: #e3f2fd;
                                                                                    color: #2196f3;
                                                                                    padding: 3px 8px;
                                                                                    border-radius: 4px;
                                                                                    font-size: 12px;
                                                                                    margin-right: 8px;
                                                                                }}
                                                                                
                                                                                .note-client {{
                                                                                    background: #e8f5e9;
                                                                                    color: #27ae60;
                                                                                    padding: 3px 8px;
                                                                                    border-radius: 4px;
                                                                                    font-size: 12px;
                                                                                }}
                                                                                
                                                                                .note-capturer {{
                                                                                    color: #666;
                                                                                    font-size: 13px;
                                                                                    margin-top: 5px;
                                                                                }}
                                                                                
                                                                                .note-content {{
                                                                                    margin-top: 10px;
                                                                                    padding: 10px;
                                                                                    background: #f8f9fa;
                                                                                    border-radius: 6px;
                                                                                    line-height: 1.5;
                                                                                }}
                                                                                
                                                                                .client-info {{
                                                                                    background: #f0f7ff;
                                                                                    padding: 15px;
                                                                                    border-radius: 8px;
                                                                                    margin: 15px 0;
                                                                                    border-left: 4px solid #2196f3;
                                                                                }}
                                                                                
                                                                                .footer {{
                                                                                    margin-top: 40px;
                                                                                    padding-top: 20px;
                                                                                    border-top: 1px solid #dee2e6;
                                                                                    text-align: center;
                                                                                    font-size: 12px;
                                                                                    color: #666;
                                                                                }}
                                                                            </style>
                                                                        </head>
                                                                        <body>
                                                                            <div class="header">
                                                                                <div class="report-title">PROJECT NOTES REPORT</div>
                                                                                <div class="report-date">Generated: {datetime.now().strftime('%d %B %Y %H:%M')}</div>
                                                                                <div style="font-size: 14px; color: #666;">
                                                                                    Connectlink Properties • Notes Management System
                                                                                </div>
                                                                            </div>
                                                                            
                                                                            <div class="stats-grid">
                                                                                <div class="stat-card">
                                                                                    <div class="stat-value">{stats[0] if stats else 0}</div>
                                                                                    <div class="stat-label">Total Notes</div>
                                                                                </div>
                                                                                <div class="stat-card">
                                                                                    <div class="stat-value">{stats[1] if stats else 0}</div>
                                                                                    <div class="stat-label">Projects</div>
                                                                                </div>
                                                                                <div class="stat-card">
                                                                                    <div class="stat-value">{stats[2] if stats else 0}</div>
                                                                                    <div class="stat-label">Clients</div>
                                                                                </div>
                                                                                <div class="stat-card">
                                                                                    <div class="stat-value">
                                                                                        {stats[4].strftime('%d/%m/%Y') if stats and stats[4] else 'N/A'}
                                                                                    </div>
                                                                                    <div class="stat-label">Latest Note</div>
                                                                                </div>
                                                                            </div>
                                                                        """
                                                                        
                                                                        # Group notes by project/client
                                                                        notes_by_project = {}
                                                                        for row in rows:
                                                                            project_id = row[4]
                                                                            if project_id not in notes_by_project:
                                                                                notes_by_project[project_id] = []
                                                                            notes_by_project[project_id].append(row)
                                                                        
                                                                        # Add notes content
                                                                        for project_id, project_notes in notes_by_project.items():
                                                                            if project_notes:
                                                                                first_note = project_notes[0]
                                                                                html_content += f"""
                                                                                <div style="margin-top: 30px;">
                                                                                    <h3 style="color: #1E2A56; border-bottom: 2px solid #1E2A56; padding-bottom: 5px;">
                                                                                        📋 Project: {first_note[10] or first_note[6] or f'ID: {project_id}'}
                                                                                    </h3>
                                                                                    <div class="client-info">
                                                                                        <strong>Client:</strong> {first_note[11] or first_note[7] or 'N/A'}<br>
                                                                                        <strong>Contact:</strong> {first_note[8] or 'N/A'}<br>
                                                                                        <strong>Next of Kin:</strong> {first_note[9] or 'N/A'}
                                                                                    </div>
                                                                                """
                                                                                
                                                                                for note in project_notes:
                                                                                    html_content += f"""
                                                                                    <div class="note-card">
                                                                                        <div class="note-header">
                                                                                            <div>
                                                                                                <span class="note-id">Note #{note[0]}</span>
                                                                                                <span class="note-date">{note[1].strftime('%d %b %Y %H:%M') if note[1] else ''}</span>
                                                                                            </div>
                                                                                            <div>
                                                                                                <span class="note-project">Project: {project_id}</span>
                                                                                            </div>
                                                                                        </div>
                                                                                        
                                                                                        <div class="note-capturer">
                                                                                            📝 Added by: {note[2] or 'Unknown'} 
                                                                                            {f'(ID: {note[3]})' if note[3] else ''}
                                                                                        </div>
                                                                                        
                                                                                        <div class="note-content">
                                                                                            {note[5] or 'No content'}
                                                                                        </div>
                                                                                    </div>
                                                                                    """
                                                                                
                                                                                html_content += "</div>"
                                                                        
                                                                        html_content += """
                                                                            <div class="footer">
                                                                                <p>© Connectlink Properties • Notes Management System</p>
                                                                                <p>Generated automatically • Confidential</p>
                                                                            </div>
                                                                        </body>
                                                                        </html>
                                                                        """
                                                                        
                                                                        # Generate PDF
                                                                        pdf_bytes = HTML(string=html_content).write_pdf()
                                                                        return pdf_bytes
                                                                        
                                                                except Exception as e:
                                                                    print(f"Error generating notes PDF: {str(e)}")
                                                                    return None


                                                            def send_notes_pdf_whatsapp(recipient_number, project_id=None, client_id=None):
                                                                """Send notes PDF via WhatsApp"""
                                                                try:
                                                                    # Generate PDF
                                                                    pdf_bytes = generate_notes_pdf(project_id, client_id)
                                                                    
                                                                    if not pdf_bytes:
                                                                        # Send error message
                                                                        message = "📋 *PROJECT NOTES*\n\nNo notes found for your request."
                                                                        send_whatsapp_text(recipient_number, message)
                                                                        return {'status': 'error', 'message': 'No notes found'}
                                                                    
                                                                    # Upload to WhatsApp
                                                                    filename = f"project_notes_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
                                                                    media_id = upload_pdf_to_whatsapp(pdf_bytes, filename)
                                                                    
                                                                    # Send text message first
                                                                    message = f"""
                                                                        📋 *PROJECT NOTES REPORT*

                                                                        Your notes report has been generated successfully!

                                                                        📄 *File:* {filename}
                                                                        📅 *Generated:* {datetime.now().strftime('%d %B %Y %H:%M')}
                                                                        🏢 *System:* Connectlink Properties Notes

                                                                        Please find the detailed notes report attached.

                                                                        _This document contains project communications and notes._
                                                                                """

        
                                                                    send_whatsapp_text(recipient_number, message)
                                                                    
                                                                    # Send PDF
                                                                    doc_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                    headers = {
                                                                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                        "Content-Type": "application/json"
                                                                    }
                                                                    
                                                                    doc_payload = {
                                                                        "messaging_product": "whatsapp",
                                                                        "to": recipient_number,
                                                                        "type": "document",
                                                                        "document": {
                                                                            "id": media_id,
                                                                            "filename": filename,
                                                                            "caption": f"Project Notes Report - {datetime.now().strftime('%d %B %Y')}"
                                                                        }
                                                                    }
                                                                    
                                                                    response = requests.post(doc_url, headers=headers, json=doc_payload)
                                                                    response.raise_for_status()
                                                                    
                                                                    return {
                                                                        'status': 'success',
                                                                        'message': 'Notes PDF sent successfully',
                                                                        'filename': filename
                                                                    }
                                                                    
                                                                except Exception as e:
                                                                    print(f"Error sending notes PDF: {str(e)}")
                                                                    return {'status': 'error', 'message': f'Failed to send: {str(e)}'}


                                                            # Helper functions
                                                            def send_whatsapp_text(recipient_number, message):
                                                                """Send text message via WhatsApp"""
                                                                try:
                                                                    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                    headers = {
                                                                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                        "Content-Type": "application/json"
                                                                    }
                                                                    
                                                                    payload = {
                                                                        "messaging_product": "whatsapp",
                                                                        "to": recipient_number,
                                                                        "type": "text",
                                                                        "text": {"body": message}
                                                                    }
                                                                    
                                                                    requests.post(url, headers=headers, json=payload)
                                                                except Exception as e:
                                                                    print(f"Error sending text: {e}")


                                                            def upload_pdf_to_whatsapp(pdf_bytes, filename):

                                                                import io
                                                                """Upload PDF to WhatsApp and return media ID"""
                                                                url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
                                                                headers = {
                                                                    "Authorization": f"Bearer {ACCESS_TOKEN}"
                                                                }
                                                                
                                                                files = {
                                                                    "file": (filename, io.BytesIO(pdf_bytes), "application/pdf"),
                                                                    "type": (None, "application/pdf"),
                                                                    "messaging_product": (None, "whatsapp")
                                                                }
                                                                
                                                                response = requests.post(url, headers=headers, files=files)
                                                                response.raise_for_status()
                                                                return response.json()["id"]


                                                            # Handle the "getnotes" option
                                                            result = send_notes_pdf_whatsapp(sender_id)

                                                            sections = [
                                                                {
                                                                    "title": "Portfolio Options",
                                                                    "rows": [
                                                                        {
                                                                            "id": "getportfolio",
                                                                            "title": "Get Master File",
                                                                            "description": "Download full portfolio"
                                                                        },
                                                                        {
                                                                            "id": "getnotes",
                                                                            "title": "Get Notes",
                                                                            "description": "Access project notes"
                                                                        },
                                                                        {
                                                                            "id": "payments_schedule",
                                                                            "title": "Get Payments Schedule",
                                                                            "description": "Access Installments schedule report"
                                                                        },
                                                                        {
                                                                            "id": "main_menu",
                                                                            "title": "Main Menu",
                                                                            "description": "Return to main menu"
                                                                        }
                                                                    ]
                                                                }
                                                            ]

                                                            send_whatsapp_list_message(
                                                                sender_id,
                                                                "Kindly select a portfolio option below.",
                                                                "ConnectLink Admin",
                                                                sections,
                                                                footer_text="ConnectLink Properties • Admin Panel"
                                                            )
                                                        
                                                            return jsonify(result)


                                                        elif selected_option == "payments_schedule":

                                                            """Export installments schedule as PDF with cross-tab table ONLY"""
                                                            try:
                                                                
                                                                # Get today's date for filtering
                                                                today = date.today()
                                                                today_str = today.strftime('%d %B %Y')
                                                                
                                                                with get_db() as (cursor, connection):
                                                                    # Query for installment projects with pending payments
                                                                    query = """
                                                                    SELECT 
                                                                        id,
                                                                        clientname,
                                                                        projectname,
                                                                        projectstartdate,
                                                                        projectadministratorname,
                                                                        totalcontractamount,
                                                                        depositorbullet,
                                                                        clientwanumber,
                                                                        momid,
                                                                        monthstopay,
                                                                        installment1amount, installment1duedate, installment1date,
                                                                        installment2amount, installment2duedate, installment2date,
                                                                        installment3amount, installment3duedate, installment3date,
                                                                        installment4amount, installment4duedate, installment4date,
                                                                        installment5amount, installment5duedate, installment5date,
                                                                        installment6amount, installment6duedate, installment6date
                                                                    FROM connectlinkdatabase 
                                                                    WHERE paymentmethod = 'Installments'
                                                                    AND (
                                                                        (installment1amount > 0 AND installment1date IS NULL) OR
                                                                        (installment2amount > 0 AND installment2date IS NULL) OR
                                                                        (installment3amount > 0 AND installment3date IS NULL) OR
                                                                        (installment4amount > 0 AND installment4date IS NULL) OR
                                                                        (installment5amount > 0 AND installment5date IS NULL) OR
                                                                        (installment6amount > 0 AND installment6date IS NULL)
                                                                    )
                                                                    ORDER BY 
                                                                        DATE_TRUNC('month', projectstartdate) DESC,
                                                                        projectstartdate ASC,
                                                                        momid ASC;
                                                                    """
                                                                    
                                                                    cursor.execute(query)
                                                                    rows = cursor.fetchall()
                                                                    
                                                                    if not rows:
                                                                        return jsonify({'status': 'error', 'message': 'No pending installments found'}), 404
                                                                    
                                                                    # Get column names
                                                                    colnames = [desc[0] for desc in cursor.description]
                                                                    
                                                                # Convert to DataFrame
                                                                df = pd.DataFrame(rows, columns=colnames)
                                                                
                                                                # ================================================
                                                                # PROCESS DATA FOR CROSS-TAB TABLE ONLY
                                                                # ================================================
                                                                monthly_data = []
                                                                summary_data = {
                                                                    'total_projects': len(df),
                                                                    'total_pending': 0.0,
                                                                    'total_overdue': 0.0,
                                                                    'total_future': 0.0,
                                                                    'monthly_totals': {}
                                                                }
                                                                
                                                                for _, row in df.iterrows():
                                                                    # Check installments 1-6
                                                                    for i in range(1, 7):
                                                                        amount = row.get(f'installment{i}amount')
                                                                        due_date = row.get(f'installment{i}duedate')
                                                                        payment_date = row.get(f'installment{i}date')
                                                                        
                                                                        if amount and float(amount) > 0 and pd.isna(payment_date):  # Pending only
                                                                            if pd.notna(due_date):
                                                                                due_month = due_date.strftime('%Y-%m')
                                                                                due_month_display = due_date.strftime('%Y-%m')  # Format: 2025-01
                                                                                
                                                                                # Check if overdue
                                                                                is_overdue = due_date < today
                                                                                
                                                                                monthly_data.append({
                                                                                    'clientname': str(row.get('clientname', '')).strip(),
                                                                                    'projectname': str(row.get('projectname', '')),
                                                                                    'due_date': due_date,
                                                                                    'due_month': due_month,
                                                                                    'due_month_display': due_month_display,
                                                                                    'amount': float(amount),
                                                                                    'installment_num': i,
                                                                                    'is_overdue': is_overdue
                                                                                })
                                                                                
                                                                                # Update summary
                                                                                summary_data['total_pending'] += float(amount)
                                                                                if is_overdue:
                                                                                    summary_data['total_overdue'] += float(amount)
                                                                                else:
                                                                                    summary_data['total_future'] += float(amount)
                                                                                
                                                                                # Add to monthly totals
                                                                                if due_month not in summary_data['monthly_totals']:
                                                                                    summary_data['monthly_totals'][due_month] = {
                                                                                        'month_display': due_month_display,
                                                                                        'total': 0.0,
                                                                                        'overdue': 0.0,
                                                                                        'future': 0.0
                                                                                    }
                                                                                
                                                                                summary_data['monthly_totals'][due_month]['total'] += float(amount)
                                                                                if is_overdue:
                                                                                    summary_data['monthly_totals'][due_month]['overdue'] += float(amount)
                                                                                else:
                                                                                    summary_data['monthly_totals'][due_month]['future'] += float(amount)
                                                                
                                                                if not monthly_data:
                                                                    return jsonify({'status': 'error', 'message': 'No pending installments found'}), 404
                                                                
                                                                # Create DataFrame from monthly data
                                                                monthly_df = pd.DataFrame(monthly_data)
                                                                
                                                                # Debug: Check client names
                                                                print(f"Total records: {len(monthly_df)}")
                                                                print(f"Unique clients: {monthly_df['clientname'].nunique()}")
                                                                print(f"Sample client names: {monthly_df['clientname'].head().tolist()}")
                                                                
                                                                # Create pivot table: Client Name as rows, Due Months as columns
                                                                pivot_table = monthly_df.pivot_table(
                                                                    index='clientname',
                                                                    columns='due_month',
                                                                    values='amount',
                                                                    aggfunc='sum',
                                                                    fill_value=0
                                                                ).reset_index()
                                                                
                                                                # Sort months chronologically
                                                                month_columns = [col for col in pivot_table.columns if col != 'clientname']
                                                                month_columns_sorted = sorted(month_columns, key=lambda x: x)
                                                                
                                                                # Format month column names to "YYYY-MM" format
                                                                month_columns_formatted = []
                                                                for month in month_columns_sorted:
                                                                    try:
                                                                        formatted = f"{month}"
                                                                        month_columns_formatted.append(formatted)
                                                                    except:
                                                                        month_columns_formatted.append(month)
                                                                
                                                                pivot_table = pivot_table[['clientname'] + month_columns_sorted]
                                                                
                                                                # Rename columns to formatted month names
                                                                column_mapping = {old: new for old, new in zip(month_columns_sorted, month_columns_formatted)}
                                                                pivot_table = pivot_table.rename(columns=column_mapping)
                                                                
                                                                # Debug: Check pivot table
                                                                print(f"Pivot table shape: {pivot_table.shape}")
                                                                print(f"Pivot table columns: {pivot_table.columns.tolist()}")
                                                                print(f"First few client names in pivot: {pivot_table['clientname'].head().tolist()}")
                                                                
                                                                # Add total column for each client
                                                                pivot_table['Total Pending'] = pivot_table[month_columns_formatted].sum(axis=1)
                                                                
                                                                # Sort by client name
                                                                pivot_table = pivot_table.sort_values('clientname')
                                                                
                                                                # Add TOTAL ROW at the bottom
                                                                total_row = {'clientname': 'TOTAL'}
                                                                for col in month_columns_formatted:
                                                                    total_row[col] = pivot_table[col].sum()
                                                                total_row['Total Pending'] = pivot_table['Total Pending'].sum()
                                                                
                                                                # Append total row
                                                                cross_tab_data = pd.concat([pivot_table, pd.DataFrame([total_row])], ignore_index=True)
                                                                
                                                                # Prepare cross-tab data for PDF template
                                                                cross_tab_rows = []
                                                                for _, row in cross_tab_data.iterrows():
                                                                    row_data = {}
                                                                    columns = ['clientname'] + month_columns_formatted + ['Total Pending']
                                                                    for col in columns:
                                                                        value = row[col] if col in row else ''
                                                                        
                                                                        # Format currency values
                                                                        if col != 'clientname':
                                                                            if isinstance(value, (int, float)):
                                                                                if value == 0:
                                                                                    row_data[col] = ""
                                                                                else:
                                                                                    row_data[col] = f"${value:,.2f}"
                                                                            else:
                                                                                row_data[col] = value
                                                                        else:
                                                                            # Ensure client name is properly displayed
                                                                            row_data[col] = str(value).strip() if pd.notna(value) else ''
                                                                    
                                                                    # Mark TOTAL row
                                                                    if str(row['clientname']).strip() == 'TOTAL':
                                                                        row_data['is_total'] = True
                                                                    else:
                                                                        row_data['is_total'] = False
                                                                    
                                                                    cross_tab_rows.append(row_data)
                                                                
                                                                # Prepare monthly summary table data
                                                                monthly_summary_rows = []
                                                                # Sort monthly totals chronologically
                                                                sorted_months = sorted(summary_data['monthly_totals'].items(), key=lambda x: x[0])
                                                                for month_key, month_data in sorted_months:
                                                                    monthly_summary_rows.append({
                                                                        'month': month_data['month_display'],
                                                                        'total': f"${month_data['total']:,.2f}",
                                                                        'overdue': f"${month_data['overdue']:,.2f}",
                                                                        'future': f"${month_data['future']:,.2f}"
                                                                    })
                                                                
                                                                # Add total row to monthly summary
                                                                monthly_summary_rows.append({
                                                                    'month': 'TOTAL',
                                                                    'total': f"${summary_data['total_pending']:,.2f}",
                                                                    'overdue': f"${summary_data['total_overdue']:,.2f}",
                                                                    'future': f"${summary_data['total_future']:,.2f}"
                                                                })
                                                                
                                                                # Prepare final PDF data
                                                                pdf_data = {
                                                                    'report_date': today_str,
                                                                    'generated_on': datetime.now().strftime('%d %B %Y %H:%M:%S'),
                                                                    'company_name': 'ConnectLink Properties',  # Replace with actual
                                                                    'company_logo': '',  # Add logo if available
                                                                    'report_title': 'INSTALLMENT PAYMENTS SCHEDULE - CROSS TAB VIEW',
                                                                    'summary': summary_data,
                                                                    'cross_tab_columns': ['Client Name'] + month_columns_formatted + ['Total Pending'],
                                                                    'cross_tab_rows': cross_tab_rows,
                                                                    'monthly_summary_rows': monthly_summary_rows,
                                                                    'total_clients': len(pivot_table) - 1,  # Excluding TOTAL row
                                                                    'total_months': len(month_columns_formatted)
                                                                }
                                                                
                                                                # Generate PDF
                                                                def generate_cross_tab_pdf():

                                                                    from weasyprint import HTML
                                                                    import io

                                                                    """Generate PDF with cross-tab table ONLY"""
                                                                    html_template = """
                                                                    <!DOCTYPE html>
                                                                    <html>
                                                                    <head>
                                                                        <meta charset="UTF-8">
                                                                        <style>
                                                                            @page {
                                                                                size: A4 landscape;
                                                                                margin: 1.5cm;
                                                                                @top-center {
                                                                                    content: "INSTALLMENT PAYMENTS SCHEDULE - CROSS TAB VIEW";
                                                                                    font-size: 16px;
                                                                                    font-weight: bold;
                                                                                    color: #2c3e50;
                                                                                }
                                                                                @bottom-center {
                                                                                    content: "Page " counter(page) " of " counter(pages);
                                                                                    font-size: 10px;
                                                                                    color: #7f8c8d;
                                                                                }
                                                                            }
                                                                            
                                                                            body {
                                                                                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                                                                line-height: 1.6;
                                                                                color: #333;
                                                                                margin: 0;
                                                                                padding: 0;
                                                                            }
                                                                            
                                                                            .header {
                                                                                text-align: center;
                                                                                margin-bottom: 20px;
                                                                                padding-bottom: 15px;
                                                                                border-bottom: 3px solid #3498db;
                                                                            }
                                                                            
                                                                            .company-name {
                                                                                font-size: 22px;
                                                                                font-weight: bold;
                                                                                color: #2c3e50;
                                                                                margin-bottom: 5px;
                                                                            }
                                                                            
                                                                            .report-title {
                                                                                font-size: 18px;
                                                                                color: #3498db;
                                                                                margin-bottom: 8px;
                                                                                text-transform: uppercase;
                                                                                letter-spacing: 1px;
                                                                            }
                                                                            
                                                                            .report-date {
                                                                                font-size: 13px;
                                                                                color: #7f8c8d;
                                                                                margin-bottom: 15px;
                                                                            }
                                                                            
                                                                            .summary-section {
                                                                                background: #f8f9fa;
                                                                                padding: 15px;
                                                                                border-radius: 6px;
                                                                                margin-bottom: 20px;
                                                                                border-left: 4px solid #3498db;
                                                                            }
                                                                            
                                                                            .summary-grid {
                                                                                display: grid;
                                                                                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                                                                                gap: 12px;
                                                                                margin-top: 12px;
                                                                            }
                                                                            
                                                                            .summary-item {
                                                                                background: white;
                                                                                padding: 12px;
                                                                                border-radius: 5px;
                                                                                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
                                                                            }
                                                                            
                                                                            .summary-label {
                                                                                font-size: 11px;
                                                                                color: #7f8c8d;
                                                                                text-transform: uppercase;
                                                                                letter-spacing: 0.5px;
                                                                                margin-bottom: 4px;
                                                                            }
                                                                            
                                                                            .summary-value {
                                                                                font-size: 18px;
                                                                                font-weight: bold;
                                                                                color: #2c3e50;
                                                                            }
                                                                            
                                                                            .summary-value.red {
                                                                                color: #e74c3c;
                                                                            }
                                                                            
                                                                            .summary-value.green {
                                                                                color: #27ae60;
                                                                            }
                                                                            
                                                                            .summary-value.blue {
                                                                                color: #3498db;
                                                                            }
                                                                            
                                                                            .crosstab-table {
                                                                                width: 100%;
                                                                                border-collapse: collapse;
                                                                                margin-top: 20px;
                                                                                font-size: 11px;
                                                                                page-break-inside: avoid;
                                                                            }
                                                                            
                                                                            .crosstab-table th {
                                                                                background: #2c3e50;
                                                                                color: white;
                                                                                padding: 10px 8px;
                                                                                text-align: center;
                                                                                font-weight: 600;
                                                                                text-transform: uppercase;
                                                                                border: 1px solid #34495e;
                                                                                vertical-align: middle;
                                                                            }
                                                                            
                                                                            .crosstab-table td {
                                                                                padding: 8px;
                                                                                border: 1px solid #dee2e6;
                                                                                text-align: right;
                                                                                vertical-align: middle;
                                                                            }
                                                                            
                                                                            .crosstab-table td:first-child {
                                                                                text-align: left;
                                                                                font-weight: 500;
                                                                                background: #f8f9fa;
                                                                                position: sticky;
                                                                                left: 0;
                                                                                z-index: 10;
                                                                                min-width: 150px;
                                                                            }
                                                                            
                                                                            .crosstab-table tr:nth-child(even):not(.total-row) {
                                                                                background: #f8f9fa;
                                                                            }
                                                                            
                                                                            .crosstab-table tr:hover:not(.total-row) {
                                                                                background: #e8f4f8;
                                                                            }
                                                                            
                                                                            .total-row {
                                                                                background: #2c3e50 !important;
                                                                                color: white;
                                                                                font-weight: bold;
                                                                                font-size: 12px;
                                                                            }
                                                                            
                                                                            .total-row td {
                                                                                border-top: 2px solid #1a252f;
                                                                                border-bottom: 2px solid #1a252f;
                                                                            }
                                                                            
                                                                            .currency {
                                                                                font-family: 'Courier New', monospace;
                                                                                font-size: 10.5px;
                                                                            }
                                                                            
                                                                            .footer {
                                                                                margin-top: 30px;
                                                                                padding-top: 15px;
                                                                                border-top: 1px solid #ecf0f1;
                                                                                text-align: center;
                                                                                font-size: 10px;
                                                                                color: #7f8c8d;
                                                                            }
                                                                            
                                                                            .note {
                                                                                font-size: 10px;
                                                                                color: #7f8c8d;
                                                                                font-style: italic;
                                                                                margin-top: 3px;
                                                                            }
                                                                            
                                                                            h2 {
                                                                                color: #2c3e50;
                                                                                border-bottom: 2px solid #3498db;
                                                                                padding-bottom: 6px;
                                                                                margin-top: 25px;
                                                                                font-size: 16px;
                                                                            }
                                                                            
                                                                            h3 {
                                                                                color: #34495e;
                                                                                margin: 15px 0 10px 0;
                                                                                font-size: 14px;
                                                                            }
                                                                            
                                                                            /* Monthly Summary Table */
                                                                            .monthly-summary-table {
                                                                                width: 100%;
                                                                                border-collapse: collapse;
                                                                                margin-top: 25px;
                                                                                font-size: 12px;
                                                                            }
                                                                            
                                                                            .monthly-summary-table th {
                                                                                background: #3498db;
                                                                                color: white;
                                                                                padding: 12px 10px;
                                                                                text-align: center;
                                                                                font-weight: 600;
                                                                                border: 1px solid #2980b9;
                                                                            }
                                                                            
                                                                            .monthly-summary-table td {
                                                                                padding: 10px;
                                                                                border: 1px solid #dee2e6;
                                                                                text-align: center;
                                                                            }
                                                                            
                                                                            .monthly-summary-table tr:nth-child(even) {
                                                                                background: #f8f9fa;
                                                                            }
                                                                            
                                                                            .monthly-summary-table .total-row {
                                                                                background: #2c3e50 !important;
                                                                                color: white;
                                                                                font-weight: bold;
                                                                            }
                                                                            
                                                                            /* Section styling */
                                                                            .section-container {
                                                                                margin-top: 30px;
                                                                                padding: 20px;
                                                                                background: #f8f9fa;
                                                                                border-radius: 8px;
                                                                                border-left: 4px solid #3498db;
                                                                            }
                                                                            
                                                                            .section-title {
                                                                                color: #2c3e50;
                                                                                margin-bottom: 15px;
                                                                                font-size: 16px;
                                                                                font-weight: 600;
                                                                            }
                                                                            
                                                                            /* Zero value styling */
                                                                            .zero-value {
                                                                                color: #bdc3c7;
                                                                            }
                                                                        </style>
                                                                    </head>
                                                                    <body>
                                                                        <div class="header">
                                                                            <div class="company-name">{{ company_name }}</div>
                                                                            <div class="report-title">{{ report_title }}</div>
                                                                            <div class="report-date">Generated on: {{ generated_on }}</div>
                                                                        </div>
                                                                        
                                                                        <div class="summary-section">
                                                                            <h3>EXECUTIVE SUMMARY</h3>
                                                                            <div class="summary-grid">
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Total Projects</div>
                                                                                    <div class="summary-value blue">{{ summary.total_projects }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Total Clients</div>
                                                                                    <div class="summary-value blue">{{ total_clients }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Total Pending</div>
                                                                                    <div class="summary-value">${{ "%.2f"|format(summary.total_pending) }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Overdue Amount</div>
                                                                                    <div class="summary-value red">${{ "%.2f"|format(summary.total_overdue) }}</div>
                                                                                </div>
                                                                                <div class="summary-item">
                                                                                    <div class="summary-label">Future Amount</div>
                                                                                    <div class="summary-value green">${{ "%.2f"|format(summary.total_future) }}</div>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                        
                                                                        <h2>PAYMENT SCHEDULE - CROSS TAB VIEW</h2>
                                                                        <p class="note">All amounts in USD. Blank cells indicate no payment due for that month.</p>
                                                                        
                                                                        <table class="crosstab-table">
                                                                            <thead>
                                                                                <tr>
                                                                                    {% for column in cross_tab_columns %}
                                                                                    <th{% if column == 'Client Name' %} style="text-align: left; min-width: 150px;"{% endif %}>
                                                                                        {{ column }}
                                                                                    </th>
                                                                                    {% endfor %}
                                                                                </tr>
                                                                            </thead>
                                                                            <tbody>
                                                                                {% for row in cross_tab_rows %}
                                                                                <tr class="{% if row.is_total %}total-row{% endif %}">
                                                                                    {% for column in cross_tab_columns %}
                                                                                    <td class="{% if column != 'Client Name' %}currency{% endif %} {% if row[column] == '' %}zero-value{% endif %}">
                                                                                        {{ row[column] }}
                                                                                    </td>
                                                                                    {% endfor %}
                                                                                </tr>
                                                                                {% endfor %}
                                                                            </tbody>
                                                                        </table>
                                                                        
                                                                        <div class="section-container">
                                                                            <div class="section-title">MONTHLY SUMMARY TABLE</div>
                                                                            
                                                                            <table class="monthly-summary-table">
                                                                                <thead>
                                                                                    <tr>
                                                                                        <th>Month</th>
                                                                                        <th>Total Pending</th>
                                                                                        <th>Overdue Amount</th>
                                                                                        <th>Future Amount</th>
                                                                                    </tr>
                                                                                </thead>
                                                                                <tbody>
                                                                                    {% for month in monthly_summary_rows %}
                                                                                    <tr class="{% if month.month == 'TOTAL' %}total-row{% endif %}">
                                                                                        <td style="text-align: left; font-weight: {% if month.month == 'TOTAL' %}bold{% else %}500{% endif %};">
                                                                                            {{ month.month }}
                                                                                        </td>
                                                                                        <td class="currency">{{ month.total }}</td>
                                                                                        <td class="currency">{{ month.overdue }}</td>
                                                                                        <td class="currency">{{ month.future }}</td>
                                                                                    </tr>
                                                                                    {% endfor %}
                                                                                </tbody>
                                                                            </table>
                                                                        </div>
                                                                        
                                                                        <div class="footer">
                                                                            <p>Generated by ConnectLink System • {{ report_date }}</p>
                                                                            <p class="note">This report shows a cross-tab summary of pending installment payments by client and month.</p>
                                                                        </div>
                                                                    </body>
                                                                    </html>
                                                                    """
                                                                    
                                                                    # Render template with data
                                                                    from jinja2 import Template
                                                                    template = Template(html_template)
                                                                    html_content = template.render(**pdf_data)
                                                                    
                                                                    # Generate PDF
                                                                    pdf_bytes = HTML(string=html_content).write_pdf()
                                                                    return pdf_bytes
                                                                
                                                                def upload_pdf_to_whatsapp(pdf_bytes, phone_number):

                                                                    import io
                                                                    """Upload PDF to WhatsApp Cloud API"""
                                                                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                                                    filename = f'installment_schedule_crosstab_{timestamp}.pdf'
                                                                    
                                                                    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
                                                                    headers = {
                                                                        "Authorization": f"Bearer {ACCESS_TOKEN}"
                                                                    }
                                                                    
                                                                    files = {
                                                                        "file": (filename, io.BytesIO(pdf_bytes), "application/pdf"),
                                                                        "type": (None, "application/pdf"),
                                                                        "messaging_product": (None, "whatsapp")
                                                                    }
                                                                    
                                                                    response = requests.post(url, headers=headers, files=files)
                                                                    response.raise_for_status()
                                                                    return response.json()["id"]
                                                                
                                                                def send_whatsapp_pdf_by_media_id(recipient_number, media_id):
                                                                    """Send PDF via WhatsApp using media ID"""
                                                                    filename = 'Installment_Payment_Schedule_CrossTab.pdf'
                                                                    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                    headers = {
                                                                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                        "Content-Type": "application/json"
                                                                    }
                                                                    
                                                                    # Format month list for WhatsApp message
                                                                    month_list = ', '.join(month_columns_formatted[:5]) + ('...' if len(month_columns_formatted) > 5 else '')
                                                                    
                                                                    # First send a text message
                                                                    text_payload = {
                                                                        "messaging_product": "whatsapp",
                                                                        "to": recipient_number,
                                                                        "type": "text",
                                                                        "text": {
                                                                            "body": f"📊 *INSTALLMENT PAYMENTS SCHEDULE - CROSS TAB VIEW*\n\n"
                                                                                f"📅 Report Date: {today_str}\n"
                                                                                f"🏗️ Total Projects: {summary_data['total_projects']}\n"
                                                                                f"👥 Total Clients: {pdf_data['total_clients']}\n"
                                                                                f"💰 Total Pending: ${summary_data['total_pending']:,.2f}\n"
                                                                                f"🔴 Overdue Amount: ${summary_data['total_overdue']:,.2f}\n"
                                                                                f"🟢 Future Amount: ${summary_data['total_future']:,.2f}\n"
                                                                                f"📈 Months Covered: {len(month_columns_formatted)} ({month_list})\n\n"
                                                                                f"📋 *REPORT FEATURES:*\n"
                                                                                f"• Cross-tab view (Clients vs Months)\n"
                                                                                f"• Monthly payment breakdown\n"
                                                                                f"• Total pending per client\n"
                                                                                f"• Monthly summary table\n"
                                                                                f"• Grand total summary\n\n"
                                                                                f"Please find the cross-tab schedule attached.\n"
                                                                                f"_Generated by ConnectLink System_"
                                                                        }
                                                                    }
                                                                    
                                                                    # Send text message
                                                                    response = requests.post(url, headers=headers, json=text_payload)
                                                                    response.raise_for_status()
                                                                    
                                                                    # Then send the PDF
                                                                    pdf_payload = {
                                                                        "messaging_product": "whatsapp",
                                                                        "to": recipient_number,
                                                                        "type": "document",
                                                                        "document": {
                                                                            "id": media_id,
                                                                            "filename": filename,
                                                                            "caption": f"Cross-Tab Installment Schedule - {today_str}\n"
                                                                                    f"Clients: {pdf_data['total_clients']} | "
                                                                                    f"Total: ${summary_data['total_pending']:,.2f} | "
                                                                                    f"Months: {len(month_columns_formatted)}"
                                                                        }
                                                                    }
                                                                    
                                                                    response = requests.post(url, headers=headers, json=pdf_payload)
                                                                    response.raise_for_status()
                                                                    return response.json()
                                                                
                                                                # Generate PDF
                                                                pdf_bytes = generate_cross_tab_pdf()
                                                                
                                                                # Get recipient phone number (you need to implement this based on your needs)
                                                                # For example, you might want to send to an administrator or get from request
                                                                
                                                                # Upload and send via WhatsApp
                                                                media_id = upload_pdf_to_whatsapp(pdf_bytes, sender_id)
                                                                whatsapp_response = send_whatsapp_pdf_by_media_id(sender_id, media_id)
   
                                                                sections = [
                                                                    {
                                                                        "title": "Portfolio Options",
                                                                        "rows": [
                                                                            {
                                                                                "id": "getportfolio",
                                                                                "title": "Get Master File",
                                                                                "description": "Download full portfolio"
                                                                            },
                                                                            {
                                                                                "id": "getnotes",
                                                                                "title": "Get Notes",
                                                                                "description": "Access project notes"
                                                                            },
                                                                            {
                                                                                "id": "payments_schedule",
                                                                                "title": "Get Payments Schedule",
                                                                                "description": "Access Installments schedule report"
                                                                            },
                                                                            {
                                                                                "id": "main_menu",
                                                                                "title": "Main Menu",
                                                                                "description": "Return to main menu"
                                                                            }
                                                                        ]
                                                                    }
                                                                ]

                                                                send_whatsapp_list_message(
                                                                    sender_id,
                                                                    "Kindly select a portfolio option below.",
                                                                    "ConnectLink Admin",
                                                                    sections,
                                                                    footer_text="ConnectLink Properties • Admin Panel"
                                                                )

                                                                return jsonify({
                                                                    'status': 'success',
                                                                    'message': 'Cross-tab installment schedule PDF generated and sent successfully',
                                                                    'whatsapp_response': whatsapp_response,
                                                                    'summary': {
                                                                        'total_projects': summary_data['total_projects'],
                                                                        'total_clients': pdf_data['total_clients'],
                                                                        'total_pending': f"${summary_data['total_pending']:,.2f}",
                                                                        'total_overdue': f"${summary_data['total_overdue']:,.2f}",
                                                                        'total_future': f"${summary_data['total_future']:,.2f}",
                                                                        'months_covered': month_columns_formatted
                                                                    }
                                                                })
                                                                 

                                                                continue

                                                            except Exception as e:
                                                                print(f"Error generating PDF: {str(e)}")
                                                                traceback.print_exc()
                                                                return jsonify({'status': 'error', 'message': f'Failed to generate schedule: {str(e)}'}), 500
                                

                                                        elif button_id == "projects":

                                                            sections = [
                                                                {
                                                                    "title": "Portfolio Options",
                                                                    "rows": [
                                                                        {
                                                                            "id": "getportfolio",
                                                                            "title": "Get Master File",
                                                                            "description": "Download full portfolio"
                                                                        },
                                                                        {
                                                                            "id": "getnotes",
                                                                            "title": "Get Notes",
                                                                            "description": "Access project notes"
                                                                        },
                                                                        {
                                                                            "id": "payments_schedule",
                                                                            "title": "Get Payments Schedule",
                                                                            "description": "Access Installments schedule report"
                                                                        },
                                                                        {
                                                                            "id": "main_menu",
                                                                            "title": "Main Menu",
                                                                            "description": "Return to main menu"
                                                                        }
                                                                    ]
                                                                }
                                                            ]

                                                            send_whatsapp_list_message(
                                                                sender_id,
                                                                "Kindly select a portfolio option below.",
                                                                "ConnectLink Admin",
                                                                sections,
                                                                footer_text="ConnectLink Properties • Admin Panel"
                                                            )

                                                            continue


                                                        elif button_id == "enquiries":

                                                            """Generate and send enquiries PDF via WhatsApp"""
                                                            try:
                                                                with get_db() as (cursor, connection):
                                                                    # Get all enquiries with username
                                                                    cursor.execute("""
                                                                        SELECT 
                                                                            id,
                                                                            timestamp,
                                                                            clientwhatsapp,
                                                                            enqcategory,
                                                                            enq,
                                                                            plan IS NOT NULL as has_plan,
                                                                            status,
                                                                            username
                                                                        FROM connectlinkenquiries 
                                                                        ORDER BY timestamp DESC
                                                                    """)
                                                                    rows = cursor.fetchall()
                                                                    
                                                                    # Get column names
                                                                    colnames = [desc[0] for desc in cursor.description]
                                                                    
                                                                    # Convert to list of dictionaries
                                                                    enquiries = []
                                                                    for row in rows:
                                                                        enquiry_dict = {}
                                                                        for i, col in enumerate(colnames):
                                                                            enquiry_dict[col] = row[i]
                                                                        enquiries.append(enquiry_dict)
                                                                    
                                                                    # Get statistics
                                                                    cursor.execute("""
                                                                        SELECT 
                                                                            COUNT(*) as total,
                                                                            COUNT(DISTINCT clientwhatsapp) as unique_clients,
                                                                            SUM(CASE WHEN plan IS NOT NULL THEN 1 ELSE 0 END) as with_attachments,
                                                                            SUM(CASE WHEN status = 'pending' OR status IS NULL THEN 1 ELSE 0 END) as pending_count,
                                                                            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_count,
                                                                            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
                                                                            COUNT(DISTINCT username) as unique_users
                                                                        FROM connectlinkenquiries;
                                                                    """)
                                                                    stats = cursor.fetchone()
                                                                    
                                                                    # Generate HTML for PDF
                                                                    html_content = f"""
                                                                    <!DOCTYPE html>
                                                                    <html>
                                                                    <head>
                                                                        <meta charset="UTF-8">
                                                                        <style>
                                                                            @page {{
                                                                                size: A4 landscape;
                                                                                margin: 1.5cm;
                                                                                @top-center {{
                                                                                    content: "ENQUIRIES MANAGEMENT REPORT";
                                                                                    font-size: 16px;
                                                                                    font-weight: bold;
                                                                                    color: #1E2A56;
                                                                                }}
                                                                                @bottom-center {{
                                                                                    content: "Connectlink Properties • Page " counter(page) " of " counter(pages);
                                                                                    font-size: 10px;
                                                                                    color: #666;
                                                                                }}
                                                                            }}
                                                                            
                                                                            body {{
                                                                                font-family: 'Helvetica', 'Arial', sans-serif;
                                                                                line-height: 1.4;
                                                                                color: #333;
                                                                                margin: 0;
                                                                                padding: 0;
                                                                            }}
                                                                            
                                                                            .header {{
                                                                                text-align: center;
                                                                                margin-bottom: 25px;
                                                                                padding-bottom: 15px;
                                                                                border-bottom: 3px solid #1E2A56;
                                                                            }}
                                                                            
                                                                            .report-title {{
                                                                                font-size: 22px;
                                                                                font-weight: bold;
                                                                                color: #1E2A56;
                                                                                margin-bottom: 5px;
                                                                            }}
                                                                            
                                                                            .report-date {{
                                                                                font-size: 14px;
                                                                                color: #666;
                                                                            }}
                                                                            
                                                                            .stats-grid {{
                                                                                display: grid;
                                                                                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                                                                                gap: 10px;
                                                                                margin: 20px 0;
                                                                            }}
                                                                            
                                                                            .stat-card {{
                                                                                background: #f8f9fa;
                                                                                padding: 12px;
                                                                                border-radius: 6px;
                                                                                text-align: center;
                                                                                border-left: 4px solid #1E2A56;
                                                                            }}
                                                                            
                                                                            .stat-value {{
                                                                                font-size: 18px;
                                                                                font-weight: bold;
                                                                                color: #1E2A56;
                                                                            }}
                                                                            
                                                                            .stat-label {{
                                                                                font-size: 11px;
                                                                                color: #666;
                                                                                margin-top: 3px;
                                                                            }}
                                                                            
                                                                            table {{
                                                                                width: 100%;
                                                                                border-collapse: collapse;
                                                                                margin-top: 20px;
                                                                                font-size: 10px;
                                                                            }}
                                                                            
                                                                            th {{
                                                                                background-color: #1E2A56;
                                                                                color: white;
                                                                                padding: 8px 6px;
                                                                                text-align: center;
                                                                                font-weight: bold;
                                                                                border: 1px solid #1E2A56;
                                                                                white-space: nowrap;
                                                                            }}
                                                                            
                                                                            td {{
                                                                                padding: 6px;
                                                                                border: 1px solid #dee2e6;
                                                                                vertical-align: top;
                                                                            }}
                                                                            
                                                                            tr:nth-child(even) {{
                                                                                background: #f8f9fa;
                                                                            }}
                                                                            
                                                                            .status-pending {{
                                                                                background: #fff3e0;
                                                                                color: #f39c12;
                                                                                padding: 3px 8px;
                                                                                border-radius: 12px;
                                                                                font-size: 9px;
                                                                                font-weight: bold;
                                                                            }}
                                                                            
                                                                            .status-in-progress {{
                                                                                background: #e3f2fd;
                                                                                color: #2196f3;
                                                                                padding: 3px 8px;
                                                                                border-radius: 12px;
                                                                                font-size: 9px;
                                                                                font-weight: bold;
                                                                            }}
                                                                            
                                                                            .status-completed {{
                                                                                background: #e8f5e9;
                                                                                color: #27ae60;
                                                                                padding: 3px 8px;
                                                                                border-radius: 12px;
                                                                                font-size: 9px;
                                                                                font-weight: bold;
                                                                            }}
                                                                            
                                                                            .category-badge {{
                                                                                background: #e3f2fd;
                                                                                color: #2196f3;
                                                                                padding: 3px 8px;
                                                                                border-radius: 12px;
                                                                                font-size: 9px;
                                                                                font-weight: bold;
                                                                            }}
                                                                            
                                                                            .whatsapp-link {{
                                                                                color: #25D366;
                                                                                text-decoration: none;
                                                                                font-weight: bold;
                                                                            }}
                                                                            
                                                                            .username-badge {{
                                                                                background: #f0f7ff;
                                                                                color: #1E2A56;
                                                                                padding: 3px 8px;
                                                                                border-radius: 12px;
                                                                                font-size: 9px;
                                                                                font-weight: bold;
                                                                            }}
                                                                            
                                                                            .message-cell {{
                                                                                max-width: 200px;
                                                                                overflow-wrap: break-word;
                                                                            }}
                                                                            
                                                                            .footer {{
                                                                                margin-top: 30px;
                                                                                padding-top: 15px;
                                                                                border-top: 1px solid #dee2e6;
                                                                                text-align: center;
                                                                                font-size: 10px;
                                                                                color: #666;
                                                                            }}
                                                                        </style>
                                                                    </head>
                                                                    <body>
                                                                        <div class="header">
                                                                            <div class="report-title">ENQUIRIES MANAGEMENT REPORT</div>
                                                                            <div class="report-date">Generated: {datetime.now().strftime('%d %B %Y %H:%M')}</div>
                                                                        </div>
                                                                        
                                                                        <div class="stats-grid">
                                                                            <div class="stat-card">
                                                                                <div class="stat-value">{stats[0] if stats else 0}</div>
                                                                                <div class="stat-label">Total Enquiries</div>
                                                                            </div>
                                                                            <div class="stat-card">
                                                                                <div class="stat-value">{stats[1] if stats else 0}</div>
                                                                                <div class="stat-label">Unique Clients</div>
                                                                            </div>
                                                                            <div class="stat-card">
                                                                                <div class="stat-value">{stats[2] if stats else 0}</div>
                                                                                <div class="stat-label">With Attachments</div>
                                                                            </div>
                                                                            <div class="stat-card">
                                                                                <div class="stat-value">{stats[6] if stats else 0}</div>
                                                                                <div class="stat-label">Enquirers</div>
                                                                            </div>
                                                                            <div class="stat-card">
                                                                                <div class="stat-value">{stats[3] if stats else 0}</div>
                                                                                <div class="stat-label">Pending</div>
                                                                            </div>
                                                                            <div class="stat-card">
                                                                                <div class="stat-value">{stats[4] if stats else 0}</div>
                                                                                <div class="stat-label">In Progress</div>
                                                                            </div>
                                                                            <div class="stat-card">
                                                                                <div class="stat-value">{stats[5] if stats else 0}</div>
                                                                                <div class="stat-label">Completed</div>
                                                                            </div>
                                                                        </div>
                                                                        
                                                                        <table>
                                                                            <thead>
                                                                                <tr>
                                                                                    <th>ID</th>
                                                                                    <th>Date & Time</th>
                                                                                    <th>Client WhatsApp</th>
                                                                                    <th>Enquirer</th>
                                                                                    <th>Category</th>
                                                                                    <th>Message</th>
                                                                                    <th>Status</th>
                                                                                    <th>Attachment</th>
                                                                                </tr>
                                                                            </thead>
                                                                            <tbody>
                                                                    """
                                                                    
                                                                    for enquiry in enquiries:
                                                                        # Format data
                                                                        timestamp = enquiry.get('timestamp')
                                                                        date_str = timestamp.strftime('%d/%m %H:%M') if timestamp else ''
                                                                        whatsapp_num = enquiry.get('clientwhatsapp', '')
                                                                        username = enquiry.get('username', 'Unknown')
                                                                        category = enquiry.get('enqcategory', '')
                                                                        message = enquiry.get('enq', 'No message')
                                                                        status = enquiry.get('status', 'pending')
                                                                        has_plan = enquiry.get('has_plan', False)
                                                                        
                                                                        # Truncate message if too long
                                                                        if message and len(message) > 100:
                                                                            message_display = message[:97] + '...'
                                                                        else:
                                                                            message_display = message or 'No message'
                                                                        
                                                                        # Status class
                                                                        status_class = ''
                                                                        status_text = ''
                                                                        if status == 'pending':
                                                                            status_class = 'status-pending'
                                                                            status_text = 'Pending'
                                                                        elif status == 'in_progress':
                                                                            status_class = 'status-in-progress'
                                                                            status_text = 'In Progress'
                                                                        elif status == 'completed':
                                                                            status_class = 'status-completed'
                                                                            status_text = 'Completed'
                                                                        else:
                                                                            status_class = 'status-pending'
                                                                            status_text = 'Pending'
                                                                        
                                                                        html_content += f"""
                                                                                <tr>
                                                                                    <td align="center"><strong>#{enquiry['id']}</strong></td>
                                                                                    <td align="center">{date_str}</td>
                                                                                    <td align="center">
                                                                                        <span class="whatsapp-link">+263{whatsapp_num}</span>
                                                                                    </td>
                                                                                    <td align="center">
                                                                                        <span class="username-badge">{username}</span>
                                                                                    </td>
                                                                                    <td align="center">
                                                                                        <span class="category-badge">{category}</span>
                                                                                    </td>
                                                                                    <td class="message-cell">{message_display}</td>
                                                                                    <td align="center">
                                                                                        <span class="{status_class}">{status_text}</span>
                                                                                    </td>
                                                                                    <td align="center">
                                                                                        {'📎 Yes' if has_plan else 'No'}
                                                                                    </td>
                                                                                </tr>
                                                                        """
                                                                    
                                                                    html_content += f"""
                                                                            </tbody>
                                                                        </table>
                                                                        
                                                                        <div class="footer">
                                                                            <p>Connectlink Properties Enquiries Management System</p>
                                                                            <p>Total Records: {len(enquiries)} • Generated Automatically</p>
                                                                        </div>
                                                                    </body>
                                                                    </html>
                                                                    """
                                                                    
                                                                    # Generate PDF
                                                                    from weasyprint import HTML
                                                                    import io
                                                                    
                                                                    pdf_bytes = HTML(string=html_content).write_pdf()
                                                                    
                                                                    # Send via WhatsApp
                                                                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                                                                    filename = f'enquiries_report_{timestamp}.pdf'
                                                                    
                                                                    # Upload to WhatsApp
                                                                    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
                                                                    headers = {
                                                                        "Authorization": f"Bearer {ACCESS_TOKEN}"
                                                                    }
                                                                    
                                                                    files = {
                                                                        "file": (filename, io.BytesIO(pdf_bytes), "application/pdf"),
                                                                        "type": (None, "application/pdf"),
                                                                        "messaging_product": (None, "whatsapp")
                                                                    }
                                                                    
                                                                    response = requests.post(url, headers=headers, files=files)
                                                                    response.raise_for_status()
                                                                    media_id = response.json()["id"]
                                                                    
                                                                    # Send message first
                                                                    message = f"""
                                                                        📋 *ENQUIRIES MANAGEMENT REPORT*

                                                                        Your enquiries report has been generated!

                                                                        📄 *File:* {filename}
                                                                        📅 *Generated:* {datetime.now().strftime('%d %B %Y %H:%M')}
                                                                        📊 *Statistics:*
                                                                        • Total Enquiries: {stats[0] if stats else 0}
                                                                        • Unique Clients: {stats[1] if stats else 0}
                                                                        • Enquirers: {stats[6] if stats else 0}
                                                                        • With Attachments: {stats[2] if stats else 0}
                                                                        • Pending: {stats[3] if stats else 0}
                                                                        • In Progress: {stats[4] if stats else 0}
                                                                        • Completed: {stats[5] if stats else 0}

                                                                        Please find the detailed enquiries report attached.

                                                                        _This document contains all client enquiries received._
                                                                                    """
                                                                    
                                                                    text_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                    text_headers = {
                                                                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                        "Content-Type": "application/json"
                                                                    }
                                                                    
                                                                    text_payload = {
                                                                        "messaging_product": "whatsapp",
                                                                        "to": sender_id,
                                                                        "type": "text",
                                                                        "text": {"body": message}
                                                                    }
                                                                    
                                                                    requests.post(text_url, headers=text_headers, json=text_payload)
                                                                    
                                                                    # Send PDF
                                                                    doc_payload = {
                                                                        "messaging_product": "whatsapp",
                                                                        "to": sender_id,
                                                                        "type": "document",
                                                                        "document": {
                                                                            "id": media_id,
                                                                            "filename": filename,
                                                                            "caption": f"Enquiries Report - {len(enquiries)} records"
                                                                        }
                                                                    }
                                                                    
                                                                    response = requests.post(text_url, headers=text_headers, json=doc_payload)
                                                                    response.raise_for_status()

                                                                    buttons = [
                                                                        {
                                                                            "type": "reply",
                                                                            "reply": {
                                                                                "id": "projects",
                                                                                "title": "Projects"
                                                                            }
                                                                        },
                                                                        {
                                                                            "type": "reply",
                                                                            "reply": {
                                                                                "id": "enquiries",
                                                                                "title": "Enquiries"
                                                                            }
                                                                        }
                                                                    ]



                                                                    send_whatsapp_button_message(
                                                                        sender_id,
                                                                        f"👋 *Hey there {admin_name}, Projects System Operator.*\n\nPlease select an option below to continue:",
                                                                        buttons,
                                                                        footer_text="ConnectLink Properties • Admin Panel"

                                                                    )
                                                                    
                                                                    return jsonify({
                                                                        'status': 'success',
                                                                        'message': 'Enquiries PDF sent successfully',
                                                                        'filename': filename,
                                                                        'total_enquiries': len(enquiries),
                                                                        'statistics': {
                                                                            'total': stats[0] if stats else 0,
                                                                            'unique_clients': stats[1] if stats else 0,
                                                                            'enquirers': stats[6] if stats else 0,
                                                                            'with_attachments': stats[2] if stats else 0,
                                                                            'pending': stats[3] if stats else 0,
                                                                            'in_progress': stats[4] if stats else 0,
                                                                            'completed': stats[5] if stats else 0
                                                                        }
                                                                    })
                                                                    
                                                            except Exception as e:
                                                                print(f"Error generating enquiries PDF: {str(e)}")
                                                                return jsonify({
                                                                    'status': 'error',
                                                                    'message': f'Failed to generate enquiries PDF: {str(e)}'
                                                                }), 500


                                                            continue

                                                        elif button_id == "main_menu" or selected_option == "main_menu":

                                                            buttons = [
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "projects",
                                                                        "title": "Projects"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "enquiries",
                                                                        "title": "Enquiries"
                                                                    }
                                                                }
                                                            ]



                                                            send_whatsapp_button_image_message(
                                                                sender_id,
                                                                f"👋 *Hey there {admin_name}, Projects System Operator.*\n\nPlease select an option below to continue:",
                                                                "https://connectlink-wbax.onrender.com/static/images/reqlogo.jpg",
                                                                buttons,
                                                                footer_text="ConnectLink Properties • Admin Panel"

                                                            )






                                                        


                                                        elif selected_option == "Myinfo":


                                                            try:


                                                                query = f"SELECT id, firstname, surname, whatsapp, address, email, role, department, currentleavedaysbalance, monthlyaccumulation, leaveapprovername, leaveapproverwhatsapp, leaveapproveremail FROM WHERE id = {str(id_user)};"
                                                                cursor.execute(query)
                                                                row = cursor.fetchone()

                                                                if row:

                                                                    columns = ["ID", "First Name", "Surname", "WhatsApp", "Address", "Email", 
                                                                            "Role", "Department", "Leave Days", "Monthly Accrual", 
                                                                            "Approver", "Approver WhatsApp", "Approver Email"]

                                                                    message_text = "*📄 Employee Details:*\n\n"
                                                                    for col, val in zip(columns, row):
                                                                        message_text += f"*{col}:* {val}\n"




                                                            except Exception as e:

                                                                print(e)

                                                                send_whatsapp_message(f"+263710910052", f"Oops, {admin_name} from ConnectLink Properties! \n\n Your Leave Application` has NOT been submitted successfully! Error; {e}")                      


                                                    else:

                                                        text = message.get("text", {}).get("body", "").lower()
                                                        print(f"📨 Message from {sender_id}: {text}")
                                                        
                                                        print("yearrrrrrrrrrrrrrrrrrrrrrrrrrrssrsrsrsrsrs")

                                                        
                                                        buttons = [
                                                            {
                                                                "type": "reply",
                                                                "reply": {
                                                                    "id": "projects",
                                                                    "title": "Projects"
                                                                }
                                                            },
                                                            {
                                                                "type": "reply",
                                                                "reply": {
                                                                    "id": "enquiries",
                                                                    "title": "Enquiries"
                                                                }
                                                            }
                                                        ]



                                                        send_whatsapp_button_image_message(
                                                            sender_id,
                                                            f"👋 *Hey there {admin_name}, Projects System Operator.*\n\nPlease select an option below to continue:",
                                                            "https://connectlink-wbax.onrender.com/static/images/reqlogo.jpg",
                                                            buttons,
                                                            footer_text="ConnectLink Properties • Admin Panel"

                                                        )



                                                        return jsonify({"status": "received"}), 200






                                                except Exception as e:
                                                    print(e)


                                                return jsonify({"status": "received"}), 200
                                                                                        
                                            elif not result:

                                                query = f"""
                                                    SELECT * FROM connectlinkdatabase
                                                    WHERE clientwanumber::TEXT LIKE %s
                                                """
                                                cursor.execute(query, (f"%{sender_number}",))
                                                result2 = cursor.fetchone()


                                                if result2:
                                                        
                                                    profile_name = result2[1]

                                                    try:

                                                        if message.get("type") == "interactive":
                                                            interactive = message.get("interactive", {})


                                                            if interactive.get("type") == "list_reply":
                                                                selected_option = interactive.get("list_reply", {}).get("id")
                                                                print(f"📋 User selected: {selected_option}")
                                                                button_id = ""

                                                            elif interactive.get("type") == "button_reply":
                                                                button_id = interactive.get("button_reply", {}).get("id")
                                                                print(f"🔘 Button clicked: {button_id}")
                                                                selected_option = ""


                                                            elif interactive.get("type") == "nfm_reply":

                                                                url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                headers = {
                                                                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                    "Content-Type": "application/json"
                                                                }

                                                                response_str = interactive.get("nfm_reply", {}).get("response_json", "{}")
                                                                selected_option = ""
                                                                button_id = ""

                                                                print("📋 Raw nfm_reply response_json:", response_str)

                                                                try:
                                                                    form_response = json.loads(response_str)
                                                                    print("✅ Parsed form_response:", form_response)
                                                                except Exception as e:
                                                                    print("❌ Error parsing nfm_reply response_json:", e)
                                                                    form_response = {}

                                                                print("🔍 Parsing form fields from form_response:")


                                                                query = f"""
                                                                    SELECT * FROM appenqtemp
                                                                    WHERE wanumber::TEXT LIKE %s
                                                                """
                                                                cursor.execute(query, (f"%{sender_id[-9:]}",))
                                                                resultenqtemp = cursor.fetchone()

                                                                enquiry_type = resultenqtemp[2]

                                                                if enquiry_type:

                                                                    query = """
                                                                        DELETE FROM appenqtemp
                                                                        WHERE wanumber::TEXT LIKE %s
                                                                    """
                                                                    cursor.execute(query, (f"%{sender_id[-9:]}",))
                                                                    connection.commit

                                                                # The form_response is already in the clean format we need
                                                                user_message = form_response.get("details", "")
                                                                attachment_list = form_response.get("attachment", [])
                                                                flow_token = form_response.get("flow_token", "")

                                                                print("Values from form_response:")
                                                                print("enquiry_type:", enquiry_type, type(enquiry_type))
                                                                print("user_message:", user_message, type(user_message))
                                                                print("attachment_list:", attachment_list, type(attachment_list))
                                                                print("flow_token:", flow_token)

                                                                # Validate required fields
                                                                if not enquiry_type:
                                                                    print("❌ No enquiry_type found in form response")
                                                                    print("❌ Full form_response:", json.dumps(form_response, indent=2))
                                                                    return jsonify({'status': 'error', 'message': 'Enquiry type is required'}), 400

                                                                # Map enquiry type IDs to display names
                                                                enquiry_type_map = {
                                                                    'kitchen_cabinets': 'Kitchen & Cabinets',
                                                                    'building': 'Building',
                                                                    'renovation': 'Renovation',
                                                                    'otherenq': 'Other'
                                                                }

                                                                enquiry_type_display = enquiry_type_map.get(enquiry_type, enquiry_type)

                                                                print(f"✅ Enquiry type display: {enquiry_type_display}")

                                                                # Process attachment if exists
                                                                attachment_data = None
                                                                has_attachment = False

                                                                if attachment_list and isinstance(attachment_list, list) and len(attachment_list) > 0:
                                                                    print("Processing attachment...")
                                                                    has_attachment = True
                                                                    
                                                                    # The attachment is an object with id, mime_type, sha256, file_name
                                                                    attachment_info = attachment_list[0]
                                                                    attachment_id = attachment_info.get('id')
                                                                    file_name = attachment_info.get('file_name', 'document.pdf')
                                                                    
                                                                    print(f"Attachment info: ID={attachment_id}, File={file_name}")
                                                                    
                                                                    # We need to download the actual file using the attachment ID
                                                                    # WhatsApp provides a separate endpoint for downloading media
                                                                    if attachment_id:
                                                                        try:
                                                                            # First, get the media URL
                                                                            media_url = f"https://graph.facebook.com/v19.0/{attachment_id}"
                                                                            headers = {
                                                                                "Authorization": f"Bearer {ACCESS_TOKEN}"
                                                                            }
                                                                            
                                                                            print(f"📥 Downloading media from: {media_url}")
                                                                            response = requests.get(media_url, headers=headers)
                                                                            response.raise_for_status()
                                                                            media_info = response.json()
                                                                            
                                                                            print(f"Media info: {media_info}")
                                                                            
                                                                            # Get the actual download URL
                                                                            download_url = media_info.get('url')
                                                                            if download_url:
                                                                                # Download the file
                                                                                print(f"📥 Downloading file from: {download_url}")
                                                                                file_response = requests.get(download_url, headers=headers)
                                                                                file_response.raise_for_status()
                                                                                
                                                                                attachment_data = file_response.content
                                                                                print(f"✅ Attachment downloaded, size: {len(attachment_data)} bytes")
                                                                            else:
                                                                                print("❌ No download URL found in media info")
                                                                                attachment_data = None
                                                                                
                                                                        except Exception as e:
                                                                            print(f"❌ Error downloading attachment: {e}")
                                                                            attachment_data = None
                                                                else:
                                                                    print("No attachment found in the response")


                                                                # Save to database
                                                                with get_db() as (cursor, connection):
                                                                    insert_query = """
                                                                        INSERT INTO connectlinkenquiries 
                                                                        (timestamp, clientwhatsapp, enqcategory, enq, plan, username)
                                                                        VALUES (%s, %s, %s, %s, %s, %s)
                                                                        RETURNING id;
                                                                    """
                                                                    
                                                                    timestamp = datetime.now()
                                                                    client_whatsapp = int(sender_id[-9:]) if sender_id.isdigit() else None
                                                                    
                                                                    print(f"✅ Saving to database:")
                                                                    print(f"  - timestamp: {timestamp}")
                                                                    print(f"  - clientwhatsapp: {client_whatsapp}")
                                                                    print(f"  - enqcategory: {enquiry_type_display}")
                                                                    print(f"  - enq: {user_message}")
                                                                    print(f"  - plan: {'Yes' if attachment_data else 'No'}")
                                                                    
                                                                    cursor.execute(
                                                                        insert_query,
                                                                        (
                                                                            timestamp,
                                                                            client_whatsapp,
                                                                            enquiry_type_display,
                                                                            user_message or '',
                                                                            attachment_data,
                                                                            profile_name
                                                                        )
                                                                    )
                                                                    
                                                                    enquiry_id = cursor.fetchone()[0]
                                                                    connection.commit()
                                                                    
                                                                    print(f"✅ Enquiry saved with ID: {enquiry_id}")
                                                                    
                                                                    # Send confirmation message to user
                                                                    confirmation_message = f"""
                                                                        ✅ *Your Enquiry has been successfully submitted to ConnectLink Properties Admin, {profile_name}!*

                                                                        📋 *Reference ID:* #{enquiry_id}
                                                                        📅 *Date:* {timestamp.strftime('%d %B %Y %H:%M')}
                                                                        🏷️ *Category:* {enquiry_type_display}
                                                                        {'📎 *Attachment:* Yes' if has_attachment else ''}

                                                                        Thank you for your enquiry. Our team will contact you within 24 hours.

                                                                        _For urgent matters, please call our office._
                                                                        """
                                                                    
                                                                    print(f"✅ Sending confirmation to {sender_id}")
                                                                    
                                                                    # Send WhatsApp confirmation
                                                                    buttons = [
                                                                        {
                                                                            "type": "reply",
                                                                            "reply": {
                                                                                "id": "enquirylog",
                                                                                "title": "Enquiries"
                                                                            }
                                                                        },
                                                                        {
                                                                            "type": "reply",
                                                                            "reply": {
                                                                                "id": "contact",
                                                                                "title": "Contact Us"
                                                                            }
                                                                        },
                                                                        {
                                                                            "type": "reply",
                                                                            "reply": {
                                                                                "id": "about",
                                                                                "title": "About Us"
                                                                            }
                                                                        }
                                                                    ]


                                                                    send_whatsapp_button_image_message(
                                                                        sender_id, 
                                                                        f"{confirmation_message} \n\n How else can we assist you today?.",
                                                                        "https://connectlink-wbax.onrender.com/static/images/reqlogo.jpg",
                                                                        buttons,
                                                                        footer_text="ConnectLink Properties • Client Panel"

                                                                    )

                                                                    
                                                                    # Also notify admin/team
                                                                    admin_notification = f"""
                                                                        🔔 *NEW ENQUIRY RECEIVED*

                                                                        📋 *Reference ID:* #{enquiry_id}
                                                                        📱 *Client WhatsApp:* {sender_id}
                                                                        📅 *Timestamp:* {timestamp.strftime('%d %B %Y %H:%M')}
                                                                        🏷️ *Category:* {enquiry_type_display}
                                                                        📝 *Details:* {user_message or 'No additional details'}
                                                                        📎 *Attachment:* {'Yes' if has_attachment else 'No'}

                                                                        Please follow up with the client.
                                                                        """
                                                                    
                                                                    # Send to admin/team
                                                                    admin_numbers = ["263774822568","263773368558"]
                                                                    
                                                                    for admin_number in admin_numbers:
                                                                        print(f"✅ Notifying admin: {admin_number}")
                                                                        send_whatsapp_message(
                                                                            admin_number,
                                                                            admin_notification
                                                                        )
                                                                    
                                                                    return jsonify({
                                                                        'status': 'success',
                                                                        'message': 'Enquiry saved successfully',
                                                                        'enquiry_id': enquiry_id,
                                                                        'data': {
                                                                            'enquiry_type': enquiry_type,
                                                                            'details': user_message,
                                                                            'has_attachment': has_attachment,
                                                                            'attachment_info': attachment_list[0] if attachment_list else None
                                                                        }
                                                                    })


                                                            if button_id == "enquirylog":

                                                                sections = [
                                                                    {
                                                                        "title": "Enquiries Options",
                                                                        "rows": [
                                                                            {
                                                                                "id": "kitchen_cabinets",
                                                                                "title": "Kitchen & Cabinets",
                                                                                "description": "Kitchen and Cabinets enquiries"
                                                                            },
                                                                            {
                                                                                "id": "building",
                                                                                "title": "Building",
                                                                                "description": "Building enquiries"
                                                                            },
                                                                            {
                                                                                "id": "renovation",
                                                                                "title": "Renovation",
                                                                                "description": "Renovation enquiries"
                                                                            },
                                                                            {
                                                                                "id": "other",
                                                                                "title": "Other",
                                                                                "description": "Other enquiries"
                                                                            },
                                                                            {
                                                                                "id": "main_menu",
                                                                                "title": "Main Menu",
                                                                                "description": "Return to main menu"
                                                                            }
                                                                        ]
                                                                    }
                                                                ]

                                                                send_whatsapp_list_message(
                                                                    sender_id,
                                                                    "Kindly select an enquiry option below.",
                                                                    "ConnectLink Enquiries",
                                                                    sections,
                                                                    footer_text="ConnectLink Properties • Client Panel"
                                                                )

                                                            elif selected_option in ["kitchen_cabinets","building","renovation","other"]:

                                                                with get_db() as (cursor, connection):
                                                                    insert_query = """
                                                                        INSERT INTO appenqtemp 
                                                                        (wanumber, enqtype)
                                                                        VALUES (%s, %s)
                                                                        RETURNING id;
                                                                    """
                                                                    
                                                                    digits = "".join(filter(str.isdigit, sender_id))
                                                                    client_whatsapp = int(digits[-9:]) if len(digits) >= 9 else None
                                                                    
                                                                    cursor.execute(
                                                                        insert_query,
                                                                        (
                                                                            client_whatsapp,
                                                                            selected_option
                                                                        )
                                                                    )

                                                                    connection.commit()

                                                                buttons = [
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "enquirylog",
                                                                            "title": "Enquiries"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "contact",
                                                                            "title": "Contact Us"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "about",
                                                                            "title": "About Us"
                                                                        }
                                                                    }
                                                                ]

                                                                if selected_option == "kitchen_cabinets":

                                                                    send_whatsapp_message(
                                                                        sender_id,
                                                                        f"Good day {profile_name},\n\n"
                                                                        "At Connectlink Kitchens and Cabinets, we specialise in the design and installation of kitchen cabinets, built-in wardrobes, bathroom vanities and TV units.\n\n"
                                                                        "We are offering these services on credit:\n"
                                                                        "- 30% deposit\n"
                                                                        "- Installation within 10 working days\n"
                                                                        "- Balance payable over 3 months\n\n"
                                                                        "We offer free 3D designs and quotations. Send your house plan or measurements via the Fill Enquiries Form below, or request a site visit.\n\n"
                                                                        "Site visits within 20km of Harare CBD cost USD $10.",
                                                                        buttons,
                                                                        footer_text="ConnectLink Properties • Client Panel"
                                                                    )

                                                                elif selected_option == "building":

                                                                    send_whatsapp_message(
                                                                        sender_id,
                                                                        f"Good day {profile_name},\n\n"
                                                                        "At Connectlink Properties, we are a full-service construction company offering turnkey building solutions nationwide.\n\n"
                                                                        "Our payment terms are:\n"
                                                                        "- 120 days (double storey)\n\n"
                                                                        "We deliver quality, reliability and professional project management from foundation to finish. Send your house plan or measurements via the Enquiries Form below, or request a site visit.",
                                                                        buttons,
                                                                        footer_text="ConnectLink Properties • Client Panel"
                                                                    )


                                                                payload = {
                                                                    "messaging_product": "whatsapp",
                                                                    "to": sender_id,
                                                                    "type": "template",
                                                                    "template": {
                                                                        "name": "enquiries",  # your template name
                                                                        "language": {"code": "en"},
                                                                        "components": [
                                                                            {
                                                                                "type": "button",
                                                                                "index": "0",
                                                                                "sub_type": "flow",
                                                                                "parameters": [
                                                                                    {
                                                                                        "type": "action",
                                                                                        "action": {
                                                                                        "flow_token": "unused"
                                                                                        }
                                                                                    }
                                                                                ]
                                                                                        # button index in your template
                                                                            }
                                                                        ]
                                                                    }
                                                                }

                                                                response = requests.post(
                                                                    f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages",
                                                                    headers={
                                                                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                        "Content-Type": "application/json"
                                                                    },
                                                                    json=payload
                                                                ) 

                                                                print(response.status_code)
                                                                print(response.text)










                                                                continue

                                                            elif button_id == "paymenthist":

                                                                def send_pdf_via_whatsapp(recipient_number, pdf_bytes, filename, caption):
                                                                    """Send PDF via WhatsApp"""
                                                                    try:
                                                                        import io

                                                                        # Upload to WhatsApp
                                                                        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
                                                                        headers = {
                                                                            "Authorization": f"Bearer {ACCESS_TOKEN}"
                                                                        }
                                                                        
                                                                        files = {
                                                                            "file": (filename, io.BytesIO(pdf_bytes), "application/pdf"),
                                                                            "type": (None, "application/pdf"),
                                                                            "messaging_product": (None, "whatsapp")
                                                                        }
                                                                        
                                                                        response = requests.post(url, headers=headers, files=files)
                                                                        response.raise_for_status()
                                                                        media_id = response.json()["id"]
                                                                        
                                                                        # Send PDF
                                                                        doc_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                        doc_headers = {
                                                                            "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                            "Content-Type": "application/json"
                                                                        }
                                                                        
                                                                        doc_payload = {
                                                                            "messaging_product": "whatsapp",
                                                                            "to": recipient_number,
                                                                            "type": "document",
                                                                            "document": {
                                                                                "id": media_id,
                                                                                "filename": filename,
                                                                                "caption": caption
                                                                            }
                                                                        }
                                                                        
                                                                        response = requests.post(doc_url, headers=doc_headers, json=doc_payload)
                                                                        response.raise_for_status()
                                                                        return True
                                                                        
                                                                    except Exception as e:
                                                                        print(f"❌ Error sending PDF: {e}")
                                                                        return False

                                                                def send_payment_history_via_whatsapp(sender_id):
                                                                    """Send payment history PDF to WhatsApp using existing pattern"""
                                                                    try:
                                                                        # Extract last 9 digits from sender_id (same as contracts)
                                                                        if sender_id and len(sender_id) >= 9:
                                                                            client_whatsapp = int(sender_id[-9:])
                                                                        else:
                                                                            client_whatsapp = int(sender_id) if sender_id and sender_id.isdigit() else None
                                                                        
                                                                        if not client_whatsapp:
                                                                            return jsonify({'status': 'error', 'message': 'Invalid WhatsApp number'}), 400
                                                                        
                                                                        with get_db() as (cursor, connection):
                                                                            # Get ALL user's projects
                                                                            cursor.execute("""
                                                                                SELECT * FROM connectlinkdatabase 
                                                                                WHERE clientwanumber = %s
                                                                                ORDER BY projectstartdate DESC
                                                                            """, (client_whatsapp,))
                                                                            
                                                                            rows = cursor.fetchall()
                                                                            
                                                                            if not rows:
                                                                                message = f"📋 No payment records found for your WhatsApp number."
                                                                                send_whatsapp_message(sender_id, message)
                                                                                return jsonify({'status': 'success', 'message': 'No payment records found'})
                                                                            
                                                                            # Send summary message
                                                                            summary = f"""
                                                                                📊 *YOUR PAYMENT HISTORY - CONNECTLINK PROPERTIES*

                                                                                Found {len(rows)} project(s) with payment records.

                                                                                _Sending payment history documents now..._
                                                                                            """
                                                                            # send_whatsapp_message(sender_id, summary)
                                                                            
                                                                            # Process each project's payment history
                                                                            for i, row in enumerate(rows):
                                                                                try:
                                                                                    print(f"📄 Generating payment history {i+1}/{len(rows)}")
                                                                                    
                                                                                    # Generate payment history PDF using your template
                                                                                    pdf_bytes = generate_payment_history_pdf(row, cursor)
                                                                                    
                                                                                    if pdf_bytes:
                                                                                        # Send payment history via WhatsApp
                                                                                        client_name = row[1]  # clientname
                                                                                        project_name = row[10]  # projectname
                                                                                        project_id = row[0]  # momid
                                                                                        
                                                                                        filename = f"Payment_History_{client_name}_{project_name}_{project_id}.pdf"
                                                                                        
                                                                                        # Create caption for the PDF
                                                                                        caption = f"""💰 *PAYMENT HISTORY*

                                                                                            Client: {client_name}
                                                                                            Project: {project_name}
                                                                                            Project ID: {project_id}

                                                                                            This document contains your complete payment history including installments, due dates, and payment status."""
                                                                                        
                                                                                        send_pdf_via_whatsapp(sender_id, pdf_bytes, filename, caption)
                                                                                        
                                                                                        # Send progress update (optional)
                                                                                        if i < len(rows) - 1:
                                                                                            progress = f"✅ Sent payment history {i+1} of {len(rows)}"
                                                                                            send_whatsapp_message(sender_id, progress)
                                                                                            time.sleep(2)  # Delay between sends
                                                                                
                                                                                except Exception as e:
                                                                                    print(f"❌ Error with payment history {i+1}: {e}")
                                                                                    error_msg = f"⚠️ Could not send payment history for project {i+1}. Will try next one."
                                                                                    send_whatsapp_message(sender_id, error_msg)
                                                                                    continue
                                                                            
                                                                            # Final message with buttons
                                                                            final_msg = f"""
                                                                                ✅ *ALL PAYMENT HISTORIES SENT!*

                                                                                _Keep your records safe for reference!_
                                                                                            """
                                                                            
                                                                            buttons = [
                                                                                {
                                                                                    "type": "reply",
                                                                                    "reply": {
                                                                                        "id": "contracts",
                                                                                        "title": "My Contracts"
                                                                                    }
                                                                                },
                                                                                {
                                                                                    "type": "reply",
                                                                                    "reply": {
                                                                                        "id": "paymenthist",
                                                                                        "title": "My Payments History"
                                                                                    }
                                                                                },
                                                                                {
                                                                                    "type": "reply",
                                                                                    "reply": {
                                                                                        "id": "enquirylog",
                                                                                        "title": "Enquiries"
                                                                                    }
                                                                                }
                                                                            ]
                                                                            
                                                                            send_whatsapp_button_message(
                                                                                sender_id, 
                                                                                f"{final_msg} \n\n How else can we assist you today?",
                                                                                buttons,
                                                                                footer_text="ConnectLink Properties • Client Panel"
                                                                            )
                                                                            
                                                                            return jsonify({
                                                                                'status': 'success', 
                                                                                'message': f'Sent {len(rows)} payment histories',
                                                                                'count': len(rows)
                                                                            })
                                                                            
                                                                    except Exception as e:
                                                                        print(f"❌ Error in payment history handler: {str(e)}")
                                                                        return jsonify({'status': 'error', 'message': str(e)}), 500


                                                                def generate_payment_history_pdf(row, cursor):
                                                                    """Generate payment history PDF using your HTML template"""
                                                                    try:
                                                                        from weasyprint import HTML
                                                                        from weasyprint import CSS
                                                                        import base64
                                                                        import os
                                                                        from datetime import datetime
                                                                        
                                                                        # Get company details
                                                                        cursor.execute("SELECT * FROM connectlinkdetails;")
                                                                        details = cursor.fetchall()
                                                                        details = pd.DataFrame(details, columns=[
                                                                            'address','contact1','contact2','email','companyname','tinnumber'
                                                                        ])
                                                                        
                                                                        companyname = details.iat[0,4] if not details.empty else "ConnectLink Properties"
                                                                        address = details.iat[0,0] if not details.empty else ""
                                                                        contact1 = details.iat[0,1] if not details.empty else ""
                                                                        contact2 = details.iat[0,2] if not details.empty else ""
                                                                        compemail = details.iat[0,3] if not details.empty else ""
                                                                        
                                                                        # Get logo as base64
                                                                        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'web-logo.png')
                                                                        logo_base64 = ""
                                                                        if os.path.exists(logo_path):
                                                                            with open(logo_path, 'rb') as img:
                                                                                logo_base64 = base64.b64encode(img.read()).decode('utf-8')
                                                                        
                                                                        # Prepare payment data
                                                                        payments = [
                                                                            {
                                                                                "name": "Installment 1",
                                                                                "amount": row[26] if len(row) > 26 else 0,
                                                                                "due": row[27].strftime("%d %B %Y") if len(row) > 27 and row[27] else "-",
                                                                                "paid": row[28].strftime("%d %B %Y") if len(row) > 28 and row[28] else "Not Paid",
                                                                            },
                                                                            {
                                                                                "name": "Installment 2",
                                                                                "amount": row[29] if len(row) > 29 else 0,
                                                                                "due": row[30].strftime("%d %B %Y") if len(row) > 30 and row[30] else "-",
                                                                                "paid": row[31].strftime("%d %B %Y") if len(row) > 31 and row[31] else "Not Paid",
                                                                            },
                                                                            {
                                                                                "name": "Installment 3",
                                                                                "amount": row[32] if len(row) > 32 else 0,
                                                                                "due": row[33].strftime("%d %B %Y") if len(row) > 33 and row[33] else "-",
                                                                                "paid": row[34].strftime("%d %B %Y") if len(row) > 34 and row[34] else "Not Paid",
                                                                            },
                                                                            {
                                                                                "name": "Installment 4",
                                                                                "amount": row[35] if len(row) > 35 else 0,
                                                                                "due": row[36].strftime("%d %B %Y") if len(row) > 36 and row[36] else "-",
                                                                                "paid": row[37].strftime("%d %B %Y") if len(row) > 37 and row[37] else "Not Paid",
                                                                            },
                                                                            {
                                                                                "name": "Installment 5",
                                                                                "amount": row[38] if len(row) > 38 else 0,
                                                                                "due": row[39].strftime("%d %B %Y") if len(row) > 39 and row[39] else "-",
                                                                                "paid": row[40].strftime("%d %B %Y") if len(row) > 40 and row[40] else "Not Paid",
                                                                            },
                                                                            {
                                                                                "name": "Installment 6",
                                                                                "amount": row[41] if len(row) > 41 else 0,
                                                                                "due": row[42].strftime("%d %B %Y") if len(row) > 42 and row[42] else "-",
                                                                                "paid": row[43].strftime("%d %B %Y") if len(row) > 43 and row[43] else "Not Paid",
                                                                            }
                                                                        ]
                                                                        
                                                                        # Build payments table rows
                                                                        payment_rows = ""
                                                                        for p in payments:
                                                                            payment_rows += f"""
                                                                                <tr>
                                                                                    <td style="border:1px solid #ccc;padding:8px;">{p['name']}</td>
                                                                                    <td style="border:1px solid #ccc;padding:8px;">{p['amount']}</td>
                                                                                    <td style="border:1px solid #ccc;padding:8px;">{p['due']}</td>
                                                                                    <td style="border:1px solid #ccc;padding:8px;">{p['paid']}</td>
                                                                                </tr>
                                                                            """
                                                                        
                                                                        # Format dates
                                                                        project_start_date = row[14].strftime("%d %B %Y") if row[14] else ""
                                                                        agreement_date = row[16].strftime("%d %B %Y") if row[16] else ""
                                                                        deposit_payment_date = row[24].strftime("%d %B %Y") if len(row) > 24 and row[24] else "—"
                                                                        
                                                                        # Generate HTML using your template
                                                                        html = f"""
                                                                        <!DOCTYPE html>
                                                                        <html lang="en">
                                                                        <head>
                                                                            <meta charset="UTF-8">
                                                                            
                                                                            <style>
                                                                                body {{
                                                                                    font-family: 'Arial', sans-serif;
                                                                                    margin: 40px;
                                                                                    color: #1E2A56;
                                                                                    background-color: #ffffff;
                                                                                    line-height: 1.5;
                                                                                }}

                                                                                .header {{
                                                                                    text-align: center;
                                                                                    margin-bottom: 25px;
                                                                                }}

                                                                                .logo {{
                                                                                    width: 170px;
                                                                                    margin-bottom: 12px;
                                                                                }}

                                                                                h1 {{
                                                                                    font-size: 24px;
                                                                                    margin: 5px 0 0 0;
                                                                                    font-weight: 800;
                                                                                }}

                                                                                .tagline {{
                                                                                    font-size: 13px;
                                                                                    color: #445;
                                                                                    margin-top: 3px;
                                                                                }}

                                                                                .section-title {{
                                                                                    font-size: 17px;
                                                                                    margin-top: 35px;
                                                                                    margin-bottom: 12px;
                                                                                    padding-bottom: 6px;
                                                                                    border-bottom: 2px solid #1E2A56;
                                                                                    font-weight: 800;
                                                                                }}

                                                                                .info-box {{
                                                                                    padding: 12px 16px;
                                                                                    border: 1px solid #d3d6e4;
                                                                                    border-radius: 8px;
                                                                                    background: #f9faff;
                                                                                    margin-bottom: 10px;
                                                                                }}

                                                                                .info-box p {{
                                                                                    margin: 3px 0;
                                                                                    font-size: 14px;
                                                                                }}

                                                                                table {{
                                                                                    width: 100%;
                                                                                    border-collapse: collapse;
                                                                                    margin-top: 10px;
                                                                                    font-size: 14px;
                                                                                }}

                                                                                th {{
                                                                                    background: #1E2A56;
                                                                                    color: #fff;
                                                                                    padding: 10px;
                                                                                    text-align: left;
                                                                                    font-size: 14px;
                                                                                }}

                                                                                td {{
                                                                                    padding: 10px;
                                                                                    border-bottom: 1px solid #e0e3ef;
                                                                                }}

                                                                                tr:nth-child(even) {{
                                                                                    background: #f4f6fb;
                                                                                }}

                                                                                .footer {{
                                                                                    margin-top: 35px;
                                                                                    text-align: right;
                                                                                    font-size: 12px;
                                                                                    color: #666;
                                                                                }}
                                                                            </style>
                                                                        </head>

                                                                        <body>

                                                                            <div class="header">
                                                                                <img src="data:image/png;base64,{logo_base64}" class="logo">
                                                                                <h3>Payments History</h3>
                                                                                <div class="tagline">Official Client Payment Record</div>
                                                                            </div>

                                                                            <div class="section-title">Client Information</div>
                                                                            <div class="info-box">
                                                                                <p><strong>Name:</strong> {row[1]}</p>
                                                                                <p><strong>Address:</strong> {row[3]}</p>
                                                                                <p><strong>Contact:</strong> 0{row[4]}</p>
                                                                                <p><strong>Email:</strong> {row[5]}</p>
                                                                            </div>

                                                                            <div class="section-title">Project Information</div>
                                                                            <div class="info-box">
                                                                                <p><strong>Project Name:</strong> {row[10]}</p>
                                                                                <p><strong>Location:</strong> {row[11]}</p>
                                                                                <p><strong>Administrator:</strong> {row[13]}</p>
                                                                                <p><strong>Start Date:</strong> {project_start_date}</p>
                                                                                <p><strong>Agreement Date:</strong> {agreement_date}</p>
                                                                            </div>

                                                                            
                                                                            <!-- DEPOSIT / BULLET PAYMENT -->
                                                                            <div class="section-title">Payments Breakdown</div>

                                                                            <div class="info-box">
                                                                                <p><strong>Deposit / Bullet Payment:</strong> USD {row[23] if len(row) > 23 and row[23] else '—'}</p>
                                                                                <p><strong>Date Paid:</strong> {deposit_payment_date}</p>
                                                                                <p><strong>Total Contract Price:</strong> USD {row[17] if len(row) > 17 else '—'}</p>
                                                                                <p><strong>Late Payment Interest:</strong> {row[45] if len(row) > 45 else 0}% per annum</p>
                                                                            </div>

                                                                            <table>
                                                                                <thead>
                                                                                    <tr>
                                                                                        <th>Installment</th>
                                                                                        <th>Amount (USD)</th>
                                                                                        <th>Due Date</th>
                                                                                        <th>Date Paid</th>
                                                                                    </tr>
                                                                                </thead>
                                                                                <tbody>
                                                                                    {payment_rows}
                                                                                </tbody>
                                                                            </table>

                                                                            <div class="footer">
                                                                                <p><strong>Generated on:</strong> {datetime.now().strftime("%d %B %Y")}</p>
                                                                                <p><strong>Company:</strong> {companyname}</p>
                                                                                <p><strong>Contact:</strong> 0{contact1} / 0{contact2}</p>
                                                                                <p><strong>Email:</strong> {compemail}</p>
                                                                            </div>

                                                                        </body>
                                                                        </html>
                                                                        """
                                                                        
                                                                        # Generate PDF
                                                                        css = CSS(string='''
                                                                            @page {
                                                                                size: A4;
                                                                                margin: 20px;
                                                                            }
                                                                        ''')
                                                                        
                                                                        html_obj = HTML(string=html)
                                                                        pdf_bytes = html_obj.write_pdf(stylesheets=[css])
                                                                        
                                                                        return pdf_bytes
                                                                        
                                                                    except Exception as e:
                                                                        print(f"❌ Error generating payment history PDF: {e}")
                                                                        return None


                                                                # Add this to your WhatsApp webhook handler for the "paymenthist" button
                                                                # In your WhatsApp message handler, add:
                                                                    # Trigger payment history sending
                                                                send_payment_history_via_whatsapp(sender_id)

                                                                
                                                                return jsonify({'status': 'processing'})

                                                            elif button_id == "contracts":
                                                                """Generate and send actual contract PDFs using the template"""

                                                                def generate_contract_pdf(row, cursor):
                                                                    """Generate contract PDF using the template"""
                                                                    try:

                                                                        from weasyprint import HTML
                                                                        import io
                                                                        # Format agreement date
                                                                        agreement_date = row[16] 
                                                                        formatted_agreement_date = agreement_date.strftime("%d %B %Y") if agreement_date else ""

                                                                        # Get company details
                                                                        cursor.execute("SELECT * FROM connectlinkdetails;")
                                                                        detailscompdata = cursor.fetchall()
                                                                        detailscompdata = pd.DataFrame(detailscompdata, columns=['address','contact1','contact2','email','companyname','tinnumber'])
                                                                        companyname = detailscompdata.iat[0,4] if not detailscompdata.empty else "ConnectLink Properties"
                                                                        address = detailscompdata.iat[0,0] if not detailscompdata.empty else ""
                                                                        contact1 = detailscompdata.iat[0,1] if not detailscompdata.empty else ""
                                                                        contact2 = detailscompdata.iat[0,2] if not detailscompdata.empty else ""
                                                                        compemail = detailscompdata.iat[0,3] if not detailscompdata.empty else ""

                                                                        # Calculate days difference
                                                                        def days_between(date1, date2):
                                                                            if date1 and date2:
                                                                                delta = date1 - date2
                                                                                return abs(delta.days)
                                                                            return 0

                                                                        date_str1 = row[14]  # projectstartdate
                                                                        date_str2 = row[24] if len(row) > 24 else None  # datedepositorbullet
                                                                        days_difference = days_between(date_str1, date_str2)

                                                                        # Prepare project data
                                                                        project = {
                                                                            'project_id_num': row[0],
                                                                            'client_name': row[1],
                                                                            'client_idnumber': row[2],
                                                                            'client_address': row[3],
                                                                            'client_whatsapp': row[4],
                                                                            'client_email': row[5],
                                                                            'next_of_kin_name': row[6] if len(row) > 6 else "",
                                                                            'next_of_kin_address': row[7] if len(row) > 7 else "",
                                                                            'next_of_kin_phone': row[8] if len(row) > 8 else "",
                                                                            'relationship': row[9] if len(row) > 9 else "",
                                                                            'project_name': row[10],
                                                                            'project_location': row[11],
                                                                            'project_description': row[12],
                                                                            'project_administrator': row[13],
                                                                            'project_start_date': row[14],
                                                                            'project_duration': row[15],
                                                                            'agreement_date': formatted_agreement_date,
                                                                            'total_contract_price': row[17],
                                                                            'depositorbullet': row[23] if len(row) > 23 else 0,
                                                                            'datedepositorbullet': row[24] if len(row) > 24 else None,
                                                                            'monthlyinstallment': row[25] if len(row) > 25 else 0,
                                                                            'installment1amount': row[26] if len(row) > 26 else 0,
                                                                            'installment1duedate': row[27].strftime("%-d %B %Y") if len(row) > 27 and row[27] else "",
                                                                            'installment2amount': row[29] if len(row) > 29 else 0,
                                                                            'installment2duedate': row[30].strftime("%-d %B %Y") if len(row) > 30 and row[30] else "",
                                                                            'installment3amount': row[32] if len(row) > 32 else 0,
                                                                            'installment3duedate': row[33].strftime("%-d %B %Y") if len(row) > 33 and row[33] else "",
                                                                            'installment4amount': row[35] if len(row) > 35 else 0,
                                                                            'installment4duedate': row[36].strftime("%-d %B %Y") if len(row) > 36 and row[36] else "",
                                                                            'installment5amount': row[38] if len(row) > 38 else 0,
                                                                            'installment5duedate': row[39].strftime("%-d %B %Y") if len(row) > 39 and row[39] else "",
                                                                            'installment6amount': row[41] if len(row) > 41 else 0,
                                                                            'installment6duedate': row[42].strftime("%-d %B %Y") if len(row) > 42 and row[42] else "",
                                                                            'latepaymentinterest': row[45] if len(row) > 45 else 0,
                                                                            'companyname': companyname,
                                                                            'companyaddress': address,
                                                                            'companycontact1': contact1,
                                                                            'companycontact2': contact2,
                                                                            'companyemail': compemail,
                                                                            'days_difference': days_difference,
                                                                            'generated_on': datetime.now().strftime('%d %B %Y')
                                                                        }

                                                                        # Generate HTML using your exact template
                                                                        html = generate_contract_html(project)
                                                                        
                                                                        
                                                                        # Add logo (adjust path as needed)
                                                                        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'web-logo.png')
                                                                        logo_base64 = ""
                                                                        if os.path.exists(logo_path):
                                                                            with open(logo_path, 'rb') as img_file:
                                                                                logo_base64 = base64.b64encode(img_file.read()).decode('utf-8')

                                                                        # Replace logo placeholder
                                                                        html = html.replace('{logo_base64}', logo_base64)
                                                                        
                                                                        # Generate PDF
                                                                        css = CSS(string='''
                                                                            @page {
                                                                                size: A4;
                                                                                margin: 20px 20px 90px 20px;
                                                                            }
                                                                        ''')
                                                                        
                                                                        html_obj = HTML(string=html)
                                                                        pdf_bytes = html_obj.write_pdf(stylesheets=[css])
                                                                        
                                                                        return pdf_bytes
                                                                        
                                                                    except Exception as e:
                                                                        print(f"❌ Error generating PDF: {e}")
                                                                        return None


                                                                def generate_contract_html(project):
                                                                    """Generate HTML from your template"""
                                                                    # Your complete HTML template here (the one you provided)
                                                                    # I'll include a shortened version - use your actual full template
                                                                    html_template = f"""
                                                                        <!DOCTYPE html>
                                                                        <html lang="en">
                                                                        <head>
                                                                            <meta charset="UTF-8">
                                                                            <title>Construction Agreement</title>
                                                                            <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700;900&display=swap" rel="stylesheet">
                                                                            <style>
                                                                                @page {{
                                                                                    size: A4;
                                                                                    margin: 30px 40px 60px 30px; /* Extra bottom margin for signature area */
                                                                                    
                                                                                    @bottom-center {{
                                                                                        content: "";
                                                                                        width: 70%;
                                                                                        border-top: 1px solid #1E2A56;
                                                                                        margin-top: 20px;
                                                                                        padding-top: 10px;
                                                                                    }}
                                                                                }}
                                                                                
                                                                                body {{ 
                                                                                    font-family: 'Roboto', sans-serif; 
                                                                                    background: #fff; 
                                                                                    color: #1E2A56;
                                                                                    margin: 0;
                                                                                    padding: 0;
                                                                                }}
                                                                                
                                                                                .page-break {{
                                                                                    page-break-after: always;
                                                                                    margin-top: 40px;
                                                                                }}
                                                                                
                                                                                .agreement-container {{
                                                                                    width: 100%;
                                                                                    max-width: 800px;
                                                                                    margin: 0 auto;
                                                                                    padding: 30px;
                                                                                    box-sizing: border-box;
                                                                                    position: relative;
                                                                                }}
                                                                                
                                                                                .watermark {{
                                                                                    position: fixed;
                                                                                    top: 40%;
                                                                                    left: 15%;
                                                                                    opacity: 0.05;
                                                                                    font-size: 100px;
                                                                                    color: #1E2A56;
                                                                                    transform: rotate(-45deg);
                                                                                    z-index: -1000;
                                                                                    font-weight: 900;
                                                                                }}
                                                                                
                                                                                .logo {{
                                                                                    display: block;
                                                                                    margin: 0 auto 15px auto;
                                                                                    width: 200px;
                                                                                    height: auto;
                                                                                }}
                                                                                
                                                                                h3.title {{
                                                                                    text-align: center;
                                                                                    font-weight: 900;
                                                                                    margin-bottom: 10px;
                                                                                    text-transform: uppercase;
                                                                                    letter-spacing: 1.6px;
                                                                                    font-size: 20px;
                                                                                    color: #1E2A56;
                                                                                }}
                                                                                
                                                                                .subtitle-line {{
                                                                                    width: 150px;
                                                                                    height: 4px;
                                                                                    background: linear-gradient(90deg, #1E2A56, #3A4B8C);
                                                                                    margin: 10px auto 30px auto;
                                                                                    border-radius: 10px;
                                                                                }}
                                                                                
                                                                                h4.section-title {{
                                                                                    text-align: center;
                                                                                    background: linear-gradient(90deg, #1E2A56, #2A3A78);
                                                                                    color: white;
                                                                                    padding: 8px 10px;
                                                                                    border-radius: 8px;
                                                                                    font-size: 13px;
                                                                                    margin-top: 20px;
                                                                                    margin-bottom: 15px;
                                                                                    font-weight: 700;
                                                                                    letter-spacing: 0.8px;
                                                                                    box-shadow: 0 3px 6px rgba(0,0,0,0.1);
                                                                                }}
                                                                                
                                                                                .section-header {{
                                                                                    background: #f0f5ff;
                                                                                    padding: 8px 10px;
                                                                                    border-left: 4px solid #1E2A56;
                                                                                    margin: 20px 0 20px 0;
                                                                                    font-weight: 700;
                                                                                    color: #1E2A56;
                                                                                    font-size: 12px;
                                                                                    border-radius: 0 8px 8px 0;
                                                                                }}
                                                                                
                                                                                .field-row {{
                                                                                    display: flex;
                                                                                    align-items: flex-start;
                                                                                    margin-bottom: 8px;
                                                                                    page-break-inside: avoid;
                                                                                }}
                                                                                
                                                                                .field-label {{
                                                                                    font-weight: 700;
                                                                                    width: 180px;
                                                                                    font-size: 12px;
                                                                                    flex-shrink: 0;
                                                                                    color: #2A3A78;
                                                                                }}
                                                                                
                                                                                .field-value {{
                                                                                    flex: 1;
                                                                                    border-bottom: 1px solid #d1d9f0;
                                                                                    padding-bottom: 5px;
                                                                                    font-size: 11px;
                                                                                    min-height: 17px;
                                                                                    color: #1E2A56;
                                                                                }}
                                                                                
                                                                                .highlight-box {{
                                                                                    background: linear-gradient(135deg, #f8faff 0%, #f0f5ff 100%);
                                                                                    font-size: 11px;
                                                                                    border: 1.5px solid #1E2A56;
                                                                                    border-radius: 12px;
                                                                                    padding: 20px;
                                                                                    margin: 10px 0;
                                                                                    box-shadow: 0 4px 12px rgba(26, 42, 86, 0.08);
                                                                                }}
                                                                                
                                                                                .scope-box {{
                                                                                    border: 1.5px solid #1E2A56;
                                                                                    border-radius: 10px;
                                                                                    padding: 10px;
                                                                                    font-size: 11px;
                                                                                    min-height: 100px;
                                                                                    background: #fafbff;
                                                                                    margin-bottom: 15px;
                                                                                    line-height: 1.3;
                                                                                }}
                                                                                
                                                                                .payment-table {{
                                                                                    width: 100%;
                                                                                    border-collapse: collapse;
                                                                                    margin: 10px 0;
                                                                                    border: 1.5px solid #1E2A56;
                                                                                    box-shadow: 0 3px 8px rgba(0,0,0,0.05);
                                                                                }}
                                                                                
                                                                                .payment-table th {{
                                                                                    background: linear-gradient(90deg, #1E2A56, #2A3A78);
                                                                                    color: white;
                                                                                    text-align: left;
                                                                                    padding: 10px;
                                                                                    font-weight: 700;
                                                                                    font-size: 11px;
                                                                                }}
                                                                                
                                                                                .payment-table td {{
                                                                                    border: 1px solid #d1d9f0;
                                                                                    padding: 10px;
                                                                                    font-size: 11px;
                                                                                }}
                                                                                
                                                                                .payment-table tr:nth-child(even) {{
                                                                                    background-color: #f9faff;
                                                                                }}
                                                                                
                                                                                ul, ol {{
                                                                                    margin: 10px 0;
                                                                                    padding-left: 20px;
                                                                                    line-height: 1.4;
                                                                                }}
                                                                                
                                                                                li {{
                                                                                    margin-bottom: 10px;
                                                                                    font-size: 11px;
                                                                                    color: #1E2A56;
                                                                                }}
                                                                                
                                                                                .terms-box {{
                                                                                    background: #f8faff;
                                                                                    border-left: 4px solid #1E2A56;
                                                                                    padding: 10px;
                                                                                    margin: 10px 0;
                                                                                    border-radius: 0 8px 8px 0;
                                                                                }}
                                                                                
                                                                                /* Signature area at bottom of each page */
                                                                                .signature-area {{
                                                                                    font-size: 8px;
                                                                                    position: fixed;
                                                                                    bottom: 5px;
                                                                                    left: 40px;
                                                                                    right: 40px;
                                                                                    padding-top: 8px;
                                                                                    border: 1px solid #1E2A56;
                                                                                    border-radius: 8px;
                                                                                    background: #f8faff;
                                                                                    z-index: 100;
                                                                                }}
                                                                                
                                                                                .signature-block {{
                                                                                    display: flex;
                                                                                    justify-content: space-between;
                                                                                    margin-top: 8px;
                                                                                }}
                                                                                
                                                                                .signature-line {{
                                                                                    flex: 1;
                                                                                    margin: 0 10px;
                                                                                }}
                                                                                
                                                                                .signature-label {{
                                                                                    font-weight: 700;
                                                                                    font-size: 10px;
                                                                                    margin-bottom: 5px;
                                                                                    display: block;
                                                                                    color: #2A3A78;
                                                                                }}
                                                                                
                                                                                .signature-space {{
                                                                                    height: 30px;
                                                                                    border-bottom: 1px solid #1E2A56;
                                                                                    margin-top: 3px;
                                                                                }}
                                                                                
                                                                                .signature-date {{
                                                                                    font-size: 10px;
                                                                                    color: #666;
                                                                                    margin-top: 5px;
                                                                                }}
                                                                                
                                                                                .footer-note {{
                                                                                    text-align: center;
                                                                                    font-size: 10px;
                                                                                    color: #888;
                                                                                    margin-top: 10px;
                                                                                    font-style: italic;
                                                                                }}
                                                                                
                                                                                /* Page number styling */
                                                                                .page-number {{
                                                                                    position: fixed;
                                                                                    bottom: 15px;
                                                                                    left: 40px;
                                                                                    font-size: 10px;
                                                                                    color: #666;
                                                                                }}
                                                                                
                                                                                .total-pages {{
                                                                                    position: fixed;
                                                                                    bottom: 15px;
                                                                                    right: 40px;
                                                                                    font-size: 10px;
                                                                                    color: #666;
                                                                                }}
                                                                                
                                                                                /* Print styles */
                                                                                @media print {{
                                                                                    .signature-area {{
                                                                                        position: fixed;
                                                                                        bottom: 5px;
                                                                                    }}
                                                                                    
                                                                                    .page-break {{
                                                                                        page-break-after: always;
                                                                                    }}
                                                                                }}
                                                                            </style>
                                                                        </head>
                                                                        <body>
                                                                            <div class="watermark">CONNECTLINK</div>
                                                                            
                                                                            <div class="agreement-container">
                                                                                <!-- Page 1 -->
                                                                                <img class="logo" src="data:image/png;base64,{{logo_base64}}" alt="ConnectLink Logo">
                                                                                
                                                                                <h3 class="title">Construction Agreement</h3>
                                                                                <div class="subtitle-line"></div>
                                                                                
                                                                                <div class="highlight-box">
                                                                                    <p style="text-align: center; font-weight: 700; margin: 0;">
                                                                                        This Construction Agreement ("Agreement") is made and entered into on 
                                                                                        <span style="color: #1E2A56; text-decoration: underline;">{project['agreement_date']}</span> 
                                                                                        ("Effective Date") by and between the parties below:
                                                                                    </p>
                                                                                </div>
                                                                                
                                                                                <h4 class="section-title">PARTIES TO THE AGREEMENT</h4>
                                                                                
                                                                                <div class="section-header">CLIENT DETAILS</div>
                                                                                <div class="field-row"><div class="field-label">Full Name:</div><div class="field-value">{project['client_name']}</div></div>
                                                                                <div class="field-row"><div class="field-label">National ID:</div><div class="field-value">{project['client_idnumber']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Address:</div><div class="field-value">{project['client_address']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Contact Number:</div><div class="field-value">0{project['client_whatsapp']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Email:</div><div class="field-value">{project['client_email']}</div></div>
                                                                                
                                                                                <div class="section-header">NEXT OF KIN DETAILS</div>
                                                                                <div class="field-row"><div class="field-label">Full Name:</div><div class="field-value">{project['next_of_kin_name']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Address:</div><div class="field-value">{project['next_of_kin_address']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Contact Number:</div><div class="field-value">0{project['next_of_kin_phone']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Relationship:</div><div class="field-value">{project['relationship']}</div></div>
                                                                                

                                                                                <div class="section-header">CONTRACTOR DETAILS</div>
                                                                                <div class="field-row"><div class="field-label">Company Name:</div><div class="field-value">{project['companyname']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Address:</div><div class="field-value">{project['companyaddress']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Contact Numbers:</div><div class="field-value">0{project['companycontact1']} / 0{project['companycontact2']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Email:</div><div class="field-value">{project['companyemail']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Project Administrator:</div><div class="field-value">{project['project_administrator']}</div></div>
                                                                                
                                                                                <!-- Page break -->
                                                                                <div class="page-break"></div>
                                                                                
                                                                                <!-- Page 2 -->

                                                                                <h4 class="section-title">PROJECT DETAILS</h4>
                                                                                <div class="field-row"><div class="field-label">Project Name:</div><div class="field-value">{project['project_name']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Project Location:</div><div class="field-value">{project['project_location']}</div></div>
                                                                                
                                                                                <div class="section-header">PROJECT SCOPE</div>
                                                                                <div class="scope-box">{project['project_description']}</div>
                                                                            

                                                                                <h4 class="section-title">PAYMENT TERMS</h4>
                                                                                <div class="field-row"><div class="field-label">Total Contract Price:</div><div class="field-value" style="font-weight: 700; color: #1E2A56;">USD {project['total_contract_price']}</div></div>
                                                                                <div class="field-row"><div class="field-label">Deposit Required:</div><div class="field-value" style="font-weight: 700; color: #1E2A56;">USD {project['depositorbullet']}</div></div>
                                                                                
                                                                                <div class="section-header">PAYMENT SCHEDULE</div>
                                                                                <table class="payment-table">
                                                                                    <thead>
                                                                                        <tr>
                                                                                            <th style="width: 60%;">Installment Due Date</th>
                                                                                            <th style="width: 40%;">Amount (USD)</th>
                                                                                        </tr>
                                                                                    </thead>
                                                                                    <tbody>
                                                                                        <tr><td>{project['installment1duedate']}</td><td style="font-weight: 700;">{project['installment1amount']}</td></tr>
                                                                                        <tr><td>{project['installment2duedate']}</td><td style="font-weight: 700;">{project['installment2amount']}</td></tr>
                                                                                        <tr><td>{project['installment3duedate']}</td><td style="font-weight: 700;">{project['installment3amount']}</td></tr>
                                                                                        <tr><td>{project['installment4duedate']}</td><td style="font-weight: 700;">{project['installment4amount']}</td></tr>
                                                                                        <tr><td>{project['installment5duedate']}</td><td style="font-weight: 700;">{project['installment5amount']}</td></tr>
                                                                                        <tr><td>{project['installment6duedate']}</td><td style="font-weight: 700;">{project['installment6amount']}</td></tr>
                                                                                    </tbody>
                                                                                </table>
                                                                                
                                                                                <!-- Page break -->
                                                                                <div class="page-break"></div>
                                                                                
                                                                                <!-- Page 3 -->

                                                                                <h4 class="section-title">TERMS AND CONDITIONS</h4>
                                                                                
                                                                                <div class="section-header">LATE PAYMENT AND INTEREST</div>
                                                                                <div class="terms-box">
                                                                                    <ul style="list-style-type: circle;">
                                                                                        <li>If the Client fails to make any payment on or before the due date, the Client shall be liable to pay interest at a rate of <strong>{project['latepaymentinterest']}%</strong> per annum.</li>
                                                                                        <li>Interest is calculated daily and compounded monthly from the due date until full payment is received.</li>
                                                                                        <li>All payments shall first be applied to interest due, then to the principal amount.</li>
                                                                                    </ul>
                                                                                </div>
                                                                                
                                                                                <div class="section-header">PROJECT TIMELINE</div>
                                                                                <ol>
                                                                                    <li>The Contractor shall commence work within <strong>{project['days_difference']} days</strong> of receiving the first payment.</li>
                                                                                    <li>The Contractor shall complete the project within <strong>{project['project_duration']} days</strong> from commencement date.</li>
                                                                                    <li>The Client shall make payments strictly as per the payment schedule outlined above.</li>
                                                                                    <li>The Client is responsible for obtaining all required permits and approvals from local authorities.</li>
                                                                                    <li>The Contractor is responsible for all materials, labor, and workmanship as per industry standards.</li>
                                                                                </ol>
                                                                                

                                                                                <div class="section-header">OWNERSHIP CLAUSE</div>
                                                                                <div class="terms-box">
                                                                                    <ul style="list-style-type: circle;">
                                                                                        <li>All installed items, materials, and equipment remain the property of <strong>ConnectLink Properties</strong> until full and final payment is received from the Client.</li>
                                                                                        <li>ConnectLink Properties reserves the right to remove, repossess, or withhold any installed items should the Client fail to make payments within the stipulated timelines.</li>
                                                                                        <li>Ownership transfers to the Client only upon settlement of the entire contract amount.</li>
                                                                                    </ul>
                                                                                </div>
                                                                                
                                                                                <div class="section-header">DESIGN CONFIRMATION</div>
                                                                                <div class="terms-box">
                                                                                    <ul style="list-style-type: circle;">
                                                                                        <li>Signing of this contract and payment of the deposit constitutes acknowledgement, confirmation, and authorization to proceed with construction of the proposed design submitted with the quotation.</li>
                                                                                        <li>Any alterations or modifications must be communicated and agreed upon <strong>before</strong> signing this contract.</li>
                                                                                        <li>All additions or variations to the approved design will be treated as change orders and will incur additional costs, billed separately or added to the original quotation.</li>
                                                                                    </ul>
                                                                                </div>

                                                                                <!-- Page break -->
                                                                                <div class="page-break"></div>
                                                                                
                                                                                <!-- Page 4 -->

                                                                                <div class="section-header">POWER PROVISION</div>
                                                                                <div class="terms-box">
                                                                                    <p style="font-size:11px;">In the event of power outages requiring electricity for construction activities, the Client shall provide a suitable generator and fuel at their own expense for the duration required.</p>
                                                                                </div>
                                                                                
                                                                                <div class="section-header">TERMINATION</div>
                                                                                <div class="terms-box">
                                                                                    <p style="font-size:11px;">This Agreement may be terminated by either party if the other party:</p>
                                                                                    <ol>
                                                                                        <li>Fails to perform any material obligation under this Agreement and such failure continues for 30 days after written notice.</li>
                                                                                        <li>Becomes insolvent, bankrupt, or enters into receivership.</li>
                                                                                        <li>Breaches any term of this Agreement causing substantial harm to the other party.</li>
                                                                                    </ol>
                                                                                </div>
                                                                                
                                                                                <div class="section-header">DISPUTE RESOLUTION</div>
                                                                                <div class="terms-box">
                                                                                    <p style="font-size:11px;">Any disputes arising from this Agreement shall be resolved through amicable negotiation. If unresolved within 30 days, the matter shall be referred to arbitration under the Arbitration Act of Zimbabwe by a single arbitrator appointed by mutual agreement.</p>
                                                                                </div>
                                                                                
                                                                                <div class="section-header">GOVERNING LAW</div>
                                                                                <div class="terms-box">
                                                                                    <p style="font-size:11px;">This Agreement shall be governed by and construed in accordance with the laws of the Republic of Zimbabwe. The courts of Zimbabwe shall have exclusive jurisdiction over any matters arising from this Agreement.</p>
                                                                                </div>
                                                                                
                                                                                <div class="section-header">ENTIRE AGREEMENT</div>
                                                                                <div class="terms-box">
                                                                                    <p style="font-size:11px;">This document constitutes the entire agreement between the parties and supersedes all prior discussions, negotiations, and agreements. No modification shall be valid unless in writing and signed by both parties.</p>
                                                                                </div>
                                                                                
                                                                            </div>
                                                                            
                                                                            <!-- Signature Area (will appear at bottom of each page) -->
                                                                            <div class="signature-area">
                                                                                <div class="signature-block">
                                                                                    <div class="signature-line">
                                                                                        <span class="signature-label">CLIENT SIGNATURE</span>
                                                                                        <div class="signature-space"></div>
                                                                                        <div class="signature-date">Date: {project['agreement_date']}</div>
                                                                                    </div>
                                                                                    
                                                                                    <div class="signature-line">
                                                                                        <span class="signature-label">CONTRACTOR SIGNATURE</span>
                                                                                        <div class="signature-space"></div>
                                                                                        <div class="signature-date">Date: {project['agreement_date']}</div>
                                                                                    </div>
                                                                                </div>
                                                                                <div class="footer-note" style="margin-top: 5px;font-weight:bold;color: black;">
                                                                                    This is a legally binding document. Please read carefully before signing.
                                                                                </div>   
                                                                            </div>
                                                                        </body>
                                                                        </html>
                                                                    """
                                                                    return html_template


                                                                def send_pdf_via_whatsapp(recipient_number, pdf_bytes, filename, caption):
                                                                    """Send PDF via WhatsApp"""
                                                                    try:
                                                                        import io

                                                                        # Upload to WhatsApp
                                                                        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
                                                                        headers = {
                                                                            "Authorization": f"Bearer {ACCESS_TOKEN}"
                                                                        }
                                                                        
                                                                        files = {
                                                                            "file": (filename, io.BytesIO(pdf_bytes), "application/pdf"),
                                                                            "type": (None, "application/pdf"),
                                                                            "messaging_product": (None, "whatsapp")
                                                                        }
                                                                        
                                                                        response = requests.post(url, headers=headers, files=files)
                                                                        response.raise_for_status()
                                                                        media_id = response.json()["id"]
                                                                        
                                                                        # Send PDF
                                                                        doc_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                        doc_headers = {
                                                                            "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                            "Content-Type": "application/json"
                                                                        }
                                                                        
                                                                        doc_payload = {
                                                                            "messaging_product": "whatsapp",
                                                                            "to": recipient_number,
                                                                            "type": "document",
                                                                            "document": {
                                                                                "id": media_id,
                                                                                "filename": filename,
                                                                                "caption": caption
                                                                            }
                                                                        }
                                                                        
                                                                        response = requests.post(doc_url, headers=doc_headers, json=doc_payload)
                                                                        response.raise_for_status()
                                                                        return True
                                                                        
                                                                    except Exception as e:
                                                                        print(f"❌ Error sending PDF: {e}")
                                                                        return False


                                                                def send_whatsapp_message(recipient_number, message):
                                                                    """Send text message via WhatsApp"""
                                                                    try:
                                                                        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                        headers = {
                                                                            "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                            "Content-Type": "application/json"
                                                                        }
                                                                        
                                                                        payload = {
                                                                            "messaging_product": "whatsapp",
                                                                            "to": recipient_number,
                                                                            "type": "text",
                                                                            "text": {"body": message}
                                                                        }
                                                                        
                                                                        response = requests.post(url, headers=headers, json=payload)
                                                                        return response.status_code == 200
                                                                        
                                                                    except Exception as e:
                                                                        print(f"❌ Error sending message: {e}")
                                                                        return False


                                                                try:
                                                                    # Extract last 9 digits from sender_id
                                                                    if sender_id and len(sender_id) >= 9:
                                                                        client_whatsapp = int(sender_id[-9:])
                                                                    else:
                                                                        client_whatsapp = int(sender_id) if sender_id and sender_id.isdigit() else None
                                                                    
                                                                    if not client_whatsapp:
                                                                        return jsonify({'status': 'error', 'message': 'Invalid WhatsApp number'}), 400
                                                                    
                                                                    with get_db() as (cursor, connection):
                                                                        # Get ALL user's contracts
                                                                        cursor.execute("""
                                                                            SELECT * FROM connectlinkdatabase 
                                                                            WHERE clientwanumber = %s
                                                                            ORDER BY projectstartdate DESC
                                                                        """, (client_whatsapp,))
                                                                        
                                                                        rows = cursor.fetchall()
                                                                        
                                                                        if not rows:
                                                                            message = f"📋 No contracts found for your WhatsApp number."
                                                                            send_whatsapp_message(sender_id, message)
                                                                            return jsonify({'status': 'success', 'message': 'No contracts found'})
                                                                        
                                                                        # Send summary message
                                                                        summary = f"""
                                                                            📋 *YOUR CONTRACTS - CONNECTLINK PROPERTIES*

                                                                            Found {len(rows)} contract(s) for your WhatsApp number.

                                                                            _Sending contract documents now..._
                                                                                        """
                                                                        # send_whatsapp_message(sender_id, summary)
                                                                        
                                                                        # Process each contract
                                                                        for i, row in enumerate(rows):
                                                                            try:
                                                                                print(f"📄 Generating contract {i+1}/{len(rows)}")
                                                                                
                                                                                # Generate PDF using your template
                                                                                pdf_bytes = generate_contract_pdf(row, cursor)
                                                                                
                                                                                if pdf_bytes:
                                                                                    # Send contract via WhatsApp
                                                                                    filename = f"Contract_{row[1]}_{row[10]}_{row[0]}.pdf"
                                                                                    send_pdf_via_whatsapp(sender_id, pdf_bytes, filename, f"Contract: {row[10]}")
                                                                                    
                                                                                    # Send progress update
                                                                                    if i < len(rows) - 1:
                                                                                        time.sleep(2)  # Delay between sends
                                                                                
                                                                            except Exception as e:
                                                                                print(f"❌ Error with contract {i+1}: {e}")
                                                                                error_msg = f"⚠️ Could not send contract {i+1}. Will try next one."
                                                                                send_whatsapp_message(sender_id, error_msg)
                                                                                continue
                                                                        
                                                                        # Final message
                                                                        final_msg = f"""
                                                                            ✅ See attached {len(rows)} contract document(s).

                                                                            _Thank you for choosing Connectlink Properties!_
                                                                                        """
                                                                        # send_whatsapp_message(sender_id, final_msg)


                                                                        
                                                                        buttons = [
                                                                            {
                                                                                "type": "reply",
                                                                                "reply": {
                                                                                    "id": "contracts",
                                                                                    "title": "My Contracts"
                                                                                }
                                                                            },
                                                                            {
                                                                                "type": "reply",
                                                                                "reply": {
                                                                                    "id": "paymenthist",
                                                                                    "title": "My Payments History"
                                                                                }
                                                                            },
                                                                            {
                                                                                "type": "reply",
                                                                                "reply": {
                                                                                    "id": "enquirylog",
                                                                                    "title": "Enquiries"
                                                                                }
                                                                            }
                                                                        ]


                                                                        send_whatsapp_button_message(
                                                                            sender_id, 
                                                                            f"{final_msg} \n\n How else can we assist you today {profile_name}?.",
                                                                            buttons,
                                                                            footer_text="ConnectLink Properties • Client Panel"

                                                                        )
                                                                        
                                                                        return jsonify({
                                                                            'status': 'success', 
                                                                            'message': f'Sent {len(rows)} contracts',
                                                                            'count': len(rows)
                                                                        })
                                                                        
                                                                except Exception as e:
                                                                    print(f"❌ Error in contracts handler: {str(e)}")
                                                                    return jsonify({'status': 'error', 'message': str(e)}), 500

                                                            elif button_id == "main_menu" or selected_option == "main_menu":

                                                                buttons = [
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "contracts",
                                                                            "title": "My Contracts"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "paymenthist",
                                                                            "title": "My Payments History"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "enquirylog",
                                                                            "title": "Enquiries"
                                                                        }
                                                                    }
                                                                ]


                                                                send_whatsapp_button_image_message(
                                                                    sender_id, 
                                                                    f"👋 Hey {profile_name}, Welcome to ConnectLink Properties! \n\n How can we assist you today?.",
                                                                    "https://connectlink-wbax.onrender.com/static/images/reqlogo.jpg",
                                                                    buttons,
                                                                    footer_text="ConnectLink Properties • Client Panel"

                                                                )

                                                                continue




                                                        else:

                                                            text = message.get("text", {}).get("body", "").lower()
                                                            print(f"📨 Message from {sender_id}: {text}")
                                                            
                                                            print("yearrrrrrrrrrrrrrrrrrrrrrrrrrrssrsrsrsrsrs")

                                                            
                                                            buttons = [
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "contracts",
                                                                        "title": "My Contracts"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "paymenthist",
                                                                        "title": "My Payments History"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "enquirylog",
                                                                        "title": "Enquiries"
                                                                    }
                                                                }
                                                            ]


                                                            send_whatsapp_button_image_message(
                                                                sender_id, 
                                                                f"👋 Hey {profile_name}, Welcome to ConnectLink Properties! \n\n How can we assist you today?.",
                                                                "https://connectlink-wbax.onrender.com/static/images/reqlogo.jpg",
                                                                buttons,
                                                                footer_text="ConnectLink Properties • Client Panel"

                                                            )

                                                            continue


                                                    except Exception as e:
                                                        print(e)



                                                elif not result2:

                                                    try:
                                                    
                                                        if message.get("type") == "interactive":
                                                            interactive = message.get("interactive", {})


                                                            if interactive.get("type") == "list_reply":
                                                                selected_option = interactive.get("list_reply", {}).get("id")
                                                                print(f"📋 User selected: {selected_option}")
                                                                button_id = ""

                                                            elif interactive.get("type") == "button_reply":
                                                                button_id = interactive.get("button_reply", {}).get("id")
                                                                print(f"🔘 Button clicked: {button_id}")
                                                                selected_option = ""


                                                            elif interactive.get("type") == "nfm_reply":

                                                                url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                headers = {
                                                                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                    "Content-Type": "application/json"
                                                                }

                                                                response_str = interactive.get("nfm_reply", {}).get("response_json", "{}")
                                                                selected_option = ""
                                                                button_id = ""

                                                                print("📋 Raw nfm_reply response_json:", response_str)

                                                                try:
                                                                    form_response = json.loads(response_str)
                                                                    print("✅ Parsed form_response:", form_response)
                                                                except Exception as e:
                                                                    print("❌ Error parsing nfm_reply response_json:", e)
                                                                    form_response = {}

                                                                print("🔍 Parsing form fields from form_response:")

                                                                query = f"""
                                                                    SELECT * FROM appenqtemp
                                                                    WHERE wanumber::TEXT LIKE %s
                                                                """
                                                                cursor.execute(query, (f"%{sender_id[-9:]}",))
                                                                resultenqtemp = cursor.fetchone()

                                                                enquiry_type = resultenqtemp[2]

                                                                if enquiry_type:

                                                                    query = """
                                                                        DELETE FROM appenqtemp
                                                                        WHERE wanumber::TEXT LIKE %s
                                                                    """
                                                                    cursor.execute(query, (f"%{sender_id[-9:]}",))
                                                                    connection.commit

                                                                # The form_response is already in the clean format we need
                                                                user_message = form_response.get("details", "")
                                                                attachment_list = form_response.get("attachment", [])
                                                                flow_token = form_response.get("flow_token", "")

                                                                print("Values from form_response:")
                                                                print("enquiry_type:", enquiry_type, type(enquiry_type))
                                                                print("user_message:", user_message, type(user_message))
                                                                print("attachment_list:", attachment_list, type(attachment_list))
                                                                print("flow_token:", flow_token)

                                                                # Validate required fields
                                                                if not enquiry_type:
                                                                    print("❌ No enquiry_type found in form response")
                                                                    print("❌ Full form_response:", json.dumps(form_response, indent=2))
                                                                    return jsonify({'status': 'error', 'message': 'Enquiry type is required'}), 400

                                                                # Map enquiry type IDs to display names
                                                                enquiry_type_map = {
                                                                    'kitchen_cabinets': 'Kitchen & Cabinets',
                                                                    'building': 'Building',
                                                                    'renovation': 'Renovation',
                                                                    'otherenq': 'Other'
                                                                }

                                                                enquiry_type_display = enquiry_type_map.get(enquiry_type, enquiry_type)

                                                                print(f"✅ Enquiry type display: {enquiry_type_display}")

                                                                # Process attachment if exists
                                                                attachment_data = None
                                                                has_attachment = False

                                                                if attachment_list and isinstance(attachment_list, list) and len(attachment_list) > 0:
                                                                    print("Processing attachment...")
                                                                    has_attachment = True
                                                                    
                                                                    # The attachment is an object with id, mime_type, sha256, file_name
                                                                    attachment_info = attachment_list[0]
                                                                    attachment_id = attachment_info.get('id')
                                                                    file_name = attachment_info.get('file_name', 'document.pdf')
                                                                    
                                                                    print(f"Attachment info: ID={attachment_id}, File={file_name}")
                                                                    
                                                                    # We need to download the actual file using the attachment ID
                                                                    # WhatsApp provides a separate endpoint for downloading media
                                                                    if attachment_id:
                                                                        try:
                                                                            # First, get the media URL
                                                                            media_url = f"https://graph.facebook.com/v19.0/{attachment_id}"
                                                                            headers = {
                                                                                "Authorization": f"Bearer {ACCESS_TOKEN}"
                                                                            }
                                                                            
                                                                            print(f"📥 Downloading media from: {media_url}")
                                                                            response = requests.get(media_url, headers=headers)
                                                                            response.raise_for_status()
                                                                            media_info = response.json()
                                                                            
                                                                            print(f"Media info: {media_info}")
                                                                            
                                                                            # Get the actual download URL
                                                                            download_url = media_info.get('url')
                                                                            if download_url:
                                                                                # Download the file
                                                                                print(f"📥 Downloading file from: {download_url}")
                                                                                file_response = requests.get(download_url, headers=headers)
                                                                                file_response.raise_for_status()
                                                                                
                                                                                attachment_data = file_response.content
                                                                                print(f"✅ Attachment downloaded, size: {len(attachment_data)} bytes")
                                                                            else:
                                                                                print("❌ No download URL found in media info")
                                                                                attachment_data = None
                                                                                
                                                                        except Exception as e:
                                                                            print(f"❌ Error downloading attachment: {e}")
                                                                            attachment_data = None
                                                                else:
                                                                    print("No attachment found in the response")


                                                                # Save to database
                                                                with get_db() as (cursor, connection):
                                                                    insert_query = """
                                                                        INSERT INTO connectlinkenquiries 
                                                                        (timestamp, clientwhatsapp, enqcategory, enq, plan, username)
                                                                        VALUES (%s, %s, %s, %s, %s, %s)
                                                                        RETURNING id;
                                                                    """
                                                                    
                                                                    timestamp = datetime.now()
                                                                    client_whatsapp = int(sender_id[-9:]) if sender_id.isdigit() else None
                                                                    
                                                                    print(f"✅ Saving to database:")
                                                                    print(f"  - timestamp: {timestamp}")
                                                                    print(f"  - clientwhatsapp: {client_whatsapp}")
                                                                    print(f"  - enqcategory: {enquiry_type_display}")
                                                                    print(f"  - enq: {user_message}")
                                                                    print(f"  - plan: {'Yes' if attachment_data else 'No'}")
                                                                    
                                                                    cursor.execute(
                                                                        insert_query,
                                                                        (
                                                                            timestamp,
                                                                            client_whatsapp,
                                                                            enquiry_type_display,
                                                                            user_message or '',
                                                                            attachment_data,
                                                                            profile_name
                                                                        )
                                                                    )
                                                                    
                                                                    enquiry_id = cursor.fetchone()[0]
                                                                    connection.commit()
                                                                    
                                                                    print(f"✅ Enquiry saved with ID: {enquiry_id}")
                                                                    
                                                                    # Send confirmation message to user
                                                                    confirmation_message = f"""
                                                                        ✅ *Your Enquiry has been successfully submitted to ConnectLink Properties Admin, {profile_name}!*

                                                                        📋 *Reference ID:* #{enquiry_id}
                                                                        📅 *Date:* {timestamp.strftime('%d %B %Y %H:%M')}
                                                                        🏷️ *Category:* {enquiry_type_display}
                                                                        {'📎 *Attachment:* Yes' if has_attachment else ''}

                                                                        Thank you for your enquiry. Our team will contact you within 24 hours.

                                                                        _For urgent matters, please call our office._
                                                                        """
                                                                    
                                                                    print(f"✅ Sending confirmation to {sender_id}")
                                                                    
                                                                    # Send WhatsApp confirmation
                                                                    buttons = [
                                                                        {
                                                                            "type": "reply",
                                                                            "reply": {
                                                                                "id": "enquirylog",
                                                                                "title": "Enquiries"
                                                                            }
                                                                        },
                                                                        {
                                                                            "type": "reply",
                                                                            "reply": {
                                                                                "id": "contact",
                                                                                "title": "Contact Us"
                                                                            }
                                                                        },
                                                                        {
                                                                            "type": "reply",
                                                                            "reply": {
                                                                                "id": "about",
                                                                                "title": "About Us"
                                                                            }
                                                                        }
                                                                    ]


                                                                    send_whatsapp_button_image_message(
                                                                        sender_id, 
                                                                        f"{confirmation_message} \n\n How else can we assist you today?.",
                                                                        "https://connectlink-wbax.onrender.com/static/images/reqlogo.jpg",
                                                                        buttons,
                                                                        footer_text="ConnectLink Properties • Client Panel"

                                                                    )

                                                                    
                                                                    # Also notify admin/team
                                                                    admin_notification = f"""
                                                                        🔔 *NEW ENQUIRY RECEIVED*

                                                                        📋 *Reference ID:* #{enquiry_id}
                                                                        📱 *Client WhatsApp:* {sender_id}
                                                                        📅 *Timestamp:* {timestamp.strftime('%d %B %Y %H:%M')}
                                                                        🏷️ *Category:* {enquiry_type_display}
                                                                        📝 *Details:* {user_message or 'No additional details'}
                                                                        📎 *Attachment:* {'Yes' if has_attachment else 'No'}

                                                                        Please follow up with the client.
                                                                        """
                                                                    
                                                                    # Send to admin/team
                                                                    admin_numbers = ["263774822568"]
                                                                    
                                                                    for admin_number in admin_numbers:
                                                                        print(f"✅ Notifying admin: {admin_number}")
                                                                        send_whatsapp_message(
                                                                            admin_number,
                                                                            admin_notification
                                                                        )
                                                                    
                                                                    return jsonify({
                                                                        'status': 'success',
                                                                        'message': 'Enquiry saved successfully',
                                                                        'enquiry_id': enquiry_id,
                                                                        'data': {
                                                                            'enquiry_type': enquiry_type,
                                                                            'details': user_message,
                                                                            'has_attachment': has_attachment,
                                                                            'attachment_info': attachment_list[0] if attachment_list else None
                                                                        }
                                                                    })


                                                            if button_id == "enquirylog":

                                                                sections = [
                                                                    {
                                                                        "title": "Enquiries Options",
                                                                        "rows": [
                                                                            {
                                                                                "id": "kitchen_cabinets",
                                                                                "title": "Kitchen & Cabinets",
                                                                                "description": "Kitchen and Cabinets enquiries"
                                                                            },
                                                                            {
                                                                                "id": "building",
                                                                                "title": "Building",
                                                                                "description": "Building enquiries"
                                                                            },
                                                                            {
                                                                                "id": "renovation",
                                                                                "title": "Renovation",
                                                                                "description": "Renovation enquiries"
                                                                            },
                                                                            {
                                                                                "id": "other",
                                                                                "title": "Other",
                                                                                "description": "Other enquiries"
                                                                            },
                                                                            {
                                                                                "id": "main_menu",
                                                                                "title": "Main Menu",
                                                                                "description": "Return to main menu"
                                                                            }
                                                                        ]
                                                                    }
                                                                ]

                                                                send_whatsapp_list_message(
                                                                    sender_id,
                                                                    "Kindly select an enquiry option below.",
                                                                    "ConnectLink Enquiries",
                                                                    sections,
                                                                    footer_text="ConnectLink Properties • Client Panel"
                                                                )

                                                            elif selected_option in ["kitchen_cabinets","building","renovation","other"]:

                                                                with get_db() as (cursor, connection):
                                                                    insert_query = """
                                                                        INSERT INTO appenqtemp 
                                                                        (wanumber, enqtype)
                                                                        VALUES (%s, %s)
                                                                        RETURNING id;
                                                                    """
                                                                    
                                                                    digits = "".join(filter(str.isdigit, sender_id))
                                                                    client_whatsapp = int(digits[-9:]) if len(digits) >= 9 else None
                                                                    
                                                                    cursor.execute(
                                                                        insert_query,
                                                                        (
                                                                            client_whatsapp,
                                                                            selected_option
                                                                        )
                                                                    )

                                                                    connection.commit()

                                                                buttons = [
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "enquirylog",
                                                                            "title": "Enquiries"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "contact",
                                                                            "title": "Contact Us"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "about",
                                                                            "title": "About Us"
                                                                        }
                                                                    }
                                                                ]

                                                                if selected_option == "kitchen_cabinets":

                                                                    send_whatsapp_message(
                                                                        sender_id,
                                                                        f"Good day {profile_name},\n\n"
                                                                        "At Connectlink Kitchens and Cabinets, we specialise in the design and installation of kitchen cabinets, built-in wardrobes, bathroom vanities and TV units.\n\n"
                                                                        "We are offering these services on credit:\n"
                                                                        "- 30% deposit\n"
                                                                        "- Installation within 10 working days\n"
                                                                        "- Balance payable over 3 months\n\n"
                                                                        "We offer free 3D designs and quotations. Send your house plan or measurements via the Fill Enquiries Form below, or request a site visit.\n\n"
                                                                        "Site visits within 20km of Harare CBD cost USD $10.",
                                                                        buttons,
                                                                        footer_text="ConnectLink Properties • Client Panel"
                                                                    )


                                                                payload = {
                                                                    "messaging_product": "whatsapp",
                                                                    "to": sender_id,
                                                                    "type": "template",
                                                                    "template": {
                                                                        "name": "enquiries",  # your template name
                                                                        "language": {"code": "en"},
                                                                        "components": [
                                                                            {
                                                                                "type": "button",
                                                                                "index": "0",
                                                                                "sub_type": "flow",
                                                                                "parameters": [
                                                                                    {
                                                                                        "type": "action",
                                                                                        "action": {
                                                                                        "flow_token": "unused"
                                                                                        }
                                                                                    }
                                                                                ]
                                                                                        # button index in your template
                                                                            }
                                                                        ]
                                                                    }
                                                                }

                                                                response = requests.post(
                                                                    f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages",
                                                                    headers={
                                                                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                        "Content-Type": "application/json"
                                                                    },
                                                                    json=payload
                                                                ) 

                                                                print(response.status_code)
                                                                print(response.text)










                                                                continue



                                                            elif button_id == "enquirylogx":


                                                                payload = {
                                                                    "messaging_product": "whatsapp",
                                                                    "to": sender_id,
                                                                    "type": "template",
                                                                    "template": {
                                                                        "name": "enquiries",  # your template name
                                                                        "language": {"code": "en"},
                                                                        "components": [
                                                                            {
                                                                                "type": "button",
                                                                                "index": "0",
                                                                                "sub_type": "flow",
                                                                                "parameters": [
                                                                                    {
                                                                                        "type": "action",
                                                                                        "action": {
                                                                                        "flow_token": "unused"
                                                                                        }
                                                                                    }
                                                                                ]
                                                                                        # button index in your template
                                                                            }
                                                                        ]
                                                                    }
                                                                }

                                                                response = requests.post(
                                                                    f"https://graph.facebook.com/v17.0/{PHONE_NUMBER_ID}/messages",
                                                                    headers={
                                                                        "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                        "Content-Type": "application/json"
                                                                    },
                                                                    json=payload
                                                                ) 

                                                                print(response.status_code)
                                                                print(response.text)



                                                                continue

                                                            elif button_id == "about":

                                                                def generate_company_profile_pdf():
                                                                    """Generate Connectlink Properties company profile as PDF"""
                                                                    try:
                                                                        from weasyprint import HTML
                                                                        import io
                                                                        
                                                                        html_content = """
                                                                        <!DOCTYPE html>
                                                                        <html>
                                                                        <head>
                                                                            <meta charset="UTF-8">
                                                                            <style>
                                                                                @page {
                                                                                    size: A4;
                                                                                    margin: 2cm;
                                                                                    @bottom-center {
                                                                                        content: "Connectlink Properties • Page " counter(page) " of " counter(pages);
                                                                                        font-size: 10px;
                                                                                        color: #666;
                                                                                    }
                                                                                }
                                                                                
                                                                                body {
                                                                                    font-family: 'Helvetica', 'Arial', sans-serif;
                                                                                    line-height: 1.6;
                                                                                    color: #333;
                                                                                    margin: 0;
                                                                                    padding: 0;
                                                                                }
                                                                                
                                                                                .header {
                                                                                    text-align: center;
                                                                                    margin-bottom: 30px;
                                                                                    padding-bottom: 20px;
                                                                                    border-bottom: 3px solid #1E2A56;
                                                                                }
                                                                                
                                                                                .company-name {
                                                                                    font-size: 28px;
                                                                                    font-weight: bold;
                                                                                    color: #1E2A56;
                                                                                    margin-bottom: 5px;
                                                                                }
                                                                                
                                                                                .tagline {
                                                                                    font-size: 16px;
                                                                                    color: #666;
                                                                                    font-style: italic;
                                                                                }
                                                                                
                                                                                .contact-info {
                                                                                    background: #f8f9fa;
                                                                                    padding: 15px;
                                                                                    border-radius: 8px;
                                                                                    margin: 20px 0;
                                                                                    text-align: center;
                                                                                    border-left: 4px solid #1E2A56;
                                                                                }
                                                                                
                                                                                .section {
                                                                                    margin-bottom: 25px;
                                                                                    page-break-inside: avoid;
                                                                                }
                                                                                
                                                                                .section-title {
                                                                                    color: #1E2A56;
                                                                                    border-bottom: 2px solid #1E2A56;
                                                                                    padding-bottom: 8px;
                                                                                    margin-bottom: 15px;
                                                                                    font-size: 20px;
                                                                                }
                                                                                
                                                                                .services-grid {
                                                                                    display: grid;
                                                                                    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
                                                                                    gap: 15px;
                                                                                    margin-top: 15px;
                                                                                }
                                                                                
                                                                                .service-card {
                                                                                    background: #f8f9fa;
                                                                                    padding: 15px;
                                                                                    border-radius: 6px;
                                                                                    border: 1px solid #dee2e6;
                                                                                }
                                                                                
                                                                                .service-title {
                                                                                    color: #1E2A56;
                                                                                    font-weight: bold;
                                                                                    margin-bottom: 8px;
                                                                                    font-size: 16px;
                                                                                }
                                                                                
                                                                                .highlight {
                                                                                    background: #e8f4f8;
                                                                                    padding: 20px;
                                                                                    border-radius: 8px;
                                                                                    margin: 20px 0;
                                                                                    border-left: 4px solid #27ae60;
                                                                                }
                                                                                
                                                                                .mission-box {
                                                                                    background: #f0f7ff;
                                                                                    padding: 20px;
                                                                                    border-radius: 8px;
                                                                                    margin: 20px 0;
                                                                                    border: 2px solid #1E2A56;
                                                                                }
                                                                                
                                                                                .address-box {
                                                                                    background: #f8f9fa;
                                                                                    padding: 15px;
                                                                                    border-radius: 6px;
                                                                                    margin-top: 20px;
                                                                                    font-size: 14px;
                                                                                }
                                                                                
                                                                                .footer {
                                                                                    margin-top: 40px;
                                                                                    padding-top: 20px;
                                                                                    border-top: 1px solid #dee2e6;
                                                                                    text-align: center;
                                                                                    font-size: 12px;
                                                                                    color: #666;
                                                                                }
                                                                                
                                                                                h3 {
                                                                                    color: #1E2A56;
                                                                                    margin: 25px 0 10px 0;
                                                                                }
                                                                                
                                                                                ul {
                                                                                    padding-left: 20px;
                                                                                }
                                                                                
                                                                                li {
                                                                                    margin-bottom: 5px;
                                                                                }
                                                                            </style>
                                                                        </head>
                                                                        <body>
                                                                            <div class="header">
                                                                                <div class="company-name">CONNECTLINK PROPERTIES</div>
                                                                                <div class="tagline">From Concept to Creation – Let's Build Together!</div>
                                                                            </div>
                                                                            
                                                                            <div class="contact-info">
                                                                                <strong>📍 Address:</strong> Colonnade Building, Corner Mutare Rd & Steven Drive, Msasa, Harare<br>
                                                                                <strong>📞 Phone:</strong> 0773 368 558 | 0718 047 602<br>
                                                                                <strong>📧 Email:</strong> info@connectlinkproperties.co.zw<br>
                                                                                <strong>🌐 Website:</strong> www.connectlinkproperties.co.zw
                                                                            </div>
                                                                            
                                                                            <div class="section">
                                                                                <div class="section-title">OUR STORY</div>
                                                                                <p>Connectlink Properties is a Zimbabwean-based real estate development company specializing in construction, property development, project management, and custom cabinetry. With over a decade of experience, we have established a commendable reputation for delivering quality services with integrity, professionalism, and client satisfaction.</p>
                                                                                
                                                                                <div class="mission-box">
                                                                                    <strong>🎯 OUR MISSION:</strong> To empower every citizen of Zimbabwe to achieve their dream of owning a property through innovative solutions and commitment to excellence.
                                                                                </div>
                                                                            </div>
                                                                            
                                                                            <div class="section">
                                                                                <div class="section-title">CORE SERVICES</div>
                                                                                <div class="services-grid">
                                                                                    <div class="service-card">
                                                                                        <div class="service-title">🏗️ CONSTRUCTION</div>
                                                                                        <ul>
                                                                                            <li>Brickwork & Roofing</li>
                                                                                            <li>Tiling & Renovations</li>
                                                                                            <li>Electrical & Plumbing</li>
                                                                                            <li>Painting & Finishes</li>
                                                                                        </ul>
                                                                                    </div>
                                                                                    
                                                                                    <div class="service-card">
                                                                                        <div class="service-title">🏠 PROPERTY DEVELOPMENTS</div>
                                                                                        <ul>
                                                                                            <li>Residential & Commercial</li>
                                                                                            <li>Site Selection & Planning</li>
                                                                                            <li>Property Management</li>
                                                                                            <li>Real Estate Services</li>
                                                                                        </ul>
                                                                                    </div>
                                                                                    
                                                                                    <div class="service-card">
                                                                                        <div class="service-title">🍳 KITCHENS & CABINETS</div>
                                                                                        <ul>
                                                                                            <li>Custom Kitchen Units</li>
                                                                                            <li>Walk-in Closets</li>
                                                                                            <li>Built-in Cupboards</li>
                                                                                            <li>Granite Works</li>
                                                                                        </ul>
                                                                                    </div>
                                                                                    
                                                                                    <div class="service-card">
                                                                                        <div class="service-title">📺 TV UNITS & VANITIES</div>
                                                                                        <ul>
                                                                                            <li>TV Mounting & Units</li>
                                                                                            <li>Bathroom Vanities</li>
                                                                                            <li>Mirror Installation</li>
                                                                                            <li>Storage Solutions</li>
                                                                                        </ul>
                                                                                    </div>
                                                                                    
                                                                                    <div class="service-card">
                                                                                        <div class="service-title">🛣️ CIVIL WORKS</div>
                                                                                        <ul>
                                                                                            <li>Road Construction</li>
                                                                                            <li>Sewer Reticulation</li>
                                                                                            <li>Water Systems</li>
                                                                                            <li>Concrete Structures</li>
                                                                                        </ul>
                                                                                    </div>
                                                                                    
                                                                                    <div class="service-card">
                                                                                        <div class="service-title">📊 PROJECT MANAGEMENT</div>
                                                                                        <ul>
                                                                                            <li>Architectural Drawings</li>
                                                                                            <li>Land Survey</li>
                                                                                            <li>Development Permits</li>
                                                                                            <li>Consultancy Services</li>
                                                                                        </ul>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                            
                                                                            <div class="section">
                                                                                <div class="section-title">WHY CHOOSE US</div>
                                                                                <div class="highlight">
                                                                                    <strong>✓ Flexible Solutions:</strong> Tailored services to meet specific client needs<br>
                                                                                    <strong>✓ Professional Team:</strong> Qualified engineers and tradesmen<br>
                                                                                    <strong>✓ Quality Assurance:</strong> Materials and workmanship meeting global standards<br>
                                                                                    <strong>✓ Client-Centric Approach:</strong> From concept to completion with full transparency<br>
                                                                                    <strong>✓ Proven Track Record:</strong> Portfolio includes residential, commercial & institutional developments
                                                                                </div>
                                                                            </div>
                                                                            
                                                                            <div class="section">
                                                                                <div class="section-title">CONTACT & LOCATIONS</div>
                                                                                <div class="address-box">
                                                                                    <strong>Main Office:</strong> Colonnade Building, Corner Mutare Rd & Steven Drive, Msasa, Harare<br>
                                                                                    <strong>Branch Office:</strong> 38A Coronation Ave, Greendale, Harare<br>
                                                                                    <strong>Business Hours:</strong> Monday - Friday: 8:00 AM - 5:00 PM | Saturday: 9:00 AM - 1:00 PM<br>
                                                                                    <strong>Emergency Services:</strong> Available 24/7 for urgent matters
                                                                                </div>
                                                                            </div>
                                                                            
                                                                            <div class="footer">
                                                                                <p>© 2024 Connectlink Properties. All Rights Reserved.</p>
                                                                                <p>Follow us: 📱 WhatsApp Business | 📘 Facebook | 📸 Instagram | 💼 LinkedIn</p>
                                                                                <p>Registered in Zimbabwe • VAT Registered • Professional Engineers Registration</p>
                                                                            </div>
                                                                        </body>
                                                                        </html>
                                                                        """
                                                                        
                                                                        # Generate PDF
                                                                        pdf_bytes = HTML(string=html_content).write_pdf()
                                                                        return pdf_bytes
                                                                        
                                                                    except Exception as e:
                                                                        print(f"Error generating company profile PDF: {str(e)}")
                                                                        return None


                                                                def send_company_profile_whatsapp(recipient_number):

                                                                    import io
                                                                    """Send company profile PDF via WhatsApp"""
                                                                    try:
                                                                        # Generate PDF
                                                                        pdf_bytes = generate_company_profile_pdf()
                                                                        
                                                                        if not pdf_bytes:
                                                                            return {'status': 'error', 'message': 'Failed to generate PDF'}
                                                                        
                                                                        # Upload to WhatsApp
                                                                        filename = 'Connectlink_Properties_Profile.pdf'
                                                                        url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
                                                                        headers = {
                                                                            "Authorization": f"Bearer {ACCESS_TOKEN}"
                                                                        }
                                                                        
                                                                        files = {
                                                                            "file": (filename, io.BytesIO(pdf_bytes), "application/pdf"),
                                                                            "type": (None, "application/pdf"),
                                                                            "messaging_product": (None, "whatsapp")
                                                                        }
                                                                        
                                                                        response = requests.post(url, headers=headers, files=files)
                                                                        response.raise_for_status()
                                                                        media_id = response.json()["id"]
                                                                        
                                                                        # Send with WhatsApp message
                                                                        message = f"""
                                                                            🏢 *CONNECTLINK PROPERTIES - COMPANY PROFILE*

                                                                            Thank you for your interest in Connectlink Properties! 

                                                                            📋 *What's included in this document:*
                                                                            • Our Story & Mission
                                                                            • Core Services Overview
                                                                            • Why Choose Us
                                                                            • Contact Information
                                                                            • Service Specializations

                                                                            🏗️ *Our Expertise:*
                                                                            • Construction & Civil Works
                                                                            • Property Development
                                                                            • Kitchens & Cabinets
                                                                            • Project Management
                                                                            • TV Units & Bathroom Vanities

                                                                            📍 *Locations:* Msasa & Greendale, Harare
                                                                            📞 *Contact:* 0773 368 558 | 0718 047 602
                                                                            📧 *Email:* info@connectlinkproperties.co.zw

                                                                            _From Concept to Creation – Let's Build Together!_

                                                                            Please find our detailed company profile attached.
                                                                                    """
                                                                        
                                                                        # First send text
                                                                        text_url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                        text_headers = {
                                                                            "Authorization": f"Bearer {ACCESS_TOKEN}",
                                                                            "Content-Type": "application/json"
                                                                        }
                                                                        
                                                                        text_payload = {
                                                                            "messaging_product": "whatsapp",
                                                                            "to": recipient_number,
                                                                            "type": "text",
                                                                            "text": {"body": message.strip()}
                                                                        }
                                                                        
                                                                        requests.post(text_url, headers=text_headers, json=text_payload)
                                                                        
                                                                        # Then send PDF
                                                                        doc_payload = {
                                                                            "messaging_product": "whatsapp",
                                                                            "to": recipient_number,
                                                                            "type": "document",
                                                                            "document": {
                                                                                "id": media_id,
                                                                                "filename": filename,
                                                                                "caption": "Connectlink Properties Company Profile"
                                                                            }
                                                                        }
                                                                        
                                                                        response = requests.post(text_url, headers=text_headers, json=doc_payload)
                                                                        response.raise_for_status()
                                                                        
                                                                        return {
                                                                            'status': 'success',
                                                                            'message': 'Company profile sent successfully',
                                                                            'whatsapp_response': response.json()
                                                                        }
                                                                        
                                                                    except Exception as e:
                                                                        print(f"Error sending company profile: {str(e)}")
                                                                        return {'status': 'error', 'message': f'Failed to send: {str(e)}'}


                                                                # Usage example

                                                                result = send_company_profile_whatsapp(sender_id)

                                                                buttons = [
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "enquirylog",
                                                                            "title": "Enquiries"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "contact",
                                                                            "title": "Contact Us"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "about",
                                                                            "title": "About Us"
                                                                        }
                                                                    }
                                                                ]


                                                                send_whatsapp_button_message(
                                                                    sender_id, 
                                                                    f"How can we assist you today, {profile_name}?.",
                                                                    buttons,
                                                                    footer_text="ConnectLink Properties • Client Panel"

                                                                )

                                                                continue

                                                            elif button_id == "contact":

                                                                """Send simplified contact info via WhatsApp"""
                                                                    # Create message
                                                                message = (
                                                                    "🏢 *CONNECTLINK PROPERTIES*\n\n"
                                                                    "📱 WhatsApp: https://wa.me/263773368558\n"
                                                                    "📍 Offices: 38A Coronation Avenue, Greendale, Harare\n"
                                                                    "📧 Email: info@connectlinkproperties.co.zw\n"
                                                                    "🌐 Website: www.connectlinkproperties.co.zw"
                                                                )
                                                                    
                                                                    # Send message
                                                                buttons = [
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "enquirylog",
                                                                            "title": "Enquiries"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "contact",
                                                                            "title": "Contact Us"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "about",
                                                                            "title": "About Us"
                                                                        }
                                                                    }
                                                                ]


                                                                send_whatsapp_button_message(
                                                                    sender_id, 
                                                                    f"{message}\n\n How can we assist you today, {profile_name}?.",
                                                                    buttons,
                                                                    footer_text="ConnectLink Properties • Client Panel"

                                                                )


                                                            elif button_id == "main_menu":

                                                                buttons = [
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "enquirylog",
                                                                            "title": "Enquiries"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "contact",
                                                                            "title": "Contact Us"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "about",
                                                                            "title": "About Us"
                                                                        }
                                                                    }
                                                                ]


                                                                send_whatsapp_button_image_message(
                                                                    sender_id, 
                                                                    f"👋 Hey {profile_name}, Welcome to ConnectLink Properties! \n\n How can we assist you today?.",
                                                                    "https://connectlink-wbax.onrender.com/static/images/reqlogo.jpg",
                                                                    buttons,
                                                                    footer_text="ConnectLink Properties • Client Panel"

                                                                )

                                                                continue
                                                            


                                                        else:

                                                            text = message.get("text", {}).get("body", "").lower()
                                                            print(f"📨 Message from {sender_id}: {text}")
                                                            
                                                            print("yearrrrrrrrrrrrrrrrrrrrrrrrrrrssrsrsrsrsrs")

                                                            
                                                            buttons = [
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "enquirylog",
                                                                        "title": "Enquiries"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "contact",
                                                                        "title": "Contact Us"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "about",
                                                                        "title": "About Us"
                                                                    }
                                                                }
                                                            ]


                                                            send_whatsapp_button_image_message(
                                                                sender_id, 
                                                                f"👋 Hey {profile_name}, Welcome to ConnectLink Properties! \n\n How can we assist you today?.",
                                                                "https://connectlink-wbax.onrender.com/static/images/reqlogo.jpg",
                                                                buttons,
                                                                footer_text="ConnectLink Properties • Client Panel"

                                                            )

                                                            continue

                                                    except Exception as e:
                                                        print(e)



                                            return jsonify({"status": "received"}), 200
                                            
                                        except Exception as e:
                                            print(e)
                                            return jsonify({"error": "internal error"}), 200

                                            


            except Exception as e:
                print(e)
                return jsonify({"error": "internal error"}), 200
            
    return jsonify({"error": "internal error"}), 200





@app.route('/export-projects-portfolio')
def export_projects_portfolio():

    with get_db() as (cursor, connection):

        try:
            today_date = datetime.now().strftime('%d %B %Y %H:%M:%S')

            # ========= SHEET 1 — PROJECTS =========
            cursor.execute("SELECT * FROM connectlinkdatabase ORDER BY id DESC")
            rows_1 = cursor.fetchall()

            cols_1 = [desc[0] for desc in cursor.description]
            df_projects = pd.DataFrame(rows_1, columns=cols_1)


            # ========= SHEET 2 — PORTFOLIO =========
            cursor.execute("SELECT * FROM connectlinknotes ORDER BY id DESC")
            rows_2 = cursor.fetchall()

            cols_2 = [desc[0] for desc in cursor.description]
            df_notes = pd.DataFrame(rows_2, columns=cols_2)

            cursor.execute("SELECT * FROM connectlinkdatabasedeletedprojects ORDER BY id DESC")
            rows_3 = cursor.fetchall()

            cols_3 = [desc[0] for desc in cursor.description]
            df_portfolio_deleted = pd.DataFrame(rows_3, columns=cols_3)


            # ========= CREATE EXCEL FILE IN MEMORY =========
            output = io.BytesIO()

            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df_projects.to_excel(writer, index=False, sheet_name="Projects Database")
                df_notes.to_excel(writer, index=False, sheet_name="Notes")
                df_portfolio_deleted.to_excel(writer, index=False, sheet_name="Deleted Projects")


            output.seek(0)

            # ========= SEND THE FILE =========
            return send_file(
                output,
                as_attachment=True,
                download_name=f"ConnectLink Properties Projects Portfolio as at {today_date}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        except Exception as e:
            print("Error:", str(e))
            return f"Error occurred: {str(e)}", 500

            
@app.route('/remove-system-user', methods=['POST'])
def remove_system_user():

    with get_db() as (cursor, connection):

        try:

            data = request.get_json()
            user_id = data.get('user_id')
            passcode = data.get('passcode')
            
            cursor.execute("DELETE FROM connectlinkusers WHERE id = %s", (user_id,))
            connection.commit()
            
            return jsonify({
                'status': 'success',
                'message': f'User has been removed successfully'
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to remove user: {str(e)}'
            }), 500




@app.route('/dashboard')
def Dashboard():

    with get_db() as (cursor, connection):

        user_uuid = session.get('user_uuid')
        user_name = session.get('user_name')
        userid = session.get('userid')

        if user_uuid:

            try:

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
                        'id', 'datecreated', 'name', 'password', 'email', 'whatsapp'
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

@app.route('/export-enquiries')
def export_enquiries():
    with get_db() as (cursor, connection):
        try:
            today_date = datetime.now().strftime('%d %B %Y %H:%M:%S')
            
            # ========= GET ENQUIRIES DATA =========
            cursor.execute("SELECT * FROM connectlinkenquiries ORDER BY id DESC")
            rows = cursor.fetchall()
            
            if not rows:
                # Return empty Excel file
                output = io.BytesIO()
                df_empty = pd.DataFrame(columns=['No enquiries found'])
                df_empty.to_excel(output, index=False, sheet_name="Enquiries")
                output.seek(0)
                
                return send_file(
                    output,
                    as_attachment=True,
                    download_name=f"ConnectLink Properties Enquiries as at {today_date}.xlsx",
                    mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
            
            cols = [desc[0] for desc in cursor.description]
            df_enquiries = pd.DataFrame(rows, columns=cols)
            
            # ========= CREATE EXCEL FILE IN MEMORY =========
            output = io.BytesIO()
            
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                # Sheet 1: Enquiries Data
                df_enquiries.to_excel(writer, index=False, sheet_name="Enquiries")
                
                # Sheet 2: Status Summary
                if 'status' in df_enquiries.columns:
                    status_counts = df_enquiries['status'].value_counts()
                    
                    # Map status to readable names
                    status_map = {
                        'pending': 'Pending',
                        'in_progress': 'In Progress',
                        'completed': 'Completed'
                    }
                    
                    # Create status summary
                    status_summary = []
                    for status, count in status_counts.items():
                        readable_status = status_map.get(status, status.title())
                        status_summary.append({
                            'Status': readable_status,
                            'Count': count
                        })
                    
                    df_status_summary = pd.DataFrame(status_summary)
                    df_status_summary.to_excel(writer, index=False, sheet_name="Status Summary", startrow=1)
                    
                    # Add header
                    worksheet = writer.sheets['Status Summary']
                    worksheet['A1'] = 'Status Distribution'
                
                # Sheet 3: Enquiries by Date (Fixed)
                if 'timestamp' in df_enquiries.columns:
                    try:
                        # Convert timestamp to date
                        df_enquiries['date'] = pd.to_datetime(df_enquiries['timestamp']).dt.date
                        
                        # Simple date count
                        date_summary = df_enquiries.groupby('date').size().reset_index(name='Count')
                        date_summary = date_summary.sort_values('date', ascending=False)
                        date_summary.to_excel(writer, index=False, sheet_name="Enquiries by Date")
                        
                        # Alternative: Status by Date (without pivot_table issues)
                        if 'status' in df_enquiries.columns:
                            # Group by date and status
                            status_date_group = df_enquiries.groupby(['date', 'status']).size().reset_index(name='Count')
                            
                            # Pivot manually to avoid column mismatch
                            dates = status_date_group['date'].unique()
                            statuses = ['pending', 'in_progress', 'completed']
                            
                            # Create empty DataFrame
                            status_by_date = pd.DataFrame({'Date': dates})
                            
                            # Fill with counts for each status
                            for status in statuses:
                                status_counts = []
                                for date in dates:
                                    count = status_date_group[
                                        (status_date_group['date'] == date) & 
                                        (status_date_group['status'] == status)
                                    ]['Count'].sum()
                                    status_counts.append(count)
                                
                                readable_status = status_map.get(status, status.title())
                                status_by_date[readable_status] = status_counts
                            
                            status_by_date = status_by_date.sort_values('Date', ascending=False)
                            status_by_date.to_excel(writer, index=False, sheet_name="Status by Date")
                            
                    except Exception as e:
                        print(f"Error creating date sheets: {e}")
                        # Continue without these sheets
                
                # Sheet 4: Statistics
                if 'status' in df_enquiries.columns:
                    total = len(df_enquiries)
                    pending = len(df_enquiries[df_enquiries['status'] == 'pending'])
                    in_progress = len(df_enquiries[df_enquiries['status'] == 'in_progress'])
                    completed = len(df_enquiries[df_enquiries['status'] == 'completed'])
                    
                    stats_data = {
                        'Metric': [
                            'Total Enquiries',
                            'Pending Enquiries',
                            'In Progress Enquiries',
                            'Completed Enquiries',
                            'Pending Percentage',
                            'In Progress Percentage',
                            'Completed Percentage'
                        ],
                        'Value': [
                            total,
                            pending,
                            in_progress,
                            completed,
                            f"{(pending/total*100):.1f}%" if total > 0 else "0%",
                            f"{(in_progress/total*100):.1f}%" if total > 0 else "0%",
                            f"{(completed/total*100):.1f}%" if total > 0 else "0%"
                        ]
                    }
                    
                    df_stats = pd.DataFrame(stats_data)
                    df_stats.to_excel(writer, index=False, sheet_name="Statistics")
            
            output.seek(0)
            
            # ========= SEND THE FILE =========
            return send_file(
                output,
                as_attachment=True,
                download_name=f"ConnectLink Properties Enquiries as at {today_date}.xlsx",
                mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
        except Exception as e:
            print(f"Error exporting enquiries: {str(e)}")
            return f"Error occurred: {str(e)}", 500

@app.route('/download_contract/<project_id>')
def download_contract(project_id):
    with get_db() as (cursor, connection):
        try:
            # Fetch project data
            cursor.execute("SELECT * FROM connectlinkdatabase WHERE id = %s", (project_id,))
            row = cursor.fetchone()
            if not row:
                return "Project not found", 404

            # Format agreement date
            agreement_date = row[16] 
            formatted_agreement_date = agreement_date.strftime("%d %B %Y")

            # Fetch company details
            cursor.execute("SELECT * FROM connectlinkdetails;")
            detailscompdata = cursor.fetchall()
            detailscompdata = pd.DataFrame(detailscompdata, columns=['address','contact1','contact2','email','companyname','tinnumber'])
            companyname = detailscompdata.iat[0,4] if not detailscompdata.empty else "ConnectLink Properties"
            address = detailscompdata.iat[0,0] if not detailscompdata.empty else ""
            contact1 = detailscompdata.iat[0,1] if not detailscompdata.empty else ""
            contact2 = detailscompdata.iat[0,2] if not detailscompdata.empty else ""
            compemail = detailscompdata.iat[0,3] if not detailscompdata.empty else ""

            # Calculate days difference
            def days_between(date1, date2):
                delta = date1 - date2
                return abs(delta.days)

            date_str1 = row[14]
            date_str2 = row[24]
            days_difference = days_between(date_str1, date_str2)

            # Map project row to dictionary
            project = {
                'project_id_num': row[0],
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
                'depositorbullet': row[23] if len(row) > 23 else None,
                'datedepositorbullet': row[24] if len(row) > 24 else None,
                'monthlyinstallment': row[25] if len(row) > 25 else None,
                'installment1amount': row[26] if len(row) > 26 else None,
                'installment1duedate': row[27].strftime("%-d %B %Y") if len(row) > 27 and row[27] else None,
                'installment2amount': row[29] if len(row) > 29 else None,
                'installment2duedate': row[30].strftime("%-d %B %Y") if len(row) > 30 and row[30] else None,
                'installment3amount': row[32] if len(row) > 32 else None,
                'installment3duedate': row[33].strftime("%-d %B %Y") if len(row) > 33 and row[33] else None,
                'installment4amount': row[35] if len(row) > 35 else None,
                'installment4duedate': row[36].strftime("%-d %B %Y") if len(row) > 36 and row[36] else None,
                'installment5amount': row[38] if len(row) > 38 else None,
                'installment5duedate': row[39].strftime("%-d %B %Y") if len(row) > 39 and row[39] else None,
                'installment6amount': row[41] if len(row) > 41 else None,
                'installment6duedate': row[42].strftime("%-d %B %Y") if len(row) > 42 and row[42] else None,
                'latepaymentinterest': row[45] if len(row) > 43 else None,
                'companyname': companyname,
                'companyaddress': address,
                'companycontact1': contact1,
                'companycontact2': contact2,
                'companyemail': compemail,
                'days_difference': days_difference,
                'relationship': row[9] if len(row) > 9 else ""
            }

            project['generated_on'] = datetime.now().strftime('%d %B %Y')

            logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'web-logo.png')
            with open(logo_path, 'rb') as img_file:
                logo_base64 = base64.b64encode(img_file.read()).decode('utf-8')

                        # HTML string (full template)
            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <title>Construction Agreement</title>
                <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700;900&display=swap" rel="stylesheet">
                <style>
                    @page {{
                        size: A4;
                        margin: 30px 40px 60px 30px; /* Extra bottom margin for signature area */
                        
                        @bottom-center {{
                            content: "";
                            width: 70%;
                            border-top: 1px solid #1E2A56;
                            margin-top: 20px;
                            padding-top: 10px;
                        }}
                    }}
                    
                    body {{ 
                        font-family: 'Roboto', sans-serif; 
                        background: #fff; 
                        color: #1E2A56;
                        margin: 0;
                        padding: 0;
                    }}
                    
                    .page-break {{
                        page-break-after: always;
                        margin-top: 40px;
                    }}
                    
                    .agreement-container {{
                        width: 100%;
                        max-width: 800px;
                        margin: 0 auto;
                        padding: 30px;
                        box-sizing: border-box;
                        position: relative;
                    }}
                    
                    .watermark {{
                        position: fixed;
                        top: 40%;
                        left: 15%;
                        opacity: 0.05;
                        font-size: 100px;
                        color: #1E2A56;
                        transform: rotate(-45deg);
                        z-index: -1000;
                        font-weight: 900;
                    }}
                    
                    .logo {{
                        display: block;
                        margin: 0 auto 15px auto;
                        width: 200px;
                        height: auto;
                    }}
                    
                    h3.title {{
                        text-align: center;
                        font-weight: 900;
                        margin-bottom: 10px;
                        text-transform: uppercase;
                        letter-spacing: 1.6px;
                        font-size: 20px;
                        color: #1E2A56;
                    }}
                    
                    .subtitle-line {{
                        width: 150px;
                        height: 4px;
                        background: linear-gradient(90deg, #1E2A56, #3A4B8C);
                        margin: 10px auto 30px auto;
                        border-radius: 10px;
                    }}
                    
                    h4.section-title {{
                        text-align: center;
                        background: linear-gradient(90deg, #1E2A56, #2A3A78);
                        color: white;
                        padding: 8px 10px;
                        border-radius: 8px;
                        font-size: 13px;
                        margin-top: 20px;
                        margin-bottom: 15px;
                        font-weight: 700;
                        letter-spacing: 0.8px;
                        box-shadow: 0 3px 6px rgba(0,0,0,0.1);
                    }}
                    
                    .section-header {{
                        background: #f0f5ff;
                        padding: 8px 10px;
                        border-left: 4px solid #1E2A56;
                        margin: 20px 0 20px 0;
                        font-weight: 700;
                        color: #1E2A56;
                        font-size: 12px;
                        border-radius: 0 8px 8px 0;
                    }}
                    
                    .field-row {{
                        display: flex;
                        align-items: flex-start;
                        margin-bottom: 8px;
                        page-break-inside: avoid;
                    }}
                    
                    .field-label {{
                        font-weight: 700;
                        width: 180px;
                        font-size: 12px;
                        flex-shrink: 0;
                        color: #2A3A78;
                    }}
                    
                    .field-value {{
                        flex: 1;
                        border-bottom: 1px solid #d1d9f0;
                        padding-bottom: 5px;
                        font-size: 11px;
                        min-height: 17px;
                        color: #1E2A56;
                    }}
                    
                    .highlight-box {{
                        background: linear-gradient(135deg, #f8faff 0%, #f0f5ff 100%);
                        font-size: 11px;
                        border: 1.5px solid #1E2A56;
                        border-radius: 12px;
                        padding: 20px;
                        margin: 10px 0;
                        box-shadow: 0 4px 12px rgba(26, 42, 86, 0.08);
                    }}
                    
                    .scope-box {{
                        border: 1.5px solid #1E2A56;
                        border-radius: 10px;
                        padding: 10px;
                        font-size: 11px;
                        min-height: 100px;
                        background: #fafbff;
                        margin-bottom: 15px;
                        line-height: 1.3;
                    }}
                    
                    .payment-table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin: 10px 0;
                        border: 1.5px solid #1E2A56;
                        box-shadow: 0 3px 8px rgba(0,0,0,0.05);
                    }}
                    
                    .payment-table th {{
                        background: linear-gradient(90deg, #1E2A56, #2A3A78);
                        color: white;
                        text-align: left;
                        padding: 10px;
                        font-weight: 700;
                        font-size: 11px;
                    }}
                    
                    .payment-table td {{
                        border: 1px solid #d1d9f0;
                        padding: 10px;
                        font-size: 11px;
                    }}
                    
                    .payment-table tr:nth-child(even) {{
                        background-color: #f9faff;
                    }}
                    
                    ul, ol {{
                        margin: 10px 0;
                        padding-left: 20px;
                        line-height: 1.4;
                    }}
                    
                    li {{
                        margin-bottom: 10px;
                        font-size: 11px;
                        color: #1E2A56;
                    }}
                    
                    .terms-box {{
                        background: #f8faff;
                        border-left: 4px solid #1E2A56;
                        padding: 10px;
                        margin: 10px 0;
                        border-radius: 0 8px 8px 0;
                    }}
                    
                    /* Signature area at bottom of each page */
                    .signature-area {{
                        font-size: 8px;
                        position: fixed;
                        bottom: 5px;
                        left: 40px;
                        right: 40px;
                        padding-top: 8px;
                        border: 1px solid #1E2A56;
                        border-radius: 8px;
                        background: #f8faff;
                        z-index: 100;
                    }}
                    
                    .signature-block {{
                        display: flex;
                        justify-content: space-between;
                        margin-top: 8px;
                    }}
                    
                    .signature-line {{
                        flex: 1;
                        margin: 0 10px;
                    }}
                    
                    .signature-label {{
                        font-weight: 700;
                        font-size: 10px;
                        margin-bottom: 5px;
                        display: block;
                        color: #2A3A78;
                    }}
                    
                    .signature-space {{
                        height: 30px;
                        border-bottom: 1px solid #1E2A56;
                        margin-top: 3px;
                    }}
                    
                    .signature-date {{
                        font-size: 10px;
                        color: #666;
                        margin-top: 5px;
                    }}
                    
                    .footer-note {{
                        text-align: center;
                        font-size: 10px;
                        color: #888;
                        margin-top: 10px;
                        font-style: italic;
                    }}
                    
                    /* Page number styling */
                    .page-number {{
                        position: fixed;
                        bottom: 15px;
                        left: 40px;
                        font-size: 10px;
                        color: #666;
                    }}
                    
                    .total-pages {{
                        position: fixed;
                        bottom: 15px;
                        right: 40px;
                        font-size: 10px;
                        color: #666;
                    }}
                    
                    /* Print styles */
                    @media print {{
                        .signature-area {{
                            position: fixed;
                            bottom: 5px;
                        }}
                        
                        .page-break {{
                            page-break-after: always;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="watermark">CONNECTLINK</div>
                
                <div class="agreement-container">
                    <!-- Page 1 -->
                    <img class="logo" src="data:image/png;base64,{logo_base64}" alt="ConnectLink Logo">
                    
                    <h3 class="title">Construction Agreement</h3>
                    <div class="subtitle-line"></div>
                    
                    <div class="highlight-box">
                        <p style="text-align: center; font-weight: 700; margin: 0;">
                            This Construction Agreement ("Agreement") is made and entered into on 
                            <span style="color: #1E2A56; text-decoration: underline;">{project['agreement_date']}</span> 
                            ("Effective Date") by and between the parties below:
                        </p>
                    </div>
                    
                    <h4 class="section-title">PARTIES TO THE AGREEMENT</h4>
                    
                    <div class="section-header">CLIENT DETAILS</div>
                    <div class="field-row"><div class="field-label">Full Name:</div><div class="field-value">{project['client_name']}</div></div>
                    <div class="field-row"><div class="field-label">National ID:</div><div class="field-value">{project['client_idnumber']}</div></div>
                    <div class="field-row"><div class="field-label">Address:</div><div class="field-value">{project['client_address']}</div></div>
                    <div class="field-row"><div class="field-label">Contact Number:</div><div class="field-value">0{project['client_whatsapp']}</div></div>
                    <div class="field-row"><div class="field-label">Email:</div><div class="field-value">{project['client_email']}</div></div>
                    
                    <div class="section-header">NEXT OF KIN DETAILS</div>
                    <div class="field-row"><div class="field-label">Full Name:</div><div class="field-value">{project['next_of_kin_name']}</div></div>
                    <div class="field-row"><div class="field-label">Address:</div><div class="field-value">{project['next_of_kin_address']}</div></div>
                    <div class="field-row"><div class="field-label">Contact Number:</div><div class="field-value">0{project['next_of_kin_phone']}</div></div>
                    <div class="field-row"><div class="field-label">Relationship:</div><div class="field-value">{project['relationship']}</div></div>
                    

                    <div class="section-header">CONTRACTOR DETAILS</div>
                    <div class="field-row"><div class="field-label">Company Name:</div><div class="field-value">{project['companyname']}</div></div>
                    <div class="field-row"><div class="field-label">Address:</div><div class="field-value">{project['companyaddress']}</div></div>
                    <div class="field-row"><div class="field-label">Contact Numbers:</div><div class="field-value">0{project['companycontact1']} / 0{project['companycontact2']}</div></div>
                    <div class="field-row"><div class="field-label">Email:</div><div class="field-value">{project['companyemail']}</div></div>
                    <div class="field-row"><div class="field-label">Project Administrator:</div><div class="field-value">{project['project_administrator']}</div></div>
                    
                    <!-- Page break -->
                    <div class="page-break"></div>
                    
                    <!-- Page 2 -->

                    <h4 class="section-title">PROJECT DETAILS</h4>
                    <div class="field-row"><div class="field-label">Project Name:</div><div class="field-value">{project['project_name']}</div></div>
                    <div class="field-row"><div class="field-label">Project Location:</div><div class="field-value">{project['project_location']}</div></div>
                    
                    <div class="section-header">PROJECT SCOPE</div>
                    <div class="scope-box">{project['project_description']}</div>
                

                    <h4 class="section-title">PAYMENT TERMS</h4>
                    <div class="field-row"><div class="field-label">Total Contract Price:</div><div class="field-value" style="font-weight: 700; color: #1E2A56;">USD {project['total_contract_price']}</div></div>
                    <div class="field-row"><div class="field-label">Deposit Required:</div><div class="field-value" style="font-weight: 700; color: #1E2A56;">USD {project['depositorbullet']}</div></div>
                    
                    <div class="section-header">PAYMENT SCHEDULE</div>
                    <table class="payment-table">
                        <thead>
                            <tr>
                                <th style="width: 60%;">Installment Due Date</th>
                                <th style="width: 40%;">Amount (USD)</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td>{project['installment1duedate']}</td><td style="font-weight: 700;">{project['installment1amount']}</td></tr>
                            <tr><td>{project['installment2duedate']}</td><td style="font-weight: 700;">{project['installment2amount']}</td></tr>
                            <tr><td>{project['installment3duedate']}</td><td style="font-weight: 700;">{project['installment3amount']}</td></tr>
                            <tr><td>{project['installment4duedate']}</td><td style="font-weight: 700;">{project['installment4amount']}</td></tr>
                            <tr><td>{project['installment5duedate']}</td><td style="font-weight: 700;">{project['installment5amount']}</td></tr>
                            <tr><td>{project['installment6duedate']}</td><td style="font-weight: 700;">{project['installment6amount']}</td></tr>
                        </tbody>
                    </table>
                    
                    <!-- Page break -->
                    <div class="page-break"></div>
                    
                    <!-- Page 3 -->

                    <h4 class="section-title">TERMS AND CONDITIONS</h4>
                    
                    <div class="section-header">LATE PAYMENT AND INTEREST</div>
                    <div class="terms-box">
                        <ul style="list-style-type: circle;">
                            <li>If the Client fails to make any payment on or before the due date, the Client shall be liable to pay interest at a rate of <strong>{project['latepaymentinterest']}%</strong> per annum.</li>
                            <li>Interest is calculated daily and compounded monthly from the due date until full payment is received.</li>
                            <li>All payments shall first be applied to interest due, then to the principal amount.</li>
                        </ul>
                    </div>
                    
                    <div class="section-header">PROJECT TIMELINE</div>
                    <ol>
                        <li>The Contractor shall commence work within <strong>{project['days_difference']} days</strong> of receiving the first payment.</li>
                        <li>The Contractor shall complete the project within <strong>{project['project_duration']} days</strong> from commencement date.</li>
                        <li>The Client shall make payments strictly as per the payment schedule outlined above.</li>
                        <li>The Client is responsible for obtaining all required permits and approvals from local authorities.</li>
                        <li>The Contractor is responsible for all materials, labor, and workmanship as per industry standards.</li>
                    </ol>
                    

                    <div class="section-header">OWNERSHIP CLAUSE</div>
                    <div class="terms-box">
                        <ul style="list-style-type: circle;">
                            <li>All installed items, materials, and equipment remain the property of <strong>ConnectLink Properties</strong> until full and final payment is received from the Client.</li>
                            <li>ConnectLink Properties reserves the right to remove, repossess, or withhold any installed items should the Client fail to make payments within the stipulated timelines.</li>
                            <li>Ownership transfers to the Client only upon settlement of the entire contract amount.</li>
                        </ul>
                    </div>
                    
                    <div class="section-header">DESIGN CONFIRMATION</div>
                    <div class="terms-box">
                        <ul style="list-style-type: circle;">
                            <li>Signing of this contract and payment of the deposit constitutes acknowledgement, confirmation, and authorization to proceed with construction of the proposed design submitted with the quotation.</li>
                            <li>Any alterations or modifications must be communicated and agreed upon <strong>before</strong> signing this contract.</li>
                            <li>All additions or variations to the approved design will be treated as change orders and will incur additional costs, billed separately or added to the original quotation.</li>
                        </ul>
                    </div>

                    <!-- Page break -->
                    <div class="page-break"></div>
                    
                    <!-- Page 4 -->

                    <div class="section-header">POWER PROVISION</div>
                    <div class="terms-box">
                        <p style="font-size:11px;">In the event of power outages requiring electricity for construction activities, the Client shall provide a suitable generator and fuel at their own expense for the duration required.</p>
                    </div>
                    
                    <div class="section-header">TERMINATION</div>
                    <div class="terms-box">
                        <p style="font-size:11px;">This Agreement may be terminated by either party if the other party:</p>
                        <ol>
                            <li>Fails to perform any material obligation under this Agreement and such failure continues for 30 days after written notice.</li>
                            <li>Becomes insolvent, bankrupt, or enters into receivership.</li>
                            <li>Breaches any term of this Agreement causing substantial harm to the other party.</li>
                        </ol>
                    </div>
                    
                    <div class="section-header">DISPUTE RESOLUTION</div>
                    <div class="terms-box">
                        <p style="font-size:11px;">Any disputes arising from this Agreement shall be resolved through amicable negotiation. If unresolved within 30 days, the matter shall be referred to arbitration under the Arbitration Act of Zimbabwe by a single arbitrator appointed by mutual agreement.</p>
                    </div>
                    
                    <div class="section-header">GOVERNING LAW</div>
                    <div class="terms-box">
                        <p style="font-size:11px;">This Agreement shall be governed by and construed in accordance with the laws of the Republic of Zimbabwe. The courts of Zimbabwe shall have exclusive jurisdiction over any matters arising from this Agreement.</p>
                    </div>
                    
                    <div class="section-header">ENTIRE AGREEMENT</div>
                    <div class="terms-box">
                        <p style="font-size:11px;">This document constitutes the entire agreement between the parties and supersedes all prior discussions, negotiations, and agreements. No modification shall be valid unless in writing and signed by both parties.</p>
                    </div>
                    
                </div>
                
                <!-- Signature Area (will appear at bottom of each page) -->
                <div class="signature-area">
                    <div class="signature-block">
                        <div class="signature-line">
                            <span class="signature-label">CLIENT SIGNATURE</span>
                            <div class="signature-space"></div>
                            <div class="signature-date">Date: {project['agreement_date']}</div>
                        </div>
                        
                        <div class="signature-line">
                            <span class="signature-label">CONTRACTOR SIGNATURE</span>
                            <div class="signature-space"></div>
                            <div class="signature-date">Date: {project['agreement_date']}</div>
                        </div>
                    </div>
                    <div class="footer-note" style="margin-top: 5px;font-weight:bold;color: black;">
                        This is a legally binding document. Please read carefully before signing.
                    </div>   
                </div>
            </body>
            </html>
            """

            # Generate PDF with better options
            css = CSS(string='''
                @page {
                    size: A4;
                    margin: 20px 20px 90px 20px;
                    
                    @bottom-right {
                        content: "Page " counter(page) " of " counter(pages);
                        font-family: 'Roboto', sans-serif;
                        font-size: 10px;
                        color: #666;
                    }
                    
                    @bottom-center {
                        content: "";
                        width: 100%;
                        border-top: 1px solid #1E2A56;
                        margin-top: 20px;
                        padding-top: 10px;
                    }
                }
                
                body {
                    font-family: 'Roboto', sans-serif;
                    margin: 0;
                    padding: 0;
                }
            ''')

            html_obj = HTML(string=html, base_url=request.host_url)

            pdf = html_obj.write_pdf(stylesheets=[css])

            response = make_response(pdf)
            response.headers['Content-Type'] = 'application/pdf'
            response.headers['Content-Disposition'] = f'attachment; filename={project["client_name"]} {project["project_name"]} contract_{project["project_id_num"]} ConnectLink Properties.pdf'
            return response

        except Exception as e:
            return str(e), 500


@app.route('/delete_project', methods=['POST'])
def delete_project():
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        admin_passcode = data.get('admin_passcode')
        
        if admin_passcode != "conlink01admin01":
            return jsonify({'status': 'error', 'message': 'Invalid admin passcode'})
        
        user_name = session.get('user_name', 'Unknown')
        userid = session.get('userid', 0)
        
        with get_db() as (cursor, connection):
            try:
                # Get ALL column names from connectlinkdatabase EXCEPT id
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'connectlinkdatabase' 
                    AND column_name != 'id'
                    ORDER BY ordinal_position
                """)
                columns = [row[0] for row in cursor.fetchall()]
                
                print(f"DEBUG: Found {len(columns)} columns excluding id")
                
                # Build the column list for SELECT (exclude id from source)
                select_columns = ', '.join([f'd.{col}' for col in columns])
                
                # Build the column list for INSERT - MUST include id first!
                insert_columns = ', '.join(['id'] + columns + ['deletedby', 'deleterid'])
                
                # Execute the copy - use project_id as the id value
                cursor.execute(f"""
                    INSERT INTO connectlinkdatabasedeletedprojects ({insert_columns})
                    SELECT %s, {select_columns}, %s, %s
                    FROM connectlinkdatabase d
                    WHERE d.id = %s
                """, (project_id, user_name, userid, project_id))
                
                # Then delete
                cursor.execute("DELETE FROM connectlinkdatabase WHERE id = %s", (project_id,))
                
                connection.commit()
                
                print(f"✅ Project {project_id} deleted and archived successfully")
                
                return jsonify({
                    'status': 'success',
                    'message': 'Project has been deleted and archived successfully.'
                })
                
            except Exception as e:
                connection.rollback()
                print(f"❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()
                return jsonify({'status': 'error', 'message': f'Database error: {str(e)}'})
                
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/download_payments_history/<project_id>')
def download_payments_history(project_id):
    with get_db() as (cursor, connection):
        try:
            # Fetch full project row (as your system does)
            cursor.execute("SELECT * FROM connectlinkdatabase WHERE id = %s", (project_id,))
            row = cursor.fetchone()
            if not row:
                return "Project not found", 404

            # Fetch company details
            cursor.execute("SELECT * FROM connectlinkdetails;")
            details = cursor.fetchall()
            details = pd.DataFrame(details, columns=[
                'address','contact1','contact2','email','companyname','tinnumber'
            ])

            companyname = details.iat[0,4] if not details.empty else ""
            address = details.iat[0,0] if not details.empty else ""
            contact1 = details.iat[0,1] if not details.empty else ""
            contact2 = details.iat[0,2] if not details.empty else ""
            compemail = details.iat[0,3] if not details.empty else ""

            # Payment fields (same index references as your system)
            payments = [
                {
                    "name": "Installment 1",
                    "amount": row[26],
                    "due": row[27].strftime("%-d %B %Y") if row[27] else "-",
                    "paid": row[28].strftime("%-d %B %Y") if row[28] else "Not Paid",
                },
                {
                    "name": "Installment 2",
                    "amount": row[29],
                    "due": row[30].strftime("%-d %B %Y") if row[30] else "-",
                    "paid": row[31].strftime("%-d %B %Y") if row[31] else "Not Paid",
                },
                {
                    "name": "Installment 3",
                    "amount": row[32],
                    "due": row[33].strftime("%-d %B %Y") if row[33] else "-",
                    "paid": row[34].strftime("%-d %B %Y") if row[34] else "Not Paid",
                },
                {
                    "name": "Installment 4",
                    "amount": row[35],
                    "due": row[36].strftime("%-d %B %Y") if row[36] else "-",
                    "paid": row[37].strftime("%-d %B %Y") if row[37] else "Not Paid",
                },
                {
                    "name": "Installment 5",
                    "amount": row[38],
                    "due": row[39].strftime("%-d %B %Y") if row[39] else "-",
                    "paid": row[40].strftime("%-d %B %Y") if row[40] else "Not Paid",
                },
                {
                    "name": "Installment 6",
                    "amount": row[41],
                    "due": row[42].strftime("%-d %B %Y") if row[42] else "-",
                    "paid": row[43].strftime("%-d %B %Y") if row[43] else "Not Paid",
                }
            ]

            # Get logo as base64
            logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'web-logo.png')
            with open(logo_path, 'rb') as img:
                logo_base64 = base64.b64encode(img.read()).decode('utf-8')

            # Build payments table rows
            payment_rows = ""
            for p in payments:
                payment_rows += f"""
                    <tr>
                        <td style="border:1px solid #ccc;padding:8px;">{p['name']}</td>
                        <td style="border:1px solid #ccc;padding:8px;">{p['amount']}</td>
                        <td style="border:1px solid #ccc;padding:8px;">{p['due']}</td>
                        <td style="border:1px solid #ccc;padding:8px;">{p['paid']}</td>
                    </tr>
                """

            html = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">

                <style>
                    body {{
                        font-family: 'Arial', sans-serif;
                        margin: 40px;
                        color: #1E2A56;
                        background-color: #ffffff;
                        line-height: 1.5;
                    }}

                    .header {{
                        text-align: center;
                        margin-bottom: 25px;
                    }}

                    .logo {{
                        width: 170px;
                        margin-bottom: 12px;
                    }}

                    h1 {{
                        font-size: 24px;
                        margin: 5px 0 0 0;
                        font-weight: 800;
                    }}

                    .tagline {{
                        font-size: 13px;
                        color: #445;
                        margin-top: 3px;
                    }}

                    .section-title {{
                        font-size: 17px;
                        margin-top: 35px;
                        margin-bottom: 12px;
                        padding-bottom: 6px;
                        border-bottom: 2px solid #1E2A56;
                        font-weight: 800;
                    }}

                    .info-box {{
                        padding: 12px 16px;
                        border: 1px solid #d3d6e4;
                        border-radius: 8px;
                        background: #f9faff;
                        margin-bottom: 10px;
                    }}

                    .info-box p {{
                        margin: 3px 0;
                        font-size: 14px;
                    }}

                    table {{
                        width: 100%;
                        border-collapse: collapse;
                        margin-top: 10px;
                        font-size: 14px;
                    }}

                    th {{
                        background: #1E2A56;
                        color: #fff;
                        padding: 10px;
                        text-align: left;
                        font-size: 14px;
                    }}

                    td {{
                        padding: 10px;
                        border-bottom: 1px solid #e0e3ef;
                    }}

                    tr:nth-child(even) {{
                        background: #f4f6fb;
                    }}

                    .footer {{
                        margin-top: 35px;
                        text-align: right;
                        font-size: 12px;
                        color: #666;
                    }}
                </style>
            </head>

            <body>

                <div class="header">
                    <img src="data:image/png;base64,{logo_base64}" class="logo">
                    <h3>Payments History</3>
                    <div class="tagline">Official Client Payment Record</div>
                </div>

                <div class="section-title">Client Information</div>
                <div class="info-box">
                    <p><strong>Name:</strong> {row[1]}</p>
                    <p><strong>Address:</strong> {row[3]}</p>
                    <p><strong>Contact:</strong> 0{row[4]}</p>
                    <p><strong>Email:</strong> {row[5]}</p>
                </div>

                <div class="section-title">Project Information</div>
                <div class="info-box">
                    <p><strong>Project Name:</strong> {row[10]}</p>
                    <p><strong>Location:</strong> {row[11]}</p>
                    <p><strong>Administrator:</strong> {row[13]}</p>
                </div>

                
                <!-- DEPOSIT / BULLET PAYMENT -->
                <div class="section-title">Payments Breakdown</div>

                <div class="info-box">
                    <p><strong>Deposit / Bullet Payment:</strong> USD {row[23] if row[23] else '—'}</p>
                    <p><strong>Date Paid:</strong> {row[24].strftime('%d %B %Y') if row[24] else '—'}</p>
                </div>

                <table>
                    <thead>
                        <tr>
                            <th>Installment</th>
                            <th>Amount (USD)</th>
                            <th>Due Date</th>
                            <th>Date Paid</th>
                        </tr>
                    </thead>
                    <tbody>
                        {payment_rows}
                    </tbody>
                </table>

                <div class="footer">
                    Generated on {datetime.now().strftime("%d %B %Y")}
                </div>

            </body>
            </html>
            """


            pdf = HTML(string=html, base_url=request.host_url).write_pdf()

            response = make_response(pdf)
            response.headers["Content-Type"] = "application/pdf"
            response.headers["Content-Disposition"] = f"attachment; filename={row[1]} {row[10]} payments history_{project_id}_ConnectLink Properties.pdf"

            return response

        except Exception as e:
            return str(e), 500


@app.route('/create-system-user', methods=['POST'])
def create_system_user():
    data = request.get_json()

    fullname = data.get("fullname")
    email = data.get("email")
    password = data.get("password")
    whatsapp = data.get("whatsapp")

    created_date = datetime.now()


    with get_db() as (cursor, connection):

        try:
            cursor.execute("""
                INSERT INTO connectlinkusers (datecreated, name, email, password, whatsapp)
                VALUES (%s, %s, %s, %s, %s)
            """, ( created_date ,fullname, email, password, whatsapp))

            connection.commit()

            return jsonify({"status": "success"})

        except Exception as e:
            return jsonify({"status": "error", "message": str(e)})


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


from flask import jsonify
from datetime import datetime

@app.route('/get_notes/<int:project_id>')
def get_notes(project_id):

    with get_db() as (cursor, connection):

        try:
            # Fetch notes from database
            cursor.execute("""
                SELECT id, timestamp, capturer, note 
                FROM connectlinknotes 
                WHERE projectid = %s 
                ORDER BY id DESC
            """, (project_id,))
            
            notes = cursor.fetchall()
            print(notes)
            
            notes_list = []
            for note in notes:
                notes_list.append({
                    'id': note[0],
                    'capturer': note[2],
                    'timestamp': note[1].strftime('%Y-%m-%d %H:%M:%S') if note[1] else None,
                    'note_text': note[3]
                })
            
            return jsonify({'success': True, 'notes': notes_list})
            
        except Exception as e:
            print(e)
            return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/add_note', methods=['POST'])
def add_note():
        
    with get_db() as (cursor, connection):

        user_uuid = session.get('user_uuid')
        user_name = session.get('user_name')
        userid = session.get('userid')

        try:
            client_name = request.form.get('client_name')
            client_number_raw = request.form.get('client_wa_number', '').strip()
            client_number = int(float(v)) if (v := client_number_raw) and v and v.lower() not in ['none', 'null', 'nan'] and v.replace('.', '', 1).isdigit() else None
            nextofkin_number = int(float(v)) if (v := request.form.get('client_next_of_kin_number', '').strip()) and v and v.lower() not in ['none', 'null', 'nan'] and v.replace('.', '', 1).isdigit() else None            
            project_name = request.form.get('project_name')
            project_id = request.form.get('project_id')
            note_text = request.form.get('note_text')
            
            print(client_name)
            print(client_number)
            print(nextofkin_number)
            print(project_name)
            print(project_id)
            print(note_text)

            if not project_id or not note_text:
                return jsonify({'success': False, 'message': 'Missing required fields'}), 400

            # Insert note into database
            cursor.execute("""
                INSERT INTO connectlinknotes (projectid, note, timestamp, capturer, projectname, clientname, clientwanumber, clientnextofkinnumber)
                VALUES (%s, %s, NOW(), %s, %s, %s, %s, %s)
            """, (project_id, note_text, user_name, project_name, client_name, client_number, nextofkin_number))  # Replace with actual user
            
            connection.commit()
            
            return jsonify({'success': True, 'message': 'Note added successfully'})
            
        except Exception as e:
            print(e)
            connection.rollback()
            return jsonify({'success': False, 'error': str(e)}), 500
    

@app.route('/get_filtered_projects/<month_filter>')
def get_filtered_projects(month_filter):
    with get_db() as (cursor, connection):
        try:
            # Get column names dynamically
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'connectlinkdatabase' 
                ORDER BY ordinal_position
            """)
            columns = [row[0] for row in cursor.fetchall()]
            
            print(f"DEBUG: Found {len(columns)} columns: {columns}")
            
            if month_filter == 'all' or not month_filter:
                query = "SELECT * FROM connectlinkdatabase ORDER BY id DESC"
                cursor.execute(query)
            else:
                # Filter by month/year
                query = """
                    SELECT * FROM connectlinkdatabase 
                    WHERE TO_CHAR(projectstartdate, 'YYYY-MM') = %s
                    ORDER BY id ASC
                """
                cursor.execute(query, (month_filter,))
            
            projects = cursor.fetchall()
            print(f"DEBUG: Retrieved {len(projects)} rows")
            
            if not projects:
                # Return empty table HTML
                empty_df = pd.DataFrame(columns=columns)
                empty_html = empty_df.to_html(classes="table table-bordered table-theme", 
                                              table_id="allprojectsTable", 
                                              index=False)
                return jsonify({
                    'status': 'success',
                    'html': empty_html,
                    'count': 0
                })
            
            # Convert to DataFrame with ALL columns
            datamain = pd.DataFrame(projects, columns=columns)

            datamain['projectstartdate'] = pd.to_datetime(datamain['projectstartdate'])
            datamain['momid'] = datamain.groupby(datamain['projectstartdate'].dt.strftime('%Y-%m'))['projectstartdate'].rank(method='first', ascending=True).astype(int)

            # Format date column for display
            if 'projectstartdate' in datamain.columns:
                datamain['projectstartdate'] = pd.to_datetime(datamain['projectstartdate']).dt.strftime('%d %B %Y')
            
            # Add Action column (same as in your run1 function)
            datamain['Action'] = datamain.apply(lambda row: f'''<div style="display: flex; gap: 10px;"><a href="/download_contract/{row['id']}" class="btn btn-primary3 download-contract-btn" data-id="{row['id']}" onclick="handleDownloadClick(this)">Download Contract</a><button class="btn btn-primary3 view-project-btn" data-bs-toggle="modal" data-bs-target="#viewprojectModal" data-id="{row['id']}">View Project</button><button class="btn btn-primary3 notes-btn" data-bs-toggle="modal" data-bs-target="#notesModal" data-id="{row['id']}" data-project-name="{row.get('projectname', '')}" data-client-name="{row.get('clientname', '')}">Notes</button><button class="btn btn-primary3 update-project-btn">Update</button></div>''', axis=1)
            
            # Reorder columns to match your original table
            # Put Action column at the end
            cols_order = [col for col in datamain.columns if col != 'Action'] + ['Action']
            datamain = datamain[cols_order]
            datamain = datamain[['momid', 'clientname', 'clientidnumber', 'clientaddress', 'clientwanumber', 'clientemail', 'clientnextofkinname', 'clientnextofkinaddress', 'clientnextofkinphone', 'nextofkinrelationship', 'projectname', 'projectlocation', 'projectdescription', 'projectadministratorname', 'projectstartdate', 'projectduration', 'contractagreementdate', 'totalcontractamount', 'paymentmethod', 'monthstopay', 'datecaptured', 'capturer', 'capturerid', 'depositorbullet', 'datedepositorbullet', 'monthlyinstallment', 'installment1amount', 'installment1duedate', 'installment1date', 'installment2amount', 'installment2duedate', 'installment2date', 'installment3amount', 'installment3duedate', 'installment3date', 'installment4amount', 'installment4duedate', 'installment4date', 'installment5amount', 'installment5duedate', 'installment5date', 'installment6amount', 'installment6duedate', 'installment6date','projectcompletionstatus', 'latepaymentinterest', 'id', 'Action']]
            
            # Convert to HTML
            html_table = datamain.to_html(
                classes="table table-bordered table-theme", 
                table_id="allprojectsTable", 
                index=False,  
                escape=False
            )
            
            return jsonify({
                'status': 'success',
                'html': html_table,
                'count': len(projects)
            })
            
        except Exception as e:
            print(f"❌ Error in get_filtered_projects: {str(e)}")
            import traceback
            traceback.print_exc()
            return jsonify({'status': 'error', 'message': str(e)})


@app.route('/export-installments-schedule-excel', methods=['GET'])
def export_installments_schedule_excel():
    """Export installments schedule as Excel - PostgreSQL version"""
    try:
        from datetime import date
        
        # Get today's date for filtering
        today = date.today()
        today_str = today.strftime('%Y-%m-%d')
        
        with get_db() as (cursor, connection):
            # Query for installment projects with pending payments
            query = """
            SELECT 
                id,
                clientname,
                projectname,
                projectstartdate,
                projectadministratorname,
                totalcontractamount,
                depositorbullet,
                clientwanumber,
                momid,
                monthstopay,
                installment1amount, installment1duedate, installment1date,
                installment2amount, installment2duedate, installment2date,
                installment3amount, installment3duedate, installment3date,
                installment4amount, installment4duedate, installment4date,
                installment5amount, installment5duedate, installment5date,
                installment6amount, installment6duedate, installment6date
            FROM connectlinkdatabase 
            WHERE paymentmethod = 'Installments'
            AND (
                (installment1amount > 0 AND installment1date IS NULL) OR
                (installment2amount > 0 AND installment2date IS NULL) OR
                (installment3amount > 0 AND installment3date IS NULL) OR
                (installment4amount > 0 AND installment4date IS NULL) OR
                (installment5amount > 0 AND installment5date IS NULL) OR
                (installment6amount > 0 AND installment6date IS NULL)
            )
            ORDER BY 
                DATE_TRUNC('month', projectstartdate) DESC,
                projectstartdate ASC,
                momid ASC;
            """
            
            cursor.execute(query)
            rows = cursor.fetchall()
            
            if not rows:
                return jsonify({'status': 'error', 'message': 'No pending installments found'}), 404
            
            # Get column names
            colnames = [desc[0] for desc in cursor.description]
            
        # Convert to DataFrame
        df = pd.DataFrame(rows, columns=colnames)
        
        # Process data for detailed sheets
        data = []
        # Collect data for monthly cross-tab
        monthly_data = []
        
        for _, row in df.iterrows():
            # Format dates
            project_start = row.get('projectstartdate')
            month_year = project_start.strftime('%Y-%m') if pd.notna(project_start) else 'No Date'
            
            project_data = {
                'Month-Year': month_year,
                'MOM ID': int(row.get('momid', 0)) if pd.notna(row.get('momid')) else 0,
                'Client Name': str(row.get('clientname', '')),
                'Project Name': str(row.get('projectname', '')),
                'Client Phone': str(row.get('clientwanumber', '')),
                'Administrator': str(row.get('projectadministratorname', '')),
                'Total Contract': float(row.get('totalcontractamount', 0)) if pd.notna(row.get('totalcontractamount')) else 0.0,
                'Deposit Paid': float(row.get('depositorbullet', 0)) if pd.notna(row.get('depositorbullet')) else 0.0,
                'Months To Pay': int(row.get('monthstopay', 0)) if pd.notna(row.get('monthstopay')) else 0,
                'Project Start': project_start.strftime('%d-%b-%Y') if pd.notna(project_start) else ''
            }
            
            # Check installments 1-6
            pending_installments = []
            total_pending = 0.0
            total_paid = 0.0
            overdue_amount = 0.0
            future_amount = 0.0
            
            for i in range(1, 7):
                amount = row.get(f'installment{i}amount')
                due_date = row.get(f'installment{i}duedate')
                payment_date = row.get(f'installment{i}date')
                
                if amount and float(amount) > 0:
                    if pd.isna(payment_date):  # Pending
                        due_str = due_date.strftime('%d-%b-%Y') if pd.notna(due_date) else 'No Due Date'
                        due_month = due_date.strftime('%Y-%m') if pd.notna(due_date) else 'No Month'
                        
                        # Check if overdue
                        is_overdue = False
                        if pd.notna(due_date):
                            is_overdue = due_date < today
                        
                        installment_data = {
                            'number': i,
                            'due_date': due_str,
                            'due_month': due_month,
                            'amount': float(amount),
                            'status': 'OVERDUE' if is_overdue else 'PENDING'
                        }
                        
                        pending_installments.append(installment_data)
                        total_pending += float(amount)
                        
                        if is_overdue:
                            overdue_amount += float(amount)
                        else:
                            future_amount += float(amount)
                        
                        # Collect for monthly cross-tab (only if not overdue and has due date)
                        if pd.notna(due_date) and due_month != 'No Month':
                            status = 'OVERDUE' if is_overdue else 'PENDING'
                            monthly_data.append({
                                'clientname': str(row.get('clientname', '')),
                                'projectname': str(row.get('projectname', '')),
                                'due_date': due_date,
                                'due_month': due_month,
                                'amount': float(amount),
                                'installment_num': i,
                                'status': status,
                                'is_overdue': is_overdue
                            })
                    else:  # Paid
                        pending_installments.append({
                            'number': i,
                            'due_date': 'PAID',
                            'amount': float(amount),
                            'status': 'PAID'
                        })
                        total_paid += float(amount)
            
            # Sort by installment number
            pending_installments.sort(key=lambda x: x['number'])
            
            # Add installment columns (up to 6 installments)
            for idx, inst in enumerate(pending_installments[:6], 1):
                project_data[f'Inst {idx}'] = f"#{inst['number']}"
                project_data[f'Due {idx}'] = inst['due_date']
                project_data[f'Amount {idx}'] = inst['amount']
                project_data[f'Status {idx}'] = inst['status']
            
            # Add totals
            project_data['Total Pending'] = total_pending
            project_data['Total Paid'] = total_paid
            project_data['Balance Due'] = float(row.get('totalcontractamount', 0) or 0) - total_paid - float(row.get('depositorbullet', 0) or 0)
            project_data['Overdue Amount'] = overdue_amount
            project_data['Future Amount'] = future_amount
            
            data.append(project_data)
        
        # Create DataFrames
        result_df = pd.DataFrame(data)
        monthly_df = pd.DataFrame(monthly_data) if monthly_data else pd.DataFrame()
        
        # Create Excel file
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            if result_df.empty:
                empty_df = pd.DataFrame({'Message': ['No pending installments found']})
                empty_df.to_excel(writer, sheet_name='No Data', index=False)
            else:
                # Sort by Month-Year and MOM ID
                result_df = result_df.sort_values(['Month-Year', 'MOM ID'])
                
                # Group by Month-Year into separate sheets
                for month_year in sorted(result_df['Month-Year'].unique()):
                    if month_year != 'No Date':
                        month_df = result_df[result_df['Month-Year'] == month_year].copy()
                        month_df = month_df.drop('Month-Year', axis=1)
                        
                        # Format currency columns
                        currency_cols = ['Total Contract', 'Deposit Paid', 'Total Pending', 'Total Paid', 
                                       'Balance Due', 'Overdue Amount', 'Future Amount']
                        for col in currency_cols:
                            if col in month_df.columns:
                                month_df[col] = month_df[col].apply(
                                    lambda x: f"${x:,.2f}" if pd.notna(x) and isinstance(x, (int, float)) else ""
                                )
                        
                        # Format installment amounts
                        for col in month_df.columns:
                            if 'Amount' in col and col.startswith('Amount'):
                                month_df[col] = month_df[col].apply(
                                    lambda x: f"${x:,.2f}" if pd.notna(x) and isinstance(x, (int, float)) else ""
                                )
                        
                        # Write to sheet (max 31 chars for sheet name)
                        sheet_name = str(month_year)[:31]
                
                # ================================================
                # MONTHLY CROSS-TAB SUMMARY (Clients vs Months)
                # ================================================
                if not monthly_df.empty:
                    # Create pivot table: Client Name as rows, Due Months as columns
                    pivot_table = monthly_df.pivot_table(
                        index='clientname',
                        columns='due_month',
                        values='amount',
                        aggfunc='sum',
                        fill_value=0
                    ).reset_index()
                    
                    # Sort months chronologically
                    month_columns = [col for col in pivot_table.columns if col != 'clientname']
                    month_columns_sorted = sorted(month_columns, key=lambda x: x)
                    pivot_table = pivot_table[['clientname'] + month_columns_sorted]
                    
                    # Add total column for each client
                    pivot_table['Total Pending'] = pivot_table[month_columns_sorted].sum(axis=1)
                    
                    # Sort by client name
                    pivot_table = pivot_table.sort_values('clientname')
                    
                    # Add TOTAL ROW at the bottom
                    total_row = {'clientname': 'TOTAL'}
                    for col in month_columns_sorted:
                        total_row[col] = pivot_table[col].sum()
                    total_row['Total Pending'] = pivot_table['Total Pending'].sum()
                    
                    # Append total row
                    pivot_table = pd.concat([pivot_table, pd.DataFrame([total_row])], ignore_index=True)
                    
                    # Format currency in pivot table
                    pivot_formatted = pivot_table.copy()
                    for col in month_columns_sorted + ['Total Pending']:
                        pivot_formatted[col] = pivot_formatted[col].apply(
                            lambda x: f"${x:,.2f}" if pd.notna(x) and x != 0 else ""
                        )
                    
                    # Write cross-tab summary
                    pivot_formatted.to_excel(writer, sheet_name='Monthly Cross-Tab', index=False)
                    
                    # Auto-adjust column widths for cross-tab
                    worksheet = writer.sheets['Monthly Cross-Tab']
                    for column in worksheet.columns:
                        max_length = 0
                        column_letter = column[0].column_letter
                        for cell in column:
                            try:
                                if len(str(cell.value)) > max_length:
                                    max_length = len(str(cell.value))
                            except:
                                pass
                        adjusted_width = min(max_length + 2, 30)
                        worksheet.column_dimensions[column_letter].width = adjusted_width
                    
                    # Create monthly totals summary with overdue/future split
                    monthly_totals = monthly_df.groupby('due_month').agg({
                        'clientname': 'nunique',
                        'amount': 'sum'
                    }).reset_index()
                    
                    # Add overdue vs future amounts
                    overdue_by_month = monthly_df[monthly_df['is_overdue']].groupby('due_month')['amount'].sum().reset_index()
                    overdue_by_month = overdue_by_month.rename(columns={'amount': 'overdue_amount'})
                    
                    future_by_month = monthly_df[~monthly_df['is_overdue']].groupby('due_month')['amount'].sum().reset_index()
                    future_by_month = future_by_month.rename(columns={'amount': 'future_amount'})
                    
                    # Merge all
                    monthly_totals = pd.merge(monthly_totals, overdue_by_month, on='due_month', how='left')
                    monthly_totals = pd.merge(monthly_totals, future_by_month, on='due_month', how='left')
                    
                    # Fill NaN with 0
                    monthly_totals['overdue_amount'] = monthly_totals['overdue_amount'].fillna(0)
                    monthly_totals['future_amount'] = monthly_totals['future_amount'].fillna(0)
                    
                    monthly_totals = monthly_totals.rename(columns={
                        'clientname': 'Unique Clients',
                        'amount': 'Total Pending'
                    }).sort_values('due_month')
                    
                    # Format currency
                    for col in ['Total Pending', 'overdue_amount', 'future_amount']:
                        monthly_totals[col] = monthly_totals[col].apply(lambda x: f"${x:,.2f}")
                                        
                    # Create summary by status (overdue vs pending)
                    status_summary = monthly_df.groupby('status').agg({
                        'clientname': 'nunique',
                        'amount': 'sum'
                    }).reset_index()
                    
                    status_summary = status_summary.rename(columns={
                        'clientname': 'Unique Clients',
                        'amount': 'Total Amount'
                    })
                    
                    # Format currency
                    status_summary['Total Amount'] = status_summary['Total Amount'].apply(lambda x: f"${x:,.2f}")
                    
                    status_summary.to_excel(writer, sheet_name='Status Summary', index=False)
                
                # ================================================
                # OVERDUE VS FUTURE SUMMARY
                # ================================================
                if not result_df.empty:
                    # Overdue summary
                    overdue_summary = result_df.groupby('Client Name').agg({
                        'Overdue Amount': 'sum',
                        'Future Amount': 'sum',
                        'Total Pending': 'sum'
                    }).reset_index()
                    
                    # Filter for clients with overdue
                    clients_with_overdue = overdue_summary[overdue_summary['Overdue Amount'] > 0].copy()
                    clients_with_overdue = clients_with_overdue.sort_values('Overdue Amount', ascending=False)
                    
                    # Format currency
                    for col in ['Overdue Amount', 'Future Amount', 'Total Pending']:
                        clients_with_overdue[col] = clients_with_overdue[col].apply(lambda x: f"${x:,.2f}")
                    
                    clients_with_overdue.to_excel(writer, sheet_name='Overdue Clients', index=False)
                
                # ================================================
                # Original Summary sheet
                # ================================================
                if not result_df.empty:
                    # Convert currency columns back to numeric for calculations
                    numeric_df = result_df.copy()
                    for col in ['Total Contract', 'Deposit Paid', 'Total Pending', 'Total Paid', 
                               'Balance Due', 'Overdue Amount', 'Future Amount']:
                        if col in numeric_df.columns:
                            # Remove $ and commas, convert to float
                            numeric_df[col] = numeric_df[col].replace(r'[\$,]', '', regex=True).replace('', '0').astype(float)
                    
                    # Monthly summary
                    monthly_summary = numeric_df.groupby('Month-Year').agg({
                        'Client Name': 'count',
                        'Total Contract': 'sum',
                        'Deposit Paid': 'sum',
                        'Total Pending': 'sum',
                        'Total Paid': 'sum',
                        'Balance Due': 'sum',
                        'Overdue Amount': 'sum',
                        'Future Amount': 'sum'
                    }).reset_index()
                    
                    monthly_summary = monthly_summary.rename(columns={
                        'Client Name': 'Projects',
                        'Total Contract': 'Contract Value',
                        'Deposit Paid': 'Deposit Collected',
                        'Total Pending': 'Pending Amount',
                        'Total Paid': 'Paid Amount',
                        'Balance Due': 'Balance Due'
                    })
                    
                    # Format currency in summary
                    currency_cols_summary = ['Contract Value', 'Deposit Collected', 'Pending Amount', 
                                           'Paid Amount', 'Balance Due', 'Overdue Amount', 'Future Amount']
                    for col in currency_cols_summary:
                        if col in monthly_summary.columns:
                            monthly_summary[col] = monthly_summary[col].apply(lambda x: f"${x:,.2f}")
                    
                    monthly_summary.to_excel(writer, sheet_name='Monthly Summary', index=False)
                    
                    # Add Report Info sheet
                    report_info = pd.DataFrame({
                        'Report Date': [today.strftime('%d-%b-%Y')],
                        'Total Projects': [len(result_df)],
                        'Total Pending Amount': [f"${numeric_df['Total Pending'].sum():,.2f}"],
                        'Total Overdue Amount': [f"${numeric_df['Overdue Amount'].sum():,.2f}"],
                        'Total Future Amount': [f"${numeric_df['Future Amount'].sum():,.2f}"],
                        'Generated At': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
                    })
                    report_info.to_excel(writer, sheet_name='Report Info', index=False)
        
        output.seek(0)
        
        # Create filename with date
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'installment_schedule_{today_str}_{timestamp}.xlsx'
        
        return send_file(
            output,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        print(f"PostgreSQL Error: {str(e)}")
        traceback.print_exc()
        return jsonify({'status': 'error', 'message': f'Failed to generate schedule: {str(e)}'}), 500


def run1(userid):

    with get_db() as (cursor, connection):

        print(userid)
        today_date = datetime.now().strftime('%d %B %Y')
        applied_date = datetime.now().strftime('%Y-%m-%d')

        enquiriesdataquery = f"SELECT * FROM connectlinkenquiries;"
        cursor.execute(enquiriesdataquery)
        enquiriesdata = cursor.fetchall()
        print(enquiriesdata)

        enquiriesdatamain = pd.DataFrame(enquiriesdata, columns=['ID','Timestamp','Contact','Enquiry','Description','Document','Username','Status'])
        enquiriesdatamain = enquiriesdatamain[['ID','Timestamp','Username','Contact','Enquiry','Description','Document','Status']]
        enquiriesdatamain_html = enquiriesdatamain.to_html(classes="table table-bordered table-theme", table_id="allenquiriesTable", index=False,  escape=False,)


        usersdataquery = f"SELECT * FROM connectlinkusers;"
        cursor.execute(usersdataquery)
        usersdata = cursor.fetchall()
        print(usersdata)

        usersdatamain = pd.DataFrame(usersdata, columns= ['id', 'datecreated','name', 'password','email','whatsapp'])

        usersdatamain['Action'] = usersdatamain.apply(lambda row: f'''<div><button class="btn btn-danger-2" data-bs-toggle="modal" data-bs-target="#removeUserModal" data-user-id="{row['id']}" data-user-name="{html.escape(str(row.get('name', '')))}"data-user-email="{html.escape(str(row.get('email', '')))}">Remove</button></div>''', axis=1)
        usersdatamain = usersdatamain[['id', 'datecreated','name','email','whatsapp','Action']]
        usersdatamain_html = usersdatamain.to_html(classes="table table-bordered table-theme", table_id="allusersTable", index=False,  escape=False,)


        ####### admins

        adminsdataquery = f"SELECT * FROM connectlinkadmin;"
        cursor.execute(adminsdataquery)
        adminsdata = cursor.fetchall()
        print(adminsdata)

        adminsdatamain = pd.DataFrame(adminsdata, columns= ['id', 'name', 'contact'])
        adminsdatamain['Action'] = adminsdatamain['id'].apply(lambda x: f'''<div style="display: flex; gap: 10px;"><button class="btn btn-primary edit-admin-details-btn" style="width:max-content;" data-bs-toggle="modal" data-bs-target="#viewprojectModal" data-ID="{x}">Edit Details</button>    <button class="btn btn-danger-2 remove-admin-btn" data-ID="{x}">Remove</button></div>''')
        adminsdatamain = adminsdatamain[['id', 'name', 'contact', 'Action']]
        table_datamain_admins_html = adminsdatamain.to_html(classes="table table-bordered table-theme", table_id="alladminsTable", index=False,  escape=False,)

        admin_options = adminsdatamain.apply(lambda row: f"{row['name']}", axis=1).tolist()


        ######### maindata
        maindataquery = f"SELECT * FROM connectlinkdatabase;"
        cursor.execute(maindataquery)
        maindata = cursor.fetchall()
        print(maindata)
        num_projects = len(maindata)
        print(f"Number of projects: {num_projects}")


        datamain = pd.DataFrame(maindata, columns= ['id', 'clientname', 'clientidnumber', 'clientaddress', 'clientwanumber', 'clientemail', 'clientnextofkinname', 'clientnextofkinaddress', 'clientnextofkinphone', 'nextofkinrelationship', 'projectname', 'projectlocation', 'projectdescription', 'projectadministratorname', 'projectstartdate', 'projectduration', 'contractagreementdate', 'totalcontractamount', 'paymentmethod', 'monthstopay', 'datecaptured', 'capturer', 'capturerid', 'depositorbullet', 'datedepositorbullet', 'monthlyinstallment', 'installment1amount', 'installment1duedate', 'installment1date', 'installment2amount', 'installment2duedate', 'installment2date', 'installment3amount', 'installment3duedate', 'installment3date', 'installment4amount', 'installment4duedate', 'installment4date', 'installment5amount', 'installment5duedate', 'installment5date', 'installment6amount', 'installment6duedate', 'installment6date','projectcompletionstatus','latepaymentinterest','momid'])

        count_ongoing = datamain[datamain["projectcompletionstatus"] == "Ongoing"].shape[0]
        count_completed = datamain[datamain["projectcompletionstatus"] == "Completed"].shape[0]
        average_duration = round(pd.to_numeric(datamain["projectduration"], errors="coerce").mean(),0)
        locations = datamain['projectlocation'].replace('', pd.NA)

        locations2 = datamain['projectlocation'].dropna().astype(str)  # remove None/NaN, ensure string
        location_counts = Counter(locations2)

        # Convert to lists for Jinja
        locations_list = list(location_counts.keys())
        frequencies_list = list(location_counts.values())

        # Get the most frequent location
        most_frequent_location = locations.value_counts(dropna=True).idxmax()

        datamain['Action'] = datamain.apply(lambda row: f''' <div style="display: flex; gap: 10px;"> <a href="/download_contract/{row['id']}" class="btn btn-primary3 download-contract-btn" data-id="{row['id']}" onclick="handleDownloadClick(this)">Download Contract</a> <button class="btn btn-primary3 view-project-btn" data-bs-toggle="modal" data-bs-target="#viewprojectModal" data-id="{row['id']}">View Project</button> <button class="btn btn-primary3 notes-btn" data-bs-toggle="modal" data-bs-target="#notesModal" data-id="{row['id']}" data-project-name="{row['projectname']}" data-client-name="{row['clientname']}"  data-client-wa-number="{row['clientwanumber']}" data-client-next-of-kin-number="{row['clientnextofkinphone']}">Notes</button> <button class="btn btn-primary3 update-project-btn">Update</button> </div>''', axis=1)        
        
        datamain['projectstartdate'] = pd.to_datetime(datamain['projectstartdate'])
        datamain['momid'] = datamain.groupby(datamain['projectstartdate'].dt.strftime('%Y-%m'))['projectstartdate'].rank(method='first', ascending=True).astype(int)

        datamain['projectstartdate'] = pd.to_datetime(datamain['projectstartdate']).dt.strftime('%d %B %Y')

        datamain = datamain[['momid', 'clientname', 'clientidnumber', 'clientaddress', 'clientwanumber', 'clientemail', 'clientnextofkinname', 'clientnextofkinaddress', 'clientnextofkinphone', 'nextofkinrelationship', 'projectname', 'projectlocation', 'projectdescription', 'projectadministratorname', 'projectstartdate', 'projectduration', 'contractagreementdate', 'totalcontractamount', 'paymentmethod', 'monthstopay', 'datecaptured', 'capturer', 'capturerid', 'depositorbullet', 'datedepositorbullet', 'monthlyinstallment', 'installment1amount', 'installment1duedate', 'installment1date', 'installment2amount', 'installment2duedate', 'installment2date', 'installment3amount', 'installment3duedate', 'installment3date', 'installment4amount', 'installment4duedate', 'installment4date', 'installment5amount', 'installment5duedate', 'installment5date', 'installment6amount', 'installment6duedate', 'installment6date','projectcompletionstatus', 'latepaymentinterest', 'id', 'Action']]
                        
        datamain = datamain.sort_values('id', ascending=False)

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
        
        cursor.execute("""
            SELECT DISTINCT 
                TO_CHAR(projectstartdate, 'Mon-YYYY') as month_display,
                TO_CHAR(projectstartdate, 'YYYY-MM') as month_value,
                MAX(projectstartdate) as max_date
            FROM connectlinkdatabase 
            WHERE projectstartdate IS NOT NULL
            GROUP BY TO_CHAR(projectstartdate, 'Mon-YYYY'), TO_CHAR(projectstartdate, 'YYYY-MM')
            ORDER BY MAX(projectstartdate) DESC
        """)
        
        month_options = cursor.fetchall()
        month_options_list = [
            {'display': row[0], 'value': row[1], 'date': row[2]} 
            for row in month_options
        ]
        
        # Add "All" option at the end
        month_options_list.append({'display': 'All', 'value': 'all', 'date': None})
        enquiries_data = get_enquiries_data()

        return {
            'month_options': month_options_list,
            "usersdatamain_html": usersdatamain_html,
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
            'count_ongoing': count_ongoing,
            'count_completed': count_completed,
            'average_duration': average_duration,
            'most_frequent_location': most_frequent_location,
            'locations': locations_list,
            'frequencies': frequencies_list,
            'admin_options': admin_options,
            "enquiriesdatamain_html" : enquiriesdatamain_html,
            "enquiries_data": enquiries_data  # Pure Python list, NO HTML
            }

def get_enquiries_data():
    """Get enquiries data for template"""
    try:
        with get_db() as (cursor, connection):
            # Get enquiries
            cursor.execute("""
                SELECT id, timestamp, clientwhatsapp, enqcategory, enq,
                       plan IS NOT NULL as has_plan, status, username
                FROM connectlinkenquiries 
                ORDER BY timestamp DESC 
                LIMIT 15
            """)
            enquiries = cursor.fetchall()
            
            # Convert to list of dicts
            enquiries_list = []
            for enquiry in enquiries:
                enquiries_list.append({
                    'id': enquiry[0],
                    'timestamp': enquiry[1].strftime('%d/%m %H:%M') if enquiry[1] else '',
                    'username': enquiry[7],
                    'clientwhatsapp': enquiry[2],
                    'category': enquiry[3],
                    'message': enquiry[4],
                    'has_plan': enquiry[5],
                    'status': enquiry[6] or 'pending'
                })
            
            return enquiries_list
            
    except Exception as e:
        print(f"Error getting enquiries: {str(e)}")
        return []


@app.route('/api/enquiries/<int:enquiry_id>/plan', methods=['GET'])
def download_enquiry_plan(enquiry_id):
    """Download the plan PDF attachment"""
    try:
        with get_db() as (cursor, connection):
            cursor.execute("""
                SELECT plan, timestamp, clientwhatsapp
                FROM connectlinkenquiries 
                WHERE id = %s AND plan IS NOT NULL;
            """, (enquiry_id,))
            row = cursor.fetchone()
            
            if not row:
                return jsonify({'status': 'error', 'message': 'Plan not found'}), 404
            
            plan_data = row[0]  # BYTEA data
            timestamp = row[1]
            client_whatsapp = row[2]
            
            if not plan_data:
                return jsonify({'status': 'error', 'message': 'Plan data is empty'}), 404
            
            # Create filename
            filename = f"enquiry_plan_{enquiry_id}_{client_whatsapp}_{timestamp.strftime('%Y%m%d')}.pdf"
            
            # Return PDF file
            return send_file(
                io.BytesIO(plan_data),
                as_attachment=True,
                download_name=filename,
                mimetype='application/pdf'
            )
            
    except Exception as e:
        print(f"Error downloading plan: {str(e)}")
        return jsonify({'status': 'error', 'message': f'Failed to download plan: {str(e)}'}), 500

# Status update endpoint remains the same
@app.route('/api/enquiries/<int:enquiry_id>/status', methods=['PUT'])
def update_enquiry_status(enquiry_id):
    """Update enquiry status"""
    try:
        data = request.json
        new_status = data.get('status')
        
        if not new_status:
            return jsonify({'status': 'error', 'message': 'Status is required'}), 400
        
        with get_db() as (cursor, connection):
            cursor.execute("""
                UPDATE connectlinkenquiries 
                SET status = %s
                WHERE id = %s
                RETURNING id;
            """, (new_status, enquiry_id))
            
            connection.commit()
            
            return jsonify({
                'status': 'success',
                'message': 'Enquiry status updated successfully',
                'enquiry_id': enquiry_id,
                'new_status': new_status
            })
            
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Failed to update status: {str(e)}'}), 500



@app.route('/')
def userlogin():
    return render_template('login.html') 

@app.route('/get_project/<int:project_id>')
def get_project(project_id):

    with get_db() as (cursor, connection):

        try:
            cursor.execute("SELECT * FROM connectlinkdatabase WHERE id=%s", (project_id,))
            row = cursor.fetchone()

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
                    'projectcompletionstatus','latepaymentinterest']

            project_dict = dict(zip(columns, row))
            print(project_dict)
            return jsonify(project_dict)

        except Exception as e:
            return jsonify({"error": str(e)})
        
def add_months(source_date, months):
    month = source_date.month - 1 + months
    year = source_date.year + (month // 12)
    month = month % 12 + 1
    # Pick the smaller of the original day or the last day of target month
    day = min(source_date.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def last_day_of_month(d):
    """Return the last day of d's month."""
    last_day = calendar.monthrange(d.year, d.month)[1]
    return date(d.year, d.month, last_day)

def clean_date_update(value):
    return value if value not in ("", None) else None

@app.route('/update_project', methods=['POST'])
def update_project():

    with get_db() as (cursor, connection):

        project_id = request.form.get('project_id')
        completion_status = request.form.get('completion_status')
        projscope = request.form.get('projscope')
        installment1_date = clean_date_update(request.form.get('installment1_paid_date'))
        installment2_date = clean_date_update(request.form.get('installment2_paid_date'))
        installment3_date = clean_date_update(request.form.get('installment3_paid_date'))
        installment4_date = clean_date_update(request.form.get('installment4_paid_date'))
        installment5_date = clean_date_update(request.form.get('installment5_paid_date'))
        installment6_date = clean_date_update(request.form.get('installment6_paid_date'))


        # --- EXAMPLE SQL (modify for your DB) ---
        query = """
            UPDATE connectlinkdatabase
            SET 
                projectcompletionstatus = %s,
                installment1date = %s,
                installment2date = %s,
                installment3date = %s,
                installment4date = %s,
                installment5date = %s,
                installment6date = %s,
                projectdescription = %s
            WHERE id = %s
        """
        
        values = (
            completion_status,
            installment1_date,
            installment2_date,
            installment3_date,
            installment4_date,
            installment5_date,
            installment6_date,
            projscope,
            project_id
        )

        cursor.execute(query, values)
        connection.commit()

        flash("Project updated successfully!", "success")
        return redirect(url_for('Dashboard'))  # or wherever you want to go


def get_mom_id_for_project(project_start_date):
    """Get MOM ID for a project based on month/year and existing momid values"""
    with get_db() as (cursor, connection):
        try:
            # Extract month and year from the project start date
            month = project_start_date.month
            year = project_start_date.year
            
            print(f"DEBUG: Looking for projects in month {month}, year {year}")
            
            # Get all projects in the same month and year
            cursor.execute("""
                SELECT id, clientname, projectname, projectstartdate, momid
                FROM connectlinkdatabase 
                WHERE EXTRACT(MONTH FROM projectstartdate) = %s 
                AND EXTRACT(YEAR FROM projectstartdate) = %s
                ORDER BY projectstartdate
            """, (month, year))
            
            projects_in_month = cursor.fetchall()
            
            print(f"DEBUG: Found {len(projects_in_month)} projects in {month}/{year}")
            
            if projects_in_month:
                # Debug print all projects found
                for project in projects_in_month:
                    print(f"  - Project ID: {project[0]}, Name: {project[2]}, Date: {project[3]}, MOM ID: {project[4]}")
                
                # Find the highest momid value (excluding NULLs)
                momid_values = [project[4] for project in projects_in_month if project[4] is not None]
                
                if momid_values:
                    highest_momid = max(momid_values)
                    print(f"DEBUG: Highest MOM ID found: {highest_momid}")
                    momcurrentid = highest_momid + 1
                else:
                    # No momid values found, start from 1
                    print(f"DEBUG: No MOM IDs found in this month/year, starting from 1")
                    momcurrentid = 1
            else:
                # No projects in this month/year, start from 1
                print(f"DEBUG: No projects found in {month}/{year}, starting from 1")
                momcurrentid = 1
            
            print(f"DEBUG: New MOM ID assigned: {momcurrentid}")
            return momcurrentid
            
        except Exception as e:
            print(f"❌ Error getting MOM ID: {str(e)}")
            # Return a default value or re-raise the exception
            return 1

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
                client_whatsapp_number = request.form.get('client_whatsapp_number')[-9:]
                client_email = request.form.get('client_email')

                next_of_kin_name = request.form.get('next_of_kin_name')
                next_of_kin_address = request.form.get('next_of_kin_address')
                next_of_kin_contact_number = request.form.get('next_of_kin_contact_number')[-9:]
                relationship = request.form.get('relationship')

                project_administrator = request.form.get('projectadministrator')

                project_name = request.form.get('project_name')
                project_location = request.form.get('project_location')
                project_start_date = request.form.get('project_start_date')

                project_start_date_date = datetime.strptime(project_start_date, "%Y-%m-%d").date()
                momcurrentid = get_mom_id_for_project(project_start_date_date)



                months_to_completion = request.form.get('months_to_completion')
                project_description = request.form.get('project_description') or ""

                ALLOWED_TAGS = set(bleach.sanitizer.ALLOWED_TAGS).union({
                    'p', 'br', 'ul', 'ol', 'li', 'span', 'strong', 'em'
                })

                ALLOWED_ATTRIBUTES = {
                    '*': ['style'],
                    'span': ['class']
                }

                clean_html = bleach.clean(
                    request.form.get("project_description", ""),
                    tags=ALLOWED_TAGS,
                    attributes=ALLOWED_ATTRIBUTES,
                    strip=True
                )

                agreement_date = request.form.get('agreement_date')
                total_contract_price = request.form.get('total_contract_price')
                latepaymentinterest = request.form.get('late_payment_interest')

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
                first_installment_due_date = request.form.get('first_installment_due_date')
                first_installment_due_date_calc = datetime.strptime(first_installment_due_date, "%Y-%m-%d").date()
                                
                installment_due_dates = []

                # Generate installment dates
                for i in range(int(months_to_pay)):
                    next_date = add_months(first_installment_due_date_calc, i)
                    installment_due_dates.append(next_date)

                # Fill up to 6 slots using same day logic for following months
                while len(installment_due_dates) < 6:
                    next_date = add_months(first_installment_due_date_calc, len(installment_due_dates))
                    installment_due_dates.append(next_date)


                installment1duedate, installment2duedate, installment3duedate, installment4duedate, installment5duedate, installment6duedate = installment_due_dates


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

                installment2duedate = installment_due_dates[1] if int(months_to_pay) >= 2 else None
                installment3duedate = installment_due_dates[2] if int(months_to_pay) >= 3 else None
                installment4duedate = installment_due_dates[3] if int(months_to_pay) >= 4 else None
                installment5duedate = installment_due_dates[4] if int(months_to_pay) >= 5 else None
                installment6duedate = installment_due_dates[5] if int(months_to_pay) >= 6 else None


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
                            momid, clientname, clientidnumber, clientaddress, clientwanumber, clientemail,
                            clientnextofkinname, clientnextofkinaddress, clientnextofkinphone, nextofkinrelationship,
                            projectname, projectlocation, projectdescription, projectadministratorname,
                            projectstartdate, projectduration, contractagreementdate, totalcontractamount,
                            paymentmethod, monthstopay, depositorbullet, datedepositorbullet, monthlyinstallment, 
                            installment1duedate, datecaptured, capturer, capturerid, projectcompletionstatus, latepaymentinterest, installment1amount, installment2amount, installment3amount, installment4amount, installment5amount, installment6amount, installment2duedate, installment3duedate, installment4duedate, installment5duedate, installment6duedate
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                        );
                    """

                    params = (
                        momcurrentid,
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
                        clean_html,
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
                        latepaymentinterest,
                        installment1amount,
                        installment2amount,
                        installment3amount,
                        installment4amount,
                        installment5amount,
                        installment6amount,
                        installment2duedate,
                        installment3duedate,
                        installment4duedate,
                        installment5duedate,
                        installment6duedate
                    )

        
                    cursor.execute(insert_query, params)
                    connection.commit()
                    print("✅ Project inserted into connectlinkdatabase")


                except Exception as e:
                    connection.rollback()
                    print("❌ Failed to insert project:", e)
                    response = {'status': 'error', 'message': 'Failed to save project.'}
                    return jsonify(response), 500

                # At the end of your try block
                return redirect(url_for('Dashboard'))  # or wherever you want to go


            except Exception as e:
                print("❌ UNCAUGHT ERROR in contract_log():", str(e))  # <-- PRINT REAL ERROR
                return jsonify({'status': 'error', 'message': str(e)}), 400

@app.route('/update_first_installment_date', methods=['POST'])
def update_first_installment_date():
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        new_date_str = data.get('new_date')

        print(project_id)
        print(new_date_str)

        cursor.execute("""
            SELECT monthstopay
            FROM connectlinkdatabase
            WHERE id = %s
        """, (project_id,))
        result = cursor.fetchone()

        months_to_pay = int(result[0])

        if not project_id or not new_date_str:
            return jsonify({"success": False, "message": "Project ID and new date are required"}), 400

        # Convert string date to Python date
        new_date = datetime.strptime(new_date_str, "%Y-%m-%d").date()

        installment_due_dates = []

        # Generate installment dates
        for i in range(int(months_to_pay)):
            next_date = add_months(new_date, i)
            installment_due_dates.append(next_date)

        # Fill up to 6 slots using same day logic for following months
        while len(installment_due_dates) < 6:
            next_date = add_months(new_date, len(installment_due_dates))
            installment_due_dates.append(next_date)


        installment1duedate, installment2duedate, installment3duedate, installment4duedate, installment5duedate, installment6duedate = installment_due_dates
        installment1duedate = installment_due_dates[0] if int(months_to_pay) >= 1 else None
        installment2duedate = installment_due_dates[1] if int(months_to_pay) >= 2 else None
        installment3duedate = installment_due_dates[2] if int(months_to_pay) >= 3 else None
        installment4duedate = installment_due_dates[3] if int(months_to_pay) >= 4 else None
        installment5duedate = installment_due_dates[4] if int(months_to_pay) >= 5 else None
        installment6duedate = installment_due_dates[5] if int(months_to_pay) >= 6 else None

        with get_db() as (cursor, connection):
            cursor.execute("""
                UPDATE connectlinkdatabase
                SET installment1duedate = %s,
                    installment2duedate = %s,
                    installment3duedate = %s,
                    installment4duedate = %s,
                    installment5duedate = %s,
                    installment6duedate = %s
                WHERE id = %s
            """, (
                installment1duedate,
                installment2duedate,
                installment3duedate,
                installment4duedate,
                installment5duedate,
                installment6duedate,
                project_id
            ))
            connection.commit()

        return jsonify({
            "success": True,
            "message": "First installment and all other installment dates updated successfully",
            "installment_dates": [str(d) if d else "" for d in installment_due_dates]
        })

    except Exception as e:
        print("Error updating first installment date:", e)
        return jsonify({"success": False, "message": str(e)}), 500

@app.route('/download_deposit_receipt/<project_id>')
def download_deposit_receipt(project_id):
    with get_db() as (cursor, connection):
        # Fetch project info

        cursor.execute("SELECT id, clientname, clientaddress, clientwanumber, clientemail,projectname, projectlocation, projectdescription, projectadministratorname, depositorbullet, datedepositorbullet  FROM connectlinkdatabase WHERE id = %s", (project_id,))
        row = cursor.fetchone()
        if not row:
            return "Project not found", 404

        # Fetch company info
        cursor.execute("SELECT * FROM connectlinkdetails;")
        details = cursor.fetchall()
        company = details[0] if details else {}

        # Get logo
        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'web-logo.png')
        with open(logo_path, 'rb') as img:
            logo_base64 = base64.b64encode(img.read()).decode('utf-8')

        # HTML template
        html = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <style>
                @page {{
                    size: A5;
                    margin: 10mm 7mm;
                }}

                body {{
                    font-family: 'Arial', sans-serif;
                    color: #1E2A56;
                    line-height: 1.5;
                    margin: 0;
                    position: relative;
                }}

                /* Watermark on top */
                .watermark {{
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%) rotate(-30deg);
                    font-size: 80px;
                    color: rgba(200, 200, 200, 0.2);
                    z-index: 9999; /* on top */
                    pointer-events: none;
                    white-space: nowrap;
                }}

                .header {{
                    text-align: center;
                    margin-bottom: 25px;
                    position: relative;
                    z-index: 1;
                }}
                .logo {{
                    width: 150px;
                    margin-bottom: 10px;
                }}
                h5 {{
                    font-size: 16px;
                    margin: 5px 0;
                    font-weight: 800;
                }}

                .section-title {{
                    font-size: 16px;
                    margin-top: 25px;
                    margin-bottom: 8px;
                    border-bottom: 2px solid #1E2A56;
                    font-weight: 800;
                    position: relative;
                    z-index: 1;
                }}

                .info-box {{
                    padding: 15px;
                    border: 1px solid #d3d6e4;
                    border-radius: 8px;
                    background: #f4f6fb;
                    margin-bottom: 15px;
                    box-shadow: 0px 2px 4px rgba(0,0,0,0.05);
                    position: relative;
                    z-index: 1;
                }}

                .info-box p {{
                    margin: 5px 0;
                    font-size: 14px;
                }}

                .footer {{
                    margin-top: 30px;
                    text-align: right;
                    font-size: 12px;
                    color: #666;
                    position: relative;
                    z-index: 1;
                }}
            </style>
        </head>
        <body>

            <div class="watermark">DEPOSIT</div>

            <div class="header">
                <img src="data:image/png;base64,{logo_base64}" class="logo">
                <h5>Deposit Receipt</h5>
            </div>

            <div class="section-title">Client Information</div>
            <div class="info-box">
                <p><strong>Name:</strong> {row[1]}</p>
                <p><strong>Address:</strong> {row[2]}</p>
                <p><strong>Contact:</strong> 0{row[3]}</p>
                <p><strong>Email:</strong> {row[4]}</p>
            </div>

            <div class="section-title">Project Information</div>
            <div class="info-box">
                <p><strong>Project Name:</strong> {row[5]}</p>
                <p><strong>Location:</strong> {row[6]}</p>
                <p><strong>Project Scope:</strong> {row[7]}</p>
                <p><strong>Administrator:</strong> {row[8]}</p>
            </div>

            <div class="section-title">Deposit Details</div>
            <div class="info-box">
                <p><strong>Deposit Paid:</strong> USD {row[9] if row[9] else '—'}</p>
                <p><strong>Date Paid:</strong> {row[10].strftime('%d %B %Y') if row[10] else '—'}</p>
            </div>

        </body>
        </html>
        """



        pdf = HTML(string=html, base_url=request.host_url).write_pdf()

        response = make_response(pdf)
        response.headers["Content-Type"] = "application/pdf"
        response.headers["Content-Disposition"] = f"attachment; filename={row[1]} {row[5]} ConnectLink Properties Deposit_Receipt_Project_{project_id}.pdf"
        return response

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