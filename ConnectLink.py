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
from weasyprint import HTML
import re
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

            cursor.execute("""DROP TABLE connectlinkdatabasedeleted;""")         

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

                def send_whatsapp_list_message(recipient, text, list_title, sections):

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
                                "text": list_title
                            },
                            "body": {
                                "text": text
                            },
                            "action": {
                                "button": "Select Option",
                                "sections": sections
                            }
                        }
                    }
                    
                    response = requests.post(WHATSAPP_API_URL,headers=headers,json=payload)

                    print("✅ Sending message to:", recipient)
                    print("📩 Message body:", text)
                    print("📡 WhatsApp API Response Status:", response.status_code)  

                    print("List message response:", response.json())
                    return response

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



                                                        elif button_id == "projects":

                                                            buttons = [
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "portfolio",
                                                                        "title": "🏗️ Projects Portfolio"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "payments",
                                                                        "title": "Payments"
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
                                                                "Kindly select a projects option below.",
                                                                buttons,
                                                                footer_text="ConnectLink Properties • Admin Panel"

                                                            )

                                                            continue


                                                        elif button_id == "quotations":

                                                            buttons = [
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "by_date_logged",
                                                                        "title": "🏗️ By Date"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "all_quot",
                                                                        "title": "All"
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
                                                                "Kindly select a Quotation enquiries option below.",
                                                                buttons,
                                                                footer_text="ConnectLink Properties • Admin Panel"

                                                            )


                                                            continue

                                                        elif button_id == "enquiries":

                                                            buttons = [
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "quotations",
                                                                        "title": "🏗️ Quotation Equiries"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "general_enquiries",
                                                                        "title": "❓ General Enquiries"
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
                                                                "Kindly select an enquiries option below.",
                                                                buttons,
                                                                footer_text="ConnectLink Properties • Admin Panel"
                                                            )


                                                            continue

                                                        elif button_id == "main_menu":

                                                            buttons = [
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "projects",
                                                                        "title": "🏗️ Projects"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "enquiries",
                                                                        "title": "❓ Enquiries"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "user_management",
                                                                        "title": "👤 User Management"
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





                                                        elif "reminder" in button_id.lower():

                                                            app_id = button_id.split("_")[1]
                                                            print(app_id)

                                                            try:
                                                            
                                                                print ("eissssssssshhhhhhhhhhhhhhhhhhhhhhhhhhhh")


                                                                try:

                                                                    buttons = [
                                                                        {"type": "reply", "reply": {"id": f"Approve5appwa_{app_id}", "title": "Approve"}},
                                                                        {"type": "reply", "reply": {"id": f"Disapproveappwa_{app_id}", "title": "Disapprove"}},
                                                                    ]
                                                                    send_whatsapp_message(
                                                                        f"26", 
                                                                        f"Hey! 😊. A gentle reminder, you have a new `` Leave Application from `{admin_name}` for ` days` from `` to ``.\n\n" 
                                                                        f"If you approve this leave application, \n\n"  
                                                                        f"Select an option below to either approve or disapprove the application."         
                                                                        , 
                                                                        buttons
                                                                    )

                                                                except Exception as e:
                                                                    print(e)



                                                            except Exception as e:
                                                                print(e)
                                                                return jsonify({"message": "Error approving leave application.", "error": str(e)}), 500
                                                        


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

                                                            
                                                        if "hello" in text.lower():

                                                            buttons = [
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "projects",
                                                                        "title": "🏗️ Projects"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "enquiries",
                                                                        "title": "❓ Enquiries"
                                                                    }
                                                                },
                                                                {
                                                                    "type": "reply",
                                                                    "reply": {
                                                                        "id": "user_management",
                                                                        "title": "👤 User Management"
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




                                                    send_whatsapp_message(
                                                        sender_id, 
                                                        "Oops, you are."
                                                    )

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


                                                            elif button_id == "quotations":

                                                                buttons = [
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "by_date_logged",
                                                                            "title": "🏗️ By Date"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "all_quot",
                                                                            "title": "All"
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
                                                                    "Kindly select a Quotation enquiries option below.",
                                                                    buttons,
                                                                    footer_text="ConnectLink Properties • Admin Panel"

                                                                )


                                                                continue

                                                            elif button_id == "enquirylog":

                                                                buttons = [
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "quotations",
                                                                            "title": "🏗️ Quotation Equiries"
                                                                        }
                                                                    },
                                                                    {
                                                                        "type": "reply",
                                                                        "reply": {
                                                                            "id": "general_enquiries",
                                                                            "title": "❓ General Enquiries"
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
                                                                    "Kindly select an enquiries option below.",
                                                                    buttons,
                                                                    footer_text="ConnectLink Properties • Client Panel"
                                                                )


                                                                continue

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

                                                                
                                                            if "hello" in text.lower():

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
                    body {{ font-family: 'Roboto', sans-serif; background: #eef2fa; color: #1E2A56; }}
                    .agreement-container {{
                        width: 100%; /* or max-width: 800px */
                        margin: auto;
                        padding: 40px;
                        border: 3px solid #1E2A56;
                        border-radius: 14px;
                        background: #fff;
                        box-shadow: 0 8px 28px rgba(0,0,0,0.12);
                        box-sizing: border-box; /* include padding/border in width */
                        overflow-wrap: break-word; /* wrap long words */
                    }}
                    .logo {{ display: block; margin: 0 auto 20px auto; width: 230px; }}
                    h2.title {{ text-align: center; font-weight: 900; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 1px; }}
                    .subtitle-line {{ width: 120px; height: 3px; background: #1E2A56; margin: 10px auto 30px auto; border-radius: 10px; }}
                    h4.section-title {{ text-align: center; background-color: #1E2A56; color: white; padding: 5px 7px; border-radius: 6px; font-size: 1rem; margin-top: 40px; margin-bottom: 20px; font-weight: 800; letter-spacing: 0.5px; }}
                    p, li {{ font-size: 0.85rem; color: #1E2A56; }}
                    .field-row {{ display: flex; align-items: center; margin-bottom: 12px; }}
                    .field-label {{ font-weight: 700; width: 170px; font-size: 14px; flex-shrink: 0; }}
                    .field-value {{ flex: 1; border-bottom: 1.5px solid #1E2A56; padding-bottom: 2px; font-size: 14px; min-height: 20px; }}
                    .scope-box {{ border: 1.5px solid #1E2A56; border-radius: 10px; padding: 10px; min-height: 80px; background: #fafbff; margin-bottom: 10px; }}
                    ul {{ margin-top: 5px; margin-bottom: 20px; }}
                    li {{ margin-bottom: 6px; }}
                    .signature-block {{ margin-top: 60px; }}
                    .signature-line {{ display:flex; align-items:center; margin-top: 30px; margin-bottom: 35px; }}
                    .signature-label {{ font-weight: 700; margin-bottom: 5px; }}
                    .watermark {{ position: fixed; top: 40%; left: 15%; opacity: 0.1; font-size: 80px; color: #1E2A56; transform: rotate(-45deg); z-index: -1000; }}
                    @page {{ size: A4; margin: 50px 40px; }}
                    </style>
                </head>
                <body>
                <div class="watermark">CONFIDENTIAL</div>
                <div class="agreement-container">

                <img class="logo" src="data:image/png;base64,{logo_base64}" alt="ConnectLink Logo">

                <h2 class="title">Construction Agreement</h2>
                <div class="subtitle-line"></div>

                <p>This Construction Agreement ("Agreement") is made and entered into on <strong class="field-value">{project['agreement_date']}</strong> ("Effective Date") by and between:</p>

                <h4 class="section-title">CLIENT DETAILS</h4>
                <div class="field-row"><div class="field-label">Full Name:</div><div class="field-value">{project['client_name']}</div></div>
                <div class="field-row"><div class="field-label">Address:</div><div class="field-value">{project['client_address']}</div></div>
                <div class="field-row"><div class="field-label">Contact Number:</div><div class="field-value">0{project['client_whatsapp']}</div></div>
                <div class="field-row"><div class="field-label">Email:</div><div class="field-value">{project['client_email']}</div></div>

                <h4 class="section-title">NEXT OF KIN DETAILS</h4>
                <div class="field-row"><div class="field-label">Full Name:</div><div class="field-value">{project['next_of_kin_name']}</div></div>
                <div class="field-row"><div class="field-label">Address:</div><div class="field-value">{project['next_of_kin_address']}</div></div>
                <div class="field-row"><div class="field-label">Contact Number:</div><div class="field-value">0{project['next_of_kin_phone']}</div></div>
                <div class="field-row"><div class="field-label">Relationship:</div><div class="field-value">{project['relationship']}</div></div>

                <h4 class="section-title">CONTRACTOR DETAILS</h4>
                <div class="field-row"><div class="field-label">Name:</div><div class="field-value">{project['companyname']}</div></div>
                <div class="field-row"><div class="field-label">Address:</div><div class="field-value">{project['companyaddress']}</div></div>
                <div class="field-row"><div class="field-label">Contact Number:</div><div class="field-value">0{project['companycontact1']} ; 0{project['companycontact2']}</div></div>
                <div class="field-row"><div class="field-label">Email:</div><div class="field-value">{project['companyemail']}</div></div>
                <div class="field-row"><div class="field-label">Administrator Name:</div><div class="field-value">{project['project_administrator']}</div></div>

                <h4 class="section-title">PROJECT DETAILS</h4>
                <div class="field-row"><div class="field-label">Project Name:</div><div class="field-value">{project['project_name']}</div></div>
                <div class="field-row"><div class="field-label">Project Location:</div><div class="field-value">{project['project_location']}</div></div>
                <p><strong>Project Scope:</strong></p>
                <div class="scope-box">{project['project_description']}</div>

                <h4 class="section-title">PAYMENT TERMS</h4>
                <div class="field-row"><div class="field-label">Total Contract Price:</div><div class="field-value">USD {project['total_contract_price']}</div></div>
                <div class="field-row"><div class="field-label">Deposit Required:</div><div class="field-value">USD {project['depositorbullet']}</div></div>

                <p><strong>Payment Schedule:</strong></p>
                <table style="width:70%; border-collapse: collapse; margin-bottom: 20px; border: 1px solid #1E2A56;">
                <thead>
                <tr>
                <th style="text-align:left; border: 1px solid #1E2A56; padding: 8px; background-color: #f0f2f8;">Installment Due Date</th>
                <th style="border: 1px solid #1E2A56; padding: 8px; background-color: #f0f2f8;">Installment (USD)</th>
                </tr>
                </thead>
                <tbody>
                <tr><td style="border: 1px solid #1E2A56; padding: 8px;font-size:13px;">{project['installment1duedate']}</td><td style="border: 1px solid #1E2A56; padding: 8px;">{project['installment1amount']}</td></tr>
                <tr><td style="border: 1px solid #1E2A56; padding: 8px;font-size:13px;">{project['installment2duedate']}</td><td style="border: 1px solid #1E2A56; padding: 8px;">{project['installment2amount']}</td></tr>
                <tr><td style="border: 1px solid #1E2A56; padding: 8px;font-size:13px;">{project['installment3duedate']}</td><td style="border: 1px solid #1E2A56; padding: 8px;">{project['installment3amount']}</td></tr>
                <tr><td style="border: 1px solid #1E2A56; padding: 8px;font-size:13px;">{project['installment4duedate']}</td><td style="border: 1px solid #1E2A56; padding: 8px;">{project['installment4amount']}</td></tr>
                <tr><td style="border: 1px solid #1E2A56; padding: 8px;font-size:13px;">{project['installment5duedate']}</td><td style="border: 1px solid #1E2A56; padding: 8px;">{project['installment5amount']}</td></tr>
                <tr><td style="border: 1px solid #1E2A56; padding: 8px;font-size:13px;">{project['installment6duedate']}</td><td style="border: 1px solid #1E2A56; padding: 8px;">{project['installment6amount']}</td></tr>               
                </tbody>
                </table>

                <h4 class="section-title">LATE PAYMENT AND INTEREST</h4>
                <ul style="list-style-type:circle;">
                    <li> If the Client fails to make any payment on or before the due date, the Client shall be liable to pay interest at a rate of {project['latepaymentinterest']}% per annum.</li>
                    <li> Interest is calculated daily and compounded monthly.</li>
                </ul>

                <h4 class="section-title">TERMS AND CONDITIONS</h4>
                <ol>
                    <li>The Contractor shall commence work within {project['days_difference']} days of receiving the first payment.</li>
                    <li>The Client shall make payments as per the payment schedule.</li>
                    <li>The Contractor shall complete the project within {project['project_duration']} days.</li>
                    <li>The Client is responsible for obtaining all required permits.</li>
                    <li>The Contractor is responsible for all materials and labor.</li>
                </ol>

                <h4 class="section-title">TERMINATION</h4>
                <p>This Agreement may be terminated if either party fails to comply with the terms herein.</p>

                <h4 class="section-title">OWNERSHIP</h4>
                <ul style="list-style-type:circle;">
                    <li>Installed items remain property of ConnectLink Properties and ownership is only transferred upon full payment from the client. </li>
                    <li>ConnectLink Properties reserves the right to remove installed items should the client fail to pay the balance within the timelines stated in this agreement.</li>
                </ul>

                <h4 class="section-title">DESIGN CONFIRMATION</h4>
                <ul style="list-style-type:circle;">
                    <li>Signing of the contract and payment of the deposit is taken as acknowledgement, confirmation and go ahead for the construction of the proposed design sent to the client prior with the quotation.</li>
                    <li>Any other alterations may be communicated and adjusted <b>before</b> the signing of the contract.</li>
                    <li>All additions to the said design will be taken as variations and will incur an additional cost that may be added to the first quotation or charged on a seperate quotation altogether.</li>
                </ul>

                <h4 class="section-title">POWER PROVISION</h4>
                <p>In the case of a power outage and there is need for electricity for the job to be carried out, the client is to provide a generator and fuel for the duration of the construction period
                as needed at the client's own expense.</p>

                <h4 class="section-title">DISPUTE RESOLUTION</h4>
                <p>Any disputes shall be resolved through arbitration under the Arbitration Act of Zimbabwe.</p>

                <h4 class="section-title">GOVERNING LAW</h4>
                <p>This Agreement is governed by the laws of Zimbabwe.</p>

                <h4 class="section-title">SIGNATURES</h4>

                <div class="signature-block">
                    <div class="signature-line">
                        <span class="signature-label">Client Signature:</span>
                        <div class="field-value" style="width:350px;"></div>
                    </div>

                    <div class="signature-line">
                        <span class="signature-label">Contractor Signature:</span>
                        <div class="field-value" style="width:350px;"></div>
                    </div>

                    <div class="signature-line">
                        <span class="signature-label">Date:</span>
                        <div class="field-value" style="width:220px;">{ project['agreement_date'] }</div>
                    </div>
                </div>

                </div>
                </body>
                </html>
                """

            # Generate PDF
            pdf = HTML(string=html, base_url=request.host_url).write_pdf()

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
        client_name = data.get('client_name')
        project_name = data.get('project_name')
        admin_passcode = data.get('admin_passcode')
        
        # Validate admin passcode
        if admin_passcode != "conlink01admin01":
            return jsonify({'status': 'error', 'message': 'Invalid admin passcode'})
        
        # Get user info from session
        user_name = session.get('user_name', 'Unknown')
        userid = session.get('userid', 0)
        
        with get_db() as (cursor, connection):
            try:
                # 1. First, fetch the project data from connectlinkdatabase
                cursor.execute("SELECT * FROM connectlinkdatabase WHERE id = %s", (project_id,))
                project_data = cursor.fetchone()
                
                if not project_data:
                    return jsonify({'status': 'error', 'message': 'Project not found'})

                print(project_data)
                
                # 2. Insert the project data into connectlinkdatabasedeleted
                cursor.execute("""
                    INSERT INTO connectlinkdatabasedeletedprojects (
                        id, clientname, clientidnumber, clientaddress, clientwanumber, clientemail,
                        clientnextofkinname, clientnextofkinaddress, clientnextofkinphone, nextofkinrelationship,
                        projectname, projectlocation, projectdescription, projectadministratorname,
                        projectstartdate, projectduration, contractagreementdate, totalcontractamount,
                        paymentmethod, monthstopay, datecaptured, capturer, capturerid,
                        deletedby, deleterid, depositorbullet, datedepositorbullet,
                        monthlyinstallment, installment1amount, installment1duedate, installment1date,
                        installment2amount, installment2duedate, installment2date,
                        installment3amount, installment3duedate, installment3date,
                        installment4amount, installment4duedate, installment4date,
                        installment5amount, installment5duedate, installment5date,
                        installment6amount, installment6duedate, installment6date,
                        projectcompletionstatus, latepaymentinterest
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
                    )
                """, (
                    project_data[0],  # clientname
                    project_data[1],  # clientname
                    project_data[2],  # clientidnumber
                    project_data[3],  # clientaddress
                    project_data[4],  # clientwanumber
                    project_data[5],  # clientemail
                    project_data[6],  # clientnextofkinname
                    project_data[7],  # clientnextofkinaddress
                    project_data[8],  # clientnextofkinphone
                    project_data[9],  # nextofkinrelationship
                    project_data[10],  # projectname
                    project_data[11],  # projectlocation
                    project_data[12],  # projectdescription
                    project_data[13],  # projectadministratorname
                    project_data[14],  # projectstartdate
                    project_data[15],  # projectduration
                    project_data[16],  # contractagreementdate
                    project_data[17],  # totalcontractamount
                    project_data[18],  # paymentmethod
                    project_data[19],  # monthstopay
                    project_data[20],  # datecaptured
                    project_data[21],  # capturer
                    project_data[22],  # capturerid
                    user_name,  # deletedby
                    userid,  # deleterid
                    project_data[23] if len(project_data) > 23 else None,  # depositorbullet
                    project_data[24] if len(project_data) > 24 else None,  # datedepositorbullet
                    project_data[25] if len(project_data) > 25 else None,  # monthlyinstallment
                    project_data[26] if len(project_data) > 26 else None,  # installment1amount
                    project_data[27] if len(project_data) > 27 else None,  # installment1duedate
                    project_data[28] if len(project_data) > 28 else None,  # installment1date
                    project_data[29] if len(project_data) > 29 else None,  # installment2amount
                    project_data[30] if len(project_data) > 30 else None,  # installment2duedate
                    project_data[31] if len(project_data) > 31 else None,  # installment2date
                    project_data[32] if len(project_data) > 32 else None,  # installment3amount
                    project_data[33] if len(project_data) > 33 else None,  # installment3duedate
                    project_data[34] if len(project_data) > 34 else None,  # installment3date
                    project_data[35] if len(project_data) > 35 else None,  # installment4amount
                    project_data[36] if len(project_data) > 36 else None,  # installment4duedate
                    project_data[37] if len(project_data) > 37 else None,  # installment4date
                    project_data[38] if len(project_data) > 38 else None,  # installment5amount
                    project_data[39] if len(project_data) > 39 else None,  # installment5duedate
                    project_data[40] if len(project_data) > 40 else None,  # installment5date
                    project_data[41] if len(project_data) > 41 else None,  # installment6amount
                    project_data[42] if len(project_data) > 42 else None,  # installment6duedate
                    project_data[43] if len(project_data) > 43 else None,  # installment6date
                    project_data[44] if len(project_data) > 44 else None,  # projectcompletionstatus
                    project_data[45] if len(project_data) > 45 else None,  # latepaymentinterest
                ))
                
                # 3. Now delete from the original table
                cursor.execute("DELETE FROM connectlinkdatabase WHERE id = %s", (project_id,))
                
                connection.commit()
                
                # Log the deletion
                print(f"Project deleted and archived: {project_id} - {project_name} for client {client_name}")
                
                return jsonify({
                    'status': 'success',
                    'message': f'Project "{project_name}" for client "{client_name}" has been deleted and archived.'
                })
                
            except Exception as e:
                connection.rollback()
                print(f"Error deleting project: {str(e)}")
                return jsonify({'status': 'error', 'message': str(e)})
                
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
            client_number = int(float(request.form.get('client_wa_number')))
            nextofkin_number = int(float(request.form.get('client_next_of_kin_number')))
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
    


def run1(userid):

    with get_db() as (cursor, connection):

        print(userid)
        today_date = datetime.now().strftime('%d %B %Y')
        applied_date = datetime.now().strftime('%Y-%m-%d')

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


        datamain = pd.DataFrame(maindata, columns= ['id', 'clientname', 'clientidnumber', 'clientaddress', 'clientwanumber', 'clientemail', 'clientnextofkinname', 'clientnextofkinaddress', 'clientnextofkinphone', 'nextofkinrelationship', 'projectname', 'projectlocation', 'projectdescription', 'projectadministratorname', 'projectstartdate', 'projectduration', 'contractagreementdate', 'totalcontractamount', 'paymentmethod', 'monthstopay', 'datecaptured', 'capturer', 'capturerid', 'depositorbullet', 'datedepositorbullet', 'monthlyinstallment', 'installment1amount', 'installment1duedate', 'installment1date', 'installment2amount', 'installment2duedate', 'installment2date', 'installment3amount', 'installment3duedate', 'installment3date', 'installment4amount', 'installment4duedate', 'installment4date', 'installment5amount', 'installment5duedate', 'installment5date', 'installment6amount', 'installment6duedate', 'installment6date','projectcompletionstatus','latepaymentinterest'])

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
        datamain['projectstartdate'] = pd.to_datetime(datamain['projectstartdate']).dt.strftime('%d %B %Y')

        datamain = datamain[['id', 'clientname', 'clientidnumber', 'clientaddress', 'clientwanumber', 'clientemail', 'clientnextofkinname', 'clientnextofkinaddress', 'clientnextofkinphone', 'nextofkinrelationship', 'projectname', 'projectlocation', 'projectdescription', 'projectadministratorname', 'projectstartdate', 'projectduration', 'contractagreementdate', 'totalcontractamount', 'paymentmethod', 'monthstopay', 'datecaptured', 'capturer', 'capturerid', 'depositorbullet', 'datedepositorbullet', 'monthlyinstallment', 'installment1amount', 'installment1duedate', 'installment1date', 'installment2amount', 'installment2duedate', 'installment2date', 'installment3amount', 'installment3duedate', 'installment3date', 'installment4amount', 'installment4duedate', 'installment4date', 'installment5amount', 'installment5duedate', 'installment5date', 'installment6amount', 'installment6duedate', 'installment6date','projectcompletionstatus', 'latepaymentinterest', 'Action']]
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
        
        return {
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
                            clientname, clientidnumber, clientaddress, clientwanumber, clientemail,
                            clientnextofkinname, clientnextofkinaddress, clientnextofkinphone, nextofkinrelationship,
                            projectname, projectlocation, projectdescription, projectadministratorname,
                            projectstartdate, projectduration, contractagreementdate, totalcontractamount,
                            paymentmethod, monthstopay, depositorbullet, datedepositorbullet, monthlyinstallment, 
                            installment1duedate, datecaptured, capturer, capturerid, projectcompletionstatus, latepaymentinterest, installment1amount, installment2amount, installment3amount, installment4amount, installment5amount, installment6amount, installment2duedate, installment3duedate, installment4duedate, installment5duedate, installment6duedate
                        ) VALUES (
                            %s, %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
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