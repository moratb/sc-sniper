from src.scheduler import SCJobScheduler
from src.listnerer import SCTelegramListener
import asyncio

if __name__ == "__main__":
    tg_client = SCTelegramListener()
    asyncio.run(tg_client.parse())  # TODO Will be a async threadpool here? Separate process
    # scheduler = SCJobScheduler()
    # scheduler.init_scheduler()
    # scheduler.schedule_jobs()
    while True:
        continue
