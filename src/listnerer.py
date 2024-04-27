import pandas as pd
from telethon import TelegramClient
from utils.common import *
from dotenv import load_dotenv
import logging

logging.basicConfig()
logging.getLogger('apscheduler').setLevel(logging.DEBUG)


class SCTelegramListener:
    def __init__(self):
        load_dotenv()
        self.telegram_api_id = os.getenv('telegram_api_id_2')
        self.telegram_api_hash = os.getenv('telegram_api_hash_2')
        self.telegram_phone_number = os.getenv('telegram_phone_number_2')
        self.pass2fa = os.getenv('telegram_pass2fa_2')
        self.chat_name = 'Solana New Liquidity Pools'
        self.client = self.init_client()

    def init_client(self):
        return TelegramClient(session=None,
                              api_id=self.telegram_api_id,
                              auto_reconnect=True,
                              api_hash=self.telegram_api_hash)

    async def start_telegram_client(self):
        tg_client = await self.client.start(phone=self.telegram_phone_number, password=self.pass2fa)
        return tg_client

    async def get_chat_id(self, client):
        res = {}
        async for dialog in client.iter_dialogs():
            res[dialog.name] = dialog.id
        return res.get(self.chat_name)

    def read_messages(self,messages):
        message = pd.DataFrame({'messages': [messages]})
        message['id'] = message['messages'].apply(lambda x: x.id)
        message['date'] = message['messages'].apply(lambda x: x.date)
        message['text'] = message['messages'].apply(lambda x: x.text)
        message['date'] = pd.to_datetime(message['date'])
        message['date'] = message['date'].dt.tz_localize(None)

        pattern = r'`([1-9A-HJ-NP-Za-km-z]{32,44})`'
        message['address'] = message['text'].str.extract(pattern)
        message['expected_launch_time'] = message['text'].str.extract(r'(?<=Launch:\*\* )(.*)')[0].str.strip('`')
        message['mcap'] = message['text'].str.extract(r'(?<=Mcap:\*\* )(.*)')[0].str.strip('`')
        message['liq'] = message['text'].str.extract(r'(?<=Liq:\*\* )(.*)')[0].str.strip('`')
        message['s_mm'] = message['text'].str.extract(r'(?<=Mutable Metadata: )(.*)')
        message['s_ma'] = message['text'].str.extract(r'(?<=Mint Authority: )(.*)')
        message['s_fa'] = message['text'].str.extract(r'(?<=Freeze Authority: )(.*)')
        message['s_s'] = message['text'].str.extract(r'(?<=Score: )(.*)')
        return message

    def parse_messages(self, messages):
        messages.loc[messages['s_mm'].str.contains('Yes'), 's_mm2'] = True
        messages.loc[messages['s_mm'].str.contains('No'), 's_mm2'] = False
        messages.loc[messages['s_ma'].str.contains('Yes'), 's_ma2'] = True
        messages.loc[messages['s_ma'].str.contains('No'), 's_ma2'] = False
        messages.loc[messages['s_fa'].str.contains('Yes'), 's_fa2'] = True
        messages.loc[messages['s_fa'].str.contains('No'), 's_fa2'] = False
        messages.loc[messages['s_s'].str.contains('Bad'), 's_q'] = 0
        messages.loc[messages['s_s'].str.contains('Neutral'), 's_q'] = 1
        messages.loc[messages['s_s'].str.contains('Good'), 's_q'] = 2
        messages['s_sni'] = messages['s_s'].str.extract(r'([0-9]+)')
        messages['s_sni'] = messages['s_sni'].fillna(0)

        mult = {'K': 1e3, 'M': 1e6, 'B': 1e9, 'T': 1e12}
        messages['mcap'] = messages['mcap'].str.strip('[$\*]')
        messages['mcap_num'] = messages['mcap'].str.extract('([0-9\.]+)').astype(float) * messages['mcap'].str.extract(
            '([A-Z])').replace(mult).fillna(1)
        messages['liq'] = messages['liq'].str.strip(r" \[.*\]")
        messages['liq_num'] = messages['liq'].str.extract('([0-9\.]+)').astype(float) * messages['liq'].str.extract(
            '([A-Z])').replace(mult).fillna(1)
        messages[['s_q', 'mcap_num', 'liq_num']] = messages[['s_q', 'mcap_num', 'liq_num']].astype(int)
        tp = messages['expected_launch_time'].str.extractall('([0-9]+)').unstack()
        tp.columns = tp.columns.droplevel(0)
        tp['hours'] = messages['expected_launch_time'].str.contains('hour')
        tp['sec'] = messages['expected_launch_time'].str.contains('second')
        tp.loc[tp['hours'] == True, 'new'] = tp.loc[tp['hours'] == True].apply(
            lambda x: dt.timedelta(hours=int(x[0]), minutes=int(x[1])), axis=1)
        tp.loc[tp['sec'] == True, 'new'] = tp.loc[tp['sec'] == True].apply(lambda x: dt.timedelta(seconds=int(x[0])),
                                                                           axis=1)
        tp.loc[tp['new'].isna(), 'new'] = tp.loc[tp['new'].isna()].apply(lambda x: dt.timedelta(minutes=int(x[0])),
                                                                         axis=1)
        tp.loc[tp['new'] >= dt.timedelta(days=30), 'new'] = dt.timedelta(seconds=0)

        messages = pd.concat([messages, tp[['new']]], axis=1)
        messages.loc[(messages['expected_launch_time'].str.contains('ago')), 'expected_launch_time_ts'] = messages[
                                                                                                              'date'] - pd.to_timedelta(
            messages['new'])
        messages.loc[(messages['expected_launch_time'].str.contains('In')), 'expected_launch_time_ts'] = messages[
                                                                                                             'date'] + pd.to_timedelta(
            messages['new'])
        messages = messages.drop(columns=['messages', 's_mm', 's_ma', 's_fa', 's_s', 'mcap', 'liq', 'text', 'new'])
        return messages

    async def parse(self):
        client = await self.start_telegram_client()
        chat_id = await self.get_chat_id(client)
        messages = await self.read_messages(chat_id)
        parsed = self.parse_messages(messages)
        return parsed

    def write_to_db(self, message):
        with SQLiteDB('dbs/calls.db') as conn:
            query = "SELECT DISTINCT address FROM calls"
            tracked_a = pd.read_sql_query(query, conn)
            message_clean = message.loc[~message['address'].isin(tracked_a['address'].unique())]
            message_clean.to_sql('calls', conn, if_exists='append', index=False)
