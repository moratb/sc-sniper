import sys
sys.path.insert(1, './')
from utils.common import *
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

def dummy_task(a):
    print('JOB DONE!! ', a)

# Setting up the scheduler with the same shared job store
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///./dbs/jobs.sqlite')
}
scheduler = BackgroundScheduler(jobstores=jobstores, timezone="UTC")
scheduler.start()

# Keep the script running
try:
    while True:
        scheduler.print_jobs()
        t.sleep(8)
except KeyboardInterrupt:
    print('Stopped.')
finally:
    # Shut down the scheduler when exiting the app
    scheduler.shutdown()