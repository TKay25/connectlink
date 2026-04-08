#!/usr/bin/env python3
"""
Debug script to check table structure and column ordering
"""
import sys
sys.path.insert(0, '/c:\\Users\\Lenovo\\Documents\\GitHub\\connectlink')

from db_helper import get_db

with get_db() as (cursor, connection):
    # Get all columns from connectlinkdatabase
    cursor.execute("""
        SELECT column_name, ordinal_position, data_type
        FROM information_schema.columns
        WHERE table_name = 'connectlinkdatabase'
        ORDER BY ordinal_position
    """)
    
    columns = cursor.fetchall()
    
    print("\n" + "="*100)
    print("CONNECTLINKDATABASE TABLE STRUCTURE")
    print("="*100)
    print(f"{'#':<4} {'Column Name':<30} {'Data Type':<20} {'Position':<10}")
    print("-"*100)
    
    for idx, col_name, data_type in columns:
        print(f"{idx:<4} {col_name:<30} {data_type:<20} {idx:<10}")
    
    print("-"*100)
    print(f"TOTAL COLUMNS: {len(columns)}")
    print("="*100 + "\n")
    
    # Check for quotation_id column specifically
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns
        WHERE table_name = 'connectlinkdatabase' AND column_name = 'quotation_id'
    """)
    
    result = cursor.fetchone()
    if result:
        print(f"✓ Column 'quotation_id' exists in database")
    else:
        print(f"✗ Column 'quotation_id' NOT FOUND in database")
    
    # Get first row to see actual data
    cursor.execute("SELECT * FROM connectlinkdatabase LIMIT 1")
    row = cursor.fetchone()
    
    if row:
        print(f"\n✓ Sample data found: {len(row)} columns returned from SELECT *")
        print(f"Expected columns: {len(columns)}")
        if len(row) == len(columns):
            print(f"✓ Column count matches!")
        else:
            print(f"✗ Column count MISMATCH: got {len(row)}, expected {len(columns)}")
    else:
        print(f"\n✗ No data in connectlinkdatabase")
