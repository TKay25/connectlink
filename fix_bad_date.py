import sys
sys.path.insert(0, '.')
from db_helper import get_db

with get_db() as (cursor, conn):
    # Find which column has year 72026
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
        cursor.execute(f"SELECT id, clientname, projectname, {col} FROM connectlinkdatabase WHERE EXTRACT(YEAR FROM {col}) > 2100 OR EXTRACT(YEAR FROM {col}) < 1900")
        rows = cursor.fetchall()
        if rows:
            for r in rows:
                print(f'BAD DATE FOUND: id={r[0]}, client={r[1]}, project={r[2]}, column={col}, value={r[3]}')
