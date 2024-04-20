import sys
sys.path.insert(1, './')
from utils.common import *
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

# Setting up the scheduler with the same shared job store
jobstores = {
    'default': SQLAlchemyJobStore(url='sqlite:///./dbs/jobs.sqlite')
}
scheduler = BackgroundScheduler(jobstores=jobstores)
scheduler.start()
scheduler.print_jobs()
scheduler.shutdown()