import sys
sys.path.insert(1, './')
from utils.common import *
from utils.blockchain import *
from tabulate import tabulate
from utils.logger import create_logger


class SCOracle:

    def __init__(self):
        self.take_profit = 1.5
        self.stop_loss = 0.9
        self.priority_fee = 5000
        self.logger = create_logger()


    def get_db_tokens(self):
        with SQLiteDB('dbs/calls.db') as conn:
            query = "SELECT *  FROM calls WHERE buy = 1"
            db_tokens = pd.read_sql_query(query, conn)
        return db_tokens
    
    def update_db_on_sell(self, token):
        with SQLiteDB('dbs/calls.db') as conn:
            update_statement = f"""
            UPDATE calls
            SET buy = {False}
            WHERE address = "{token}"
            """
            conn.execute(update_statement)
    
    def get_wallet_tokens(self):
        return getSPLtokens(wallet)
    

    def calculate_prices(self, db_tokens, wallet_tokens):
        tracked_tokens = pd.merge(
            wallet_tokens,
            db_tokens[['address','buy_price']],
            how='inner', left_on='token_address', right_on='address'
        )
        if tracked_tokens.empty:
            self.logger.info('No tokens are tracked')
            return tracked_tokens
        cur_prices = check_multi_price(tracked_tokens['token_address'].to_list())
        cur_prices = pd.DataFrame().from_dict(cur_prices,orient='index')
        cur_prices = cur_prices.reset_index().rename(columns={'index':'address'})
        tracked_tokens = pd.merge(tracked_tokens, cur_prices, how='inner', on='address')
        tracked_tokens['liq_req'] = tracked_tokens['amount_int']*tracked_tokens['price']
        tracked_tokens['price_change'] = tracked_tokens['price']/tracked_tokens['buy_price']
        tracked_tokens['sell_tag'] = np.where((tracked_tokens['liq_req'] < tracked_tokens['liquidity']) &
                                              ((tracked_tokens['price_change'] >= self.take_profit) |
                                               (tracked_tokens['price_change'] <= self.stop_loss)), True, False)
        self.logger.info('price changes:')
        self.logger.info(tracked_tokens[['address','price_change','liquidity']].to_markdown(headers='keys',tablefmt='psql'))
        return tracked_tokens[tracked_tokens['sell_tag']==True]

    def sell_tokens(self, tokens_for_sale):
        if tokens_for_sale.empty:
            self.logger.warn('No tokens are ready to sell yet')
            return None
        for i, row in tokens_for_sale.iterrows():
            self.logger.info(dt.datetime.now(), 'Attempt to SELL: ', i, row['address'], 'X: ', row['price_change'])
            result, txid = tx_procedure(wallet=wallet, asset_in=row['address'], asset_out=SOL_ca,
                                        mode='sell', fee=self.priority_fee)
            self.logger.info('Result: ', result)
            if result == {'Ok': None}:
                self.logger.info('Success SELL!', row['address'], txid)
                self.update_db_on_sell(row['address'])
                self.logger.info('DB updated with sell data!')
            return None
