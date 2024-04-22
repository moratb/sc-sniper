import sys
from utils.common import *

# Connect to a database (or create one if it doesn't exist)
with SQLiteDB('dbs/calls2.db') as conn:
    create_table_query = """
    CREATE TABLE IF NOT EXISTS calls (
        id INTEGER PRIMARY KEY,
        date TEXT,
        address TEXT,
        expected_launch_time TEXT,
        expected_launch_time_ts TEXT,
        s_mm2 BOOL,
        s_ma2 BOOL,
        s_fa2 BOOL,
        s_q INTEGER,
        s_sni INTEGER,
        mcap_num INTEGER,
        liq_num INTEGER,
        launched BOOL,
        launch_time TEXT,
        buy BOOL,
        buy_time TEXT,
        buy_price REAL
    )
    """
    conn.execute(create_table_query)