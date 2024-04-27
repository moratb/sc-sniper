from utils.common import *
from utils.blockchain import *
from utils.ml import *

USD_AMOUNT = 1
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
            tx_object = prepare_tx(wallet=wallet, asset_in=SOL_ca, asset_out=token,
                                   amount=SOL_AMOUNT, mode='buy', fee=PRIORITY_FEE)
            tx_object['signed_tx'] = sign_tx(tx_object, wallet)
            send_response = sendTransaction(tx_object['signed_tx'])
            tx_object['txid'] = send_response.value
            result = asyncio.run(txsender(tx_object))
            print('Result: ', result)
            if result == {'Ok': None}:
                print('SUCCESS BUY')
                break
            else:
                continue
    else:
        print('Test 2 not passed', decision1, decision2)
        return None