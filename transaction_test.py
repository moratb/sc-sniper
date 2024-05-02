from utils.common import *
from utils.blockchain import *
from utils.ml import *
from utils.coretask import *

# execute until success!
# while True:
#    start = dt.datetime.now()
#    print('attempt start', start)
#    tx_object = prepare_tx(wallet=wallet, asset_in=SOL_ca, asset_out='6xLaHkqfFn2VL5hRyEecN5oPPkqUNderCxcCd2df3Gs8',
#                           amount=0.0008, mode='buy', fee=1000)
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

core_task('13xhqfs6QFyBgQGZA6rpH2LbVcVRJuJCAj41j6LLy6Lf', dt.datetime(2024,5,1,7,18, tzinfo=dt.timezone.utc))