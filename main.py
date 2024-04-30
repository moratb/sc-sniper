import time
from time import sleep
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
        msg = handler.read_messages(message)
        parsed = handler.parse_messages(msg)
        handler.write_to_db(parsed)

    await client.run_until_disconnected()


def messages_listening_thread():
    asyncio.run(messages_listening())


def jobs_scheduling_thread():
    scheduler = SCJobScheduler()
    scheduler.init_scheduler()
    scheduler.scheduler.start()
    while True:
        time.sleep(60)
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
        sleep(60)  # TODO sleep timer or else?


if __name__ == "__main__":
    t1 = threading.Thread(target=messages_listening_thread)
    t2 = Process(target=jobs_scheduling_thread)  # Using process poll instead of thread to match executor config
    t3 = threading.Thread(target=oracle_scheduling_thread)
    t1.start()
    t2.start()
    t3.start()
