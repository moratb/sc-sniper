from utils.common import *
from utils.blockchain import *
from utils.ml import *
from utils.coretask import *

## execute until success!
#while True:
#    start = dt.datetime.now()
#    print('attempt start', start)
#    tx_object = prepare_tx(wallet=wallet, asset_in=SOL_ca, asset_out='8AntP7Hxft8Yjr52UQ3RnBHU4njTkDFDho97gE4vRzkt',
#                           amount=0.0006, mode='buy', fee=0)
#    #tx_object = prepare_tx(wallet=wallet, asset_in='8AntP7Hxft8Yjr52UQ3RnBHU4njTkDFDho97gE4vRzkt', asset_out=SOL_ca,
#    #                       mode='sell', fee=1000)
#    tx_object['signed_tx'] = sign_tx(tx_object, wallet)
#    send_response = sendTransaction(tx_object['signed_tx'])
#    tx_object['txid'] = send_response.value
#    result = asyncio.run(txsender(tx_object))
#    if result:
#        print('Result: ', result)
#        break
#    else:
#        continue

core_task('AZwF5h6uKHxp8ta27ba4t3S5LQ9JdwHmkeae22ACDgqy', dt.datetime.fromtimestamp(1713260700))