from utils.common import *
from utils.blockchain import *
from utils.ml import *

USD_AMOUNT = 0.1
PRIORITY_FEE = 5000

def core_task(token, launch_time):
    ## PART 1 - GET STATIC DATA
    static_data = get_static_data(token)

    ## PART 2 - GET OCHL DATA AND PREPARE
    ochl_data = get_ochl_data(token, launch_time)

    ## PART 3 - PREPARE DATA 
    final_df = prepare_for_ml(static_data, ochl_data)
    if not isinstance(final_df, pd.DataFrame):
        print('Test 1 not passed')
        return None

    ## PART 4 - APPLY ML
    decision1, decision2 = make_predictions(final_df)

    if (decision1==1) & (decision2>5):
        while True:
            print(dt.datetime.now(),' Attempt to BUY: ',token)
            ## PART 5 - BUY
            cur_price = check_multi_price([SOL_ca])
            SOL_AMOUNT = USD_AMOUNT / cur_price[SOL_ca]['price']
            result, txid = tx_procedure(wallet=wallet, asset_in=SOL_ca, asset_out=token,
                                        amount=SOL_AMOUNT, mode='buy', fee=PRIORITY_FEE)
            print('Result: ', result, txid)
            if result == {'Ok': None}:
                print('Success BUY', token, txid)
                buy_price = check_buy_price(txid, USD_AMOUNT)
                ## PART 6 WRITE TO DB
                with SQLiteDB('dbs/calls.db') as conn:
                    update_statement = f"""
                    UPDATE calls
                    SET
                        buy = {True},
                        buy_time = "{dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}",
                        buy_price = {buy_price}
                    WHERE address = "{token}"
                    """
                    conn.execute(update_statement)
                print('DB updated with buy data!')
                break
            else:
                continue
    else:
        print('Test 2 not passed', decision1, decision2)
        return None