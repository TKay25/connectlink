import uuid
import os
import html
os.environ.setdefault("MPLCONFIGDIR", "/tmp/.matplotlib")
import bleach
from db_helper import get_db, execute_query
import numpy as np
from mysql.connector import Error
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_file,flash, make_response, after_this_request, Response, send_from_directory
from datetime import datetime, timedelta, date
import calendar
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import seaborn as sns
import psycopg2
import psycopg2.extras
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
import logging
from decimal import Decimal
import gc
import google.generativeai as genai
from flask_cors import CORS
import secrets
import hashlib
from functools import wraps
from psycopg2.extras import RealDictCursor
import pytz
from ai_classifier import classify_product, get_category_suggestions




#import threading
#from apscheduler.schedulers.background import BackgroundScheduler


app = Flask(__name__)
app.secret_key = 'your_secret_key'  
app.secret_key = '011235'
app.permanent_session_lifetime = timedelta(minutes=360)
user_sessions = {}

database = 'connectlinkdata'

GEMINI_API_KEY = "AIzaSyBJ8hqTuCjDhpabMtgJ-MXO9aQ3_f-if2g"  # Replace with your actual key
genai.configure(api_key=GEMINI_API_KEY)

def initialize_database_tables():
    """Initialize all required database tables on startup"""
    try:
        with get_db() as (cursor, connection):

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kitchen_items (
                    id SERIAL PRIMARY KEY,
                    item_name VARCHAR(255) NOT NULL UNIQUE,
                    default_price DECIMAL(15, 2) DEFAULT 0,
                    default_days INT DEFAULT 1,
                    is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotation_kitchen_items (
                    id SERIAL PRIMARY KEY,
                    quotation_id INT NOT NULL REFERENCES quotations(id) ON DELETE CASCADE,
                    item_name VARCHAR(255) NOT NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    amount DECIMAL(15, 2) NOT NULL,
                days INT NOT NULL DEFAULT 1,
                item_order INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );""")

            # Add missing columns to quotation_kitchen_items table
            try:
                cursor.execute("""
                    ALTER TABLE quotation_kitchen_items 
                    ADD COLUMN IF NOT EXISTS unit_price DECIMAL(15, 2) DEFAULT 0
                """)
            except Exception as e:
                print(f"Note: Could not add unit_price column: {e}")

            try:
                cursor.execute("""
                    ALTER TABLE quotation_kitchen_items 
                    ADD COLUMN IF NOT EXISTS total_price DECIMAL(15, 2) DEFAULT 0
                """)
            except Exception as e:
                print(f"Note: Could not add total_price column: {e}")

            cursor.execute("""
            INSERT INTO kitchen_items (item_name, default_price, default_days) VALUES
            ('Matt Kitchen including Local Granite', 4500, 5),
            ('Matt Kitchen including Quartz', 5500, 5),
            ('Gloss Kitchen including Quartz', 6000, 5),
            ('High Gloss Kitchen including Quartz', 6500, 5),
            ('Main Bedroom Cabinets', 2500, 3),
            ('Other Bedroom Cabinets', 1800, 2),
            ('Quartz Countertop', 800, 2),
            ('Granite Countertop', 600, 2),
            ('Solid Wood Cabinet', 350, 1),
            ('MDF Cabinet', 200, 1),
            ('Glass Cabinet Doors', 150, 1),
            ('Soft-Close Hinges', 80, 0),
            ('Drawer Runners', 100, 0),
            ('Kitchen Sink', 250, 1),
            ('Mixer Tap', 120, 1),
            ('Backsplash Tiling', 400, 2),
            ('Under Cabinet Lighting', 180, 1),
            ('Island Countertop', 800, 2),
            ('Wine Rack', 120, 1),
            ('Corner Cabinet Carousel', 300, 1),
            ('Pull-out Pantry', 250, 1)
            ON CONFLICT (item_name) DO NOTHING;""")

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
            
            try:
                columns = get_table_columns("connectlinkdatabase")
                print(f"✓ Connected to connectlinkdatabase with columns: {columns}")
            except Exception as e:
                print(f"⚠️  Warning: Could not fetch connectlinkdatabase columns: {e}")

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
                SELECT 
                    qi.quotation_id,
                    qi.item_name,
                    qi.quantity,
                    qi.unit_rate,
                    qi.total_price
                FROM quotation_items qi
                ORDER BY qi.quotation_id DESC
                LIMIT 10
            """)
            debug_items = cursor.fetchall()
            print("\n=== DEBUG: Last 10 quotation items from database ===")
            for item in debug_items:
                print(f"Quotation {item[0]}: {item[1]} - Qty:{item[2]}, Rate:{item[3]}, Total:{item[4]}")
            print("==================================================\n")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appenqtemp (
                    id SERIAL PRIMARY KEY,
                    wanumber INT,
                    enqtype VARCHAR (100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whatsapp_reminders_logs (
                    id SERIAL PRIMARY KEY,
                    client_name VARCHAR (100),
                    whatsapp_number INT,
                    project_name VARCHAR (100),
                    installmentnumber INT,
                    amountdue INT,
                    status VARCHAR (100),
                    daysinfo INT,
                    sentat TIMESTAMP,
                    api_response VARCHAR (1000)
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
                CREATE TABLE IF NOT EXISTS enquiry_attachment_button_map (
                    id SERIAL PRIMARY KEY,
                    template_message_id VARCHAR(255),
                    enquiry_id INT,
                    recipient_whatsapp VARCHAR(30),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkusers (
                    id SERIAL PRIMARY KEY,
                    datecreated date,
                    name VARCHAR (200),
                    password varchar (100),
                    email VARCHAR (100),
                    whatsapp INT
                );
            """)
            # Fix whatsapp column type (was INT, needs to be VARCHAR for phone numbers with extensions)
            try:
                cursor.execute("""
                    ALTER TABLE connectlinkusers 
                    ALTER COLUMN whatsapp TYPE VARCHAR(50)
                """)
                connection.commit()
            except Exception:
                connection.rollback()  # Column might already be VARCHAR

            # Fix all other phone/WhatsApp columns from INT to VARCHAR
            phone_column_fixes = [
                ("connectlinkdetails", "contact1"),
                ("connectlinkdetails", "contact2"),
                ("appenqtemp", "wanumber"),
                ("whatsapp_reminders_logs", "whatsapp_number"),
                ("connectlinkenquiries", "clientwhatsapp"),
                ("connectlinkadmin", "contact"),
                ("connectlinkdatabase", "clientwanumber"),
                ("connectlinkdatabase", "clientnextofkinphone"),
                ("connectlinkdatabasedeletedprojects", "clientwanumber"),
                ("connectlinkdatabasedeletedprojects", "clientnextofkinphone"),
                ("connectlinknotes", "clientwanumber"),
                ("connectlinknotes", "clientnextofkinnumber"),
            ]
            for table, col in phone_column_fixes:
                try:
                    cursor.execute(f"""
                        ALTER TABLE {table} 
                        ALTER COLUMN {col} TYPE VARCHAR(50)
                    """)
                    connection.commit()
                except Exception:
                    connection.rollback()  # Column might not exist or already VARCHAR

            # ===== UNIFIED ADMIN USERS TABLE =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS admin_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) NOT NULL UNIQUE,
                    password VARCHAR(100) NOT NULL,
                    full_name VARCHAR(200) NOT NULL,
                    email VARCHAR(200),
                    whatsapp VARCHAR(50),
                    source_system VARCHAR(20) DEFAULT 'projects',
                    source_id INT,
                    role VARCHAR(50) DEFAULT 'operator',
                    is_active BOOLEAN DEFAULT TRUE,
                    must_reset_password BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            connection.commit()

            # Add must_reset_password column if missing (existing databases)
            try:
                cursor.execute("""
                    ALTER TABLE admin_users
                    ADD COLUMN IF NOT EXISTS must_reset_password BOOLEAN DEFAULT FALSE
                """)
                connection.commit()
            except Exception as e:
                print(f"Note: Could not add must_reset_password column: {e}")

            # Add subsidiary column to admin_users if not exists
            try:
                cursor.execute("""
                    ALTER TABLE admin_users
                    ADD COLUMN IF NOT EXISTS subsidiary VARCHAR(50) DEFAULT ''
                """)
                connection.commit()
            except Exception as e:
                print(f"Note: Could not add subsidiary column: {e}")

            # Migrate existing users from connectlinkusers to admin_users (if not already there)
            try:
                cursor.execute("""
                    INSERT INTO admin_users (username, password, full_name, email, whatsapp, source_system, source_id, role, created_at)
                    SELECT email, password, name, email, CAST(whatsapp AS VARCHAR), 'projects', id, 'admin', COALESCE(datecreated::timestamp, NOW())
                    FROM connectlinkusers
                    WHERE email IS NOT NULL AND email != ''
                    ON CONFLICT (username) DO NOTHING
                """)
                migrated_cl = cursor.rowcount
            except Exception as e:
                migrated_cl = 0
                print(f"Note: connectlinkusers migration: {e}")

            try:
                cursor.execute("""
                    INSERT INTO admin_users (username, password, full_name, email, source_system, source_id, role, created_at)
                    SELECT username, password, full_name, username, 'hardware', id, role, COALESCE(created_at, NOW())
                    FROM hardware_users
                    WHERE username IS NOT NULL AND username != ''
                    ON CONFLICT (username) DO NOTHING
                """)
                migrated_hw = cursor.rowcount
            except Exception as e:
                migrated_hw = 0
                print(f"Note: hardware_users migration: {e}")

            if migrated_cl + migrated_hw > 0:
                print(f"✅ Migrated {migrated_cl} projects + {migrated_hw} hardware users to admin_users")
            connection.commit()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS whatsapp_messages (
                    id SERIAL PRIMARY KEY,
                    sender_phone VARCHAR(20),
                    sender_name VARCHAR(200),
                    message_text TEXT,
                    message_type VARCHAR(50),
                    direction VARCHAR(10) DEFAULT 'incoming',
                    status VARCHAR(50) DEFAULT 'received',
                    media_id VARCHAR(255),
                    file_name VARCHAR(255),
                    replied_to_id INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # Add columns if they don't exist (for existing tables)
            try:
                cursor.execute("ALTER TABLE whatsapp_messages ADD COLUMN IF NOT EXISTS media_id VARCHAR(255)")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE whatsapp_messages ADD COLUMN IF NOT EXISTS replied_to_id INTEGER")
            except Exception:
                pass
            
            # Create bulk_send_logs table for tracking
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS bulk_send_logs (
                        id SERIAL PRIMARY KEY,
                        bulk_id VARCHAR(50) NOT NULL,
                        recipient VARCHAR(20) NOT NULL,
                        success BOOLEAN DEFAULT FALSE,
                        status VARCHAR(50) DEFAULT 'failed',
                        error_detail TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            except Exception:
                pass
            
            # Create quick_replies table
            try:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS quick_replies (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR(100) NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE whatsapp_messages ADD COLUMN IF NOT EXISTS file_name VARCHAR(255)")
            except Exception:
                pass
            
            # Add index for faster conversation lookup
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_whatsapp_messages_sender
                ON whatsapp_messages(sender_phone, created_at DESC);
            """)
            
            # Create chatbot_interactions table for tracking menu/button clicks and keywords
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chatbot_interactions (
                    id SERIAL PRIMARY KEY,
                    sender_phone VARCHAR(20),
                    sender_name VARCHAR(200),
                    interaction_type VARCHAR(50) NOT NULL,
                    interaction_key VARCHAR(200),
                    interaction_label VARCHAR(500),
                    category VARCHAR(100),
                    matched_project_id INT,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chatbot_interactions_sender
                ON chatbot_interactions(sender_phone, created_at DESC);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chatbot_interactions_type
                ON chatbot_interactions(interaction_type, created_at DESC);
            """)
            
            # Create chat_human_mode table for toggling chatbot auto-replies per contact
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS chat_human_mode (
                    id SERIAL PRIMARY KEY,
                    sender_phone VARCHAR(20) NOT NULL UNIQUE,
                    human_mode BOOLEAN NOT NULL DEFAULT FALSE,
                    toggled_by VARCHAR(100),
                    toggled_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_chat_human_mode_phone
                ON chat_human_mode(sender_phone);
            """)
            
            current_date = datetime.now().strftime('%Y-%m-%d')
            # Create connectlinkadmin table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS connectlinkadmin (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR (200),
                    contact INT
                );
            """)

            # Create quotation rates table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotation_rates (
                    id SERIAL PRIMARY KEY,
                    quotation_item VARCHAR(255) NOT NULL,
                    days_per_sq_meter DECIMAL(10, 8) NOT NULL DEFAULT 0,
                    inhouse_unit_rate NUMERIC(20, 13) NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Ensure existing databases can store high-precision inhouse rates
            # Wrapped in DO block so it's a no-op if the column is already NUMERIC(20,13)
            cursor.execute("""
                DO $$
                BEGIN
                    ALTER TABLE quotation_rates
                        ALTER COLUMN inhouse_unit_rate TYPE NUMERIC(20, 13)
                        USING inhouse_unit_rate::NUMERIC(20, 13);
                EXCEPTION WHEN others THEN
                    NULL;
                END $$;
            """)
            
            # Create product categories table for dynamically created categories
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_categories (
                    id SERIAL PRIMARY KEY,
                    category_name VARCHAR(100) NOT NULL,
                    subcategory_name VARCHAR(100) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category_name, subcategory_name)
                );
            """)

            # Check if quotation_rates table is empty and populate with initial data
            cursor.execute("SELECT COUNT(*) FROM quotation_rates")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Insert initial quotation rates data
                quotation_data = [
                    ('Setting out', 0, 1),
                    ('Excavation', 0.05, 2.9),
                    ('Footing', 0.0375, 12),
                    ('Box', 0.075, 20),
                    ('Slab', 0.025, 15),
                    ('Window sill level', 0.058333333, 20),
                    ('Backfilling and compaction', 0.025, 7),
                    ('Window head', 0.025974026, 20),
                    ('Ring Beam', 0.032467532, 23),
                    ('Wall plate', 0.038961039, 10),
                    ('Roofing', 0.083333333, 35),
                    ('Aluminium', 0.041666667, 16),
                    ('Shattering', 0.038961039, 10),
                    ('Steel Fixing', 0.097402597, 35),
                    ('Deck Pouring', 0.032467532, 20),
                    ('1st Fix Electricals', 0.02597403, 23),
                    ('1st Fix Plumbing', 0.025974026, 9.25),
                    ('External Plastering', 0.045454545, 5.5),
                    ('Internal Plastering', 0.051948052, 5.5),
                    ('Ceiling', 0.064935065, 13),
                    ('Skimming', 0.045454545, 3.5),
                    ('Flooring', 0.032467532, 3.5),
                    ('Tiling', 0.051948052, 12),
                    ('Wall Tiling', 0.023529412, 0),
                    ('Painting', 0.051948052, 15),
                    ('Final fix Plumbing', 0.025974026, 9.25),
                    ('Final fix Electricals', 0.025974026, 5),
                    ('Cleaning', 0, 0)
                ]
                
                cursor.executemany("""
                    INSERT INTO quotation_rates (quotation_item, days_per_sq_meter, inhouse_unit_rate)
                    VALUES (%s, %s, %s)
                """, quotation_data)
                
                connection.commit()
                print(f"✓ Initialized quotation_rates table with {len(quotation_data)} items")

            # Create project_schedules table for Gantt charts
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS project_schedules (
                    id SERIAL PRIMARY KEY,
                    project_name VARCHAR(255) NOT NULL,
                    schedule_data JSONB NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Create quotations table to store quotation headers
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotations (
                    id SERIAL PRIMARY KEY,
                    client_name VARCHAR(255) NOT NULL,
                    client_whatsapp VARCHAR(20),
                    quotation_date DATE NOT NULL,
                    category VARCHAR(100) NOT NULL,
                    project_size DECIMAL(10, 2),
                    total_cost DECIMAL(15, 2) NOT NULL,
                    markup_percentage DECIMAL(5, 2),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Add client_whatsapp column if it doesn't exist (for existing tables)
            cursor.execute("""
                ALTER TABLE quotations 
                ADD COLUMN IF NOT EXISTS client_whatsapp VARCHAR(20)
            """)
            cursor.execute("""
                ALTER TABLE quotations 
                ADD COLUMN IF NOT EXISTS notes TEXT DEFAULT ''
            """)

            # Create quotation_items table to store construction items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotation_items (
                    id SERIAL PRIMARY KEY,
                    quotation_id INT NOT NULL,
                    item_name VARCHAR(255) NOT NULL,
                    quantity DECIMAL(10, 2),
                    unit_rate DECIMAL(12, 2),
                    total_price DECIMAL(15, 2),
                    item_order INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
                );
            """)

            # Create quotation_schedules table to store project schedule items
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotation_schedules (
                    id SERIAL PRIMARY KEY,
                    quotation_id INT NOT NULL,
                    work_scope VARCHAR(255) NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    days INT,
                    task_order INT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
                );
            """)

            # Create secure quotation share links for WhatsApp template URL buttons
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotation_share_links (
                    id SERIAL PRIMARY KEY,
                    quotation_id INT NOT NULL,
                    share_token VARCHAR(120) NOT NULL UNIQUE,
                    expires_at TIMESTAMP NOT NULL,
                    download_clicked_at TIMESTAMP,
                    download_pdf_sent_at TIMESTAMP,
                    download_pdf_sent_success BOOLEAN DEFAULT FALSE,
                    download_click_whatsapp VARCHAR(20),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
                );
            """)

            # Track outbound quotation WhatsApp messages so async status failures can trigger template fallback
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotation_whatsapp_outbox (
                    id SERIAL PRIMARY KEY,
                    outbound_message_id VARCHAR(255) NOT NULL UNIQUE,
                    quotation_id INT NOT NULL,
                    whatsapp_number VARCHAR(20),
                    client_name VARCHAR(255),
                    template_fallback_sent BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
                );
            """)

            # Log WhatsApp quotation send outcomes for portal reporting
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS quotation_whatsapp_send_logs (
                    id SERIAL PRIMARY KEY,
                    quotation_id INT NOT NULL,
                    whatsapp_number VARCHAR(20),
                    client_name VARCHAR(255),
                    snapshot_category VARCHAR(255),
                    snapshot_project_size DECIMAL(15,2),
                    snapshot_total_cost DECIMAL(15,2),
                    snapshot_markup DECIMAL(5,2),
                    snapshot_quotation_date DATE,
                    send_type VARCHAR(40) NOT NULL,
                    send_status VARCHAR(20) NOT NULL DEFAULT 'success',
                    error_details TEXT,
                    whatsapp_message_id VARCHAR(255),
                    source_channel VARCHAR(40) DEFAULT 'portal',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (quotation_id) REFERENCES quotations(id) ON DELETE CASCADE
                );
            """)

            # Ensure older databases also have status/error columns on send logs
            cursor.execute("""
                ALTER TABLE quotation_whatsapp_send_logs
                ADD COLUMN IF NOT EXISTS send_status VARCHAR(20) NOT NULL DEFAULT 'success'
            """)
            cursor.execute("""
                ALTER TABLE quotation_whatsapp_send_logs
                ADD COLUMN IF NOT EXISTS error_details TEXT
            """)
            cursor.execute("""
                ALTER TABLE quotation_whatsapp_send_logs
                ADD COLUMN IF NOT EXISTS snapshot_category VARCHAR(255)
            """)
            cursor.execute("""
                ALTER TABLE quotation_whatsapp_send_logs
                ADD COLUMN IF NOT EXISTS snapshot_project_size DECIMAL(15,2)
            """)
            cursor.execute("""
                ALTER TABLE quotation_whatsapp_send_logs
                ADD COLUMN IF NOT EXISTS snapshot_total_cost DECIMAL(15,2)
            """)
            cursor.execute("""
                ALTER TABLE quotation_whatsapp_send_logs
                ADD COLUMN IF NOT EXISTS snapshot_markup DECIMAL(5,2)
            """)
            cursor.execute("""
                ALTER TABLE quotation_whatsapp_send_logs
                ADD COLUMN IF NOT EXISTS snapshot_quotation_date DATE
            """)

            # Ensure older databases can track quotation download clicks/success
            cursor.execute("""
                ALTER TABLE quotation_share_links
                ADD COLUMN IF NOT EXISTS download_clicked_at TIMESTAMP
            """)
            cursor.execute("""
                ALTER TABLE quotation_share_links
                ADD COLUMN IF NOT EXISTS download_pdf_sent_at TIMESTAMP
            """)
            cursor.execute("""
                ALTER TABLE quotation_share_links
                ADD COLUMN IF NOT EXISTS download_pdf_sent_success BOOLEAN DEFAULT FALSE
            """)
            cursor.execute("""
                ALTER TABLE quotation_share_links
                ADD COLUMN IF NOT EXISTS download_click_whatsapp VARCHAR(20)
            """)

            cursor.execute("""
                ALTER TABLE quotation_share_links
                ADD COLUMN IF NOT EXISTS pdf_data BYTEA
            """)
            cursor.execute("""
                ALTER TABLE quotation_share_links
                ADD COLUMN IF NOT EXISTS pdf_filename VARCHAR(255) DEFAULT ''
            """)

            #cursor.execute("""
            #    UPDATE connectlinkdatabase 
            #    SET projectname = 'Bulawayo Full House Construction'
            #    WHERE id = 57;
            #""")

            '''cursor.execute("""
                ALTER TABLE connectlinkdatabase DROP COLUMN depositrequired;
            """)'''

            try:
                cursor.execute("""DELETE FROM connectlinkenquiries WHERE id BETWEEN 1 AND 8;""")
                cursor.execute("""DELETE FROM connectlinkenquiries WHERE id = 25;""")
                connection.commit()
            except Exception as e:
                connection.rollback()
                print(f"Note: Could not delete records from connectlinkenquiries: {e}")

            try:
                cursor.execute("""
                    ALTER TABLE appenqtemp 
                    ALTER COLUMN wanumber TYPE BIGINT;
                """)
                connection.commit()
            except Exception as e:
                connection.rollback()
                print(f"Note: Could not alter appenqtemp.wanumber type: {e}")

            try:
                cursor.execute("""
                    ALTER TABLE appenqtemp
                    ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP;
                """)
                connection.commit()
            except Exception as e:
                connection.rollback()
                print(f"Note: Could not add appenqtemp.created_at: {e}")

            # Update clientwhatsapp for record with id 6
            '''cursor.execute("""
                UPDATE connectlinkenquiries 
                SET clientwhatsapp = %s 
                WHERE id = %s;
            """, (263714560713, 18))

            cursor.execute("""
                UPDATE connectlinkenquiries 
                SET clientwhatsapp = %s 
                WHERE id = %s;
            """, (14383367749, 12))

            cursor.execute("""
                UPDATE connectlinkenquiries 
                SET clientwhatsapp = 263000000000 + clientwhatsapp 
                WHERE id BETWEEN 13 AND 16;
            """)'''

            '''cursor.execute("""DELETE FROM connectlinkadmin WHERE id BETWEEN 1 AND 6;""")
            cursor.execute("""TRUNCATE TABLE connectlinknotes;""")'''




            tables = ['connectlinkdatabase', 'connectlinknotes', 'connectlinkadmin']
            for table in tables:
                try:
                    cursor.execute(f"SELECT pg_get_serial_sequence('{table}', 'id');")
                    seq_name = cursor.fetchone()[0]  # fetch the first column of the first row
                    if seq_name:
                        print(f"✓ Sequence for {table}: {seq_name}")
                except Exception as e:
                    connection.rollback()
                    print(f"Note: Could not check sequence for {table}: {e}")


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
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment7amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment7duedate date;",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment7date date;",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment8amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment8duedate date;",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment8date date;",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment9amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment9duedate date;",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment9date date;",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment10amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment10duedate date;",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS installment10date date;",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS projectcompletionstatus varchar(100);",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS quotation_id INT;",
                "ALTER TABLE connectlinkdatabasedeletedprojects ADD COLUMN IF NOT EXISTS adjusted_schedules_json TEXT;",
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
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment7amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment7duedate date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment7date date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment8amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment8duedate date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment8date date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment9amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment9duedate date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment9date date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment10amount NUMERIC(12,2);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment10duedate date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS installment10date date;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS projectcompletionstatus varchar(100);",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS latepaymentinterest INT;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS quotation_id INT;",
                "ALTER TABLE connectlinkdatabase ADD COLUMN IF NOT EXISTS adjusted_schedules_json TEXT;",
                "ALTER TABLE connectlinknotes ADD COLUMN IF NOT EXISTS projectname varchar(100);",
                "ALTER TABLE connectlinknotes ADD COLUMN IF NOT EXISTS clientname varchar(100);",
                "ALTER TABLE connectlinknotes ADD COLUMN IF NOT EXISTS clientwanumber INT;",
                "ALTER TABLE connectlinknotes ADD COLUMN IF NOT EXISTS clientnextofkinnumber INT;"

            ]

            for sql_stmt in payment_alters:
                cursor.execute(sql_stmt)


            try:
                # Create the update query for PostgreSQL
                update_query = """
                UPDATE connectlinkdatabase 
                SET 
                    installment1duedate = CASE 
                        WHEN installment1duedate IS NOT NULL 
                        AND EXTRACT(YEAR FROM installment1duedate) = 2025 
                        THEN installment1duedate + INTERVAL '1 year' 
                        ELSE installment1duedate 
                    END,
                    installment2duedate = CASE 
                        WHEN installment2duedate IS NOT NULL 
                        AND EXTRACT(YEAR FROM installment2duedate) = 2025 
                        THEN installment2duedate + INTERVAL '1 year' 
                        ELSE installment2duedate 
                    END,
                    installment3duedate = CASE 
                        WHEN installment3duedate IS NOT NULL 
                        AND EXTRACT(YEAR FROM installment3duedate) = 2025 
                        THEN installment3duedate + INTERVAL '1 year' 
                        ELSE installment3duedate 
                    END,
                    installment4duedate = CASE 
                        WHEN installment4duedate IS NOT NULL 
                        AND EXTRACT(YEAR FROM installment4duedate) = 2025 
                        THEN installment4duedate + INTERVAL '1 year' 
                        ELSE installment4duedate 
                    END,
                    installment5duedate = CASE 
                        WHEN installment5duedate IS NOT NULL 
                        AND EXTRACT(YEAR FROM installment5duedate) = 2025 
                        THEN installment5duedate + INTERVAL '1 year' 
                        ELSE installment5duedate 
                    END,
                    installment6duedate = CASE 
                        WHEN installment6duedate IS NOT NULL 
                        AND EXTRACT(YEAR FROM installment6duedate) = 2025 
                        THEN installment6duedate + INTERVAL '1 year' 
                        ELSE installment6duedate 
                    END,
                    installment7duedate = CASE 
                        WHEN installment7duedate IS NOT NULL 
                        AND EXTRACT(YEAR FROM installment7duedate) = 2025 
                        THEN installment7duedate + INTERVAL '1 year' 
                        ELSE installment7duedate 
                    END,
                    installment8duedate = CASE 
                        WHEN installment8duedate IS NOT NULL 
                        AND EXTRACT(YEAR FROM installment8duedate) = 2025 
                        THEN installment8duedate + INTERVAL '1 year' 
                        ELSE installment8duedate 
                    END,
                    installment9duedate = CASE 
                        WHEN installment9duedate IS NOT NULL 
                        AND EXTRACT(YEAR FROM installment9duedate) = 2025 
                        THEN installment9duedate + INTERVAL '1 year' 
                        ELSE installment9duedate 
                    END,
                    installment10duedate = CASE 
                        WHEN installment10duedate IS NOT NULL 
                        AND EXTRACT(YEAR FROM installment10duedate) = 2025 
                        THEN installment10duedate + INTERVAL '1 year' 
                        ELSE installment10duedate 
                    END
                WHERE id = %s
                RETURNING *;
                """
                
                cursor.execute(update_query, (125,))
                updated_row = cursor.fetchone()
                connection.commit()
                
                print(f"✓ Updated due dates for project ID 125")
                
            except Exception as e:
                connection.rollback()
                print(f"⚠️  Error updating dates: {e}")

            ## hardware initialisation

            
            # Products table
            execute_query("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    category VARCHAR(50) NOT NULL,
                    unit_type VARCHAR(20) DEFAULT 'piece',
                    unit_details VARCHAR(100),
                    price DECIMAL(10,2) NOT NULL,
                    stock INTEGER DEFAULT 0,
                    min_stock_level INTEGER DEFAULT 10,
                    description TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """, commit=True)

            # Stock additions table
            execute_query("""
                CREATE TABLE IF NOT EXISTS stock_additions (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id),
                    quantity INTEGER NOT NULL,
                    buy_price DECIMAL(10,2) NOT NULL,
                    total_cost DECIMAL(10,2) NOT NULL,
                    funding_source VARCHAR(20) NOT NULL,
                    user_id INTEGER,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """, commit=True)

            # Stock reductions table
            execute_query("""
                CREATE TABLE IF NOT EXISTS stock_reductions (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id),
                    quantity INTEGER NOT NULL,
                    reason VARCHAR(50) NOT NULL,
                    notes TEXT,
                    user_id INTEGER,
                    reduced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """, commit=True)

            # Remove old columns if they exist
            execute_query("""
                ALTER TABLE products 
                    DROP COLUMN IF EXISTS barcode,
                    DROP COLUMN IF EXISTS icon
            """, commit=True)

            execute_query("""
                ALTER TABLE products 
                ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE
            """, commit=True)

            # Rename price to sell_price if it exists
            try:
                check_query = """
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'products' AND column_name = 'price'
                """
                result = execute_query(check_query, fetch_one=True)
                
                if result:
                    execute_query("""
                        ALTER TABLE products 
                        RENAME COLUMN price TO sell_price
                    """, commit=True)
                    print("Renamed price column to sell_price")
            except Exception as e:
                print(f"Note: Could not rename column: {e}")

            # Add buy_price column if it doesn't exist
            execute_query("""
                ALTER TABLE transaction_items 
                ADD COLUMN IF NOT EXISTS unit_type VARCHAR(20) DEFAULT 'piece';
            """, commit=True)
            
            # Transactions table - CREATE OR UPDATE
            execute_query("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    transaction_number VARCHAR(50) UNIQUE NOT NULL,
                    user_id INTEGER,
                    payment_method VARCHAR(20) NOT NULL,
                    status VARCHAR(20) DEFAULT 'completed',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """, commit=True)
            
            # Drop foreign key constraint if it exists (to support hardware_users)
            try:
                execute_query("""
                    ALTER TABLE transactions 
                    DROP CONSTRAINT IF EXISTS transactions_user_id_fkey
                """, commit=True)
                print("✓ Removed foreign key constraint from transactions.user_id")
            except Exception as e:
                print(f"Note: {e}")
            
            execute_query("""
                ALTER TABLE transactions 
                ADD COLUMN IF NOT EXISTS tax DECIMAL(10,2) DEFAULT 0.00
            """, commit=True)
            
            execute_query("""
                ALTER TABLE transactions 
                ADD COLUMN IF NOT EXISTS tax_rate DECIMAL(5,2) DEFAULT 10.0
            """, commit=True)
            
            execute_query("""
                ALTER TABLE transactions 
                ADD COLUMN IF NOT EXISTS total DECIMAL(10,2) DEFAULT 0.00
            """, commit=True)
            
            execute_query("""
                ALTER TABLE transactions 
                ADD COLUMN IF NOT EXISTS amount_paid DECIMAL(10,2) DEFAULT 0.00
            """, commit=True)
            
            execute_query("""
                ALTER TABLE transactions 
                ADD COLUMN IF NOT EXISTS change_amount DECIMAL(10,2) DEFAULT 0.00
            """, commit=True)
            
            # Transaction Items table
            execute_query("""
                CREATE TABLE IF NOT EXISTS transaction_items (
                    id SERIAL PRIMARY KEY,
                    transaction_id INTEGER REFERENCES transactions(id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(id),
                    quantity INTEGER NOT NULL,
                    price_at_time DECIMAL(10,2) NOT NULL,
                    subtotal DECIMAL(10,2) NOT NULL
                )
            """, commit=True)
            
            # Categories table
            execute_query("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) UNIQUE NOT NULL,
                    display_order INTEGER DEFAULT 0
                )
            """, commit=True)

            # Create hardware_users table for hardware POS system with role-based access
            execute_query("""
                CREATE TABLE IF NOT EXISTS hardware_users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(80) UNIQUE NOT NULL,
                    password VARCHAR(100) NOT NULL,
                    full_name VARCHAR(100) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """, commit=True)

            # Create default hardware users if not exists
            try:
                hw_admin_check = execute_query("SELECT id FROM hardware_users WHERE username = %s", ('mrsgadmin',), fetch_one=True)
                if not hw_admin_check:
                    # Admin user - full access to all features
                    result = execute_query("""
                        INSERT INTO hardware_users (username, password, full_name, role)
                        VALUES (%s, %s, %s, %s)
                    """, ('mrsgadmin', 'mrsgogweo1admin01', 'Mrs G Admin', 'admin'), commit=True)
                    print("✓ Hardware admin user created - username: mrsgadmin")
                else:
                    print("✓ Hardware admin user already exists")
            except Exception as e:
                print(f"❌ Error creating hardware admin user: {e}")

            # Create operator user if not exists
            try:
                hw_operator_check = execute_query("SELECT id FROM hardware_users WHERE username = %s", ('shopoperatoruser',), fetch_one=True)
                if not hw_operator_check:
                    # Operator user - only POS and transactions access
                    result = execute_query("""
                        INSERT INTO hardware_users (username, password, full_name, role)
                        VALUES (%s, %s, %s, %s)
                    """, ('shopoperatoruser', 'conlinkhardwareshopoperator2026', 'Shop Operator', 'operator'), commit=True)
                    print("✓ Hardware operator user created - username: shopoperatoruser")
                else:
                    print("✓ Hardware operator user already exists")
            except Exception as e:
                print(f"❌ Error creating hardware operator user: {e}")
            
            
            # Create default categories
            default_categories = [
                ('Tools', 1),
                ('Measuring Tools', 2),
                ('Fasteners', 3),
                ('Paint', 4),
                ('Lumber', 5),
                ('Electrical', 6),
                ('Plumbing', 7),
                ('Safety', 8),
                ('Blankets', 9)
            ]
            
            for cat_name, order in default_categories:
                cat_check = execute_query("SELECT id FROM categories WHERE name = %s", (cat_name,), fetch_one=True)
                if not cat_check:
                    execute_query("""
                        INSERT INTO categories (name, display_order)
                        VALUES (%s, %s)
                    """, (cat_name, order), commit=True)


            # Create activity_log table for tracking user actions
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS activity_log (
                    id SERIAL PRIMARY KEY,
                    action_type VARCHAR(50) NOT NULL,
                    description TEXT NOT NULL,
                    user_name VARCHAR(100),
                    reference_type VARCHAR(50),
                    reference_id INT,
                    details JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # Add indexes for faster querying
            try:
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_created_at ON activity_log(created_at DESC);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_action_type ON activity_log(action_type);")
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_activity_log_reference ON activity_log(reference_type, reference_id);")
            except Exception as e:
                connection.rollback()
                print(f"Note: Could not create activity_log indexes: {e}")

            connection.commit()
            print("✅ Database tables initialized successfully!")

            # Fix bad date year 72026 -> 2026 (reported by user)
            try:
                date_cols = [
                    'projectstartdate', 'contractagreementdate', 'datedepositorbullet',
                    'installment1duedate', 'installment1date',
                    'installment2duedate', 'installment2date',
                    'installment3duedate', 'installment3date',
                    'installment4duedate', 'installment4date',
                    'installment5duedate', 'installment5date',
                    'installment6duedate', 'installment6date',
                    'installment7duedate', 'installment7date',
                    'installment8duedate', 'installment8date',
                    'installment9duedate', 'installment9date',
                    'installment10duedate', 'installment10date'
                ]
                for col in date_cols:
                    # Use to_char to get YYYY-MM-DD string, replace bad year, cast back
                    cursor.execute(f"""
                        UPDATE connectlinkdatabase
                        SET {col} = REPLACE(TO_CHAR({col}, 'YYYY-MM-DD'), '72026', '2026')::date
                        WHERE {col} IS NOT NULL
                        AND TO_CHAR({col}, 'YYYY') = '72026'
                    """)
                    fixed_count = cursor.rowcount
                    if fixed_count > 0:
                        print(f"✅ Fixed 72026->2026 in {col} for {fixed_count} record(s)")
                        connection.commit()
                connection.commit()
                print("✅ Bad date cleanup complete!")
            except Exception as cleanup_err:
                print(f"Note: Date cleanup error: {cleanup_err}")

            # ===== USER PERMISSIONS TABLE =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_permissions (
                    id SERIAL PRIMARY KEY,
                    user_type VARCHAR(20) NOT NULL,
                    user_id INT NOT NULL,
                    can_manage_projects BOOLEAN DEFAULT FALSE,
                    can_manage_hardware BOOLEAN DEFAULT FALSE,
                    can_manage_hr BOOLEAN DEFAULT FALSE,
                    can_add_users BOOLEAN DEFAULT FALSE,
                    can_edit_users BOOLEAN DEFAULT FALSE,
                    can_delete_users BOOLEAN DEFAULT FALSE,
                    can_export_data BOOLEAN DEFAULT FALSE,
                    can_view_audit BOOLEAN DEFAULT FALSE,
                    can_manage_roles BOOLEAN DEFAULT FALSE,
                    can_view_payments BOOLEAN DEFAULT FALSE,
                    is_super_admin BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_type, user_id)
                );
            """)
            connection.commit()
            # Add can_view_payments column if it doesn't exist (for existing tables)
            try:
                cursor.execute("""
                    ALTER TABLE user_permissions
                    ADD COLUMN IF NOT EXISTS can_view_payments BOOLEAN DEFAULT FALSE
                """)
                connection.commit()
            except Exception as e:
                print(f"Note: Could not add can_view_payments column: {e}")

            # Add can_edit_projects column if it doesn't exist
            try:
                cursor.execute("""
                    ALTER TABLE user_permissions
                    ADD COLUMN IF NOT EXISTS can_edit_projects BOOLEAN DEFAULT TRUE
                """)
                connection.commit()
            except Exception as e:
                print(f"Note: Could not add can_edit_projects column: {e}")

            print("✅ User permissions table initialized!")

            # ========== HR MODULE TABLES ==========
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_employees (
                    id SERIAL PRIMARY KEY,
                    user_id INT REFERENCES connectlinkusers(id) ON DELETE SET NULL,
                    first_name VARCHAR(100) NOT NULL,
                    last_name VARCHAR(100) NOT NULL,
                    whatsapp VARCHAR(50),
                    email VARCHAR(200),
                    address TEXT,
                    password VARCHAR(100),
                    role VARCHAR(50) DEFAULT 'Ordinary User',
                    department VARCHAR(100),
                    designation VARCHAR(100),
                    gender VARCHAR(10),
                    dob DATE,
                    marital_status VARCHAR(50),
                    nationality VARCHAR(100),
                    date_joined DATE,
                    leave_approver_name VARCHAR(200),
                    leave_approver_id INT,
                    leave_approver_email VARCHAR(200),
                    leave_approver_whatsapp VARCHAR(50),
                    current_leave_balance DECIMAL(10,2) DEFAULT 21,
                    monthly_accumulation DECIMAL(5,2) DEFAULT 1.75,
                    bank_holder_name VARCHAR(100),
                    bank_holder_surname VARCHAR(100),
                    bank_name VARCHAR(100),
                    bank_account_number VARCHAR(50),
                    bank_branch VARCHAR(100),
                    bank_branch_code VARCHAR(20),
                    basic_salary DECIMAL(12,2) DEFAULT 0,
                    usd_percent DECIMAL(5,2) DEFAULT 100,
                    zwg_percent DECIMAL(5,2) DEFAULT 0,
                    exchange_rate DECIMAL(12,4) DEFAULT 1,
                    currency VARCHAR(10) DEFAULT 'USD',
                    c8_number VARCHAR(50),
                    c8_type VARCHAR(20),
                    employment_type VARCHAR(50) DEFAULT 'Permanent',
                    status VARCHAR(20) DEFAULT 'Active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Add subsidiary column to hr_employees if not exists
            try:
                cursor.execute("""
                    ALTER TABLE hr_employees
                    ADD COLUMN IF NOT EXISTS subsidiary VARCHAR(50) DEFAULT ''
                """)
                connection.commit()
            except Exception as e:
                print(f"Note: Could not add subsidiary column to hr_employees: {e}")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_leave_applications (
                    id SERIAL PRIMARY KEY,
                    employee_id INT REFERENCES hr_employees(id) ON DELETE CASCADE,
                    employee_name VARCHAR(300) NOT NULL,
                    leave_type VARCHAR(50) NOT NULL,
                    from_date DATE NOT NULL,
                    to_date DATE NOT NULL,
                    days INT NOT NULL,
                    reason TEXT,
                    status VARCHAR(20) DEFAULT 'Pending',
                    approved_by VARCHAR(200),
                    approved_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Employee leave type balances (per-employee, per-leave-type)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_employee_leave_balances (
                    id SERIAL PRIMARY KEY,
                    employee_id INT NOT NULL REFERENCES hr_employees(id) ON DELETE CASCADE,
                    leave_type VARCHAR(50) NOT NULL,
                    current_balance DECIMAL(10,2) DEFAULT 0,
                    monthly_accrual DECIMAL(10,2) DEFAULT 0,
                    annual_accrual DECIMAL(10,2) DEFAULT 0,
                    carry_forward DECIMAL(10,2) DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(employee_id, leave_type)
                );
            """)
            connection.commit()
            print("✅ Employee leave balances table initialized")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_leave_approved (
                    id SERIAL PRIMARY KEY,
                    application_id INT REFERENCES hr_leave_applications(id) ON DELETE CASCADE,
                    employee_id INT,
                    employee_name VARCHAR(300),
                    leave_type VARCHAR(50),
                    from_date DATE,
                    to_date DATE,
                    days INT,
                    approved_by VARCHAR(200),
                    approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_leave_declined (
                    id SERIAL PRIMARY KEY,
                    application_id INT,
                    employee_id INT,
                    employee_name VARCHAR(300),
                    leave_type VARCHAR(50),
                    from_date DATE,
                    to_date DATE,
                    days INT,
                    reason TEXT,
                    declined_by VARCHAR(200),
                    declined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # ===== PASSWORD RESET CODES TABLE =====
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS password_reset_codes (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(100) NOT NULL,
                    code VARCHAR(6) NOT NULL,
                    whatsapp VARCHAR(50),
                    expires_at TIMESTAMP NOT NULL,
                    used BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            connection.commit()
            print("✅ Password reset codes table initialized")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_attendance (
                    id SERIAL PRIMARY KEY,
                    employee_id INT REFERENCES hr_employees(id) ON DELETE CASCADE,
                    date DATE DEFAULT CURRENT_DATE,
                    check_in TIME,
                    check_out TIME,
                    status VARCHAR(20) DEFAULT 'Present',
                    notes TEXT,
                    UNIQUE(employee_id, date)
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_payroll (
                    id SERIAL PRIMARY KEY,
                    employee_id INT REFERENCES hr_employees(id) ON DELETE CASCADE,
                    period VARCHAR(20) NOT NULL,
                    basic_pay DECIMAL(12,2) DEFAULT 0,
                    allowances DECIMAL(12,2) DEFAULT 0,
                    deductions DECIMAL(12,2) DEFAULT 0,
                    net_pay DECIMAL(12,2) DEFAULT 0,
                    status VARCHAR(20) DEFAULT 'Pending',
                    processed_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hr_assets (
                    id SERIAL PRIMARY KEY,
                    asset_tag VARCHAR(50) UNIQUE,
                    asset_name VARCHAR(200) NOT NULL,
                    category VARCHAR(100),
                    assigned_to INT REFERENCES hr_employees(id) ON DELETE SET NULL,
                    value DECIMAL(12,2) DEFAULT 0,
                    purchase_date DATE,
                    status VARCHAR(20) DEFAULT 'In Service',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            connection.commit()
            print("✅ HR module tables initialized!")

            # ========== PAYE TAX TABLES ==========
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paye_tax_tables (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    description TEXT,
                    filename VARCHAR(255),
                    period VARCHAR(20),
                    is_active BOOLEAN DEFAULT FALSE,
                    uploaded_by VARCHAR(100),
                    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS paye_tax_brackets (
                    id SERIAL PRIMARY KEY,
                    table_id INT NOT NULL REFERENCES paye_tax_tables(id) ON DELETE CASCADE,
                    band VARCHAR(100),
                    income_from DECIMAL(15,2) DEFAULT 0,
                    income_to DECIMAL(15,2) DEFAULT 0,
                    tax_rate DECIMAL(5,2) DEFAULT 0,
                    cumulative_tax DECIMAL(15,2) DEFAULT 0,
                    bracket_order INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Ensure at most one active table
            cursor.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_paye_active_unique
                ON paye_tax_tables ((true)) WHERE is_active = true;
            """)

            connection.commit()
            print("✅ PAYE tax tables initialized!")

            # ========== PAYROLL DEDUCTION CONFIG ==========
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payroll_deduction_config (
                    id SERIAL PRIMARY KEY,
                    deduction_code VARCHAR(50) UNIQUE NOT NULL,
                    deduction_name VARCHAR(200) NOT NULL,
                    description TEXT,
                    rate DECIMAL(10,4) DEFAULT 0,
                    rate_type VARCHAR(30) DEFAULT 'percentage_of_paye',
                    ceiling_amount DECIMAL(15,2) DEFAULT 0,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_employee_deduction BOOLEAN DEFAULT TRUE,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Seed default Zimbabwe statutory deductions
            cursor.execute("SELECT COUNT(*) FROM payroll_deduction_config")
            if cursor.fetchone()[0] == 0:
                seed_deductions = [
                    ('AIDS_LEVY', 'AIDS Levy', '3% of PAYE tax amount', 3.0, 'percentage_of_paye', 0, True, True),
                    ('NSSA_EMPLOYEE', 'NSSA (Employee)', 'NSSA employee pension contribution', 4.5, 'percentage_of_gross', 0, True, True),
                    ('NSSA_EMPLOYER', 'NSSA (Employer)', 'NSSA employer pension contribution', 4.5, 'percentage_of_gross', 0, True, False),
                    ('ZIMDEF', 'ZIMDEF Levy', 'Zimbabwe Manpower Development Levy', 1.0, 'percentage_of_gross', 0, True, True),
                ]
                for dc in seed_deductions:
                    cursor.execute("""
                        INSERT INTO payroll_deduction_config
                            (deduction_code, deduction_name, description, rate, rate_type, ceiling_amount, is_active, is_employee_deduction)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (deduction_code) DO NOTHING
                    """, dc)
                connection.commit()
                print("✅ Default payroll deductions seeded!")

            # Add deduction breakdown columns to hr_payroll if not present
            for col in [
                "paye_tax DECIMAL(12,2) DEFAULT 0",
                "aids_levy DECIMAL(12,2) DEFAULT 0",
                "nssa DECIMAL(12,2) DEFAULT 0",
                "zimdef DECIMAL(12,2) DEFAULT 0",
                "gross_pay DECIMAL(12,2) DEFAULT 0"
            ]:
                try:
                    cursor.execute(f"ALTER TABLE hr_payroll ADD COLUMN IF NOT EXISTS {col}")
                except Exception:
                    pass
            connection.commit()
            print("✅ Payroll deduction columns added!")

            # ========== PAYROLL ARCHIVES TABLE ==========
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS payroll_archives (
                    id SERIAL PRIMARY KEY,
                    period VARCHAR(20) NOT NULL,
                    filename VARCHAR(255) NOT NULL,
                    file_data BYTEA NOT NULL,
                    file_size INT DEFAULT 0,
                    employee_count INT DEFAULT 0,
                    total_gross DECIMAL(15,2) DEFAULT 0,
                    total_net DECIMAL(15,2) DEFAULT 0,
                    generated_by VARCHAR(100),
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(period)
                );
            """)
            connection.commit()
            print("✅ Payroll archives table initialized!")

    except Exception as e:
        print(f"❌ Error initializing database tables: {e}")

def migrate_product_categories():
    """Migrate existing products to new category structure"""
    try:
        print("🔄 Migrating product categories...")
        
        with get_db() as (cursor, connection):
            # Check if migration has already been done
            cursor.execute("""
                SELECT COUNT(*) FROM products 
                WHERE category IN ('General Tools', 'Finishing & Painting Tools', 'Paint & Coatings', 
                                   'Safety Equipment', 'Cleaning Supplies', 'Kitchen & Bathroom',
                                   'Appliances', 'Cookware & Pots')
            """)
            migrated_count = cursor.fetchone()[0]
            
            if migrated_count > 0:
                print("✅ Categories already migrated, skipping...")
                return
            
            # Define category mappings
            category_map = {
                # Paint-related items
                'Paint Brushes': 'Finishing & Painting Tools',
                'Rolling Brush': 'Finishing & Painting Tools',
                'Flicker Brush': 'Finishing & Painting Tools',
                'Trowels': 'Finishing & Painting Tools',
                'Floats': 'Finishing & Painting Tools',
                'Wooden Float': 'Finishing & Painting Tools',
                'Jointers': 'Finishing & Painting Tools',
                
                # Paint/Coatings
                'Paint': 'Paint & Coatings',
                'Spray Paint': 'Paint & Coatings',
                'Lime Green': 'Paint & Coatings',
                
                # Tools stay as General Tools (unless above)
                'Hammers': 'General Tools',
                'Claw Hammer': 'General Tools',
                'Chasing Hammer': 'General Tools',
                'Hammer Heads': 'General Tools',
                'Shovel': 'General Tools',
                'Spade': 'General Tools',
                'Screwdrivers': 'General Tools',
                'Allen Keys': 'General Tools',
                'Spanners': 'General Tools',
                'Shifting Spanner': 'General Tools',
                'Pliers': 'General Tools',
                'Side Cutters': 'General Tools',
                'Cutters': 'General Tools',
                'Saws': 'General Tools',
                'Hack Saws': 'General Tools',
                'Drill Bits': 'General Tools',
                'Concrete Drill Bits': 'General Tools',
                'Flicker Machine': 'General Tools',
                'Torque Wrench': 'General Tools',
                'Wheel Barrows': 'General Tools',
                
                # Safety category
                'Gloves': 'Safety Equipment',
                'Glass Gloves': 'Safety Equipment',
                'PVC Gloves': 'Safety Equipment',
                'Goggles': 'Safety Equipment',
                'Masks': 'Safety Equipment',
                'Hard Hats': 'Safety Equipment',
                
                # Cleaning category
                'Brooms': 'Cleaning Supplies',
                'Square Brooms': 'Cleaning Supplies',
                'Flat Brooms': 'Cleaning Supplies',
                'Mops': 'Cleaning Supplies',
                'Rakes': 'Cleaning Supplies',
                
                # Kitchen & Bathroom
                'Shower Mixers': 'Kitchen & Bathroom',
                'Basin': 'Kitchen & Bathroom',
                'Pan Connectors': 'Kitchen & Bathroom',
                'S-Trap': 'Kitchen & Bathroom',
                'P-Trap': 'Kitchen & Bathroom',
                
                # Appliances
                'Stove': 'Appliances',
                'Oven': 'Appliances',
                
                # Pots & Cookware
                'Garden Pots': 'Cookware & Pots',
                'Gainstar Pots': 'Cookware & Pots',
                'Maifam Pots': 'Cookware & Pots',
                'Cast Iron Pots': 'Cookware & Pots',
            }
            
            # Update products with mapped categories
            for old_category, new_category in category_map.items():
                try:
                    cursor.execute("""
                        UPDATE products 
                        SET category = %s
                        WHERE category = %s
                    """, (new_category, old_category))
                    connection.commit()
                except Exception as e:
                    connection.rollback()
                    print(f"Note: Could not update category '{old_category}' to '{new_category}': {e}")
            
            # Rename remaining old categories
            old_to_new = {
                'Bathroom & Kitchen': 'Kitchen & Bathroom',
                'Cleaning': 'Cleaning Supplies',
                'Safety': 'Safety Equipment',
                'Garden & Pots': 'Cookware & Pots',
            }
            
            for old, new in old_to_new.items():
                try:
                    cursor.execute("""
                        UPDATE products 
                        SET category = %s
                        WHERE category = %s
                    """, (new, old))
                    connection.commit()
                except Exception as e:
                    connection.rollback()
                    print(f"Note: Could not rename category '{old}' to '{new}': {e}")
            
            print("✅ Product categories migrated successfully!")
            
    except Exception as e:
        print(f"⚠️ Category migration error: {e}")

initialize_database_tables()
migrate_product_categories()



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


                def send_whatsapp_button_image_message(recipient, text, image_url, buttons, footer_text=None):
                    # Check if human mode is enabled for this recipient
                    try:
                        to_digits = re.sub(r'[^0-9]', '', str(recipient))
                        cursor.execute("""
                            SELECT human_mode FROM chat_human_mode 
                            WHERE sender_phone = %s 
                               OR RIGHT(sender_phone, 9) = RIGHT(%s, 9)
                        """, (recipient, to_digits))
                        row = cursor.fetchone()
                        if row and row[0]:
                            print(f"🚫 Human mode ON for {recipient} — skipping chatbot auto-reply (button image message)")
                            return None
                    except Exception as e:
                        print(f"⚠️ Human mode check error in button_image_message: {e}")
                    
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
                    print("📡 Button image message response:", response.status_code)
                    
                    # Save to whatsapp_messages for chat portal visibility
                    if response.status_code == 200:
                        try:
                            with get_db() as (save_cursor, save_conn):
                                buttons_summary = ', '.join([b.get('reply', {}).get('title', '') for b in (buttons or [])])
                                display_text = f"{text[:250]} [Buttons: {buttons_summary[:100]}]"
                                save_cursor.execute("""
                                    INSERT INTO whatsapp_messages 
                                    (sender_phone, sender_name, message_text, message_type, direction, status)
                                    VALUES (%s, %s, %s, 'interactive', 'outgoing', 'sent')
                                """, (recipient, 'ConnectLink Bot', display_text[:500]))
                                save_conn.commit()
                        except Exception as save_err:
                            print(f"⚠️ Failed to save button image message: {save_err}")
                    
                    return response

                def send_whatsapp_message(to, text, buttons=None, footer_text = None):

                    # Check if human mode is enabled for this recipient — skip auto-reply if ON
                    try:
                        to_digits = re.sub(r'[^0-9]', '', str(to))
                        # Match by exact or trailing 9-12 digits (handles +263, 263, 0 prefix variations)
                        cursor.execute("""
                            SELECT human_mode FROM chat_human_mode 
                            WHERE sender_phone = %s 
                               OR RIGHT(sender_phone, 9) = RIGHT(%s, 9)
                        """, (to, to_digits))
                        row = cursor.fetchone()
                        if row and row[0]:
                            print(f"🚫 Human mode ON for {to} — skipping chatbot auto-reply")
                            return
                    except Exception as e:
                        print(f"⚠️ Human mode check error: {e}")

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
                        resp_json = response.json()

                        print("✅ Message sent successfully.")
                        print("📝 Response JSON:", resp_json)

                        # Save outgoing bot message to whatsapp_messages for chat portal visibility
                        try:
                            with get_db() as (save_cursor, save_conn):
                                sender_name = 'ConnectLink Bot'
                                save_cursor.execute("""
                                    INSERT INTO whatsapp_messages 
                                    (sender_phone, sender_name, message_text, message_type, direction, status)
                                    VALUES (%s, %s, %s, %s, 'outgoing', 'sent')
                                """, (to, sender_name, text[:500], 'text'))
                                save_conn.commit()
                        except Exception as save_err:
                            print(f"⚠️ Failed to save outgoing bot message: {save_err}")

                        print("done trying")
                        return resp_json
                    
                    except requests.exceptions.RequestException as e:
                        print("❌ WhatsApp API Error:", e)
                        # Save failed message to whatsapp_messages too
                        try:
                            with get_db() as (save_cursor, save_conn):
                                sender_name = 'ConnectLink Bot'
                                error_detail = str(e)[:200]
                                save_cursor.execute("""
                                    INSERT INTO whatsapp_messages 
                                    (sender_phone, sender_name, message_text, message_type, direction, status)
                                    VALUES (%s, %s, %s, %s, 'outgoing', 'failed')
                                """, (to, sender_name, f"{text[:300]} [FAILED: {error_detail}]", 'text'))
                                save_conn.commit()
                        except Exception as save_err:
                            print(f"⚠️ Failed to save failed bot message: {save_err}")
                        return {"error": str(e)}

                def send_whatsapp_button_message(recipient, text, buttons, footer_text=None):
                    """Send WhatsApp interactive button message with footer"""
                    # Check if human mode is enabled for this recipient
                    try:
                        to_digits = re.sub(r'[^0-9]', '', str(recipient))
                        cursor.execute("""
                            SELECT human_mode FROM chat_human_mode 
                            WHERE sender_phone = %s 
                               OR RIGHT(sender_phone, 9) = RIGHT(%s, 9)
                        """, (recipient, to_digits))
                        row = cursor.fetchone()
                        if row and row[0]:
                            print(f"🚫 Human mode ON for {recipient} — skipping chatbot auto-reply (button message)")
                            return None
                    except Exception as e:
                        print(f"⚠️ Human mode check error in button_message: {e}")
                    
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
                        else:
                            # Save to whatsapp_messages for chat portal visibility
                            try:
                                with get_db() as (save_cursor, save_conn):
                                    buttons_summary = ', '.join([b.get('reply', {}).get('title', '') for b in (buttons or [])])
                                    display_text = f"{text[:300]} [Buttons: {buttons_summary[:100]}]"
                                    save_cursor.execute("""
                                        INSERT INTO whatsapp_messages 
                                        (sender_phone, sender_name, message_text, message_type, direction, status)
                                        VALUES (%s, %s, %s, 'interactive', 'outgoing', 'sent')
                                    """, (recipient, 'ConnectLink Bot', display_text[:500]))
                                    save_conn.commit()
                            except Exception as save_err:
                                print(f"⚠️ Failed to save button message: {save_err}")
                        
                        return response
                        
                    except Exception as e:
                        print(f"❌ Error sending WhatsApp button message: {str(e)}")
                        # Save failed attempt
                        try:
                            with get_db() as (save_cursor, save_conn):
                                save_cursor.execute("""
                                    INSERT INTO whatsapp_messages 
                                    (sender_phone, sender_name, message_text, message_type, direction, status)
                                    VALUES (%s, %s, %s, 'interactive', 'outgoing', 'failed')
                                """, (recipient, 'ConnectLink Bot', f"{text[:300]} [FAILED: {str(e)[:100]}]"))
                                save_conn.commit()
                        except Exception:
                            pass
                        return None
                    
                def send_whatsapp_list_message(recipient, text, header_text, sections, footer_text=None):
                    """Send WhatsApp interactive list message"""
                    # Check if human mode is enabled for this recipient
                    try:
                        to_digits = re.sub(r'[^0-9]', '', str(recipient))
                        cursor.execute("""
                            SELECT human_mode FROM chat_human_mode 
                            WHERE sender_phone = %s 
                               OR RIGHT(sender_phone, 9) = RIGHT(%s, 9)
                        """, (recipient, to_digits))
                        row = cursor.fetchone()
                        if row and row[0]:
                            print(f"🚫 Human mode ON for {recipient} — skipping chatbot auto-reply (list message)")
                            return None
                    except Exception as e:
                        print(f"⚠️ Human mode check error in list_message: {e}")
                    
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
                        
                        if response.status_code == 200:
                            # Save to whatsapp_messages for chat portal visibility
                            try:
                                with get_db() as (save_cursor, save_conn):
                                    sections_summary = ' | '.join([s.get('title', '') for s in (sections or [])])
                                    display_text = f"{text[:250]} [Options: {sections_summary[:150]}]"
                                    save_cursor.execute("""
                                        INSERT INTO whatsapp_messages 
                                        (sender_phone, sender_name, message_text, message_type, direction, status)
                                        VALUES (%s, %s, %s, 'interactive', 'outgoing', 'sent')
                                    """, (recipient, 'ConnectLink Bot', display_text[:500]))
                                    save_conn.commit()
                            except Exception as save_err:
                                print(f"⚠️ Failed to save list message: {save_err}")
                        
                        return response
                        
                    except Exception as e:
                        print(f"❌ Error sending WhatsApp list message: {str(e)}")
                        # Save failed attempt
                        try:
                            with get_db() as (save_cursor, save_conn):
                                save_cursor.execute("""
                                    INSERT INTO whatsapp_messages 
                                    (sender_phone, sender_name, message_text, message_type, direction, status)
                                    VALUES (%s, %s, %s, 'interactive', 'outgoing', 'failed')
                                """, (recipient, 'ConnectLink Bot', f"{text[:300]} [FAILED: {str(e)[:100]}]"))
                                save_conn.commit()
                        except Exception:
                            pass
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
                            if "statuses" in change["value"]:
                                for status_event in change["value"].get("statuses", []):
                                    try:
                                        outbound_message_id = status_event.get("id")
                                        recipient_id = status_event.get("recipient_id")
                                        status_value = (status_event.get("status") or "").lower()
                                        error_text = json.dumps(status_event.get("errors", []))

                                        if status_value != "failed":
                                            continue

                                        if not outbound_message_id:
                                            continue

                                        if not is_template_window_error(error_text):
                                            continue

                                        cursor.execute("""
                                            SELECT quotation_id, whatsapp_number, client_name, template_fallback_sent
                                            FROM quotation_whatsapp_outbox
                                            WHERE outbound_message_id = %s
                                        """, (outbound_message_id,))
                                        outbox_row = cursor.fetchone()

                                        if not outbox_row:
                                            print(f"ℹ️ No quotation outbox match for failed message_id={outbound_message_id}")
                                            continue

                                        safe_qid = int(outbox_row[0])
                                        target_number = normalize_whatsapp_number(outbox_row[1] or recipient_id)
                                        target_client_name = (outbox_row[2] or 'Client').strip() or 'Client'
                                        fallback_already_sent = bool(outbox_row[3])

                                        q_category = ''
                                        q_size = 0
                                        q_total = 0
                                        q_markup = 0
                                        q_date = None
                                        try:
                                            cursor.execute("""
                                                SELECT category, project_size, total_cost, markup_percentage, quotation_date
                                                FROM quotations
                                                WHERE id = %s
                                            """, (safe_qid,))
                                            qrow = cursor.fetchone()
                                            if qrow:
                                                q_category = qrow[0] or ''
                                                q_size = float(qrow[1]) if qrow[1] else 0
                                                q_total = float(qrow[2]) if qrow[2] else 0
                                                q_markup = float(qrow[3]) if qrow[3] else 0
                                                q_date = qrow[4] if qrow[4] else None
                                        except Exception as qerr:
                                            print(f"⚠️ Could not fetch quotation metadata for fallback: {qerr}")

                                        # Record the failure once so portal can show Failed status entries
                                        cursor.execute("""
                                            SELECT COUNT(*)
                                            FROM quotation_whatsapp_send_logs
                                            WHERE whatsapp_message_id = %s
                                              AND send_status = 'failed'
                                              AND send_type = 'document'
                                        """, (outbound_message_id,))
                                        existing_failed = cursor.fetchone()[0]
                                        if existing_failed == 0:
                                            log_quotation_whatsapp_send(
                                                safe_qid,
                                                target_number,
                                                target_client_name,
                                                'document',
                                                outbound_message_id,
                                                'webhook_status',
                                                send_status='failed',
                                                error_details=error_text,
                                                snapshot_category=q_category,
                                                snapshot_project_size=q_size,
                                                snapshot_total_cost=q_total,
                                                snapshot_markup=q_markup,
                                                snapshot_quotation_date=q_date
                                            )

                                        if fallback_already_sent:
                                            print(f"ℹ️ Template fallback already sent for message_id={outbound_message_id}")
                                            continue

                                        if not target_number:
                                            print(f"⚠️ Could not derive WhatsApp number for failed message_id={outbound_message_id}")
                                            continue

                                        share_token = create_quotation_share_token(safe_qid)
                                        template_response = send_quotation_download_template(
                                            target_number,
                                            share_token,
                                            client_name=target_client_name,
                                            category=q_category,
                                            project_size=q_size
                                        )

                                        fallback_message_id = template_response.get('messages', [{}])[0].get('id', '')
                                        log_quotation_whatsapp_send(
                                            safe_qid,
                                            target_number,
                                            target_client_name,
                                            'template_fallback',
                                            fallback_message_id,
                                            'webhook_async_fallback',
                                            snapshot_category=q_category,
                                            snapshot_project_size=q_size,
                                            snapshot_total_cost=q_total,
                                            snapshot_markup=q_markup,
                                            snapshot_quotation_date=q_date
                                        )

                                        cursor.execute("""
                                            UPDATE quotation_whatsapp_outbox
                                            SET template_fallback_sent = TRUE,
                                                updated_at = CURRENT_TIMESTAMP
                                            WHERE outbound_message_id = %s
                                        """, (outbound_message_id,))
                                        connection.commit()

                                        print(
                                            f"✅ Async fallback template sent for quotation {safe_qid} "
                                            f"to {target_number} after status failure 131047. response={template_response}"
                                        )
                                    except Exception as status_err:
                                        connection.rollback()
                                        print(f"❌ Error handling failed WhatsApp status fallback: {status_err}")

                            if "messages" in change["value"]:
                                for message in change["value"]["messages"]:

                                    conversation_id = str(uuid.uuid4())
                                    session['conversation_id'] = conversation_id
                                

                                    sender_id = message["from"]
                                    sender_number = sender_id[-9:]
                                    print(f"📱 Conversation {conversation_id}: Sender's WhatsApp number: {sender_number}")
                                    session['client'] = str(sender_number)

                                    message_type = message.get("type")
                                    
                                    # ---- SAVE ALL INCOMING MESSAGES ----
                                    try:
                                        # Extract message text based on type
                                        msg_text = ""
                                        media_id = None
                                        file_name = None
                                        if message_type == "text":
                                            msg_text = message.get("text", {}).get("body", "")
                                        elif message_type == "interactive":
                                            interactive = message.get("interactive", {})
                                            itype = interactive.get("type", "")
                                            if itype == "list_reply":
                                                msg_text = interactive.get("list_reply", {}).get("title", "") or interactive.get("list_reply", {}).get("id", "")
                                            elif itype == "button_reply":
                                                msg_text = interactive.get("button_reply", {}).get("title", "") or interactive.get("button_reply", {}).get("id", "")
                                            elif itype == "nfm_reply":
                                                msg_text = interactive.get("nfm_reply", {}).get("response_json", "")
                                        elif message_type == "image":
                                            img_info = message.get("image", {})
                                            media_id = img_info.get("id", "")
                                            file_name = img_info.get("caption", "") or "Image"
                                            msg_text = img_info.get("caption", "") or "[Image]"
                                        elif message_type == "document":
                                            doc_info = message.get("document", {})
                                            media_id = doc_info.get("id", "")
                                            file_name = doc_info.get("filename", "")
                                            msg_text = doc_info.get("caption", "") or f"[Document: {file_name}]"
                                        elif message_type == "audio":
                                            audio_info = message.get("audio", {})
                                            media_id = audio_info.get("id", "")
                                            file_name = "Audio"
                                            msg_text = "[Audio]"
                                        elif message_type == "video":
                                            video_info = message.get("video", {})
                                            media_id = video_info.get("id", "")
                                            file_name = video_info.get("caption", "") or "Video"
                                            msg_text = video_info.get("caption", "") or "[Video]"
                                        elif message_type == "location":
                                            msg_text = "[Location]"
                                        
                                        # Get sender name if possible
                                        sender_name = profile_name or "Unknown"
                                        
                                        # Save to database (use a separate connection to avoid interfering)
                                        with get_db() as (save_cursor, save_conn):
                                            save_cursor.execute("""
                                                INSERT INTO whatsapp_messages 
                                                (sender_phone, sender_name, message_text, message_type, direction, status, media_id, file_name)
                                                VALUES (%s, %s, %s, %s, 'incoming', 'received', %s, %s)
                                            """, (sender_id, sender_name, msg_text[:500], message_type or 'unknown', media_id, file_name))
                                            save_conn.commit()
                                    except Exception as save_err:
                                        print(f"⚠️ Failed to save incoming message: {save_err}")

                                    #external_database_url = "postgresql://lmsdatabase_8ag3_user:6WD9lOnHkiU7utlUUjT88m4XgEYQMTLb@dpg-ctp9h0aj1k6c739h9di0-a.oregon-postgres.render.com/lmsdatabase_8ag3"

                                    with get_db() as (cursor, connection):

                                        try:
                                            
                                            query = """
                                                SELECT id, datecreated, name, password, email, whatsapp
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
                                                
                                                    if message.get("type") == "interactive" and not (
                                                        message.get("interactive", {}).get("type") == "button_reply"
                                                        and (
                                                            (message.get("interactive", {}).get("button_reply", {}).get("id", "") or "").lower().startswith("quotation_")
                                                            or (message.get("interactive", {}).get("button_reply", {}).get("id", "") or "").lower().startswith("enquiry_attachment_")
                                                            or (message.get("interactive", {}).get("button_reply", {}).get("title", "") or "").strip().lower() == "download attachment"
                                                        )
                                                    ):
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


                                                        # Log button/list interaction for analytics
                                                        if button_id:
                                                            log_chatbot_interaction(sender_id, admin_name, 'button_click', button_id, button_id)
                                                        if selected_option:
                                                            log_chatbot_interaction(sender_id, admin_name, 'list_select', selected_option, selected_option)

                                                        # Keyword matching for text messages
                                                        if not button_id and not selected_option and message_type == "text":
                                                            kw_match = resolve_chatbot_keyword(msg_text)
                                                            if kw_match:
                                                                keyword, handler_id = kw_match
                                                                print(f"🔑 Keyword match: '{keyword}' → handler: {handler_id}")
                                                                log_chatbot_interaction(sender_id, admin_name, 'keyword', keyword, handler_id)
                                                                # Map keyword handler to the corresponding action
                                                                if handler_id == 'main_menu':
                                                                    button_id = 'main_menu'
                                                                elif handler_id in ('projects', 'getportfolio', 'getnotes', 'portfolio'):
                                                                    button_id = handler_id if handler_id in ('portfolio', 'projects', 'main_menu') else 'portfolio'
                                                                    if handler_id == 'getportfolio':
                                                                        selected_option = 'getportfolio'
                                                                    elif handler_id == 'getnotes':
                                                                        selected_option = 'getnotes'
                                                                elif handler_id == 'enquirylog':
                                                                    button_id = 'enquirylog'
                                                                elif handler_id in ('kitchen_cabinels', 'building', 'renovation', 'other'):
                                                                    selected_option = handler_id
                                                                    button_id = ''
                                                                elif handler_id == 'paymenthist':
                                                                    button_id = 'paymenthist'

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
                                                                        installment6amount, installment6duedate, installment6date,
                                                                        installment7amount, installment7duedate, installment7date,
                                                                        installment8amount, installment8duedate, installment8date,
                                                                        installment9amount, installment9duedate, installment9date,
                                                                        installment10amount, installment10duedate, installment10date
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
                                                                    
                                                                    # Save to whatsapp_messages for chat portal visibility
                                                                    try:
                                                                        with get_db() as (save_cursor, save_conn):
                                                                            save_cursor.execute("""
                                                                                INSERT INTO whatsapp_messages 
                                                                                (sender_phone, sender_name, message_text, message_type, direction, status, media_id, file_name)
                                                                                VALUES (%s, %s, %s, 'document', 'outgoing', 'sent', %s, %s)
                                                                            """, (recipient_number, 'ConnectLink Bot', f"[Document: {filename}]", media_id, filename))
                                                                            save_conn.commit()
                                                                    except Exception as save_err:
                                                                        print(f"⚠️ Failed to save portfolio PDF message: {save_err}")
                                                                    
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
                                                                    
                                                                    resp = requests.post(url, headers=headers, json=payload)
                                                                    
                                                                    # Save to whatsapp_messages for chat portal visibility
                                                                    if resp.status_code == 200:
                                                                        try:
                                                                            with get_db() as (save_cursor, save_conn):
                                                                                save_cursor.execute("""
                                                                                    INSERT INTO whatsapp_messages 
                                                                                    (sender_phone, sender_name, message_text, message_type, direction, status)
                                                                                    VALUES (%s, %s, %s, 'text', 'outgoing', 'sent')
                                                                                """, (recipient_number, 'ConnectLink Bot', message[:500]))
                                                                                save_conn.commit()
                                                                        except Exception as save_err:
                                                                            print(f"⚠️ Failed to save text message: {save_err}")
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
                                                                    
                                                                    # Save to whatsapp_messages for chat portal visibility
                                                                    try:
                                                                        with get_db() as (save_cursor, save_conn):
                                                                            save_cursor.execute("""
                                                                                INSERT INTO whatsapp_messages 
                                                                                (sender_phone, sender_name, message_text, message_type, direction, status, media_id, file_name)
                                                                                VALUES (%s, %s, %s, 'document', 'outgoing', 'sent', %s, %s)
                                                                            """, (recipient_number, 'ConnectLink Bot', f"[Document: {filename}]", media_id, filename))
                                                                            save_conn.commit()
                                                                    except Exception as save_err:
                                                                        print(f"⚠️ Failed to save cross-tab PDF message: {save_err}")
                                                                    
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
                                                                        ORDER BY id DESC
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


                                                    elif (
                                                        message_type == "button"
                                                        or (
                                                            message_type == "interactive"
                                                            and message.get("interactive", {}).get("type") == "button_reply"
                                                        )
                                                    ):

                                                        # Unified function to send any receipt via WhatsApp
                                                        def send_receipt_via_whatsapp(recipient_number, project_id, receipt_type, config):
                                                            """Send any receipt PDF via WhatsApp"""
                                                            try:
                                                                import io
                                                                from weasyprint import HTML
                                                                
                                                                # Generate PDF
                                                                pdf_bytes = generate_unified_receipt_pdf(project_id, receipt_type, config)
                                                                if not pdf_bytes:
                                                                    print(f"❌ Failed to generate PDF for project {project_id}")
                                                                    send_text_message(recipient_number, "❌ Error generating receipt. Please contact support.")
                                                                    return False
                                                                
                                                                # Get project details for filename and caption
                                                                with get_db() as (cursor, connection):
                                                                    cursor.execute(f"""
                                                                        SELECT clientname, projectname, {config['amount_field']}, {config['date_field']}
                                                                        FROM connectlinkdatabase WHERE id = %s
                                                                    """, (project_id,))
                                                                    row = cursor.fetchone()
                                                                    
                                                                    if row:
                                                                        client_name, project_name, amount, date_paid = row
                                                                        # Sanitize client name for filename (remove spaces, special chars)
                                                                        safe_client_name = ''.join(c for c in client_name if c.isalnum() or c == ' ').replace(' ', '_')
                                                                        filename = f"{config['filename_prefix']}_{safe_client_name}_{project_id}.pdf"
                                                                        
                                                                        date_str = date_paid.strftime('%d %B %Y') if date_paid else '—'
                                                                        
                                                                        caption = f"""📄 *{config['title'].upper()} RECEIPT*

                                                        Client: {client_name}
                                                        Project: {project_name}
                                                        Amount: USD {amount if amount else '0'}
                                                        Date: {date_str}

                                                        Send 'Hello' to view your contracts or to log enquiries."""
                                                                    else:
                                                                        filename = f"{config['filename_prefix']}_{project_id}.pdf"
                                                                        caption = f"📄 {config['title']} Receipt - Project {project_id}"
                                                                
                                                                print(f"📤 Uploading PDF to WhatsApp...")
                                                                
                                                                # Upload to WhatsApp
                                                                url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
                                                                headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
                                                                
                                                                files = {
                                                                    "file": (filename, io.BytesIO(pdf_bytes), "application/pdf"),
                                                                    "type": (None, "application/pdf"),
                                                                    "messaging_product": (None, "whatsapp")
                                                                }
                                                                
                                                                response = requests.post(url, headers=headers, files=files, timeout=30)
                                                                response.raise_for_status()
                                                                media_id = response.json()["id"]
                                                                
                                                                print(f"✅ Media uploaded, ID: {media_id}")
                                                                
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
                                                                
                                                                print(f"📤 Sending document to {recipient_number}...")
                                                                response = requests.post(doc_url, headers=doc_headers, json=doc_payload, timeout=30)
                                                                response.raise_for_status()
                                                                
                                                                print(f"✅ PDF sent successfully!")
                                                                return True
                                                                
                                                            except Exception as e:
                                                                print(f"❌ Error sending PDF: {e}")
                                                                send_text_message(recipient_number, "❌ Failed to send receipt. Please try again or contact support.")
                                                                return False

                                                        # Unified PDF generator
                                                        def generate_unified_receipt_pdf(project_id, receipt_type, config):
                                                            """Generate PDF receipt for any type"""
                                                            try:
                                                                from weasyprint import HTML
                                                                import io
                                                                from datetime import datetime

                                                                with get_db() as (cursor, connection):
                                                                    # Build dynamic SQL based on whether receipt has due date
                                                                    if config['has_due_date']:
                                                                        cursor.execute(f"""
                                                                            SELECT id, clientname, clientaddress, clientwanumber, clientemail,
                                                                                projectname, projectlocation, projectdescription, projectadministratorname,
                                                                                {config['amount_field']}, {config['due_date_field']}, {config['date_field']}
                                                                            FROM connectlinkdatabase WHERE id = %s
                                                                        """, (project_id,))
                                                                    else:
                                                                        cursor.execute(f"""
                                                                            SELECT id, clientname, clientaddress, clientwanumber, clientemail,
                                                                                projectname, projectlocation, projectdescription, projectadministratorname,
                                                                                {config['amount_field']}, {config['date_field']}
                                                                            FROM connectlinkdatabase WHERE id = %s
                                                                        """, (project_id,))
                                                                    
                                                                    row = cursor.fetchone()
                                                                    if not row:
                                                                        return None

                                                                    # Fetch company info
                                                                    cursor.execute("SELECT * FROM connectlinkdetails;")
                                                                    details = cursor.fetchall()
                                                                    company = details[0] if details else {}

                                                                    # Get logo
                                                                    logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'web-logo.png')
                                                                    with open(logo_path, 'rb') as img:
                                                                        logo_base64 = base64.b64encode(img.read()).decode('utf-8')

                                                                    # Format amount with standard US/UK thousands separator
                                                                    amount = row[9]  # amount field is always at index 9
                                                                    try:
                                                                        formatted_amount = f"{float(amount):,.2f}"
                                                                    except Exception:
                                                                        formatted_amount = '0.00'
                                                                    # For compatibility with templates that use whole/decimal
                                                                    if '.' in formatted_amount:
                                                                        formatted_whole, decimal = formatted_amount.split('.')
                                                                    else:
                                                                        formatted_whole, decimal = formatted_amount, '00'

                                                                    # Format dates
                                                                    if config['has_due_date']:
                                                                        due_date = row[10]
                                                                        due_date_str = due_date.strftime('%d %b %Y') if due_date else '—'
                                                                        due_date_long = due_date.strftime('%d %B %Y') if due_date else '—'
                                                                        paid_date = row[11]
                                                                        paid_date_idx = 11
                                                                    else:
                                                                        paid_date = row[10]
                                                                        paid_date_idx = 10
                                                                    
                                                                    paid_date_str = paid_date.strftime('%d %b %Y') if paid_date else '—'
                                                                    paid_date_long = paid_date.strftime('%d %B %Y') if paid_date else '—'

                                                                    # Choose template based on receipt type
                                                                    if receipt_type == 'deposit':
                                                                        html = generate_deposit_template(
                                                                            row, logo_base64, formatted_whole, decimal, 
                                                                            formatted_amount, paid_date_str, paid_date_long,
                                                                            config['watermark'], config['title']
                                                                        )
                                                                    else:
                                                                        html = generate_installment_template(
                                                                            row, logo_base64, formatted_whole, decimal,
                                                                            formatted_amount, due_date_str, due_date_long,
                                                                            paid_date_str, paid_date_long, config['watermark'],
                                                                            config['title']
                                                                        )

                                                                    # Generate PDF
                                                                    pdf = HTML(string=html).write_pdf()
                                                                    return pdf

                                                            except Exception as e:
                                                                print(f"❌ PDF generation error: {str(e)}")
                                                                return None

                                                        def generate_deposit_template(row, logo_base64, whole, decimal, formatted_amount, 
                                                                                    paid_date_str, paid_date_long, watermark, title):
                                                            """Generate HTML for deposit receipt"""
                                                            return f"""
                                                            <!DOCTYPE html>
                                                            <html>
                                                            <head>
                                                                <meta charset="UTF-8">
                                                                <style>
                                                                    @page {{ size: A5; margin: 5mm; }}
                                                                    body {{ font-family: 'Helvetica', sans-serif; font-size: 10px; }}
                                                                    .receipt-container {{ border: 1px solid #d0d0d0; padding: 15px; min-height: 680px; }}
                                                                    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1E2A56; }}
                                                                    .logo {{ width: 180px; }}
                                                                    .receipt-title h5 {{ color: #1E2A56; font-size: 16px; }}
                                                                    .payment-summary {{ background: #fafbfd; border: 1px solid #e8e8e8; border-radius: 4px; padding: 15px; }}
                                                                    .payment-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; text-align: center; }}
                                                                    .payment-amount {{ font-size: 18px; font-weight: 600; color: #1E2A56; }}
                                                                    .amount-whole {{ font-size: 18px; color: #1E2A56; }}
                                                                    .amount-decimal {{ font-size: 10px; color: #999; vertical-align: super; }}
                                                                    .status-paid {{ background: #27ae60; color: white; padding: 3px 10px; border-radius: 12px; }}
                                                                    .section {{ border: 1px solid #e8e8e8; border-radius: 4px; margin-bottom: 15px; }}
                                                                    .section-header {{ background: #f5f7fa; padding: 8px; font-weight: 600; color: #1E2A56; }}
                                                                    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
                                                                    .info-row {{ display: flex; margin-bottom: 6px; }}
                                                                    .info-label {{ width: 70px; color: #666; }}
                                                                    .footer {{ margin-top: 25px; text-align: center; color: #999; font-size: 8px; }}
                                                                </style>
                                                            </head>
                                                            <body>
                                                                <div class="receipt-container">
                                                                    <div class="header">
                                                                        <img src="data:image/png;base64,{logo_base64}" class="logo">
                                                                        <div class="receipt-title">
                                                                            <h5>{title.upper()} RECEIPT</h5>
                                                                            <div>REF: CON-{row[0]}-{watermark}</div>
                                                                        </div>
                                                                    </div>

                                                                    <div class="payment-summary">
                                                                        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                                                            <span class="status-paid">PAID</span>
                                                                            <span>Transaction ID: TRX-{row[0]}-DEP</span>
                                                                        </div>
                                                                        <div class="payment-grid">
                                                                            <div class="payment-item">
                                                                                <div class="payment-label">Amount</div>
                                                                                <div class="payment-amount">
                                                                                    USD <span class="amount-whole">{whole}</span>.<span class="amount-decimal">{decimal}</span>
                                                                                </div>
                                                                            </div>
                                                                            <div class="payment-item">
                                                                                <div class="payment-label">Date Paid</div>
                                                                                <div class="payment-date">{paid_date_str}</div>
                                                                            </div>
                                                                        </div>
                                                                    </div>

                                                                    <div class="section">
                                                                        <div class="section-header">CLIENT INFORMATION</div>
                                                                        <div class="section-content">
                                                                            <div class="grid-2">
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Name:</span><span>{row[1]}</span></div>
                                                                                    <div class="info-row"><span class="info-label">Address:</span><span>{row[2]}</span></div>
                                                                                </div>
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Contact:</span><span>0{row[3]}</span></div>
                                                                                    <div class="info-row"><span class="info-label">Email:</span><span>{row[4]}</span></div>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    </div>

                                                                    <div class="section">
                                                                        <div class="section-header">PROJECT INFORMATION</div>
                                                                        <div class="section-content">
                                                                            <div class="grid-2">
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Project:</span><span>{row[5]}</span></div>
                                                                                    <div class="info-row"><span class="info-label">Location:</span><span>{row[6]}</span></div>
                                                                                </div>
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Scope:</span><span>{row[7]}</span></div>
                                                                                    <div class="info-row"><span class="info-label">Admin:</span><span>{row[8]}</span></div>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    </div>

                                                                    <div class="section">
                                                                        <div class="section-header">PAYMENT DETAILS</div>
                                                                        <div class="section-content">
                                                                            <div class="grid-2">
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Payment:</span><span>{title}</span></div>
                                                                                    <div class="info-row"><span class="info-label">Amount:</span><span>USD {formatted_amount}</span></div>
                                                                                </div>
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Date Paid:</span><span>{paid_date_long}</span></div>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    </div>

                                                                    <div class="footer">
                                                                        <div>Official receipt from ConnectLink Properties</div>
                                                                        <div>info@connectlinkproperties.co.zw | +263 773368558</div>
                                                                        <div>Generated: {datetime.now().strftime('%d %B %Y at %H:%M')}</div>
                                                                    </div>
                                                                </div>
                                                            </body>
                                                            </html>
                                                            """

                                                        def generate_installment_template(row, logo_base64, whole, decimal, formatted_amount,
                                                                                        due_date_str, due_date_long, paid_date_str, paid_date_long,
                                                                                        watermark, title):
                                                            """Generate HTML for installment receipt"""
                                                            return f"""
                                                            <!DOCTYPE html>
                                                            <html>
                                                            <head>
                                                                <meta charset="UTF-8">
                                                                <style>
                                                                    @page {{ size: A5; margin: 5mm; }}
                                                                    body {{ font-family: 'Helvetica', sans-serif; font-size: 10px; }}
                                                                    .receipt-container {{ border: 1px solid #d0d0d0; padding: 15px; min-height: 680px; }}
                                                                    .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1E2A56; }}
                                                                    .logo {{ width: 180px; }}
                                                                    .receipt-title h5 {{ color: #1E2A56; font-size: 16px; }}
                                                                    .payment-summary {{ background: #fafbfd; border: 1px solid #e8e8e8; border-radius: 4px; padding: 15px; }}
                                                                    .payment-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; text-align: center; }}
                                                                    .payment-amount {{ font-size: 18px; font-weight: 600; color: #1E2A56; }}
                                                                    .amount-whole {{ font-size: 18px; color: #1E2A56; }}
                                                                    .amount-decimal {{ font-size: 10px; color: #999; vertical-align: super; }}
                                                                    .status-paid {{ background: #27ae60; color: white; padding: 3px 10px; border-radius: 12px; }}
                                                                    .section {{ border: 1px solid #e8e8e8; border-radius: 4px; margin-bottom: 15px; }}
                                                                    .section-header {{ background: #f5f7fa; padding: 8px; font-weight: 600; color: #1E2A56; }}
                                                                    .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
                                                                    .info-row {{ display: flex; margin-bottom: 6px; }}
                                                                    .info-label {{ width: 70px; color: #666; }}
                                                                    .footer {{ margin-top: 25px; text-align: center; color: #999; font-size: 8px; }}
                                                                </style>
                                                            </head>
                                                            <body>
                                                                <div class="receipt-container">
                                                                    <div class="header">
                                                                        <img src="data:image/png;base64,{logo_base64}" class="logo">
                                                                        <div class="receipt-title">
                                                                            <h5>{title.upper()} RECEIPT</h5>
                                                                            <div>REF: CON-{row[0]}-{watermark}</div>
                                                                        </div>
                                                                    </div>

                                                                    <div class="payment-summary">
                                                                        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                                                            <span class="status-paid">PAID</span>
                                                                            <span>Transaction ID: TRX-{row[0]}-INST</span>
                                                                        </div>
                                                                        <div class="payment-grid">
                                                                            <div class="payment-item">
                                                                                <div class="payment-label">Amount</div>
                                                                                <div class="payment-amount">
                                                                                    USD <span class="amount-whole">{whole}</span>.<span class="amount-decimal">{decimal}</span>
                                                                                </div>
                                                                            </div>
                                                                            <div class="payment-item">
                                                                                <div class="payment-label">Due Date</div>
                                                                                <div class="payment-date">{due_date_str}</div>
                                                                            </div>
                                                                            <div class="payment-item">
                                                                                <div class="payment-label">Paid Date</div>
                                                                                <div class="payment-date">{paid_date_str}</div>
                                                                            </div>
                                                                        </div>
                                                                    </div>

                                                                    <div class="section">
                                                                        <div class="section-header">CLIENT INFORMATION</div>
                                                                        <div class="section-content">
                                                                            <div class="grid-2">
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Name:</span><span>{row[1]}</span></div>
                                                                                    <div class="info-row"><span class="info-label">Address:</span><span>{row[2]}</span></div>
                                                                                </div>
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Contact:</span><span>0{row[3]}</span></div>
                                                                                    <div class="info-row"><span class="info-label">Email:</span><span>{row[4]}</span></div>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    </div>

                                                                    <div class="section">
                                                                        <div class="section-header">PROJECT INFORMATION</div>
                                                                        <div class="section-content">
                                                                            <div class="grid-2">
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Project:</span><span>{row[5]}</span></div>
                                                                                    <div class="info-row"><span class="info-label">Location:</span><span>{row[6]}</span></div>
                                                                                </div>
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Scope:</span><span>{row[7]}</span></div>
                                                                                    <div class="info-row"><span class="info-label">Admin:</span><span>{row[8]}</span></div>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    </div>

                                                                    <div class="section">
                                                                        <div class="section-header">PAYMENT DETAILS</div>
                                                                        <div class="section-content">
                                                                            <div class="grid-2">
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Installment:</span><span>{title}</span></div>
                                                                                    <div class="info-row"><span class="info-label">Amount:</span><span>USD {formatted_amount}</span></div>
                                                                                </div>
                                                                                <div>
                                                                                    <div class="info-row"><span class="info-label">Due Date:</span><span>{due_date_long}</span></div>
                                                                                    <div class="info-row"><span class="info-label">Paid Date:</span><span>{paid_date_long}</span></div>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    </div>

                                                                    <div class="footer">
                                                                        <div>Official receipt from ConnectLink Properties</div>
                                                                        <div>info@connectlinkproperties.co.zw | +263 773368558</div>
                                                                        <div>Generated: {datetime.now().strftime('%d %B %Y at %H:%M')}</div>
                                                                    </div>
                                                                </div>
                                                            </body>
                                                            </html>
                                                            """

                                                        # Keep your existing send_text_message function
                                                        def send_text_message(to_number, text):
                                                            """Send simple text message via WhatsApp"""
                                                            url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                            
                                                            headers = {
                                                                'Authorization': f'Bearer {ACCESS_TOKEN}',
                                                                'Content-Type': 'application/json'
                                                            }
                                                            
                                                            data = {
                                                                "messaging_product": "whatsapp",
                                                                "recipient_type": "individual",
                                                                "to": to_number,
                                                                "type": "text",
                                                                "text": {
                                                                    "body": text
                                                                }
                                                            }
                                                            
                                                            try:
                                                                response = requests.post(url, headers=headers, json=data, timeout=30)
                                                                return response.json()
                                                            except Exception as e:
                                                                print(f"❌ Text message error: {str(e)}")
                                                                return None
                                                        
                                                        button = message.get("button", {})
                                                        interactive_button_reply = message.get("interactive", {}).get("button_reply", {})
                                                        button_text = button.get("text", "") or interactive_button_reply.get("title", "")
                                                        payload = button.get("payload", "") or interactive_button_reply.get("id", "")
                                                        
                                                        print(f"🔘 Template button clicked: {button_text}")
                                                        print(f"📦 Button payload: {payload}")
                                                        
                                                        # Find which receipt type this payload matches
                                                        matched_type = None
                                                        project_id = None
                                                        
                                                        for receipt_type, config in RECEIPT_CONFIG.items():
                                                            if payload and payload.startswith(config['payload_prefix']):
                                                                matched_type = receipt_type
                                                                project_id = payload.replace(config['payload_prefix'], '')
                                                                break
                                                        
                                                        normalized_button_text = (button_text or "").strip().lower()

                                                        if payload and payload.lower().startswith('enquiry_attachment_'):
                                                            try:
                                                                enquiry_id = int(payload.split('_')[-1])
                                                            except (IndexError, ValueError):
                                                                enquiry_id = None

                                                            if enquiry_id:
                                                                send_text_message(sender_id, "⏳ Fetching the enquiry attachment, please wait...")
                                                                # ADD THIS: Small delay before processing
                                                                time.sleep(1)  # Critical for mobile
                                                                
                                                                # Now deliver the attachment
                                                                try:
                                                                    result = deliver_enquiry_attachment_pdf(enquiry_id, sender_id, send_text_message)
                                                                    if not result:
                                                                        send_whatsapp_message(sender_id, "❌ Could not retrieve the attachment. Please contact support.")
                                                                except Exception as e:
                                                                    print(f"❌ Error delivering attachment: {e}")
                                                                    send_whatsapp_message(sender_id, "❌ An error occurred. Please try again or contact support.")

                                                                return jsonify({"status": "received"}), 200
                                                            else:
                                                                send_text_message(sender_id, "❌ Invalid enquiry attachment reference.")
                                                                return jsonify({"status": "received"}), 200

                                                        elif normalized_button_text == 'download attachment':
                                                            enquiry_id = resolve_enquiry_attachment_id_from_click(message, sender_id)

                                                            if enquiry_id:
                                                                send_text_message(sender_id, "⏳ Fetching the enquiry attachment, please wait...")
                                                                time.sleep(1)  # Critical for mobile
                                                                
                                                                # Now deliver the attachment
                                                                try:
                                                                    result = deliver_enquiry_attachment_pdf(enquiry_id, sender_id, send_text_message)
                                                                    if not result:
                                                                        send_whatsapp_message(sender_id, "❌ Could not retrieve the attachment. Please contact support.")
                                                                except Exception as e:
                                                                    print(f"❌ Error delivering attachment: {e}")
                                                                    send_whatsapp_message(sender_id, "❌ An error occurred. Please try again or contact support.")

                                                                return jsonify({"status": "received"}), 200
                                                            
                                                            else:
                                                                send_text_message(sender_id, "❌ No enquiry attachment is available to download.")
                                                                return jsonify({"status": "received"}), 200

                                                        elif payload and payload.lower().startswith('quotation_'):
                                                            # Template quick-reply: "Download Quotation" button
                                                            # Payload format: quotation_{id}_{random} or just quotation_{id}
                                                            try:
                                                                parts = payload.split('_')
                                                                qid = int(parts[1])
                                                            except (IndexError, ValueError):
                                                                qid = None

                                                            if qid:
                                                                mark_quotation_download_clicked(payload, sender_id)
                                                                deliver_shared_quotation_pdf(payload, qid, sender_id, send_text_message)
                                                                return jsonify({"status": "received"}), 200
                                                            else:
                                                                print("❌ Invalid quotation reference in button payload.")
                                                                return jsonify({"status": "received"}), 200

                                                        elif payload and payload.lower().startswith('contract_'):
                                                            # Template quick-reply: "Download Contract Agreement" button
                                                            try:
                                                                parts = payload.split('_')
                                                                contract_project_id = int(parts[1])
                                                            except (IndexError, ValueError):
                                                                contract_project_id = None

                                                            if contract_project_id:
                                                                print(f"📋 Contract download requested for project #{contract_project_id}")
                                                                # Generate and send contract PDF
                                                                try:
                                                                    with app.test_client() as client:
                                                                        resp = client.get(f'/download_contract/{contract_project_id}')
                                                                        if resp.status_code == 200:
                                                                            pdf_bytes = resp.data
                                                                            safe_name = f"Contract_{contract_project_id}"
                                                                            filename = f"Contract_{contract_project_id}.pdf"
                                                                            caption = f"CONTRACT AGREEMENT\n\nConnectLink Properties"
                                                                            send_pdf_document_whatsapp(sender_id, pdf_bytes, filename, caption)
                                                                            print(f"✅ Contract {contract_project_id} sent to {sender_id}")
                                                                        else:
                                                                            raise ValueError(f"Contract generation failed: {resp.status_code}")
                                                                except Exception as ce:
                                                                    print(f"❌ Error sending contract {contract_project_id}: {ce}")
                                                                    # Fallback: send download URL
                                                                    contract_url = get_contract_download_url(contract_project_id)
                                                                    if contract_url:
                                                                        send_text_message(sender_id, f"📋 Open your contract here:\n{contract_url}")
                                                                    else:
                                                                        send_text_message(sender_id, "❌ Could not generate contract. Please contact ConnectLink.")
                                                            else:
                                                                print("❌ Invalid contract reference in button payload.")
                                                            return jsonify({"status": "received"}), 200

                                                        elif matched_type and project_id:
                                                            config = RECEIPT_CONFIG[matched_type]
                                                            print(f"🎯 Extracted project_id: {project_id} for {config['title']}")
                                                            
                                                            # Send processing message
                                                            send_text_message(sender_id, config['processing_message'])
                                                            
                                                            # Send PDF receipt
                                                            send_receipt_via_whatsapp(sender_id, project_id, matched_type, config)
                                                        else:
                                                            print(f"❌ Unknown payload: {payload}")



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

                                                        if message.get("type") == "interactive" and not (
                                                            message.get("interactive", {}).get("type") == "button_reply"
                                                            and (
                                                                (message.get("interactive", {}).get("button_reply", {}).get("id", "") or "").lower().startswith("quotation_")
                                                                or (message.get("interactive", {}).get("button_reply", {}).get("id", "") or "").lower().startswith("enquiry_attachment_")
                                                                or (message.get("interactive", {}).get("button_reply", {}).get("title", "") or "").strip().lower() == "download attachment"
                                                            )
                                                        ):
                                                            interactive = message.get("interactive", {})


                                                            if interactive.get("type") == "list_reply":
                                                                selected_option = interactive.get("list_reply", {}).get("id")
                                                                print(f"📋 User selected: {selected_option}")
                                                                button_id = ""

                                                            elif interactive.get("type") == "button_reply":
                                                                button_id = interactive.get("button_reply", {}).get("id")
                                                                print(f"🔘 Button clicked: {button_id}")
                                                                selected_option = ""

                                                            # Log button/list interaction for analytics
                                                            if button_id:
                                                                log_chatbot_interaction(sender_id, profile_name or 'Client', 'button_click', button_id, button_id)
                                                            if selected_option:
                                                                log_chatbot_interaction(sender_id, profile_name or 'Client', 'list_select', selected_option, selected_option)

                                                            # Keyword matching for text messages from clients
                                                            if not button_id and not selected_option and message_type == "text":
                                                                kw_match = resolve_chatbot_keyword(msg_text)
                                                                if kw_match:
                                                                    keyword, handler_id = kw_match
                                                                    print(f"🔑 Client keyword match: '{keyword}' → handler: {handler_id}")
                                                                    log_chatbot_interaction(sender_id, profile_name or 'Client', 'keyword', keyword, handler_id)
                                                                    if handler_id in ('contracts', 'my contracts'):
                                                                        button_id = 'contracts'
                                                                    elif handler_id in ('paymenthist', 'payments_schedule', 'payments', 'payment history'):
                                                                        button_id = 'paymenthist'
                                                                    elif handler_id == 'enquiries':
                                                                        button_id = 'enquiries'
                                                                    elif handler_id == 'main_menu':
                                                                        button_id = 'main_menu'

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
                                                                cursor.execute(query, (f"%{sender_id}",))
                                                                resultenqtemp = cursor.fetchone()

                                                                enquiry_type = resultenqtemp[2]

                                                                if enquiry_type:

                                                                    query = """
                                                                        DELETE FROM appenqtemp
                                                                        WHERE wanumber::TEXT LIKE %s
                                                                    """
                                                                    cursor.execute(query, (f"%{sender_id}",))
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
                                                                    client_whatsapp = int(sender_id) 

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

                                                                    
                                                                    def send_admin_notification(admin_number, client_whatsapp, enquiry_data):
                                                                        url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
                                                                        
                                                                        headers = {
                                                                            'Authorization': f'Bearer {ACCESS_TOKEN}',
                                                                            'Content-Type': 'application/json'
                                                                        }
                                                                        
                                                                        # Clean client WhatsApp number and create wa.me link
                                                                        wa_link = f"https://wa.me/+{sender_id}"
                                                                        
                                                                        # Format timestamp
                                                                        timestamp_param = enquiry_data.get('timestamp', datetime.now())
                                                                        if isinstance(timestamp_param, datetime):
                                                                            timestamp_str = timestamp_param.strftime('%d %B %Y %H:%M')
                                                                        else:
                                                                            timestamp_str = str(timestamp_param)

                                                                        has_attachment_value = str(enquiry_data.get('has_attachment', '')).strip().lower()
                                                                        use_attachment_template = has_attachment_value == 'yes'

                                                                        # ALWAYS send enqauto2 first (it works)
                                                                        template_name = "enqauto2"
                                                                        components = [
                                                                            {
                                                                                "type": "body",
                                                                                "parameters": [
                                                                                    {"type": "text", "text": f"#{enquiry_data.get('enquiry_id')}"},
                                                                                    {"type": "text", "text": f"+{sender_id}"},
                                                                                    {"type": "text", "text": timestamp_str},
                                                                                    {"type": "text", "text": enquiry_data.get('enquiry_type_display', 'General')},
                                                                                    {"type": "text", "text": enquiry_data.get('user_message', 'No additional details')},
                                                                                    {"type": "text", "text": enquiry_data.get('has_attachment')}
                                                                                ]
                                                                            }
                                                                        ]

                                                                        payload = {
                                                                            "messaging_product": "whatsapp",
                                                                            "recipient_type": "individual",
                                                                            "to": admin_number,
                                                                            "type": "template",
                                                                            "template": {
                                                                                "name": template_name,
                                                                                "language": {"code": "en"},
                                                                                "components": components
                                                                            }
                                                                        }

                                                                        # Send enqauto2
                                                                        response = requests.post(url, headers=headers, json=payload)
                                                                        response_data = response.json()

                                                                        # If there's an attachment, ALSO send enquiryattachment (even without variables)
                                                                        if use_attachment_template:
                                                                            attachment_payload = {
                                                                                "messaging_product": "whatsapp",
                                                                                "recipient_type": "individual",
                                                                                "to": admin_number,
                                                                                "type": "template",
                                                                                "template": {
                                                                                    "name": "enquiryattachment",
                                                                                    "language": {"code": "en"}
                                                                                    # NO components array because it has no variables!
                                                                                }
                                                                            }
                                                                            
                                                                            attachment_response = requests.post(url, headers=headers, json=attachment_payload)
                                                                            print(f"✅ enquiryattachment sent: {attachment_response.status_code}")

                                                                        if isinstance(response_data, dict) and response_data.get('error'):
                                                                            error_data = response_data.get('error', {})
                                                                            error_details = str((error_data.get('error_data') or {}).get('details', '')).lower()

                                                                            if use_attachment_template:
                                                                                print(f"❌ enquiryattachment template failed for admin {admin_number}: {response_data}")
                                                                                try:
                                                                                    fallback_sent = deliver_enquiry_attachment_pdf(
                                                                                        enquiry_data.get('enquiry_id'),
                                                                                        admin_number,
                                                                                        send_text_message=None
                                                                                    )
                                                                                    if fallback_sent:
                                                                                        response_data = {
                                                                                            "messages": [{"id": f"attachment_fallback_{enquiry_data.get('enquiry_id')}"}],
                                                                                            "fallback": "direct_attachment_pdf"
                                                                                        }
                                                                                        print("✅ Attachment sent via direct PDF fallback")
                                                                                except Exception as fallback_exc:
                                                                                    print(f"❌ Direct attachment fallback failed: {fallback_exc}")
                                                                            else:
                                                                                # Some approved versions of enqauto2 include a button component.
                                                                                # Retry with common button variants when Meta reports component mismatch.
                                                                                if error_data.get('code') == 132000 or 'button' in error_details:
                                                                                    fallback_component_sets = [
                                                                                        components + [{
                                                                                            "type": "button",
                                                                                            "sub_type": "quick_reply",
                                                                                            "index": 0,
                                                                                            "parameters": [
                                                                                                {"type": "payload", "payload": f"contact_client_{enquiry_data.get('enquiry_id')}"}
                                                                                            ]
                                                                                        }],
                                                                                        components + [{
                                                                                            "type": "button",
                                                                                            "sub_type": "url",
                                                                                            "index": 0,
                                                                                            "parameters": [
                                                                                                {"type": "text", "text": wa_link}
                                                                                            ]
                                                                                        }],
                                                                                        components + [{
                                                                                            "type": "button",
                                                                                            "sub_type": "quick_reply",
                                                                                            "index": 0,
                                                                                            "parameters": [
                                                                                                {"type": "text", "text": wa_link}
                                                                                            ]
                                                                                        }]
                                                                                    ]

                                                                                    for fallback_components in fallback_component_sets:
                                                                                        fallback_payload = {
                                                                                            "messaging_product": "whatsapp",
                                                                                            "recipient_type": "individual",
                                                                                            "to": admin_number,
                                                                                            "type": "template",
                                                                                            "template": {
                                                                                                "name": template_name,
                                                                                                "language": {"code": "en"},
                                                                                                "components": fallback_components
                                                                                            }
                                                                                        }
                                                                                        fallback_response = requests.post(url, headers=headers, json=fallback_payload)
                                                                                        fallback_data = fallback_response.json()
                                                                                        if isinstance(fallback_data, dict) and not fallback_data.get('error'):
                                                                                            print("✅ enqauto2 sent after fallback with button component")
                                                                                            response_data = fallback_data
                                                                                            break

                                                                        if use_attachment_template:
                                                                            message_id = ((response_data.get('messages') or [{}])[0]).get('id') if isinstance(response_data, dict) else None
                                                                            if message_id:
                                                                                log_enquiry_attachment_button_message(
                                                                                    message_id,
                                                                                    enquiry_data.get('enquiry_id'),
                                                                                    admin_number
                                                                                )

                                                                        return response_data

                                                                    # Usage
                                                                    admin_numbers = ["263774822568", "263773368558", "263777665277"]
                                                                    #
                                                                    client_whatsapp = sender_id

                                                                    for admin_number in admin_numbers:
                                                                        print(f"✅ Notifying admin: {admin_number}")
                                                                        
                                                                        enquiry_data = {
                                                                            'enquiry_id': enquiry_id,
                                                                            'user_message': user_message,
                                                                            'enquiry_type_display': enquiry_type_display,
                                                                            'has_attachment': 'Yes' if has_attachment else 'No',
                                                                            'timestamp': datetime.now()
                                                                        }
                                                                        
                                                                        result = send_admin_notification(admin_number, client_whatsapp, enquiry_data)
                                                                        print(f"Response: {result}")
                                                                        
                                                                    
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

                                                                    query = f"""
                                                                        SELECT * FROM appenqtemp
                                                                        WHERE wanumber::TEXT LIKE %s
                                                                    """
                                                                    cursor.execute(query, (f"%{sender_id}",))
                                                                    resultenqtemp = cursor.fetchone()

                                                                    if resultenqtemp:

                                                                        query = """
                                                                            DELETE FROM appenqtemp
                                                                            WHERE wanumber::TEXT LIKE %s
                                                                        """
                                                                        cursor.execute(query, (f"%{sender_id}",))
                                                                        connection.commit()

                                                                    insert_query = """
                                                                        INSERT INTO appenqtemp 
                                                                        (wanumber, enqtype)
                                                                        VALUES (%s, %s)
                                                                        RETURNING id;
                                                                    """
                                                                    
                                                                    digits = "".join(filter(str.isdigit, sender_id))
                                                                    client_whatsapp = int(digits)
                                                                    
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
                                                                        "- Minimum deposit: 30%\n"
                                                                        "- Balance payable over 3–6 months\n\n"
                                                                        "Our project turnaround times are:\n"
                                                                        "- 90 days (standard foundation)\n"
                                                                        "- 110 days (special foundation)\n"
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
                                                                
                                                                # Save to whatsapp_messages for chat UI
                                                                try:
                                                                    with get_db() as (save_cursor, save_conn):
                                                                        save_cursor.execute("""
                                                                            INSERT INTO whatsapp_messages 
                                                                            (sender_phone, sender_name, message_text, message_type, direction, status)
                                                                            VALUES (%s, %s, %s, %s, 'outgoing', 'sent')
                                                                        """, (sender_id, 'ConnectLink Bot', '[Template: enquiries] Enquiry form sent', 'template'))
                                                                        save_conn.commit()
                                                                except Exception as save_err:
                                                                    print(f"⚠️ Failed to save enquiry template to messages: {save_err}")

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
                                                                            'payment_method': row[18] if len(row) > 18 else '',
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
                                                                            'installment7amount': row[47] if len(row) > 47 else None,
                                                                            'installment7duedate': row[48].strftime("%-d %B %Y") if len(row) > 48 and row[48] else None,
                                                                            'installment8amount': row[50] if len(row) > 50 else None,
                                                                            'installment8duedate': row[51].strftime("%-d %B %Y") if len(row) > 51 and row[51] else None,
                                                                            'installment9amount': row[53] if len(row) > 53 else None,
                                                                            'installment9duedate': row[54].strftime("%-d %B %Y") if len(row) > 54 and row[54] else None,
                                                                            'installment10amount': row[56] if len(row) > 56 else None,
                                                                            'installment10duedate': row[57].strftime("%-d %B %Y") if len(row) > 57 and row[57] else None,
                                                                            'latepaymentinterest': row[45] if len(row) > 45 else None,
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

                                                                                ol {{
                                                                                    list-style-type: none; /* Remove default numbers */
                                                                                    counter-reset: item; /* Create a counter for top level */
                                                                                    padding-left: 0;
                                                                                }}

                                                                                ol > li {{
                                                                                    counter-increment: item; /* Increment top level */
                                                                                    margin-bottom: 10px;
                                                                                }}

                                                                                /* Target top-level list items that contain nested lists */
                                                                                ol > li::before {{
                                                                                    content: counter(item) ". "; /* Adds "1. ", "2. " etc */
                                                                                    font-weight: bold;
                                                                                    margin-right: 5px;
                                                                                }}

                                                                                /* Style for the nested lists (Second level) */
                                                                                ol ol {{
                                                                                    counter-reset: subitem; /* Reset counter for sub-items */
                                                                                    margin-top: 5px;
                                                                                    margin-left: 30px; /* Indent the whole sub-list */
                                                                                    list-style-type: none;
                                                                                }}

                                                                                ol ol > li {{
                                                                                    counter-increment: subitem; /* Increment sub-item */
                                                                                    margin-bottom: 5px;
                                                                                }}

                                                                                ol ol > li::before {{
                                                                                    content: counter(item) "." counter(subitem) ". "; /* Generates "1.1", "1.2" etc */
                                                                                    margin-right: 5px;
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
                                                                                <div class="field-row"><div class="field-label">Payment Method:</div><div class="field-value" style="font-weight: 700; color: #1E2A56;">{project.get('payment_method', '')}</div></div>

                                                                                {'' if str(project.get('payment_method', '')).strip() == 'Once Off Payment' else f'''
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
                                                                                        <tr><td>{project['installment7duedate']}</td><td style="font-weight: 700;">{project['installment7amount']}</td></tr>
                                                                                        <tr><td>{project['installment8duedate']}</td><td style="font-weight: 700;">{project['installment8amount']}</td></tr>
                                                                                        <tr><td>{project['installment9duedate']}</td><td style="font-weight: 700;">{project['installment9amount']}</td></tr>
                                                                                        <tr><td>{project['installment10duedate']}</td><td style="font-weight: 700;">{project['installment10amount']}</td></tr>
                                                                                    </tbody>
                                                                                </table>
                                                                                '''}
                                                                                
                                                                                <!-- Page break -->
                                                                                <div class="page-break"></div>
                                                                                
                                                                                <!-- Page 3 -->

                                                                                <h4 class="section-title">TERMS AND CONDITIONS</h4>

                                                                                <div class="section-header">PAYMENT TERMS</div>
                                                                                <div class="terms-box">
                                                                                    <ul style="list-style-type: circle;">
                                                                                        <li>The Client shall pay the Contract Price in accordance with the agreed payment schedule.</li>
                                                                                        <li>All payments shall be made in United States Dollars (USD) unless otherwise agreed in writing.</li>
                                                                                        <li>Any amount not paid on the due date shall attract mora interest at a rate of <strong>{project['latepaymentinterest']}%</strong> per annum above the prevailing Reserve Bank of Zimbabwe lending rate, calculated daily and compounded monthly from the due date until full payment.</li>
                                                                                        <li>Interest shall accrue automatically without the need for formal demand.</li>
                                                                                        <li>All payments received shall first be applied to accrued interest, then legal costs (if any), and thereafter to the principal sum.</li>
                                                                                        <li>In the event of default exceeding 14 days, the Contractor reserves the right to suspend works upon written notice until payment is regularized.</li>
                                                                                    </ul>
                                                                                </div>
                                                                                
                                                                                <div class="section-header">PROJECT TIMELINE</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>The Contractor shall commence work within <strong>{project['days_difference']} days</strong> of;
                                                                                            <ol>
                                                                                                <li>Receipt of the agreed initial deposit payment and;</li> 
                                                                                                <li>Provision of site access by the Client.</li>
                                                                                            </ol>
                                                                                        </li>
                                                                                        <li>The Contractor shall complete the project within <strong>{project['project_duration']} calender days</strong> from the commencement date.</li>
                                                                                        <li>The completion period shall be extended where delays are caused by;
                                                                                            <ol>
                                                                                                <li>Variations requested by the Client;</li>
                                                                                                <li>Late payments;</li>
                                                                                                <li>Failure by the Client to obtain statutory approvals;</li>
                                                                                                <li>Force majeure events;</li>
                                                                                                <li>Shortage of materials beyond the Contractor's reasonable control.</li>
                                                                                            </ol>
                                                                                        </li>
                                                                                        <li>The Client is responsible for obtaining all required permits and approvals from local authorities.</li>
                                                                                        <li>The Contractor is responsible for all materials, labor, and workmanship as per industry standards.</li>
                                                                                    </ol>
                                                                                </div>
                                                                                
                                                                                <div class="section-header">SITE SECURITY</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>The Client shall ensure reasonable site security, including secure access control.</li>
                                                                                        <li>The Contractor shall not be liable for theft, vandalism, or damage occurring on site unless caused by its proven negligence.</li>
                                                                                    </ol>
                                                                                </div> 

                                                                                <div class="section-header">ACCOMMODATION PROVISION</div>
                                                                                <div class="terms-box">
                                                                                    <p style="font-size:11px;">The Client shall provide suitable accommodation for the Contractor's personnel at the project site for kitchen and cabinets projects.</p>
                                                                                </div>

                                                                                <!-- Page break -->
                                                                                <div class="page-break"></div>
                                                                                
                                                                                <!-- Page 4 -->

                                                                                <h4 class="section-title">TERMS AND CONDITIONS</h4>

                                                                                <div class="section-header">FORCE MAJEURE</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>Neither party shall be liable for delay or failure to perform obligations caused by events beyond their reasonable control, including but not limited to:
                                                                                            <ol>
                                                                                                <li>Acts of God;</li>
                                                                                                <li>War, civil unrest, or government restrictions;</li>
                                                                                                <li>Utility failures or prolonged load shedding;</li>
                                                                                                <li>Material shortages;</li>
                                                                                                <li>Currency instability rendering procurement of materials commercially impracticable despite reasonable mitigation efforts.</li>
                                                                                            </ol>
                                                                                        </li>
                                                                                        <li>The affected party shall notify the other in writing within a reasonable time.</li>
                                                                                        <li>Time for performance shall be extended for the duration of the force majeure event.</li>
                                                                                    </ol>
                                                                                </div>

                                                                                <div class="section-header">DESIGN CONFIRMATION AND VARIATIONS</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>Signing of this Agreement and payment of the deposit shall constitute acknowledgment and approval of the submitted design</li>
                                                                                        <li>No variation or alteration shall be valid unless:
                                                                                            <ul>
                                                                                                <li>Requested in writing;</li>
                                                                                                <li>Costed by the Contractor; and</li>
                                                                                                <li>Approved in writing by both parties.</li>
                                                                                            </ul>
                                                                                        </li>
                                                                                        <li>Approved variations shall:
                                                                                            <ol>`
                                                                                                <li>Be treated as Change Orders;</li>
                                                                                                <li>Adjust the Contract Price accordingly; and</li>
                                                                                                <li>Extend the completion period where necessary.</li>
                                                                                            </ol>
                                                                                        </li>
                                                                                        <li>The Contractor shall not be obliged to proceed with any variation until written approval and payment of any required adjustment is received.</li>
                                                                                    </ol>
                                                                                </div>

                                                                                <div class="section-header">TRANSPORT PROVISION</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>Transport within a 20-kilometre radius of Harare Central Business District is included in the Contract Price.</li>
                                                                                        <li>Thereafter, transport shall be charged at USD 0.50 per kilometre, calculated from Harare CBD to site and return.</li>
                                                                                        <li>Transport charges shall be invoiced monthly and payable within seven (7) days.</li>
                                                                                    </ol>
                                                                                </div>


                                                                                <!-- Page break -->
                                                                                <div class="page-break"></div>
                                                                                
                                                                                <!-- Page 5 -->

                                                                                <h4 class="section-title">TERMS AND CONDITIONS</h4>

                                                                                <div class="section-header">OWNERSHIP AND RETENTION OF TITLE</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>Ownership of all materials, goods, and installed items shall remain vested in <strong>ConnectLink Properties</strong> until full and final payment of the Contract Price.</li>
                                                                                        <li>Where materials have been incorporated into the works and cannot be removed without material damage, the Contractor shall retain a contractual right to claim the value thereof.</li>
                                                                                        <li>The Client shall not alienate, encumber, pledge, or dispose of unpaid materials prior to full settlement.</li>
                                                                                        <li>In the event of payment default, the Contractor shall be entitled to approach a competent court of Zimbabwe for:
                                                                                            <ol>
                                                                                                <li>An order authorizing repossession; or</li>
                                                                                                <li>Recovery of the outstanding balance together with interest and costs.</li>
                                                                                            </ol>
                                                                                        </li>
                                                                                        <li>Nothing in this clause shall permit unlawful self-help repossession.</li>
                                                                                    </ol>
                                                                                </div>

                                                                                <div class="section-header">DEFECTS LIABILITY</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>The Contractor warrants workmanship for a period of six (6) months from the date of practical completion. Practical Completion shall mean the stage at which the works are substantially complete and capable of beneficial occupation or use, save for minor defects not materially affecting functionality.</li>
                                                                                        <li>The warranty shall not apply to:
                                                                                            <ol>
                                                                                                <li>Normal wear and tear;</li>
                                                                                                <li>Misuse or negligence by the Client;</li>
                                                                                                <li>Structural defects not attributable to the Contractor;</li>
                                                                                                <li>Materials supplied by the Client.</li>
                                                                                            </ol>
                                                                                        </li>
                                                                                        <li>The Contractor's liability shall be limited to repair or replacement of defective workmanship only.</li>
                                                                                        <li>Nothing in this clause excludes liability for latent defects arising from gross negligence or wilful misconduct.</li>
                                                                                    </ol>
                                                                                </div>

                                                                                <div class="section-header">POWER PROVISION</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>Where electrical power is required and unavailable due to load shedding or power outages, the Client shall provide a suitable generator and fuel at their own cost unless otherwise agreed in writing.</li>
                                                                                        <li>Delays arising from power unavailability shall extend the completion period.</li>
                                                                                    </ol>
                                                                                </div>

                                                                                <div class="section-header">WATER PROVISION</div>
                                                                                <div class="terms-box">
                                                                                    <p style="font-size:11px;">The Client shall provide water or a suitable water supply and water storage tank(s) of at least 5000 liters for construction activities at their own expense.</p>
                                                                                </div>

                                                                                <!-- Page break -->
                                                                                <div class="page-break"></div>
                                                                                
                                                                                <!-- Page 6 -->

                                                                                <h4 class="section-title">TERMS AND CONDITIONS</h4>

                                                                                <div class="section-header">RISK AND INSURANCE</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>The risk in the works, materials, and equipment shall remain with the Contractor until Practical Completion.</li>
                                                                                        <li>Upon Practical Completion, risk shall pass to the Client.</li>
                                                                                        <li>The Client shall be responsible for insuring the works against fire, theft, vandalism, and other insurable risks from the date of Practical Completion.</li>
                                                                                        <li>Unless otherwise agreed in writing, the Contractor shall not be responsible for loss or damage caused by:
                                                                                            <ol>
                                                                                                <li>Civil unrest;</li>
                                                                                                <li>Theft not attributable to Contractor negligence;</li>
                                                                                                <li>Acts of third parties beyond Contractor control;</li>
                                                                                            </ol>
                                                                                        </li>
                                                                                        <li>The Contractor's liability shall be limited to repair or replacement of defective workmanship only.</li>
                                                                                        <li>Nothing in this clause excludes liability for latent defects arising from gross negligence or wilful misconduct.</li>
                                                                                    </ol>
                                                                                </div>

                                                                                <div class="section-header">LIMITATION OF LIABILITY</div>
                                                                                <div class="terms-box">
                                                                                    <p style="font-size:11px;">The Contractor's total liability arising from this Agreement shall not exceed the total Contract Price, except in cases of gross negligence or wilful misconduct.</p>
                                                                                </div>

                                                                                <div class="section-header">INDEMNITY CLAUSE</div>
                                                                                <div class="terms-box">
                                                                                    <p style="font-size:11px;">ConnectLink Properties will not be liable against claims or damages arising from injuries to the Client's personnel on site.</p>
                                                                                </div>

                                                                                <div class="section-header">TERMINATION</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>Either party may terminate this Agreement if the other:
                                                                                            <ol>
                                                                                                <li>Commits a material breach and fails to remedy such breach within fourteen (14) days of written notice;</li>
                                                                                                <li>Becomes insolvent in terms of the Insolvency Act [Chapter 6:07];</li>
                                                                                                <li>Is placed under liquidation or judicial management.</li>
                                                                                            </ol>
                                                                                        </li>
                                                                                        <li>Upon termination:
                                                                                            <ol>
                                                                                                <li>The Client shall pay for all work completed and materials ordered up to the date of termination;</li>
                                                                                                <li>Deposits shall be refundable only after deduction of costs incurred;</li>
                                                                                                <li>The Contractor may suspend further works immediately.</li>
                                                                                            </ol>
                                                                                        </li>
                                                                                        <li>Termination shall not prejudice accrued rights, including the right to claim damages.</li>
                                                                                    </ol>
                                                                                </div>

                                                                                <!-- Page break -->
                                                                                <div class="page-break"></div>
                                                                                
                                                                                <!-- Page 5 -->

                                                                                <h4 class="section-title">TERMS AND CONDITIONS</h4>



                                                                                <div class="section-header">DISPUTE RESOLUTION</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>The parties shall first attempt amicable resolution within fourteen (14) days.</li>
                                                                                        <li>Failing resolution, the dispute shall be referred to arbitration in Harare in terms of the Arbitration Act [Chapter 7:15].</li>
                                                                                        <li>The arbitration shall be conducted by a single arbitrator appointed by mutual agreement, failing which the arbitrator shall be appointed by the Commercial Arbitration Centre of Zimbabwe.</li>
                                                                                        <li>The arbitration award shall be final and binding.</li>
                                                                                        <li>The courts of Zimbabwe shall retain jurisdiction solely for purposes of enforcing the arbitral award.</li>
                                                                                    </ol>
                                                                                </div>

                                                                                <div class="section-header">GOVERNING LAW</div>
                                                                                <div class="terms-box">
                                                                                    <p style="font-size:11px;">This Agreement shall be governed by and construed in accordance with the laws of Zimbabwe.</p>
                                                                                </div>

                                                                                <div class="section-header">NOTICES</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>Any notice required in terms of this Agreement shall be in writing.</li>
                                                                                        <li>Notices shall be delivered::
                                                                                            <ul>
                                                                                                <li>By hand (with signed acknowledgment of receipt);</li>
                                                                                                <li>By registered mail;</li>
                                                                                                <li>By courier; or</li>
                                                                                                <li>By email to the designated address of the receiving party.</li>
                                                                                            </ul>
                                                                                        </li>
                                                                                        <li>Notices sent by email shall be deemed received on the date of transmission, provided no delivery failure notification is received.</li>
                                                                                    </ol>
                                                                                </div>

                                                                                <div class="section-header">ENTIRE AGREEMENT</div>
                                                                                <div class="terms-box">
                                                                                    <ol>
                                                                                        <li>This document constitutes the entire agreement between the parties and supersedes all prior negotiations or representations.</li>
                                                                                        <li>No amendment or variation shall be valid unless reduced to writing and signed by both parties.</li>
                                                                                    </ol>
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
                                                                    # Check if human mode is enabled for this recipient
                                                                    try:
                                                                        to_digits = re.sub(r'[^0-9]', '', str(recipient_number))
                                                                        cursor.execute("""
                                                                            SELECT human_mode FROM chat_human_mode 
                                                                            WHERE sender_phone = %s 
                                                                               OR RIGHT(sender_phone, 9) = RIGHT(%s, 9)
                                                                        """, (recipient_number, to_digits))
                                                                        row = cursor.fetchone()
                                                                        if row and row[0]:
                                                                            print(f"🚫 Human mode ON for {recipient_number} — skipping chatbot auto-reply")
                                                                            return True
                                                                    except Exception as e:
                                                                        print(f"⚠️ Human mode check error: {e}")
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
                                                                        
                                                                        # Save to whatsapp_messages for chat portal visibility
                                                                        if response.status_code == 200:
                                                                            try:
                                                                                with get_db() as (save_cursor, save_conn):
                                                                                    save_cursor.execute("""
                                                                                        INSERT INTO whatsapp_messages 
                                                                                        (sender_phone, sender_name, message_text, message_type, direction, status)
                                                                                        VALUES (%s, %s, %s, 'text', 'outgoing', 'sent')
                                                                                    """, (recipient_number, 'ConnectLink Bot', message[:500]))
                                                                                    save_conn.commit()
                                                                            except Exception as save_err:
                                                                                print(f"⚠️ Failed to save bot message: {save_err}")
                                                                        
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

                                                        elif (
                                                            message_type == "button"
                                                            or (
                                                                message_type == "interactive"
                                                                and message.get("interactive", {}).get("type") == "button_reply"
                                                            )
                                                        ):

                                                            # Unified function to send any receipt via WhatsApp
                                                            def send_receipt_via_whatsapp(recipient_number, project_id, receipt_type, config):
                                                                """Send any receipt PDF via WhatsApp"""
                                                                try:
                                                                    import io
                                                                    from weasyprint import HTML
                                                                    
                                                                    # Generate PDF
                                                                    pdf_bytes = generate_unified_receipt_pdf(project_id, receipt_type, config)
                                                                    if not pdf_bytes:
                                                                        print(f"❌ Failed to generate PDF for project {project_id}")
                                                                        send_text_message(recipient_number, "❌ Error generating receipt. Please contact support.")
                                                                        return False
                                                                    
                                                                    # Get project details for filename and caption
                                                                    with get_db() as (cursor, connection):
                                                                        cursor.execute(f"""
                                                                            SELECT clientname, projectname, {config['amount_field']}, {config['date_field']}
                                                                            FROM connectlinkdatabase WHERE id = %s
                                                                        """, (project_id,))
                                                                        row = cursor.fetchone()
                                                                        
                                                                        if row:
                                                                            client_name, project_name, amount, date_paid = row
                                                                            # Sanitize client name for filename (remove spaces, special chars)
                                                                            safe_client_name = ''.join(c for c in client_name if c.isalnum() or c == ' ').replace(' ', '_')
                                                                            filename = f"{config['filename_prefix']}_{safe_client_name}_{project_id}.pdf"
                                                                            
                                                                            date_str = date_paid.strftime('%d %B %Y') if date_paid else '—'
                                                                            
                                                                            caption = f"""📄 *{config['title'].upper()} RECEIPT*

                                                            Client: {client_name}
                                                            Project: {project_name}
                                                            Amount: USD {amount if amount else '0'}
                                                            Date: {date_str}

                                                            Send 'Hello' to view your contracts or to log enquiries."""
                                                                        else:
                                                                            filename = f"{config['filename_prefix']}_{project_id}.pdf"
                                                                            caption = f"📄 {config['title']} Receipt - Project {project_id}"
                                                                    
                                                                    print(f"📤 Uploading PDF to WhatsApp...")
                                                                    
                                                                    # Upload to WhatsApp
                                                                    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/media"
                                                                    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
                                                                    
                                                                    files = {
                                                                        "file": (filename, io.BytesIO(pdf_bytes), "application/pdf"),
                                                                        "type": (None, "application/pdf"),
                                                                        "messaging_product": (None, "whatsapp")
                                                                    }
                                                                    
                                                                    response = requests.post(url, headers=headers, files=files, timeout=30)
                                                                    response.raise_for_status()
                                                                    media_id = response.json()["id"]
                                                                    
                                                                    print(f"✅ Media uploaded, ID: {media_id}")
                                                                    
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
                                                                    
                                                                    print(f"📤 Sending document to {recipient_number}...")
                                                                    response = requests.post(doc_url, headers=doc_headers, json=doc_payload, timeout=30)
                                                                    response.raise_for_status()
                                                                    
                                                                    print(f"✅ PDF sent successfully!")
                                                                    return True
                                                                    
                                                                except Exception as e:
                                                                    print(f"❌ Error sending PDF: {e}")
                                                                    send_text_message(recipient_number, "❌ Failed to send receipt. Please try again or contact support.")
                                                                    return False

                                                            # Unified PDF generator
                                                            def generate_unified_receipt_pdf(project_id, receipt_type, config):
                                                                """Generate PDF receipt for any type"""
                                                                try:
                                                                    from weasyprint import HTML
                                                                    import io
                                                                    from datetime import datetime

                                                                    with get_db() as (cursor, connection):
                                                                        # Build dynamic SQL based on whether receipt has due date
                                                                        if config['has_due_date']:
                                                                            cursor.execute(f"""
                                                                                SELECT id, clientname, clientaddress, clientwanumber, clientemail,
                                                                                    projectname, projectlocation, projectdescription, projectadministratorname,
                                                                                    {config['amount_field']}, {config['due_date_field']}, {config['date_field']}
                                                                                FROM connectlinkdatabase WHERE id = %s
                                                                            """, (project_id,))
                                                                        else:
                                                                            cursor.execute(f"""
                                                                                SELECT id, clientname, clientaddress, clientwanumber, clientemail,
                                                                                    projectname, projectlocation, projectdescription, projectadministratorname,
                                                                                    {config['amount_field']}, {config['date_field']}
                                                                                FROM connectlinkdatabase WHERE id = %s
                                                                            """, (project_id,))
                                                                        
                                                                        row = cursor.fetchone()
                                                                        if not row:
                                                                            return None

                                                                        # Fetch company info
                                                                        cursor.execute("SELECT * FROM connectlinkdetails;")
                                                                        details = cursor.fetchall()
                                                                        company = details[0] if details else {}

                                                                        # Get logo
                                                                        logo_path = os.path.join(os.path.dirname(__file__), 'static', 'images', 'web-logo.png')
                                                                        with open(logo_path, 'rb') as img:
                                                                            logo_base64 = base64.b64encode(img.read()).decode('utf-8')

                                                                        # Format amount with standard US/UK thousands separator
                                                                        amount = row[9]  # amount field is always at index 9
                                                                        try:
                                                                            formatted_amount = f"{float(amount):,.2f}"
                                                                        except Exception:
                                                                            formatted_amount = '0.00'
                                                                        # For compatibility with templates that use whole/decimal
                                                                        if '.' in formatted_amount:
                                                                            formatted_whole, decimal = formatted_amount.split('.')
                                                                        else:
                                                                            formatted_whole, decimal = formatted_amount, '00'

                                                                        # Format dates
                                                                        if config['has_due_date']:
                                                                            due_date = row[10]
                                                                            due_date_str = due_date.strftime('%d %b %Y') if due_date else '—'
                                                                            due_date_long = due_date.strftime('%d %B %Y') if due_date else '—'
                                                                            paid_date = row[11]
                                                                            paid_date_idx = 11
                                                                        else:
                                                                            paid_date = row[10]
                                                                            paid_date_idx = 10
                                                                        
                                                                        paid_date_str = paid_date.strftime('%d %b %Y') if paid_date else '—'
                                                                        paid_date_long = paid_date.strftime('%d %B %Y') if paid_date else '—'

                                                                        # Choose template based on receipt type
                                                                        if receipt_type == 'deposit':
                                                                            html = generate_deposit_template(
                                                                                row, logo_base64, formatted_whole, decimal, 
                                                                                formatted_amount, paid_date_str, paid_date_long,
                                                                                config['watermark'], config['title']
                                                                            )
                                                                        else:
                                                                            html = generate_installment_template(
                                                                                row, logo_base64, formatted_whole, decimal,
                                                                                formatted_amount, due_date_str, due_date_long,
                                                                                paid_date_str, paid_date_long, config['watermark'],
                                                                                config['title']
                                                                            )

                                                                        # Generate PDF
                                                                        pdf = HTML(string=html).write_pdf()
                                                                        return pdf

                                                                except Exception as e:
                                                                    print(f"❌ PDF generation error: {str(e)}")
                                                                    return None

                                                            def generate_deposit_template(row, logo_base64, whole, decimal, formatted_amount, 
                                                                                        paid_date_str, paid_date_long, watermark, title):
                                                                """Generate HTML for deposit receipt"""
                                                                return f"""
                                                                <!DOCTYPE html>
                                                                <html>
                                                                <head>
                                                                    <meta charset="UTF-8">
                                                                    <style>
                                                                        @page {{ size: A5; margin: 5mm; }}
                                                                        body {{ font-family: 'Helvetica', sans-serif; font-size: 10px; }}
                                                                        .receipt-container {{ border: 1px solid #d0d0d0; padding: 15px; min-height: 680px; }}
                                                                        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1E2A56; }}
                                                                        .logo {{ width: 180px; }}
                                                                        .receipt-title h5 {{ color: #1E2A56; font-size: 16px; }}
                                                                        .payment-summary {{ background: #fafbfd; border: 1px solid #e8e8e8; border-radius: 4px; padding: 15px; }}
                                                                        .payment-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; text-align: center; }}
                                                                        .payment-amount {{ font-size: 18px; font-weight: 600; color: #1E2A56; }}
                                                                        .amount-whole {{ font-size: 18px; color: #1E2A56; }}
                                                                        .amount-decimal {{ font-size: 10px; color: #999; vertical-align: super; }}
                                                                        .status-paid {{ background: #27ae60; color: white; padding: 3px 10px; border-radius: 12px; }}
                                                                        .section {{ border: 1px solid #e8e8e8; border-radius: 4px; margin-bottom: 15px; }}
                                                                        .section-header {{ background: #f5f7fa; padding: 8px; font-weight: 600; color: #1E2A56; }}
                                                                        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
                                                                        .info-row {{ display: flex; margin-bottom: 6px; }}
                                                                        .info-label {{ width: 70px; color: #666; }}
                                                                        .footer {{ margin-top: 25px; text-align: center; color: #999; font-size: 8px; }}
                                                                    </style>
                                                                </head>
                                                                <body>
                                                                    <div class="receipt-container">
                                                                        <div class="header">
                                                                            <img src="data:image/png;base64,{logo_base64}" class="logo">
                                                                            <div class="receipt-title">
                                                                                <h5>{title.upper()} RECEIPT</h5>
                                                                                <div>REF: CON-{row[0]}-{watermark}</div>
                                                                            </div>
                                                                        </div>

                                                                        <div class="payment-summary">
                                                                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                                                                <span class="status-paid">PAID</span>
                                                                                <span>Transaction ID: TRX-{row[0]}-DEP</span>
                                                                            </div>
                                                                            <div class="payment-grid">
                                                                                <div class="payment-item">
                                                                                    <div class="payment-label">Amount</div>
                                                                                    <div class="payment-amount">
                                                                                        USD <span class="amount-whole">{whole}</span>.<span class="amount-decimal">{decimal}</span>
                                                                                    </div>
                                                                                </div>
                                                                                <div class="payment-item">
                                                                                    <div class="payment-label">Date Paid</div>
                                                                                    <div class="payment-date">{paid_date_str}</div>
                                                                                </div>
                                                                            </div>
                                                                        </div>

                                                                        <div class="section">
                                                                            <div class="section-header">CLIENT INFORMATION</div>
                                                                            <div class="section-content">
                                                                                <div class="grid-2">
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Name:</span><span>{row[1]}</span></div>
                                                                                        <div class="info-row"><span class="info-label">Address:</span><span>{row[2]}</span></div>
                                                                                    </div>
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Contact:</span><span>0{row[3]}</span></div>
                                                                                        <div class="info-row"><span class="info-label">Email:</span><span>{row[4]}</span></div>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        </div>

                                                                        <div class="section">
                                                                            <div class="section-header">PROJECT INFORMATION</div>
                                                                            <div class="section-content">
                                                                                <div class="grid-2">
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Project:</span><span>{row[5]}</span></div>
                                                                                        <div class="info-row"><span class="info-label">Location:</span><span>{row[6]}</span></div>
                                                                                    </div>
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Scope:</span><span>{row[7]}</span></div>
                                                                                        <div class="info-row"><span class="info-label">Admin:</span><span>{row[8]}</span></div>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        </div>

                                                                        <div class="section">
                                                                            <div class="section-header">PAYMENT DETAILS</div>
                                                                            <div class="section-content">
                                                                                <div class="grid-2">
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Payment:</span><span>{title}</span></div>
                                                                                        <div class="info-row"><span class="info-label">Amount:</span><span>USD {formatted_amount}</span></div>
                                                                                    </div>
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Date Paid:</span><span>{paid_date_long}</span></div>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        </div>

                                                                        <div class="footer">
                                                                            <div>Official receipt from ConnectLink Properties</div>
                                                                            <div>info@connectlinkproperties.co.zw | +263 773368558</div>
                                                                            <div>Generated: {datetime.now().strftime('%d %B %Y at %H:%M')}</div>
                                                                        </div>
                                                                    </div>
                                                                </body>
                                                                </html>
                                                                """

                                                            def generate_installment_template(row, logo_base64, whole, decimal, formatted_amount,
                                                                                            due_date_str, due_date_long, paid_date_str, paid_date_long,
                                                                                            watermark, title):
                                                                """Generate HTML for installment receipt"""
                                                                return f"""
                                                                <!DOCTYPE html>
                                                                <html>
                                                                <head>
                                                                    <meta charset="UTF-8">
                                                                    <style>
                                                                        @page {{ size: A5; margin: 5mm; }}
                                                                        body {{ font-family: 'Helvetica', sans-serif; font-size: 10px; }}
                                                                        .receipt-container {{ border: 1px solid #d0d0d0; padding: 15px; min-height: 680px; }}
                                                                        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 2px solid #1E2A56; }}
                                                                        .logo {{ width: 180px; }}
                                                                        .receipt-title h5 {{ color: #1E2A56; font-size: 16px; }}
                                                                        .payment-summary {{ background: #fafbfd; border: 1px solid #e8e8e8; border-radius: 4px; padding: 15px; }}
                                                                        .payment-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; text-align: center; }}
                                                                        .payment-amount {{ font-size: 18px; font-weight: 600; color: #1E2A56; }}
                                                                        .amount-whole {{ font-size: 18px; color: #1E2A56; }}
                                                                        .amount-decimal {{ font-size: 10px; color: #999; vertical-align: super; }}
                                                                        .status-paid {{ background: #27ae60; color: white; padding: 3px 10px; border-radius: 12px; }}
                                                                        .section {{ border: 1px solid #e8e8e8; border-radius: 4px; margin-bottom: 15px; }}
                                                                        .section-header {{ background: #f5f7fa; padding: 8px; font-weight: 600; color: #1E2A56; }}
                                                                        .grid-2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }}
                                                                        .info-row {{ display: flex; margin-bottom: 6px; }}
                                                                        .info-label {{ width: 70px; color: #666; }}
                                                                        .footer {{ margin-top: 25px; text-align: center; color: #999; font-size: 8px; }}
                                                                    </style>
                                                                </head>
                                                                <body>
                                                                    <div class="receipt-container">
                                                                        <div class="header">
                                                                            <img src="data:image/png;base64,{logo_base64}" class="logo">
                                                                            <div class="receipt-title">
                                                                                <h5>{title.upper()} RECEIPT</h5>
                                                                                <div>REF: CON-{row[0]}-{watermark}</div>
                                                                            </div>
                                                                        </div>

                                                                        <div class="payment-summary">
                                                                            <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                                                                                <span class="status-paid">PAID</span>
                                                                                <span>Transaction ID: TRX-{row[0]}-INST</span>
                                                                            </div>
                                                                            <div class="payment-grid">
                                                                                <div class="payment-item">
                                                                                    <div class="payment-label">Amount</div>
                                                                                    <div class="payment-amount">
                                                                                        USD <span class="amount-whole">{whole}</span>.<span class="amount-decimal">{decimal}</span>
                                                                                    </div>
                                                                                </div>
                                                                                <div class="payment-item">
                                                                                    <div class="payment-label">Due Date</div>
                                                                                    <div class="payment-date">{due_date_str}</div>
                                                                                </div>
                                                                                <div class="payment-item">
                                                                                    <div class="payment-label">Paid Date</div>
                                                                                    <div class="payment-date">{paid_date_str}</div>
                                                                                </div>
                                                                            </div>
                                                                        </div>

                                                                        <div class="section">
                                                                            <div class="section-header">CLIENT INFORMATION</div>
                                                                            <div class="section-content">
                                                                                <div class="grid-2">
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Name:</span><span>{row[1]}</span></div>
                                                                                        <div class="info-row"><span class="info-label">Address:</span><span>{row[2]}</span></div>
                                                                                    </div>
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Contact:</span><span>0{row[3]}</span></div>
                                                                                        <div class="info-row"><span class="info-label">Email:</span><span>{row[4]}</span></div>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        </div>

                                                                        <div class="section">
                                                                            <div class="section-header">PROJECT INFORMATION</div>
                                                                            <div class="section-content">
                                                                                <div class="grid-2">
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Project:</span><span>{row[5]}</span></div>
                                                                                        <div class="info-row"><span class="info-label">Location:</span><span>{row[6]}</span></div>
                                                                                    </div>
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Scope:</span><span>{row[7]}</span></div>
                                                                                        <div class="info-row"><span class="info-label">Admin:</span><span>{row[8]}</span></div>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        </div>

                                                                        <div class="section">
                                                                            <div class="section-header">PAYMENT DETAILS</div>
                                                                            <div class="section-content">
                                                                                <div class="grid-2">
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Installment:</span><span>{title}</span></div>
                                                                                        <div class="info-row"><span class="info-label">Amount:</span><span>USD {formatted_amount}</span></div>
                                                                                    </div>
                                                                                    <div>
                                                                                        <div class="info-row"><span class="info-label">Due Date:</span><span>{due_date_long}</span></div>
                                                                                        <div class="info-row"><span class="info-label">Paid Date:</span><span>{paid_date_long}</span></div>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        </div>

                                                                        <div class="footer">
                                                                            <div>Official receipt from ConnectLink Properties</div>
                                                                            <div>info@connectlinkproperties.co.zw | +263 773368558</div>
                                                                            <div>Generated: {datetime.now().strftime('%d %B %Y at %H:%M')}</div>
                                                                        </div>
                                                                    </div>
                                                                </body>
                                                                </html>
                                                                """

                                                            # Keep your existing send_text_message function
                                                            def send_text_message(to_number, text):
                                                                """Send simple text message via WhatsApp"""
                                                                url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
                                                                
                                                                headers = {
                                                                    'Authorization': f'Bearer {ACCESS_TOKEN}',
                                                                    'Content-Type': 'application/json'
                                                                }
                                                                
                                                                data = {
                                                                    "messaging_product": "whatsapp",
                                                                    "recipient_type": "individual",
                                                                    "to": to_number,
                                                                    "type": "text",
                                                                    "text": {
                                                                        "body": text
                                                                    }
                                                                }
                                                                
                                                                try:
                                                                    response = requests.post(url, headers=headers, json=data, timeout=30)
                                                                    return response.json()
                                                                except Exception as e:
                                                                    print(f"❌ Text message error: {str(e)}")
                                                                    return None


                                                            button = message.get("button", {})
                                                            interactive_button_reply = message.get("interactive", {}).get("button_reply", {})
                                                            button_text = button.get("text", "") or interactive_button_reply.get("title", "")
                                                            payload = button.get("payload", "") or interactive_button_reply.get("id", "")
                                                            
                                                            print(f"🔘 Template button clicked: {button_text}")
                                                            print(f"📦 Button payload: {payload}")
                                                            
                                                            # Find which receipt type this payload matches
                                                            matched_type = None
                                                            project_id = None
                                                            
                                                            for receipt_type, config in RECEIPT_CONFIG.items():
                                                                if payload and payload.startswith(config['payload_prefix']):
                                                                    matched_type = receipt_type
                                                                    project_id = payload.replace(config['payload_prefix'], '')
                                                                    break
                                                            
                                                            normalized_button_text = (button_text or "").strip().lower()

                                                            if payload and payload.lower().startswith('enquiry_attachment_'):
                                                                try:
                                                                    enquiry_id = int(payload.split('_')[-1])
                                                                except (IndexError, ValueError):
                                                                    enquiry_id = None

                                                                if enquiry_id:
                                                                    send_text_message(sender_id, "⏳ Fetching the enquiry attachment, please wait...")
                                                                    time.sleep(1)  # Critical for mobile
                                                                    
                                                                    # Now deliver the attachment
                                                                    try:
                                                                        result = deliver_enquiry_attachment_pdf(enquiry_id, sender_id, send_text_message)
                                                                        if not result:
                                                                            send_whatsapp_message(sender_id, "❌ Could not retrieve the attachment. Please contact support.")
                                                                    except Exception as e:
                                                                        print(f"❌ Error delivering attachment: {e}")
                                                                        send_whatsapp_message(sender_id, "❌ An error occurred. Please try again or contact support.")

                                                                    continue
                                                                else:
                                                                    send_text_message(sender_id, "❌ Invalid enquiry attachment reference.")
                                                                    continue

                                                            elif normalized_button_text == 'download attachment':
                                                                enquiry_id = resolve_enquiry_attachment_id_from_click(message, sender_id)

                                                                if enquiry_id:
                                                                    send_text_message(sender_id, "⏳ Fetching the enquiry attachment, please wait...")
                                                                    time.sleep(1)  # Critical for mobile
                                                                    
                                                                    # Now deliver the attachment
                                                                    try:
                                                                        result = deliver_enquiry_attachment_pdf(enquiry_id, sender_id, send_text_message)
                                                                        if not result:
                                                                            send_whatsapp_message(sender_id, "❌ Could not retrieve the attachment. Please contact support.")
                                                                    except Exception as e:
                                                                        print(f"❌ Error delivering attachment: {e}")
                                                                        send_whatsapp_message(sender_id, "❌ An error occurred. Please try again or contact support.")

                                                                    continue
                                                                else:
                                                                    send_text_message(sender_id, "❌ No enquiry attachment is available to download.")
                                                                    continue

                                                            elif payload and payload.lower().startswith('quotation_'):
                                                                try:
                                                                    parts = payload.split('_')
                                                                    qid = int(parts[1])
                                                                except (IndexError, ValueError):
                                                                    qid = None

                                                                if qid:
                                                                    mark_quotation_download_clicked(payload, sender_id)
                                                                    send_text_message(sender_id, "⏳ Generating your quotation PDF, please wait...")
                                                                    deliver_shared_quotation_pdf(payload, qid, sender_id, send_text_message)
                                                                    continue
                                                                else:
                                                                    send_text_message(sender_id, "❌ Invalid quotation reference.")
                                                                    continue

                                                            elif matched_type and project_id:
                                                                config = RECEIPT_CONFIG[matched_type]
                                                                print(f"🎯 Extracted project_id: {project_id} for {config['title']}")
                                                                
                                                                # Send processing message
                                                                send_text_message(sender_id, config['processing_message'])
                                                                
                                                                # Send PDF receipt
                                                                send_receipt_via_whatsapp(sender_id, project_id, matched_type, config)
                                                            else:
                                                                print(f"❌ Unknown payload: {payload}")



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
                                                    
                                                        if message.get("type") == "interactive" and not (
                                                            message.get("interactive", {}).get("type") == "button_reply"
                                                            and (
                                                                (message.get("interactive", {}).get("button_reply", {}).get("id", "") or "").lower().startswith("quotation_")
                                                                or (message.get("interactive", {}).get("button_reply", {}).get("id", "") or "").lower().startswith("enquiry_attachment_")
                                                                or (message.get("interactive", {}).get("button_reply", {}).get("title", "") or "").strip().lower() == "download attachment"
                                                            )
                                                        ):
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
                                                                cursor.execute(query, (f"%{sender_id}",))
                                                                resultenqtemp = cursor.fetchone()

                                                                enquiry_type = resultenqtemp[2]

                                                                if enquiry_type:

                                                                    query = """
                                                                        DELETE FROM appenqtemp
                                                                        WHERE wanumber::TEXT LIKE %s
                                                                    """
                                                                    cursor.execute(query, (f"%{sender_id}",))
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
                                                                    client_whatsapp = int(sender_id)
                                                                    
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

                                                                    
                                                                    def send_admin_notification(admin_number, client_whatsapp, enquiry_data):
                                                                        url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
                                                                        
                                                                        headers = {
                                                                            'Authorization': f'Bearer {ACCESS_TOKEN}',
                                                                            'Content-Type': 'application/json'
                                                                        }
                                                                        
                                                                        # Clean client WhatsApp number and create wa.me link
                                                                        wa_link = f"https://wa.me/+{sender_id}"
                                                                        
                                                                        # Format timestamp
                                                                        timestamp = enquiry_data.get('timestamp', datetime.now())
                                                                        if isinstance(timestamp, datetime):
                                                                            timestamp_str = timestamp.strftime('%d %B %Y %H:%M')
                                                                        else:
                                                                            timestamp_str = str(timestamp)

                                                                        has_attachment_value = str(enquiry_data.get('has_attachment', '')).strip().lower()
                                                                        use_attachment_template = has_attachment_value == 'yes'

                                                                        # ALWAYS send enqauto2 first (it works)
                                                                        template_name = "enqauto2"
                                                                        components = [
                                                                            {
                                                                                "type": "body",
                                                                                "parameters": [
                                                                                    {"type": "text", "text": f"#{enquiry_data.get('enquiry_id')}"},
                                                                                    {"type": "text", "text": f"+{sender_id}"},
                                                                                    {"type": "text", "text": timestamp_str},
                                                                                    {"type": "text", "text": enquiry_data.get('enquiry_type_display', 'General')},
                                                                                    {"type": "text", "text": enquiry_data.get('user_message', 'No additional details')},
                                                                                    {"type": "text", "text": enquiry_data.get('has_attachment')}
                                                                                ]
                                                                            }
                                                                        ]

                                                                        payload = {
                                                                            "messaging_product": "whatsapp",
                                                                            "recipient_type": "individual",
                                                                            "to": admin_number,
                                                                            "type": "template",
                                                                            "template": {
                                                                                "name": template_name,
                                                                                "language": {"code": "en"},
                                                                                "components": components
                                                                            }
                                                                        }

                                                                        # Send enqauto2
                                                                        response = requests.post(url, headers=headers, json=payload)
                                                                        response_data = response.json()

                                                                        # If there's an attachment, ALSO send enquiryattachment (even without variables)
                                                                        if use_attachment_template:
                                                                            attachment_payload = {
                                                                                "messaging_product": "whatsapp",
                                                                                "recipient_type": "individual",
                                                                                "to": admin_number,
                                                                                "type": "template",
                                                                                "template": {
                                                                                    "name": "enquiryattachment",
                                                                                    "language": {"code": "en"}
                                                                                    # NO components array because it has no variables!
                                                                                }
                                                                            }
                                                                            
                                                                            attachment_response = requests.post(url, headers=headers, json=attachment_payload)
                                                                            print(f"✅ enquiryattachment sent: {attachment_response.status_code}")


                                                                        if isinstance(response_data, dict) and response_data.get('error'):
                                                                            error_data = response_data.get('error', {})
                                                                            error_details = str((error_data.get('error_data') or {}).get('details', '')).lower()

                                                                            if use_attachment_template:
                                                                                print(f"❌ enquiryattachment template failed for admin {admin_number}: {response_data}")
                                                                                try:
                                                                                    fallback_sent = deliver_enquiry_attachment_pdf(
                                                                                        enquiry_data.get('enquiry_id'),
                                                                                        admin_number,
                                                                                        send_text_message=None
                                                                                    )
                                                                                    if fallback_sent:
                                                                                        response_data = {
                                                                                            "messages": [{"id": f"attachment_fallback_{enquiry_data.get('enquiry_id')}"}],
                                                                                            "fallback": "direct_attachment_pdf"
                                                                                        }
                                                                                        print("✅ Attachment sent via direct PDF fallback")
                                                                                except Exception as fallback_exc:
                                                                                    print(f"❌ Direct attachment fallback failed: {fallback_exc}")
                                                                            else:
                                                                                # Some approved versions of enqauto2 include a button component.
                                                                                # Retry with common button variants when Meta reports component mismatch.
                                                                                if error_data.get('code') == 132000 or 'button' in error_details:
                                                                                    fallback_component_sets = [
                                                                                        components + [{
                                                                                            "type": "button",
                                                                                            "sub_type": "quick_reply",
                                                                                            "index": 0,
                                                                                            "parameters": [
                                                                                                {"type": "payload", "payload": f"contact_client_{enquiry_data.get('enquiry_id')}"}
                                                                                            ]
                                                                                        }],
                                                                                        components + [{
                                                                                            "type": "button",
                                                                                            "sub_type": "url",
                                                                                            "index": 0,
                                                                                            "parameters": [
                                                                                                {"type": "text", "text": wa_link}
                                                                                            ]
                                                                                        }],
                                                                                        components + [{
                                                                                            "type": "button",
                                                                                            "sub_type": "quick_reply",
                                                                                            "index": 0,
                                                                                            "parameters": [
                                                                                                {"type": "text", "text": wa_link}
                                                                                            ]
                                                                                        }]
                                                                                    ]

                                                                                    for fallback_components in fallback_component_sets:
                                                                                        fallback_payload = {
                                                                                            "messaging_product": "whatsapp",
                                                                                            "recipient_type": "individual",
                                                                                            "to": admin_number,
                                                                                            "type": "template",
                                                                                            "template": {
                                                                                                "name": template_name,
                                                                                                "language": {"code": "en"},
                                                                                                "components": fallback_components
                                                                                            }
                                                                                        }
                                                                                        fallback_response = requests.post(url, headers=headers, json=fallback_payload)
                                                                                        fallback_data = fallback_response.json()
                                                                                        if isinstance(fallback_data, dict) and not fallback_data.get('error'):
                                                                                            print("✅ enqauto2 sent after fallback with button component")
                                                                                            response_data = fallback_data
                                                                                            break

                                                                        if use_attachment_template:
                                                                            message_id = ((response_data.get('messages') or [{}])[0]).get('id') if isinstance(response_data, dict) else None
                                                                            if message_id:
                                                                                log_enquiry_attachment_button_message(
                                                                                    message_id,
                                                                                    enquiry_data.get('enquiry_id'),
                                                                                    admin_number
                                                                                )

                                                                        return response_data

                                                                    # Usage
                                                                    admin_numbers = ["263774822568", "263773368558", "263777665277"]
                                                                    #, "263773368558", "263777665277"
                                                                    client_whatsapp = sender_id

                                                                    for admin_number in admin_numbers:
                                                                        print(f"✅ Notifying admin: {admin_number}")
                                                                        
                                                                        enquiry_data = {
                                                                            'enquiry_id': enquiry_id,
                                                                            'user_message': user_message,
                                                                            'enquiry_type_display': enquiry_type_display,
                                                                            'has_attachment': 'Yes' if has_attachment else 'No',
                                                                            'timestamp': datetime.now()
                                                                        }
                                                                        
                                                                        result = send_admin_notification(admin_number, client_whatsapp, enquiry_data)
                                                                        print(f"Response: {result}")


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

                                                                    query = f"""
                                                                        SELECT * FROM appenqtemp
                                                                        WHERE wanumber::TEXT LIKE %s
                                                                    """
                                                                    cursor.execute(query, (f"%{sender_id}",))
                                                                    resultenqtemp = cursor.fetchone()

                                                                    if resultenqtemp:

                                                                        query = """
                                                                            DELETE FROM appenqtemp
                                                                            WHERE wanumber::TEXT LIKE %s
                                                                        """
                                                                        cursor.execute(query, (f"%{sender_id}",))
                                                                        connection.commit()

                                                                    insert_query = """
                                                                        INSERT INTO appenqtemp 
                                                                        (wanumber, enqtype)
                                                                        VALUES (%s, %s)
                                                                        RETURNING id;
                                                                    """
                                                                    
                                                                    digits = "".join(filter(str.isdigit, sender_id))
                                                                    client_whatsapp = int(digits)
                                                                    
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
                                                                        "- Minimum deposit: 30%\n"
                                                                        "- Balance payable over 3–6 months\n\n"
                                                                        "Our project turnaround times are:\n"
                                                                        "- 90 days (standard foundation)\n"
                                                                        "- 110 days (special foundation)\n"
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

                                                                # Save to whatsapp_messages for chat UI
                                                                try:
                                                                    with get_db() as (save_cursor, save_conn):
                                                                        save_cursor.execute("""
                                                                            INSERT INTO whatsapp_messages 
                                                                            (sender_phone, sender_name, message_text, message_type, direction, status)
                                                                            VALUES (%s, %s, %s, %s, 'outgoing', 'sent')
                                                                        """, (sender_id, 'ConnectLink Bot', '[Template: enquiries] Enquiry form sent', 'template'))
                                                                        save_conn.commit()
                                                                except Exception as save_err:
                                                                    print(f"⚠️ Failed to save enquiry template to messages: {save_err}")

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

                                                                # Save to whatsapp_messages for chat UI
                                                                try:
                                                                    with get_db() as (save_cursor, save_conn):
                                                                        save_cursor.execute("""
                                                                            INSERT INTO whatsapp_messages 
                                                                            (sender_phone, sender_name, message_text, message_type, direction, status)
                                                                            VALUES (%s, %s, %s, %s, 'outgoing', 'sent')
                                                                        """, (sender_id, 'ConnectLink Bot', '[Template: enquiries] Enquiry form sent (enquirylogx)', 'template'))
                                                                        save_conn.commit()
                                                                except Exception as save_err:
                                                                    print(f"⚠️ Failed to save enquiry template to messages: {save_err}")

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
                                                            

                                                        elif (
                                                            message_type == "button"
                                                            or (
                                                                message_type == "interactive"
                                                                and message.get("interactive", {}).get("type") == "button_reply"
                                                            )
                                                        ):

                                                            button = message.get("button", {})
                                                            interactive_button_reply = message.get("interactive", {}).get("button_reply", {})
                                                            button_text = button.get("text", "") or interactive_button_reply.get("title", "")
                                                            payload = button.get("payload", "") or interactive_button_reply.get("id", "")

                                                            print(f"🔘 Template button clicked: {button_text}")
                                                            print(f"📦 Button payload: {payload}")

                                                            def send_text_message(to_number, text):
                                                                """Send simple text message via WhatsApp"""
                                                                url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"

                                                                headers = {
                                                                    'Authorization': f'Bearer {ACCESS_TOKEN}',
                                                                    'Content-Type': 'application/json'
                                                                }

                                                                data = {
                                                                    "messaging_product": "whatsapp",
                                                                    "recipient_type": "individual",
                                                                    "to": to_number,
                                                                    "type": "text",
                                                                    "text": {
                                                                        "body": text
                                                                    }
                                                                }

                                                                try:
                                                                    response = requests.post(url, headers=headers, json=data, timeout=30)
                                                                    return response.json()
                                                                except Exception as e:
                                                                    print(f"❌ Text message error: {str(e)}")
                                                                    return None

                                                            normalized_button_text = (button_text or "").strip().lower()

                                                            if payload and payload.lower().startswith('enquiry_attachment_'):
                                                                try:
                                                                    enquiry_id = int(payload.split('_')[-1])
                                                                except (IndexError, ValueError):
                                                                    enquiry_id = None

                                                                if enquiry_id:
                                                                    send_text_message(sender_id, "⏳ Fetching the enquiry attachment, please wait...")
                                                                    time.sleep(1)  # Critical for mobile
                                                                    
                                                                    # Now deliver the attachment
                                                                    try:
                                                                        result = deliver_enquiry_attachment_pdf(enquiry_id, sender_id, send_text_message)
                                                                        if not result:
                                                                            send_whatsapp_message(sender_id, "❌ Could not retrieve the attachment. Please contact support.")
                                                                    except Exception as e:
                                                                        print(f"❌ Error delivering attachment: {e}")
                                                                        send_whatsapp_message(sender_id, "❌ An error occurred. Please try again or contact support.")
                                                                        
                                                                    continue
                                                                else:
                                                                    send_text_message(sender_id, "❌ Invalid enquiry attachment reference.")
                                                                    continue

                                                            elif normalized_button_text == 'download attachment':
                                                                enquiry_id = resolve_enquiry_attachment_id_from_click(message, sender_id)

                                                                if enquiry_id:
                                                                    send_text_message(sender_id, "⏳ Fetching the enquiry attachment, please wait...")
                                                                    time.sleep(1)  # Critical for mobile
                                                                    
                                                                    # Now deliver the attachment
                                                                    try:
                                                                        result = deliver_enquiry_attachment_pdf(enquiry_id, sender_id, send_text_message)
                                                                        if not result:
                                                                            send_whatsapp_message(sender_id, "❌ Could not retrieve the attachment. Please contact support.")
                                                                    except Exception as e:
                                                                        print(f"❌ Error delivering attachment: {e}")
                                                                        send_whatsapp_message(sender_id, "❌ An error occurred. Please try again or contact support.")
                                                                        
                                                                    continue
                                                                else:
                                                                    send_text_message(sender_id, "❌ No enquiry attachment is available to download.")
                                                                    continue

                                                            elif payload and payload.lower().startswith('quotation_'):
                                                                try:
                                                                    parts = payload.split('_')
                                                                    qid = int(parts[1])
                                                                except (IndexError, ValueError):
                                                                    qid = None

                                                                if qid:
                                                                    mark_quotation_download_clicked(payload, sender_id)
                                                                    send_text_message(sender_id, "⏳ Generating your quotation PDF, please wait...")
                                                                    deliver_shared_quotation_pdf(payload, qid, sender_id, send_text_message)
                                                                    continue
                                                                else:
                                                                    send_text_message(sender_id, "❌ Invalid quotation reference.")
                                                                    continue
                                                            else:
                                                                print(f"❌ Unknown payload: {payload}")


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





#### hardware stuff


def get_zimbabwe_time():
    """Get current time in Zimbabwe timezone"""
    from datetime import datetime
    from pytz import timezone
    zw_tz = timezone('Africa/Harare')
    return datetime.now(zw_tz)


def hash_password(password):
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_transaction_number():
    """Generate unique transaction number"""
    date_str = datetime.now().strftime('%Y%m%d')
    random_part = secrets.token_hex(4).upper()
    return f"REC-{date_str}-{random_part}-CONLINK"

def login_required(f):
    """Decorator to check if user is logged in"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """Decorator to check if user is admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return jsonify({'error': 'Authentication required'}), 401
        if session.get('role') != 'admin':
            return jsonify({'error': 'Admin access required'}), 403
        return f(*args, **kwargs)
    return decorated_function

def get_user_by_id(user_id):
    """Get user by ID"""
    query = "SELECT id, username, email, full_name, role, created_at FROM users WHERE id = %s"
    result = execute_query(query, (user_id,), fetch_one=True)
    return result


# ==================== ACTIVITY LOG SYSTEM ====================

def log_activity(action_type, description, reference_type=None, reference_id=None, details=None):
    """Log an activity to the activity_log table"""
    try:
        user_name = session.get('username') or session.get('user_name') or 'System'
        with get_db() as (cursor, connection):
            cursor.execute("""
                INSERT INTO activity_log (action_type, description, user_name, reference_type, reference_id, details)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                action_type,
                description,
                user_name,
                reference_type,
                reference_id,
                psycopg2.extras.Json(details) if details else None
            ))
            connection.commit()
    except Exception as e:
        print(f"❌ Failed to log activity: {e}")


@app.route('/api/activity-log', methods=['GET', 'POST'])
def handle_activity_log():
    if request.method == 'POST':
        try:
            data = request.get_json()
            action_type = data.get('action_type', 'system')
            description = data.get('description', '')
            reference_type = data.get('reference_type')
            reference_id = data.get('reference_id')
            details = data.get('details')
            log_activity(action_type, description, reference_type, reference_id, details)
            return jsonify({'success': True})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET - fetch activity log
    try:
        limit = request.args.get('limit', 100, type=int)
        action_filter = request.args.get('action_type', '')
        user_filter = request.args.get('user_name', '')
        
        with get_db() as (cursor, connection):
            conditions = []
            params = []
            
            if action_filter:
                conditions.append("action_type = %s")
                params.append(action_filter)
            if user_filter:
                conditions.append("user_name = %s")
                params.append(user_filter)
            
            where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
            
            cursor.execute(f"""
                SELECT id, action_type, description, user_name, reference_type, reference_id, 
                       details, created_at
                FROM activity_log
                {where_clause}
                ORDER BY created_at DESC
                LIMIT %s
            """, tuple(params) + (limit,))
            
            rows = cursor.fetchall()
            activities = []
            for row in rows:
                activities.append({
                    'id': row[0],
                    'action_type': row[1],
                    'description': row[2],
                    'user_name': row[3] or 'System',
                    'reference_type': row[4],
                    'reference_id': row[5],
                    'details': row[6],
                    'created_at': row[7].strftime('%d/%m/%Y %H:%M') if row[7] else ''
                })
            
            return jsonify({'success': True, 'data': activities, 'count': len(activities)})
    except Exception as e:
        print(f"❌ Error fetching activity log: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/activity-log-users', methods=['GET'])
def get_activity_log_users():
    """Get distinct user names from activity_log"""
    try:
        with get_db() as (cursor, connection):
            cursor.execute("""
                SELECT DISTINCT user_name FROM activity_log
                WHERE user_name IS NOT NULL
                ORDER BY user_name
            """)
            users = [row[0] for row in cursor.fetchall()]
            return jsonify({'success': True, 'users': users})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def run1hardware():
    """Fetch all active products from the Products table"""
    query = """
        SELECT id, name, category, unit_type, unit_details, buy_price, sell_price, stock, 
               min_stock_level, description, created_at, updated_at
        FROM products
        WHERE is_active = TRUE
        ORDER BY name
    """
    result = execute_query(query, fetch_all=True)
    
    products = []
    if result:
        for row in result:
            products.append({
                'id': row[0],
                'name': row[1],
                'category': row[2],
                'unit_type': row[3],
                'unit_details': row[4],
                'buy_price': float(row[5]) if row[5] else 0.00,
                'sell_price': float(row[6]) if row[6] else 0.00,  # Make sure this exists
                'stock': row[7] if row[7] else 0,
                'min_stock_level': row[8] if row[8] else 10,
                'description': row[9] if row[9] else '',
                'created_at': row[10].isoformat() if row[10] else None,
                'updated_at': row[11].isoformat() if row[11] else None,
                'low_stock': row[7] < row[8] if row[7] and row[8] else False
            })
    
    return products




# Get specific stock addition
# Get specific stock addition
@app.route('/api/stock-additions/<int:addition_id>', methods=['GET'])
@login_required
def get_stock_addition(addition_id):
    query = """
        SELECT sa.id, sa.product_id, p.name as product_name, sa.quantity, 
               sa.buy_price, sa.total_cost, sa.funding_source, 
               p.stock as current_stock,
               sa.buy_price as cost_per_unit
        FROM stock_additions sa
        LEFT JOIN products p ON sa.product_id = p.id
        WHERE sa.id = %s
    """
    result = execute_query(query, (addition_id,), fetch_one=True)
    
    if not result:
        return jsonify({'error': 'Stock addition not found'}), 404
    
    return jsonify({
        'success': True,
        'addition': {
            'id': result[0],
            'product_id': result[1],
            'product_name': result[2],
            'quantity': result[3],
            'total_cost': float(result[5]),
            'cost_per_unit': float(result[8]),
            'funding_source': result[6],
            'current_stock': result[7]
        }
    })


# Update stock addition - FIXED to properly update product stock
@app.route('/api/stock-additions/<int:addition_id>', methods=['PUT'])
@login_required
def update_stock_addition(addition_id):
    try:
        data = request.json
        
        # Get old stock addition data
        old_data = execute_query(
            "SELECT product_id, quantity, buy_price, total_cost, funding_source FROM stock_additions WHERE id = %s",
            (addition_id,), fetch_one=True
        )
        
        if not old_data:
            return jsonify({'error': 'Stock addition not found'}), 404
        
        old_product_id = old_data[0]
        old_quantity = old_data[1]
        old_cost_per_unit = old_data[2]
        old_total_cost = old_data[3]
        old_funding_source = old_data[4]
        
        # Calculate stock difference for the product
        stock_difference = data['quantity'] - old_quantity
        
        # Update stock addition record
        update_query = """
            UPDATE stock_additions 
            SET quantity = %s, buy_price = %s, total_cost = %s, funding_source = %s
            WHERE id = %s
        """
        execute_query(update_query, (
            data['quantity'],
            data['cost_per_unit'],
            data['total_cost'],
            data['funding_source'],
            addition_id
        ), commit=True)
        
        # Update product stock - CRITICAL: This updates the actual product inventory
        update_stock_query = """
            UPDATE products 
            SET stock = stock + %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        execute_query(update_stock_query, (stock_difference, old_product_id), commit=True)
        
        return jsonify({
            'success': True, 
            'message': 'Stock addition updated successfully',
            'stock_change': stock_difference
        })
        
    except Exception as e:
        print(f"Error updating stock addition: {e}")
        return jsonify({'error': str(e)}), 500

# Delete stock addition - FIXED to properly remove stock
@app.route('/api/stock-additions/<int:addition_id>', methods=['DELETE'])
@login_required
def delete_stock_addition(addition_id):
    try:
        data = request.json
        
        # Get the addition details
        addition = execute_query(
            "SELECT product_id, quantity FROM stock_additions WHERE id = %s",
            (addition_id,), fetch_one=True
        )
        
        if not addition:
            return jsonify({'error': 'Stock addition not found'}), 404
        
        product_id = addition[0]
        quantity_to_remove = addition[1]
        
        # Remove stock from product (subtract the quantity)
        update_stock_query = """
            UPDATE products 
            SET stock = stock - %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s AND stock >= %s
        """
        execute_query(update_stock_query, (quantity_to_remove, product_id, quantity_to_remove), commit=True)
        
        # Delete the addition record
        delete_query = "DELETE FROM stock_additions WHERE id = %s"
        execute_query(delete_query, (addition_id,), commit=True)
        
        return jsonify({
            'success': True, 
            'message': 'Stock addition deleted successfully',
            'stock_removed': quantity_to_remove
        })
        
    except Exception as e:
        print(f"Error deleting stock addition: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== USER AUTHENTICATION ====================

@app.route('/api/stock-additions', methods=['GET'])
@login_required
def get_stock_additions():
    """Get stock addition history for reinvestment tracking"""
    query = """
        SELECT sa.id, sa.added_at as date, p.id as product_id, p.name as product_name, 
               sa.quantity, sa.total_cost, sa.funding_source, u.full_name as user,
               sa.buy_price as cost_per_unit
        FROM stock_additions sa
        LEFT JOIN products p ON sa.product_id = p.id
        LEFT JOIN users u ON sa.user_id = u.id
        ORDER BY sa.added_at DESC
        LIMIT 100
    """
    result = execute_query(query, fetch_all=True)
    
    additions = []
    if result:
        for row in result:
            additions.append({
                'id': row[0],
                'date': row[1].isoformat() if row[1] else '',
                'product_id': row[2],
                'product_name': row[3],
                'quantity': row[4],
                'total_cost': float(row[5]),
                'funding_source': row[6],
                'user': row[7] or 'System',
                'cost_per_unit': float(row[8]) if row[8] else 0
            })
    
    return jsonify({
        'success': True,
        'additions': additions
    })

@app.route('/api/stock-movements', methods=['GET'])
@login_required
def get_stock_movements():
    """Get stock movements (additions & reductions) within a date range for audit report"""
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    if not start_date or not end_date:
        return jsonify({'success': False, 'error': 'start_date and end_date are required'}), 400
    
    # Get stock at the start of the period (initial stock per product)
    initial_query = """
        SELECT p.id, p.name, p.category, p.unit_type, p.unit_details, p.buy_price, p.sell_price,
               COALESCE(initial.stock, 0) as initial_stock
        FROM products p
        LEFT JOIN LATERAL (
            SELECT sa.product_id,
                   p2.stock - COALESCE(sa.total_added, 0) + COALESCE(sr.total_removed, 0) as stock
            FROM products p2
            LEFT JOIN (
                SELECT product_id, SUM(quantity) as total_added
                FROM stock_additions
                WHERE added_at < %s::timestamp
                GROUP BY product_id
            ) sa ON sa.product_id = p2.id
            LEFT JOIN (
                SELECT product_id, SUM(quantity) as total_removed
                FROM stock_reductions
                WHERE reduced_at < %s::timestamp
                GROUP BY product_id
            ) sr ON sr.product_id = p2.id
            WHERE p2.id = p.id
        ) initial ON true
        WHERE p.is_active = TRUE OR p.is_active IS NULL
        ORDER BY p.name
    """
    
    # For initial stock, get the stock level at the END of the day BEFORE start_date
    # A simpler approach: get the current stock and subtract movements in the period
    # But even simpler: we take the stock value recorded just before start date
    
    # Get product list with initial stock (stock as recorded just before start_date)
    # We'll compute this by taking current stock and reversing movements in the period
    products_result = execute_query("""
        SELECT p.id, p.name, p.category, p.unit_type, p.unit_details, 
               COALESCE(p.buy_price, 0) as buy_price, COALESCE(p.sell_price, 0) as sell_price
        FROM products p
        WHERE p.is_active = TRUE OR p.is_active IS NULL
        ORDER BY p.name
    """, fetch_all=True)
    
    # Get additions in the period
    additions_query = """
        SELECT sa.id, sa.product_id, p.name as product_name, p.category,
               'addition' as movement_type, sa.quantity, sa.buy_price, sa.total_cost,
               sa.funding_source, u.full_name as user_name, sa.added_at as movement_date
        FROM stock_additions sa
        LEFT JOIN products p ON sa.product_id = p.id
        LEFT JOIN users u ON sa.user_id = u.id
        WHERE sa.added_at >= %s::timestamp AND sa.added_at <= (%s::timestamp + INTERVAL '1 day')
        ORDER BY sa.added_at DESC
    """
    additions = execute_query(additions_query, (start_date, end_date), fetch_all=True) or []
    
    # Get reductions in the period
    reductions_query = """
        SELECT sr.id, sr.product_id, p.name as product_name, p.category,
               'reduction' as movement_type, sr.quantity, 0 as buy_price, 0 as total_cost,
               sr.reason as funding_source, u.full_name as user_name, sr.reduced_at as movement_date
        FROM stock_reductions sr
        LEFT JOIN products p ON sr.product_id = p.id
        LEFT JOIN users u ON sr.user_id = u.id
        WHERE sr.reduced_at >= %s::timestamp AND sr.reduced_at <= (%s::timestamp + INTERVAL '1 day')
        ORDER BY sr.reduced_at DESC
    """
    reductions = execute_query(reductions_query, (start_date, end_date), fetch_all=True) or []
    
    # Also get sales from transaction_items (captures ALL sales, including historical ones
    # that were never logged to stock_reductions)
    sales_query = """
        SELECT ti.id, ti.product_id, p.name as product_name, p.category,
               'reduction' as movement_type, ti.quantity, 0 as buy_price, 0 as total_cost,
               'item_sale' as funding_source, u.full_name as user_name, t.created_at as movement_date
        FROM transaction_items ti
        JOIN transactions t ON ti.transaction_id = t.id
        LEFT JOIN products p ON ti.product_id = p.id
        LEFT JOIN users u ON t.user_id = u.id
        WHERE t.created_at >= %s::timestamp AND t.created_at <= (%s::timestamp + INTERVAL '1 day')
        ORDER BY t.created_at DESC
    """
    transaction_sales = execute_query(sales_query, (start_date, end_date), fetch_all=True) or []
    
    # Separate reductions by type (from stock_reductions table)
    # IMPORTANT: Only count inventory edits from stock_reductions.
    # Sales come from transaction_items (to avoid double-counting with new
    # sales that are also logged to stock_reductions with reason='item_sale')
    inventory_edit_reductions = []
    sales_reductions = []
    for row in reductions:
        reason = row[8] or ''
        if reason == 'item_sale':
            continue  # Skip - sales come from transaction_items instead
        else:
            inventory_edit_reductions.append(row)
    
    # Merge transaction_items sales into sales_reductions (catches ALL sales, not just new ones)
    for row in transaction_sales:
        sales_reductions.append(row)
    
    # Build combined reductions list for period totals
    all_reductions = inventory_edit_reductions + sales_reductions
    
    # Build product map with initial stock (current stock - additions in period + reductions in period)
    product_map = {}
    if products_result:
        for row in products_result:
            product_map[row[0]] = {
                'id': row[0],
                'name': row[1],
                'category': row[2],
                'unit_type': row[3],
                'unit_details': row[4],
                'buy_price': float(row[5]),
                'sell_price': float(row[6]),
                'initial_stock': 0,
                'total_additions': 0,
                'total_reductions': 0,
                'inventory_edit_reductions': 0,
                'sales_reductions': 0
            }
    
    # Get current stock for all products
    current_stocks = execute_query("SELECT id, stock FROM products WHERE is_active = TRUE OR is_active IS NULL", fetch_all=True) or []
    current_stock_map = {}
    for row in current_stocks:
        current_stock_map[row[0]] = row[1]
    
    # Calculate period totals from additions/reductions
    period_additions = {}  # product_id -> total
    period_reductions = {}  # product_id -> total
    
    if additions:
        for row in additions:
            pid = row[1]
            qty = row[5]
            period_additions[pid] = period_additions.get(pid, 0) + qty
            if pid in product_map:
                product_map[pid]['total_additions'] += qty
    
    if all_reductions:
        for row in all_reductions:
            pid = row[1]
            qty = row[5]
            reason = row[8] or ''
            period_reductions[pid] = period_reductions.get(pid, 0) + qty
            if pid in product_map:
                product_map[pid]['total_reductions'] += qty
                if reason == 'item_sale':
                    product_map[pid]['sales_reductions'] += qty
                else:
                    product_map[pid]['inventory_edit_reductions'] += qty
    
    # Calculate initial stock: current - additions_in_period + reductions_in_period
    # Clamp to 0 since opening stock cannot be negative
    for pid, product in product_map.items():
        current = current_stock_map.get(pid, 0)
        calculated = current - period_additions.get(pid, 0) + period_reductions.get(pid, 0)
        product['initial_stock'] = max(0, calculated)
        product['final_stock'] = current
    
    # Parse movements - additions
    movements = []
    
    if additions:
        for row in additions:
            movements.append({
                'id': row[0],
                'product_id': row[1],
                'product_name': row[2],
                'category': row[3],
                'type': 'addition',
                'quantity': row[5],
                'buy_price': float(row[6]) if row[6] else 0,
                'total_cost': float(row[7]) if row[7] else 0,
                'details': f"Funding: {row[8]}" if row[8] else '',
                'user': row[9] or 'System',
                'date': row[10].isoformat() if row[10] else '',
                'reduction_type': None
            })
    
    # Parse movements - inventory edit reductions
    if inventory_edit_reductions:
        for row in inventory_edit_reductions:
            movements.append({
                'id': row[0],
                'product_id': row[1],
                'product_name': row[2],
                'category': row[3],
                'type': 'reduction',
                'quantity': row[5],
                'buy_price': 0,
                'total_cost': 0,
                'details': f"Reason: {row[8]}" if row[8] else '',
                'user': row[9] or 'System',
                'date': row[10].isoformat() if row[10] else '',
                'reduction_type': 'inventory_edit'
            })
    
    # Parse movements - sales reductions
    if sales_reductions:
        for row in sales_reductions:
            movements.append({
                'id': row[0],
                'product_id': row[1],
                'product_name': row[2],
                'category': row[3],
                'type': 'reduction',
                'quantity': row[5],
                'buy_price': 0,
                'total_cost': 0,
                'details': f"Sale: {row[8]}" if row[8] else '',
                'user': row[9] or 'System',
                'date': row[10].isoformat() if row[10] else '',
                'reduction_type': 'item_sale'
            })
    
    # Sort movements by date descending
    movements.sort(key=lambda m: m['date'], reverse=True)
    
    # Build summary
    products_list = sorted(product_map.values(), key=lambda p: p['name'])
    
    summary = {
        'total_products': len(products_list),
        'total_additions': sum(m['quantity'] for m in movements if m['type'] == 'addition'),
        'total_reductions': sum(m['quantity'] for m in movements if m['type'] == 'reduction'),
        'total_addition_cost': sum(m['total_cost'] for m in movements if m['type'] == 'addition'),
    }
    
    return jsonify({
        'success': True,
        'products': products_list,
        'movements': movements,
        'summary': summary
    })

@app.route('/api/login', methods=['POST'])
def api_login():
    """API endpoint for POS login - checks admin_users only"""
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'success': False, 'message': 'Username and password required'}), 400
    
    try:
        with get_db() as (cursor, connection):
            cursor.execute("""
                SELECT id, username, password, full_name, role, source_system
                FROM admin_users WHERE username = %s AND is_active = TRUE
            """, (username,))
            user = cursor.fetchone()
            
            if not user:
                return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
            
            if user[2] != password:
                return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
            
            session.permanent = True
            session['user_id'] = int(user[0])
            session['username'] = user[1]
            session['full_name'] = user[3]
            session['role'] = user[4]
            session['userid'] = int(user[0])
            session['user_name'] = user[3]
            
            log_activity('user_login', f'POS login via admin_users: {username}', 'user', user[0])
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user[0],
                    'username': user[1],
                    'full_name': user[3],
                    'role': user[4]
                },
                'message': 'Login successful',
                'redirect': '/pos-system.html'
            }), 200
            
    except Exception as e:
        print(f"⚠️  POS login error: {e}")
        return jsonify({'success': False, 'message': 'Invalid credentials'}), 401


@app.route('/api/logoutpos', methods=['POST','GET'])
def api_logout():
    user_name = session.get('username') or session.get('user_name') or 'Unknown'
    log_activity('user_logout', f'User {user_name} logged out from POS', 'user', session.get('user_id') or session.get('userid'))
    session.clear()
    return render_template('mainindex.html')  # Or send_from_directory for static HTML

@app.route('/api/check-auth', methods=['GET'])
def check_auth():
    """Check if user is authenticated via session"""
    if 'user_id' in session:
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['user_id'],
                'username': session.get('username'),
                'full_name': session.get('full_name'),
                'role': session.get('role', 'user')
            }
        })
    elif 'userid' in session:
        # For building project users without role
        return jsonify({
            'authenticated': True,
            'user': {
                'id': session['userid'],
                'username': session.get('user_name', 'User'),
                'full_name': session.get('user_name', 'User'),
                'role': 'admin'
            }
        })
    return jsonify({'authenticated': False}), 401


@app.route('/api/debug/hardware-users', methods=['GET'])
def debug_hardware_users():
    """Debug endpoint to check hardware_users table - REMOVE IN PRODUCTION"""
    try:
        with get_db() as (cursor, connection):
            # Check if table exists
            cursor.execute("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'hardware_users'
            """)
            table_exists = cursor.fetchone()
            
            if not table_exists:
                return jsonify({'error': 'hardware_users table does not exist'}), 404
            
            # Get all hardware users
            cursor.execute("SELECT id, username, full_name, role FROM hardware_users")
            users = cursor.fetchall()
            
            return jsonify({
                'table_exists': True,
                'users_count': len(users) if users else 0,
                'users': [
                    {'id': u[0], 'username': u[1], 'full_name': u[2], 'role': u[3]}
                    for u in users
                ] if users else []
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ==================== PRODUCT MANAGEMENT ====================

@app.route('/api/products', methods=['GET'])
@login_required
def get_products_api():
    """API endpoint to fetch products using run1()"""
    category = request.args.get('category')
    search = request.args.get('search')
    
    # Get all products using run1
    all_products = run1hardware()
    
    # Apply filters
    filtered_products = all_products
    if category and category != 'all':
        filtered_products = [p for p in filtered_products if p['category'] == category]
    if search:
        search_lower = search.lower()
        filtered_products = [p for p in filtered_products 
                            if search_lower in p['name'].lower() 
                            or (p.get('unit_details') and search_lower in p['unit_details'].lower())]
    
    return jsonify({
        'success': True,
        'products': filtered_products,
        'total': len(filtered_products)
    })

@app.route('/api/products/<int:product_id>', methods=['GET'])
@login_required
def get_product(product_id):
    query = "SELECT id, name, category, unit_type, unit_details, buy_price, sell_price, stock, min_stock_level, description FROM products WHERE id = %s"
    product = execute_query(query, (product_id,), fetch_one=True)
    
    if not product:
        return jsonify({'error': 'Product not found'}), 404
    
    return jsonify({
        'success': True,
        'product': {
            'id': product[0],
            'name': product[1],
            'category': product[2],
            'unit_type': product[3],
            'unit_details': product[4],
            'buy_price': float(product[5]) if product[5] else 0.00,
            'sell_price': float(product[6]),
            'stock': product[7],
            'min_stock_level': product[8],
            'description': product[9]
        }
    })

@app.route('/api/products', methods=['POST'])
@login_required
def create_product():
    """Create new product"""
    data = request.json
    
    # Validate required fields
    if 'sell_price' not in data:
        return jsonify({'error': 'sell_price is required'}), 400
    
    query = """
        INSERT INTO products (name, category, unit_type, unit_details, buy_price, sell_price, stock, min_stock_level, description)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """
    
    params = (
        data['name'],
        data['category'],
        data.get('unit_type', 'piece'),
        data.get('unit_details', ''),
        data.get('buy_price', 0.00),
        data['sell_price'],
        data.get('stock', 0),
        data.get('min_stock_level', 10),
        data.get('description', '')
    )
    
    result = execute_query(query, params, fetch_one=True, commit=True)
    
    return jsonify({
        'success': True,
        'product_id': result[0],
        'message': 'Product created successfully'
    }), 201

@app.route('/api/products/<int:product_id>/price', methods=['PUT'])
@login_required
def update_product_price(product_id):
    """Update product selling price - using ONLY sell_price"""
    try:
        data = request.json
        new_price = data.get('sell_price')
        
        if new_price is None:
            return jsonify({'error': 'New price is required'}), 400
        
        # Get current product info
        product_query = "SELECT id, name, buy_price, sell_price FROM products WHERE id = %s"
        product = execute_query(product_query, (product_id,), fetch_one=True)
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        product_name = product[1]
        current_sell_price = float(product[3]) if product[3] else 0
        buy_price = float(product[2]) if product[2] else 0
        
        # Update ONLY sell_price - NO 'price' column reference
        update_query = """
            UPDATE products 
            SET sell_price = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE id = %s
        """
        execute_query(update_query, (new_price, product_id), commit=True)
        
        return jsonify({
            'success': True,
            'message': f'Price updated from ${current_sell_price:.2f} to ${new_price:.2f}',
            'old_price': current_sell_price,
            'new_price': new_price
        })
        
    except Exception as e:
        print(f"Error updating product price: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products/<int:product_id>', methods=['PUT'])
@login_required
def update_product(product_id):
    data = request.json
    
    update_fields = []
    params = []
    
    updatable_fields = ['name', 'category', 'unit_type', 'unit_details', 'buy_price', 'sell_price', 'price', 'stock', 'min_stock_level', 'description']
    
    for field in updatable_fields:
        if field in data:
            update_fields.append(f"{field} = %s")
            params.append(data[field])
    
    # If this is a stock addition, track funding source in a separate table
    if 'funding_source' in data and 'total_cost' in data:
        # Log this stock addition with funding source
        stock_log_query = """
            INSERT INTO stock_additions (product_id, quantity, buy_price, total_cost, funding_source, user_id, added_at)
            VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        """
        # Get current stock to calculate quantity added
        current_stock = execute_query("SELECT stock FROM products WHERE id = %s", (product_id,), fetch_one=True)
        if current_stock:
            quantity_added = data.get('stock') - current_stock[0]
        else:
            quantity_added = data.get('stock', 0)
            
        execute_query(stock_log_query, (
            product_id,
            quantity_added,
            data.get('buy_price', 0),
            data.get('total_cost', 0),
            data.get('funding_source'),
            session['user_id']
        ), commit=True)
    
    if not update_fields:
        return jsonify({'error': 'No fields to update'}), 400
    
    params.append(product_id)
    query = f"UPDATE products SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP WHERE id = %s"
    
    execute_query(query, tuple(params), commit=True)
    
    return jsonify({'success': True, 'message': 'Product updated successfully'})

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
@login_required
def delete_product(product_id):
    # Soft delete - just mark as inactive
    execute_query("""
        UPDATE products 
        SET is_active = FALSE, updated_at = CURRENT_TIMESTAMP 
        WHERE id = %s
    """, (product_id,), commit=True)
    
    return jsonify({'success': True, 'message': 'Product deactivated successfully'})

@app.route('/api/products/<int:product_id>/subtract-stock', methods=['PUT'])
@login_required
def subtract_stock(product_id):
    """Subtract stock from a product with reason tracking"""
    try:
        data = request.json
        quantity = data.get('quantity', 0)
        reason = data.get('reason', 'other')
        notes = data.get('notes', '')
        
        if quantity <= 0:
            return jsonify({'error': 'Quantity must be greater than 0'}), 400
        
        # Get current stock
        product = execute_query("""
            SELECT id, stock, name FROM products WHERE id = %s
        """, (product_id,), fetch_one=True)
        
        if not product:
            return jsonify({'error': 'Product not found'}), 404
        
        current_stock = product[1]
        product_name = product[2]
        
        # Check if there's enough stock
        if quantity > current_stock:
            return jsonify({
                'error': f'Insufficient stock. You have {current_stock} units but trying to remove {quantity}'
            }), 400
        
        # Subtract stock
        new_stock = current_stock - quantity
        execute_query("""
            UPDATE products 
            SET stock = %s, updated_at = CURRENT_TIMESTAMP 
            WHERE id = %s
        """, (new_stock, product_id), commit=True)
        
        # Try to log the stock reduction (table may not exist yet)
        try:
            execute_query("""
                INSERT INTO stock_reductions (product_id, quantity, reason, notes, user_id, reduced_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (product_id, quantity, reason, notes, session['user_id']), commit=True)
        except Exception as log_error:
            # If the table doesn't exist, just log to console and continue
            print(f"Warning: Could not log stock reduction: {str(log_error)}")
        
        return jsonify({
            'success': True,
            'message': f'Removed {quantity} units from {product_name}. Reason: {reason}',
            'new_stock': new_stock
        })
    
    except Exception as e:
        print(f"Error subtracting stock: {str(e)}")
        return jsonify({'error': 'Failed to subtract stock', 'details': str(e)}), 500

# ==================== AI PRODUCT CLASSIFICATION ====================

@app.route('/api/ai/classify-product', methods=['POST'])
@login_required
def ai_classify_product():
    """
    AI endpoint to automatically classify a product into category & subcategory
    
    Request body:
    {
        "product_name": "LED Bulb 60W",
        "description": "Warm white, energy efficient"
    }
    
    Response:
    {
        "category": "Electrical",
        "subcategory": "LED Lights",
        "confidence": 92,
        "method": "exact_match"
    }
    """
    try:
        data = request.json
        product_name = data.get('product_name', '').strip()
        description = data.get('description', '').strip()
        
        if not product_name:
            return jsonify({'error': 'Product name is required'}), 400
        
        # Get AI classification
        result = classify_product(product_name, description)
        
        return jsonify({
            'success': True,
            'classification': result
        })
    
    except Exception as e:
        print(f"AI Classification Error: {str(e)}")
        return jsonify({
            'error': 'Classification failed',
            'details': str(e),
            'category': 'Other',
            'subcategory': 'Other'
        }), 500


@app.route('/api/ai/category-suggestions', methods=['GET'])
@login_required
def ai_category_suggestions():
    """
    Get category suggestions as user types product name (autocomplete)
    
    Query params:
    - partial_name: Partial product name to match
    - limit: Max suggestions (default: 3)
    
    Response:
    {
        "suggestions": [
            {
                "name": "Screwdrivers",
                "category": "General Tools",
                "match_score": 95
            }
        ]
    }
    """
    try:
        partial_name = request.args.get('partial_name', '').strip()
        limit = request.args.get('limit', 3, type=int)
        
        if len(partial_name) < 2:
            return jsonify({'suggestions': []})
        
        suggestions = get_category_suggestions(partial_name)
        
        return jsonify({
            'success': True,
            'suggestions': suggestions[:limit]
        })
    
    except Exception as e:
        print(f"Category Suggestions Error: {str(e)}")
        return jsonify({
            'error': 'Failed to get suggestions',
            'details': str(e),
            'suggestions': []
        }), 500


@app.route('/api/ai/test-classifier', methods=['GET'])
def test_ai_classifier():
    """
    Test endpoint to verify AI classifier is working (no auth required)
    Returns test results
    """
    try:
        test_products = [
            ("Titanium Screwdriver", "Phillips head, magnetic tip"),
            ("LED Bulb 60W", "Warm white, energy efficient"),
            ("Chrome Door Lock", "Heavy duty, security lock"),
        ]
        
        results = []
        for product_name, description in test_products:
            classification = classify_product(product_name, description)
            results.append({
                'product_name': product_name,
                'classification': classification
            })
        
        return jsonify({
            'success': True,
            'test_results': results,
            'message': 'AI Classifier is working correctly!'
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/categories/create', methods=['POST'])
@login_required
def create_new_category():
    """
    Create a new product category and subcategory
    
    Request body:
    {
        "category_name": "Smart Home Devices",
        "subcategory_name": "Smart Lights"
    }
    
    Response:
    {
        "success": true,
        "category_name": "Smart Home Devices",
        "subcategory_name": "Smart Lights",
        "message": "Category created successfully"
    }
    """
    try:
        data = request.json
        category_name = data.get('category_name', '').strip()
        subcategory_name = data.get('subcategory_name', '').strip()
        
        if not category_name or not subcategory_name:
            return jsonify({
                'success': False,
                'message': 'Category name and subcategory name are required'
            }), 400
        
        # Validate inputs (prevent injection)
        if len(category_name) > 100 or len(subcategory_name) > 100:
            return jsonify({
                'success': False,
                'message': 'Names must be less than 100 characters'
            }), 400
        
        # Try to create a database record for the new category
        # This helps track user-created categories
        try:
            with get_db() as (cursor, connection):
                # Check if category already exists
                cursor.execute("""
                    SELECT id FROM product_categories 
                    WHERE category_name = %s AND subcategory_name = %s
                """, (category_name, subcategory_name))
                
                existing = cursor.fetchone()
                if existing:
                    return jsonify({
                        'success': False,
                        'message': 'This category/subcategory combination already exists'
                    }), 400
                
                # Insert new category
                cursor.execute("""
                    INSERT INTO product_categories (category_name, subcategory_name, created_at)
                    VALUES (%s, %s, NOW())
                """, (category_name, subcategory_name))
                
                connection.commit()
        except Exception as e:
            # If table doesn't exist, just continue (categories stored in memory)
            print(f"Warning: Could not save category to database: {str(e)}")
            pass
        
        return jsonify({
            'success': True,
            'category_name': category_name,
            'subcategory_name': subcategory_name,
            'message': 'Category created successfully'
        })
    
    except Exception as e:
        print(f"Error creating category: {str(e)}")
        return jsonify({
            'success': False,
            'message': 'Error creating category',
            'error': str(e)
        }), 500

# ==================== TRANSACTION MANAGEMENT ====================

@app.route('/api/transactions', methods=['POST'])
@login_required
def create_transaction():
    """Create new transaction"""
    try:
        data = request.json
        items = data.get('items', [])
        
        if not items:
            return jsonify({'error': 'No items in transaction'}), 400
        
        subtotal = sum(item['price'] * item['quantity'] for item in items)
        total = subtotal
        
        transaction_number = generate_transaction_number()
        
        # Get Zimbabwe time
        zimbabwe_now = get_zimbabwe_time()

        print("yearrrrrrrrrrrrrrrrrrrrrrrrrrrrrrr")

        print(zimbabwe_now)
        
        # Insert transaction with explicit Zimbabwe time
        trans_query = """
            INSERT INTO transactions (transaction_number, user_id, subtotal, tax, total, payment_method, amount_paid, change_amount, notes, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
        """
        
        trans_params = (
            transaction_number,
            session['user_id'],
            subtotal,
            0,
            total,
            data['payment_method'],
            data.get('amount_paid', total),
            data.get('change_amount', 0),
            data.get('notes', ''),
            zimbabwe_now
        )
        
        trans_result = execute_query(trans_query, trans_params, fetch_one=True, commit=True)
        transaction_id = trans_result[0]
        
        # Insert transaction items
        for item in items:
            product_query = "SELECT unit_type, unit_details FROM products WHERE id = %s"
            product_info = execute_query(product_query, (item['id'],), fetch_one=True)
            
            unit_type = product_info[0] if product_info else ''
            unit_details = product_info[1] if product_info else ''
            
            item_query = """
                INSERT INTO transaction_items (transaction_id, product_id, quantity, price_at_time, subtotal, unit_type, unit_details)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            item_params = (
                transaction_id,
                item['id'],
                item['quantity'],
                item['price'],
                item['price'] * item['quantity'],
                unit_type,
                unit_details
            )
            execute_query(item_query, item_params, commit=True)
            
            stock_query = "UPDATE products SET stock = stock - %s WHERE id = %s"
            execute_query(stock_query, (item['quantity'], item['id']), commit=True)
            
            # Log sale reduction to stock_reductions for audit trail
            try:
                execute_query("""
                    INSERT INTO stock_reductions (product_id, quantity, reason, notes, user_id, reduced_at)
                    VALUES (%s, %s, 'item_sale', %s, %s, CURRENT_TIMESTAMP)
                """, (item['id'], item['quantity'], f"Sale #{transaction_number}", session.get('user_id', 0)), commit=True)
            except Exception as log_err:
                print(f"Warning: Could not log sale reduction: {str(log_err)}")
        
        return jsonify({
            'success': True,
            'transaction_id': transaction_id,
            'transaction_number': transaction_number,
            'created_at': zimbabwe_now.isoformat(),
            'message': 'Transaction completed successfully'
        }), 201
        
    except Exception as e:
        print(f"Error creating transaction: {e}")
        return jsonify({'error': str(e)}), 500
                
@app.route('/api/transactions', methods=['GET'])
@login_required
def get_transactions():
    """Get all transactions"""
    limit = request.args.get('limit', 50, type=int)
    
    query = """
        SELECT t.id, t.transaction_number, t.user_id, u.full_name as cashier, 
               t.subtotal, t.tax, t.total, t.payment_method, t.amount_paid, 
               t.change_amount, t.status, t.created_at,
               COALESCE((
                   SELECT json_agg(json_build_object(
                       'product_id', ti.product_id,
                       'product_name', p.name,
                       'quantity', ti.quantity,
                       'price', ti.price_at_time,
                       'subtotal', ti.subtotal,
                       'unit_type', ti.unit_type,
                       'unit_details', ti.unit_details,
                       'buy_price', p.buy_price,
                       'category', p.category
                   ))
                   FROM transaction_items ti
                   LEFT JOIN products p ON ti.product_id = p.id
                   WHERE ti.transaction_id = t.id
               ), '[]'::json) as items
        FROM transactions t
        LEFT JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC
        LIMIT %s
    """
    
    transactions = execute_query(query, (limit,), fetch_all=True)
    
    transaction_list = []
    for t in transactions:
        transaction_list.append({
            'id': t[0],
            'transaction_number': t[1],
            'user_id': t[2],
            'cashier': t[3],
            'subtotal': float(t[4]),
            'tax': float(t[5]),
            'total': float(t[6]),
            'payment_method': t[7],
            'amount_paid': float(t[8]),
            'change_amount': float(t[9]),
            'status': t[10],
            'created_at': t[11].isoformat() if t[11] else None,
            'items': t[12] if t[12] else []
        })
    
    return jsonify({
        'success': True,
        'transactions': transaction_list
    })

@app.route('/api/transactions/daily-summary', methods=['GET'])
@login_required
def get_daily_summary():
    """Get today's sales summary"""
    query = """
        SELECT 
            COALESCE(SUM(total), 0) as total_sales,
            COALESCE(SUM(subtotal), 0) as total_subtotal,
            COALESCE(SUM(tax), 0) as total_tax,
            COUNT(*) as transaction_count,
            COALESCE(SUM(
                (SELECT COALESCE(SUM(quantity), 0) 
                 FROM transaction_items 
                 WHERE transaction_id = transactions.id)
            ), 0) as items_sold
        FROM transactions
        WHERE DATE(created_at) = CURRENT_DATE
        AND status = 'completed'
    """
    
    result = execute_query(query, fetch_one=True)
    
    return jsonify({
        'success': True,
        'today_sales': float(result[0]) if result else 0,
        'total_subtotal': float(result[1]) if result else 0,
        'total_tax': float(result[2]) if result else 0,
        'transaction_count': result[3] if result else 0,
        'items_sold': result[4] if result else 0
    })

@app.route('/api/transactions/clear-all', methods=['DELETE'])
@login_required
def clear_all_transactions():
    """Clear all transaction history - ADMIN ONLY"""
    try:
        # Verify user is admin
        user_role = session.get('role', 'user')
        if user_role != 'admin':
            return jsonify({'success': False, 'error': 'Unauthorized: Admin access required'}), 403
        
        with get_db() as (cursor, connection):
            # Delete transaction items first (has foreign key to transactions)
            cursor.execute("DELETE FROM transaction_items")
            deleted_items = cursor.rowcount
            
            # Delete transactions
            cursor.execute("DELETE FROM transactions")
            deleted_transactions = cursor.rowcount
            
            connection.commit()
            
            print(f"✓ Cleared {deleted_transactions} transactions and {deleted_items} transaction items")
            
            return jsonify({
                'success': True,
                'message': f'Successfully cleared {deleted_transactions} transactions',
                'transactions_deleted': deleted_transactions,
                'items_deleted': deleted_items
            }), 200
    
    except Exception as e:
        print(f"Error clearing transactions: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== CATEGORY MANAGEMENT ====================

@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    query = "SELECT name FROM categories ORDER BY display_order"
    categories = execute_query(query, fetch_all=True)
    
    category_list = [{'name': 'all'}]  # Add 'All' category
    for cat in categories:
        category_list.append({
            'name': cat[0]
        })
    
    return jsonify({
        'success': True,
        'categories': category_list
    })

# ==================== DASHBOARD STATISTICS ====================

@app.route('/api/dashboard/stats', methods=['GET'])
@login_required
def get_dashboard_stats():
    """Get dashboard statistics"""
    today_query = """
        SELECT 
            COALESCE(SUM(total), 0) as today_sales,
            COALESCE(SUM(
                (SELECT COALESCE(SUM(quantity), 0) 
                 FROM transaction_items 
                 WHERE transaction_id = transactions.id)
            ), 0) as items_sold
        FROM transactions
        WHERE DATE(created_at) = CURRENT_DATE
        AND status = 'completed'
    """
    today_result = execute_query(today_query, fetch_one=True)
    
    low_stock_query = "SELECT COUNT(*) FROM products WHERE stock < COALESCE(min_stock_level, 10)"
    low_stock_result = execute_query(low_stock_query, fetch_one=True)
    
    total_products_query = "SELECT COUNT(*) FROM products"
    total_products_result = execute_query(total_products_query, fetch_one=True)
    
    # Calculate total profit from all transactions
    profit_query = """
        SELECT COALESCE(SUM(
            ti.quantity * (ti.price_at_time - p.buy_price)
        ), 0) as total_profit
        FROM transaction_items ti
        JOIN products p ON ti.product_id = p.id
        JOIN transactions t ON ti.transaction_id = t.id
        WHERE t.status = 'completed'
    """
    profit_result = execute_query(profit_query, fetch_one=True)
    total_profit = float(profit_result[0]) if profit_result else 0
    
    return jsonify({
        'success': True,
        'stats': {
            'today_sales': float(today_result[0]) if today_result else 0,
            'items_sold': today_result[1] if today_result else 0,
            'low_stock_count': low_stock_result[0] if low_stock_result else 0,
            'total_products': total_products_result[0] if total_products_result else 0,
            'total_profit': total_profit  # Add this field
        }
    })

# ==================== INITIALIZE DATABASE ====================

with app.app_context():
    initialize_database_tables()    






#### building projects


@app.route('/ask_ai', methods=['POST'])
def ask_ai():
    """Analyze database data using Google Gemini AI"""
    try:
        data = request.json
        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'success': False, 'answer': 'Please provide a question'})
        
        # Step 1: Get ALL data from database
        database_data = get_all_database_data()
        
        # Step 2: Call Gemini AI with the data
        answer = call_gemini_ai(question, database_data)
        
        return jsonify({
            'success': True,
            'answer': answer
        })
        
    except Exception as e:
        print(f"AI Error: {str(e)}")
        return jsonify({'success': False, 'answer': f'Error: {str(e)}'}), 500

def get_all_database_data():
    """Extract ALL data from database in readable format"""
    with get_db() as (cursor, connection):
        # Get basic statistics FIRST (so AI can answer even if full query fails)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_projects,
                COALESCE(SUM(totalcontractamount), 0) as total_value,
                COALESCE(SUM(depositorbullet), 0) as total_deposit,
                COUNT(DISTINCT clientname) as unique_clients
            FROM connectlinkdatabase 
            WHERE totalcontractamount > 0
        """)
        stats = cursor.fetchone()
        
        data_summary = []
        data_summary.append("=== DATABASE STATISTICS ===")
        data_summary.append(f"Total Projects: {stats[0]}")
        data_summary.append(f"Total Contract Value: ${float(stats[1]):,.2f}")
        data_summary.append(f"Total Deposit Collected: ${float(stats[2]):,.2f}")
        data_summary.append(f"Unique Clients: {stats[3]}")
        
        # Get payment methods
        cursor.execute("""
            SELECT 
                COALESCE(paymentmethod, 'Not Specified') as method,
                COUNT(*) as project_count,
                COALESCE(SUM(totalcontractamount), 0) as total_amount
            FROM connectlinkdatabase 
            GROUP BY paymentmethod
            ORDER BY total_amount DESC
            LIMIT 10
        """)
        payment_methods = cursor.fetchall()
        
        data_summary.append("\n=== PAYMENT METHODS ===")
        for method, count, total in payment_methods:
            data_summary.append(f"{method}: {count} projects, Total: ${float(total):,.2f}")
        
        # Get recent projects
        cursor.execute("""
            SELECT 
                clientname, projectname, 
                COALESCE(totalcontractamount, 0) as total,
                COALESCE(depositorbullet, 0) as deposit,
                paymentmethod
            FROM connectlinkdatabase 
            ORDER BY COALESCE(datedepositorbullet, CURRENT_DATE) DESC 
            LIMIT 5
        """)
        recent_projects = cursor.fetchall()
        
        data_summary.append("\n=== RECENT PROJECTS ===")
        for client, project, total, deposit, method in recent_projects:
            data_summary.append(f"{client}: {project}")
            data_summary.append(f"  Amount: ${float(total):,.2f}, Deposit: ${float(deposit):,.2f}, Method: {method}")
        
        return "\n".join(data_summary)

def call_gemini_ai(question, database_data):
    """Call Google Gemini AI with our database data"""
    try:
        # Initialize the CORRECT model name
        # Try different available models in order
        available_models = ['gemini-1.0-pro', 'gemini-pro', 'models/gemini-pro']
        
        for model_name in available_models:
            try:
                model = genai.GenerativeModel(model_name)
                
                # Create the prompt
                prompt = f"""
                You are a financial data analyst. Analyze this database and answer the question.
                
                DATABASE DATA:
                {database_data}
                
                QUESTION: {question}
                
                INSTRUCTIONS:
                1. Answer based ONLY on the data provided
                2. Be specific with numbers
                3. Format money as $X,XXX.XX
                4. Keep answer concise
                5. If data missing, say what information is available
                
                ANSWER:
                """
                
                # Generate response
                response = model.generate_content(prompt)
                return response.text
                
            except Exception as e:
                print(f"Tried model {model_name}: {str(e)}")
                continue
        
        # If all models fail, try the list models approach
        models = genai.list_models()
        for m in models:
            if 'generateContent' in m.supported_generation_methods:
                model = genai.GenerativeModel(m.name)
                response = model.generate_content(f"Database: {database_data}\nQuestion: {question}")
                return response.text
        
        # Fallback to direct database query
        return get_direct_answer(question)
        
    except Exception as e:
        print(f"Gemini error: {str(e)}")
        return get_direct_answer(question)

def get_direct_answer(question):
    """Direct database query without AI"""
    with get_db() as (cursor, connection):
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['total contract', 'total value', 'overall', 'sum']):
            cursor.execute("SELECT COALESCE(SUM(totalcontractamount), 0) FROM connectlinkdatabase")
            total = cursor.fetchone()[0]
            return f"Total Contract Value: **${float(total):,.2f}**"
        
        elif 'deposit' in question_lower:
            cursor.execute("SELECT COALESCE(SUM(depositorbullet), 0) FROM connectlinkdatabase")
            deposit = cursor.fetchone()[0]
            return f"Total Deposits Collected: **${float(deposit):,.2f}**"
        
        elif 'how many' in question_lower or 'count' in question_lower:
            cursor.execute("SELECT COUNT(*) FROM connectlinkdatabase")
            count = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(DISTINCT clientname) FROM connectlinkdatabase")
            clients = cursor.fetchone()[0]
            return f"**{count}** total projects from **{clients}** unique clients"
        
        elif 'payment method' in question_lower:
            cursor.execute("""
                SELECT paymentmethod, COUNT(*), COALESCE(SUM(totalcontractamount), 0)
                FROM connectlinkdatabase 
                GROUP BY paymentmethod 
                ORDER BY SUM(totalcontractamount) DESC
            """)
            methods = cursor.fetchall()
            answer = "**Payment Methods:**\n"
            for method, count, total in methods:
                method_name = method if method else "Not specified"
                answer += f"- {method_name}: {count} projects, ${float(total):,.2f}\n"
            return answer
        
        elif 'recent' in question_lower or 'latest' in question_lower:
            cursor.execute("""
                SELECT clientname, projectname, totalcontractamount
                FROM connectlinkdatabase 
                ORDER BY COALESCE(datedepositorbullet, CURRENT_DATE) DESC 
                LIMIT 5
            """)
            recent = cursor.fetchall()
            answer = "**Recent Projects:**\n"
            for client, project, amount in recent:
                answer += f"- {client}: {project} (${float(amount or 0):,.2f})\n"
            return answer
        
        else:
            return f"I can answer questions about:\n• Total contract value\n• Total deposits\n• Number of projects and clients\n• Payment methods\n• Recent projects\n\nTry asking: 'What is my total contract value?' or 'How many projects do I have?'"
        

ACCESS_TOKEN = "EAAMk5Wj6ZBLABQZAZBaIfs9V338WQbkpZB5KfVQ58fUcjrX4nZCJm9SqSWsG6ouZCl9ZAIXGZCDo7xzitOUO5AgsPwtIaUMqpHj9iZCsJI4irPjcryKpeAchBf0ASjNPazQRrwBeL3dMs3tu4jbmlg3B2fYiZCEJhQQO4ZB4WSH8oHh07CCRKR2N2ZBWKMxVbLeyO8fA3gZDZD"
PHONE_NUMBER_ID = "977519838770637"
VERIFY_TOKEN = "2012753506232550"
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
power = "Echelon Equipment Pvt Ltd"
bot = "ConnectLink Properties"
QUOTATION_DOWNLOAD_TEMPLATE_NAME = os.getenv('WHATSAPP_QUOTATION_DOWNLOAD_TEMPLATE', 'quotationdownload')
CONTRACT_DOWNLOAD_TEMPLATE_NAME = os.getenv('WHATSAPP_CONTRACT_DOWNLOAD_TEMPLATE', 'contractdownloadtemplate')
PUBLIC_BASE_URL = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')
QUOTATION_SHARE_TOKEN_HOURS = int(os.getenv('QUOTATION_SHARE_TOKEN_HOURS', '168'))


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
                
                # ========= SHEET 4 — PROJECT 125 WORK SCOPE (if exists) =========
                project_125_exists = len(df_projects[df_projects['id'] == 125]) > 0
                if project_125_exists:
                    work_scope_data = {
                        'Work Scope': [
                            'Bathroom Plumbing',
                            'Main Kitchen',
                            'Bedroom Cabinets',
                            'TV unit',
                            'Boundary wall',
                            'Kitchenette',
                            'Electricals',
                            'Manhole construction',
                            'Painting',
                            'Gate',
                            'Tank Stand',
                            'Landscaping',
                            'Final fix Plumbing',
                            'Final fix Electricals',
                            'Verandah roof',
                            'Garage roof',
                            'Verandah Tiles',
                            'Floor Tiles'
                        ],
                        'Start date': [
                            '31/04/2026',
                            '27/3/2026',
                            '28/3/2026',
                            '5/4/2026',
                            '10/4/2026',
                            '5/4/2026',
                            '4/4/2026',
                            '4/4/2026',
                            '6/4/2026',
                            '12/4/2026',
                            '26/4/2026',
                            '1/5/2026',
                            '6/5/2026',
                            '6/5/2026',
                            '11/05/2026',
                            '16/5/2026',
                            '17/5/2026',
                            '17/5/2026'
                        ],
                        'End date': [
                            '3/4/2026',
                            '4/4/2026',
                            '4/4/2026',
                            '6/4/2026',
                            '',
                            '7/4/2026',
                            '8/4/2026',
                            '9/4/2026',
                            '11/4/2026',
                            '13/4/2026',
                            '30/4/2026',
                            '10/5/2026',
                            '10/5/2026',
                            '10/5/2026',
                            '16/5/2026',
                            '21/5/2026',
                            '23/5/2025',
                            '23/5/2025'
                        ],
                        'Days': [
                            4,
                            7,
                            6,
                            1,
                            '',
                            2,
                            4,
                            5,
                            5,
                            1,
                            4,
                            9,
                            4,
                            4,
                            5,
                            5,
                            6,
                            6
                        ]
                    }
                    df_work_scope = pd.DataFrame(work_scope_data)
                    df_work_scope.to_excel(writer, index=False, sheet_name="Project 125 Work Scope")


            output.seek(0)

            log_activity('export_portfolio', f'Projects portfolio exported to Excel ({len(df_projects)} projects, {len(df_notes)} notes)', 'project', None, {'projects': len(df_projects), 'notes': len(df_notes), 'format': 'excel'})
            
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
            
            # Log user removal
            try:
                log_activity(
                    'user_removed',
                    f'System user (ID: {user_id}) removed',
                    'user',
                    user_id,
                    {'removed_by': session.get('user_name', 'Unknown')}
                )
            except Exception as log_err:
                print(f"⚠️ Failed to log user removal: {log_err}")
            
            return jsonify({
                'status': 'success',
                'message': f'User has been removed successfully'
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to remove user: {str(e)}'
            }), 500


@app.route('/update-system-user', methods=['POST'])
def update_system_user():
    data = request.get_json() or {}

    user_id = data.get('user_id')
    full_name = (data.get('fullname') or '').strip()
    email = (data.get('email') or '').strip()
    whatsapp = (data.get('whatsapp') or '').strip()

    if not user_id:
        return jsonify({'status': 'error', 'message': 'User ID is required'}), 400

    if not full_name or not email:
        return jsonify({'status': 'error', 'message': 'Name and email are required'}), 400

    with get_db() as (cursor, connection):
        try:
            cursor.execute("""
                UPDATE connectlinkusers
                SET name = %s,
                    email = %s,
                    whatsapp = %s
                WHERE id = %s
            """, (full_name, email, whatsapp or None, user_id))

            if cursor.rowcount == 0:
                return jsonify({'status': 'error', 'message': 'User not found'}), 404

            connection.commit()

            # Log user update
            try:
                log_activity(
                    'user_updated',
                    f'System user (ID: {user_id}) updated - name: {full_name}, email: {email}',
                    'user',
                    user_id,
                    {'name': full_name, 'email': email, 'whatsapp': whatsapp, 'updated_by': session.get('user_name', 'Unknown')}
                )
            except Exception as log_err:
                print(f"⚠️ Failed to log user update: {log_err}")

            return jsonify({
                'status': 'success',
                'message': 'User updated successfully'
            })
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Failed to update user: {str(e)}'
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

                # Look up user's source_id from admin_users for permission lookup
                cursor.execute("SELECT source_system, source_id FROM admin_users WHERE id = %s", (userid,))
                au = cursor.fetchone()
                source_sys = au[0] if au else 'projects'
                source_id = au[1] if au else userid

                # Check user permissions for Payments tab across all user types
                # Try source_system first, then 'projects', then fallback to hr/hardware
                perms = get_user_permissions(source_sys, source_id)
                can_view_payments = perms.get('can_view_payments', False) or perms.get('is_super_admin', False)
                if not can_view_payments:
                    for utype in ('projects', 'hr', 'hardware'):
                        if utype == source_sys:
                            continue
                        p = get_user_permissions(utype, source_id)
                        if p.get('can_view_payments', False) or p.get('is_super_admin', False):
                            can_view_payments = True
                            break

                can_edit_projects = perms.get('can_edit_projects', True)
                # Only override to True if user is super admin
                if perms.get('is_super_admin', False):
                    can_edit_projects = True
                # If still not set, try primary user_type='projects' as fallback
                if not can_edit_projects and source_sys != 'projects':
                    p2 = get_user_permissions('projects', source_id)
                    if p2.get('can_edit_projects', False) or p2.get('is_super_admin', False):
                        can_edit_projects = True

                # Check other portal permissions for navbar switching
                can_manage_hr = perms.get('can_manage_hr', False) or perms.get('is_super_admin', False)
                can_manage_hardware = perms.get('can_manage_hardware', False) or perms.get('is_super_admin', False)
                can_manage_roles = perms.get('can_manage_roles', False) or perms.get('is_super_admin', False)
                if not any([can_manage_hr, can_manage_hardware, can_manage_roles]):
                    for utype in ('hr', 'hardware', 'projects'):
                        p = get_user_permissions(utype, source_id)
                        if p.get('is_super_admin', False):
                            can_manage_hr = can_manage_hardware = can_manage_roles = True
                            break
                        if p.get('can_manage_hr', False): can_manage_hr = True
                        if p.get('can_manage_hardware', False): can_manage_hardware = True
                        if p.get('can_manage_roles', False): can_manage_roles = True

                print("Back from adventures")

                return render_template('adminpage.html', **results, userid=userid, user_name=user_name,
                                       can_view_payments=can_view_payments, can_edit_projects=can_edit_projects,
                                       can_manage_hr=can_manage_hr, can_manage_hardware=can_manage_hardware,
                                       can_manage_roles=can_manage_roles)
                    
            except Exception as e:

                print(f"Dashboard error: {e}")
                print(traceback.format_exc())

                return render_template('mainindex.html')

        else:
                return render_template('mainindex.html')

# Dedicated WhatsApp App Page
@app.route('/whatsapp-app')
def whatsapp_app():
    user_uuid = session.get('user_uuid')
    user_name = session.get('user_name')
    userid = session.get('userid')
    if user_uuid:
        return render_template('whatsapp_app.html', user_name=user_name, userid=userid)
    return render_template('mainindex.html')


@app.route('/api/request-reset-code', methods=['POST'])
def request_reset_code():
    """Send a 6-digit verification code to the user's WhatsApp for password reset"""
    try:
        data = request.get_json()
        username_or_email = data.get('username', '').strip()
        if not username_or_email:
            return jsonify({'success': False, 'message': 'Please enter your username or email.'}), 400

        with get_db() as (cursor, connection):
            # Look up user in admin_users
            cursor.execute("""
                SELECT id, username, full_name, email, whatsapp
                FROM admin_users WHERE (username = %s OR email = %s) AND is_active = TRUE
            """, (username_or_email, username_or_email))
            user = cursor.fetchone()

            if not user:
                # Fallback to connectlinkusers
                cursor.execute("""
                    SELECT id, name, email, whatsapp FROM connectlinkusers WHERE email = %s OR name = %s
                """, (username_or_email, username_or_email))
                user_row = cursor.fetchone()
                if user_row:
                    user_id = user_row[0]
                    user_name = user_row[1]
                    user_email = user_row[2] or ''
                    user_whatsapp = str(user_row[3] or '')
                else:
                    return jsonify({'success': False, 'message': 'User not found. Please check your email/username.'}), 404
            else:
                user_id = user[0]
                user_name = user[2] or user[1]
                user_email = user[3] or ''
                user_whatsapp = user[4] or ''

            if not user_whatsapp:
                return jsonify({'success': False, 'message': 'No WhatsApp number found for this account. Contact your administrator.'}), 400

            # Generate 6-digit code
            code = str(random.randint(100000, 999999))
            expires_at = datetime.now() + timedelta(minutes=10)

            # Save code to DB
            cursor.execute("""
                INSERT INTO password_reset_codes (username, code, whatsapp, expires_at)
                VALUES (%s, %s, %s, %s)
            """, (username_or_email, code, user_whatsapp, expires_at))
            connection.commit()

            # Send code via WhatsApp
            recipient_clean = re.sub(r'[^0-9]', '', user_whatsapp)
            if recipient_clean.startswith('0'):
                recipient_clean = '263' + recipient_clean[1:]
            elif not recipient_clean.startswith('263'):
                recipient_clean = '263' + recipient_clean

            message_text = (
                f"🔐 *ConnectLink Password Reset*\n\n"
                f"Hi {user_name},\n\n"
                f"Your verification code is:\n\n"
                f"*{code}*\n\n"
                f"This code expires in 10 minutes.\n\n"
                f"If you did not request this, please ignore this message."
            )

            try:
                from urllib.parse import urlencode
                import urllib.request
                whatsapp_text = message_text.replace('*', '')
                payload = {
                    "messaging_product": "whatsapp",
                    "to": recipient_clean,
                    "type": "text",
                    "text": {"body": whatsapp_text}
                }
                payload_json = json.dumps(payload)
                headers = {
                    "Authorization": f"Bearer {ACCESS_TOKEN}",
                    "Content-Type": "application/json"
                }
                req = urllib.request.Request(WHATSAPP_API_URL, data=payload_json.encode(), headers=headers, method='POST')
                resp = urllib.request.urlopen(req)
                resp_data = json.loads(resp.read().decode())
                wa_status = 'sent' if resp_data.get('messages') else 'failed'

                # Log to whatsapp_messages
                try:
                    cursor.execute("""
                        INSERT INTO whatsapp_messages (sender_phone, sender_name, message_text, message_type, direction, status)
                        VALUES (%s, %s, %s, 'text', 'outgoing', %s)
                    """, (recipient_clean, 'System', f"Password reset code sent to {username_or_email}", wa_status))
                    connection.commit()
                except Exception:
                    pass
            except Exception as wa_err:
                print(f"WhatsApp send error: {wa_err}")
                # Still return success to the user (code is in DB)
                pass

            return jsonify({
                'success': True,
                'message': f'A verification code has been sent to the WhatsApp number on file for {username_or_email}.',
                'whatsapp_masked': user_whatsapp[:3] + '****' + user_whatsapp[-3:] if len(user_whatsapp) > 6 else '****'
            }), 200

    except Exception as e:
        print(f"Request reset code error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/verify-reset-code', methods=['POST'])
def verify_reset_code():
    """Verify the code and reset the password"""
    try:
        data = request.get_json()
        username_or_email = data.get('username', '').strip()
        code = data.get('code', '').strip()
        new_password = data.get('new_password', '')

        if not username_or_email or not code or not new_password:
            return jsonify({'success': False, 'message': 'All fields are required.'}), 400
        if len(new_password) < 4:
            return jsonify({'success': False, 'message': 'Password must be at least 4 characters.'}), 400

        with get_db() as (cursor, connection):
            # Find valid code
            cursor.execute("""
                SELECT id, code, expires_at, used FROM password_reset_codes
                WHERE username = %s AND used = FALSE
                ORDER BY created_at DESC LIMIT 1
            """, (username_or_email,))
            row = cursor.fetchone()

            if not row:
                return jsonify({'success': False, 'message': 'No verification code found. Please request a new one.'}), 400

            code_id = row[0]
            stored_code = row[1]
            expires_at = row[2]
            used = row[3]

            if used:
                return jsonify({'success': False, 'message': 'This code has already been used. Please request a new one.'}), 400

            if datetime.now() > expires_at:
                return jsonify({'success': False, 'message': 'Code has expired. Please request a new one.'}), 400

            if code != stored_code:
                return jsonify({'success': False, 'message': 'Incorrect verification code. Please try again.'}), 400

            # Mark code as used
            cursor.execute("UPDATE password_reset_codes SET used = TRUE WHERE id = %s", (code_id,))

            # Reset password in ALL tables for universal sync
            cursor.execute("""
                UPDATE admin_users SET password = %s, must_reset_password = FALSE, updated_at = NOW()
                WHERE username = %s
            """, (new_password, username_or_email))

            cursor.execute("""
                UPDATE connectlinkusers SET password = %s WHERE email = %s OR name = %s
            """, (new_password, username_or_email, username_or_email))

            cursor.execute("""
                UPDATE hardware_users SET password = %s WHERE username = %s
            """, (new_password, username_or_email))

            connection.commit()
            log_activity('password_reset', f'Password reset via WhatsApp code for: {username_or_email}', 'user', 0)
            return jsonify({'success': True, 'message': '✅ Password reset successfully! You can now log in with your new password.'}), 200

    except Exception as e:
        print(f"Verify reset code error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/reset-password', methods=['POST'])
def reset_password():
    """Reset password for any user (checks admin_users, connectlinkusers, hardware_users)"""
    try:
        data = request.get_json()
        username_or_email = data.get('username', '').strip()
        old_password = data.get('old_password', '')
        new_password = data.get('new_password', '')

        if not username_or_email or not old_password or not new_password:
            return jsonify({'success': False, 'message': 'All fields are required.'}), 400
        if len(new_password) < 4:
            return jsonify({'success': False, 'message': 'New password must be at least 4 characters.'}), 400

        with get_db() as (cursor, connection):
            # Try admin_users first
            cursor.execute("SELECT id, password, must_reset_password FROM admin_users WHERE username = %s", (username_or_email,))
            row = cursor.fetchone()
            if row:
                if row[1] != old_password:
                    return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 401
                cursor.execute("UPDATE admin_users SET password = %s, must_reset_password = FALSE, updated_at = NOW() WHERE id = %s", (new_password, row[0]))
                connection.commit()
                log_activity('password_reset', f'Password reset for admin user: {username_or_email}', 'user', row[0])
                return jsonify({'success': True, 'message': 'Password reset successfully!', 'must_reset': bool(row[2])}), 200

            # Fallback: try connectlinkusers
            cursor.execute("SELECT id, password FROM connectlinkusers WHERE email = %s OR name = %s", (username_or_email, username_or_email))
            row = cursor.fetchone()
            if row:
                if row[1] != old_password:
                    return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 401
                cursor.execute("UPDATE connectlinkusers SET password = %s WHERE id = %s", (new_password, row[0]))
                # Also update admin_users if it exists there
                try:
                    cursor.execute("UPDATE admin_users SET password = %s, updated_at = NOW() WHERE username = %s", (new_password, username_or_email))
                except Exception:
                    pass
                connection.commit()
                log_activity('password_reset', f'Password reset for projects user: {username_or_email}', 'user', row[0])
                return jsonify({'success': True, 'message': 'Password reset successfully!'}), 200

            # Fallback: try hardware_users
            cursor.execute("SELECT id, password FROM hardware_users WHERE username = %s", (username_or_email,))
            row = cursor.fetchone()
            if row:
                if row[1] != old_password:
                    return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 401
                cursor.execute("UPDATE hardware_users SET password = %s WHERE id = %s", (new_password, row[0]))
                # Also update admin_users if it exists there
                try:
                    cursor.execute("UPDATE admin_users SET password = %s, updated_at = NOW() WHERE username = %s", (new_password, username_or_email))
                except Exception:
                    pass
                connection.commit()
                log_activity('password_reset', f'Password reset for hardware user: {username_or_email}', 'user', row[0])
                return jsonify({'success': True, 'message': 'Password reset successfully!'}), 200

            return jsonify({'success': False, 'message': 'User not found.'}), 404

    except Exception as e:
        print(f"Password reset error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/login', methods=['