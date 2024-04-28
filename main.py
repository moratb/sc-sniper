from src.scheduler import SCJobScheduler
from src.listnerer import SCTelegramListener
import asyncio
from telethon.sync import events
import threading
from multiprocessing import Process


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

        print('Written new message to DataBase')

    await client.run_until_disconnected()


def messages_listening_thread():
    asyncio.run(messages_listening())

def jobs_scheduling_thread():
    scheduler = SCJobScheduler()
    scheduler.init_scheduler()
    scheduler.schedule_jobs()
    scheduler.scheduler.start()
    while True:
        pass #TODO maybe think about smth better to keep thread alive


if __name__ == "__main__":
    t1 = threading.Thread(target=messages_listening_thread)
    t2 = Process(target=jobs_scheduling_thread) # USing process poll instead of thread to match executor config
    t1.start()
    t2.start()


