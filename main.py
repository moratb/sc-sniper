import time as t
import sys
from src.oracle import SCOracle
from src.scheduler import SCJobScheduler
from src.listnerer import SCTelegramListener
from utils.logger import create_logger
import asyncio
from telethon.sync import events
import threading
from multiprocessing import Process

logger = create_logger()


async def messages_listening():
    handler = SCTelegramListener()
    client = await handler.start_telegram_client()
    chat_id = await handler.get_chat_id(client)

    @client.on(events.NewMessage(chats=[chat_id]))
    async def handle_message(event):
        message = event.message
        try:
            msg = handler.read_messages(message)
            parsed = handler.parse_messages(msg)
            handler.write_to_db(parsed)
        except Exception as e:
            logger.info(f"Message reading issue: {e}")


    catch_up_task = asyncio.create_task(handler.catch_up_periodically())

    await client.run_until_disconnected()


def messages_listening_thread():
    asyncio.run(messages_listening())


def jobs_scheduling_thread():
    scheduler = SCJobScheduler()
    scheduler.init_scheduler()
    scheduler.scheduler.start()
    while True:
        t.sleep(120)
        scheduler.schedule_jobs()
        pass



def oracle_scheduling_thread():
    while True:
        try:
            oracle = SCOracle()
            db_tokens = oracle.get_db_tokens()
            wallet_tokens = oracle.get_wallet_tokens()
            tokens_for_sale = oracle.calculate_prices(db_tokens, wallet_tokens)
            oracle.sell_tokens(tokens_for_sale)
        except Exception as e:
            print(e)
        t.sleep(60)


if __name__ == "__main__":
    t.sleep(5)
    mode = sys.argv[1]

    if mode == "ls":
        t1 = threading.Thread(target=messages_listening_thread)
        t2 = Process(target=jobs_scheduling_thread)
        t1.start()
        t2.start()

    elif mode == "oracle":
        t3 = Process(target=oracle_scheduling_thread)
        t3.start()
    
    elif mode == 'full':
        t1 = threading.Thread(target=messages_listening_thread)
        t2 = Process(target=jobs_scheduling_thread)
        t3 = Process(target=oracle_scheduling_thread)
        t1.start()
        t2.start()
        t3.start()