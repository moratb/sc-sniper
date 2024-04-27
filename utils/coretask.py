from utils.common import *
from utils.blockchain import *
import numpy as np

USD_AMOUNT = 1
PRIORITY_FEE = 5000

def core_task(token, launch_time):
    ## PART 1 - GET DATA AND PREPARE
    data = get_price_data(token, int(launch_time.timestamp()), int((launch_time + dt.timedelta(minutes=20)).timestamp()))
    data_example = data['c'].sum()

    ## PART 2 - APPLY ML
    decision = np.random.choice(a=2, size=1,p=[0.9,0.1])[0]

    if decision:
        while True:
            print(dt.datetime.now(),' Attempt to BUY: ',token)
            ## PART 3 - BUY
            price_data = check_multi_price([SOL_ca])
            SOL_AMOUNT = USD_AMOUNT / price_data[SOL_ca]['price']
            tx_object = prepare_tx(wallet=wallet, asset_in=SOL_ca, asset_out=token,
                                   amount=SOL_AMOUNT, mode='buy', fee=PRIORITY_FEE)
            tx_object['signed_tx'] = sign_tx(tx_object, wallet)
            send_response = sendTransaction(tx_object['signed_tx'])
            tx_object['txid'] = send_response.value
            result = asyncio.run(txsender(tx_object))
            print('Result: ', result)
            if result == {'Ok': None}:
                break
            else:
                continue