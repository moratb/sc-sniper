import datetime as dt
import os

from pytz import utc
import pandas as pd
import sys

from utils.common import *

##loading scheduler
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore


class SCJobScheduler:

    def __init__(self):
        self.jobstores = {'default': SQLAlchemyJobStore(url='sqlite:///dbs/jobs.sqlite')
                          }
        self.executors = {
            'default': {'type': 'threadpool', 'max_workers': 1}
        }
        self.job_defaults = {
            'coalesce': False,
            'max_instances': 1
        }
        self.scheduler = None

    def dummy_func(self, token, launch_time):
        print(token, launch_time)
        print('dummy func triggered')
        return

    def update_launch_date(self, index, status, time):
        ltime = f'"{time}"' if time else "NULL"
        with SQLiteDB('dbs/calls.db') as conn:
            update_statement = f"""
            UPDATE calls
            SET launched = {status}, launch_time = {ltime}
            WHERE id = {index}
            """
            conn.execute(update_statement)

    def schedule_jobs(self):
        with SQLiteDB('dbs/calls.db') as conn:
            query = "SELECT * FROM calls "  # WHERE launched is NULL
            df = pd.read_sql_query(query, conn)
            df = df.loc[dt.datetime.now() > pd.to_datetime(df['expected_launch_time_ts']) + dt.timedelta(minutes=5)]
            for i, row in df[-2:].iterrows():
                print('trying: ', i, row['address'])
                elt = int(dt.datetime.strptime(row['expected_launch_time_ts'], '%Y-%m-%d %H:%M:%S').timestamp())
                tmp_df = get_price_data(row['address'], elt - 60 * 60, elt + 60 * 60 * 25)
                if not tmp_df.empty:
                    launched = True
                    launch_time = dt.datetime.fromtimestamp(tmp_df['unixTime'].min(), tz=dt.timezone.utc)
                    self.scheduler.add_job(func=self.dummy_func,
                                           trigger='date',
                                           run_date=str(launch_time + dt.timedelta(minutes=20)),
                                           id=str(row['id']),
                                           jobstore=self.jobstores['default'],
                                           replace_existing=True,
                                           kwargs={'token': row['address'], 'launch_time': launch_time})
                else:
                    print('not launched')
                    launched = False
                    launch_time = None
                self.update_launch_date(row['id'], launched, launch_time)

    def init_scheduler(self):
        self.scheduler = BackgroundScheduler(jobstores=self.jobstores, executors=self.executors,
                                             job_defaults=self.job_defaults, timezone="UTC")
        self.scheduler.start()
        return
