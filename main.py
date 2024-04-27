from src.scheduler import SCJobScheduler
from src.listnerer import SCTelegramListener
import asyncio
from telethon.sync import events
import threading


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
    scheduler.scheduler.shutdown()


if __name__ == "__main__":
    t1 = threading.Thread(target=messages_listening_thread)
    t2 = threading.Thread(target=jobs_scheduling_thread)
    t1.start()
    t2.start()


