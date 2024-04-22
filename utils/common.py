import functools
import traceback
import sqlite3
import time as t
import datetime as dt
import requests
import pandas as pd
import numpy as np
import os
from dotenv import load_dotenv
load_dotenv()
API_KEY = os.getenv('bi_api_key')


class SQLiteDB:
    def __init__(self, database):
        self.database = database
        self.conn = None

    def __enter__(self):
        self.conn = sqlite3.connect(self.database)
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.conn.close()


def retry(max_attempts=10, retry_delay=1):
    def decorator_retry(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            attempt = 0
            while attempt < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    print(f"Attempt {attempt} failed with error: {e}.\nTraceback: {traceback.format_exc()}")
                    attempt += 1
                    if attempt < max_attempts:
                        t.sleep(retry_delay)
                    else:
                        print("Max retries reached!")
            return None
        return wrapper
    return decorator_retry


@retry(max_attempts=10, retry_delay=1)
def get_price_data(token, time_from, time_to):
    url = "https://public-api.birdeye.so/defi/ohlcv"
    headers = {"x-chain": "solana", "X-API-KEY": API_KEY}
    params = {
        "address": token,
        "type": '1m',
        "time_from": time_from,
        "time_to": time_to
    }
    response = requests.get(url, headers=headers, params=params)
    prices_df = pd.DataFrame(response.json()['data']['items'])
    prices_df['address'] = token
    return prices_df