from src.scheduler import SCJobScheduler


if __name__ == "__main__":
    scheduler = SCJobScheduler()
    scheduler.init_scheduler()
    scheduler.schedule_jobs()


