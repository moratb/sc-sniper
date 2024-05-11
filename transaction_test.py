from utils.common import *
from utils.blockchain import *
from utils.ml import *
from utils.coretask import *

#execute until success!
# while True:
#    start = dt.datetime.now()
#    print('attempt start', start)
#    #tx_object = prepare_tx(wallet=wallet, asset_in=SOL_ca, asset_out='7gbEP2TAy5wM3TmMp5utCrRvdJ3FFqYjgN5KDpXiWPmo',
#    #                       amount=0.0008, mode='buy', fee=0)
#    tx_object = prepare_tx(wallet=wallet, asset_in='7gbEP2TAy5wM3TmMp5utCrRvdJ3FFqYjgN5KDpXiWPmo', asset_out=SOL_ca,
#                           mode='sell', fee=0)
#    tx_object['signed_tx'] = sign_tx(tx_object, wallet)
#    send_response = sendTransaction(tx_object['signed_tx'])
#    tx_object['txid'] = send_response.value
#    result = asyncio.run(txsender(tx_object))
#    if result:
#        print('Result: ', result)
#        break
#    else:
#        continue

core_task('3Ums67fvFTAwyYneQJHBK4nFpyR8YhkEVXje1LWit7s8', dt.datetime(2024,5,8,20,30, tzinfo=dt.timezone.utc))