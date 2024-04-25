from utils.blockchain import *

## execute until success!
while True:
    start = dt.datetime.now()
    print('attempt start', start)
    tx_object = prepare_tx(wallet=wallet, asset_in=SOL_ca, asset_out='8AntP7Hxft8Yjr52UQ3RnBHU4njTkDFDho97gE4vRzkt',
                            amount=0.1/153, mode='buy', fee='auto')
    #tx_object = prepare_tx(wallet=wallet, asset_in='8AntP7Hxft8Yjr52UQ3RnBHU4njTkDFDho97gE4vRzkt',
    #                       asset_out=SOL_ca, mode='sell', fee=10000)
    tx_object['signed_tx'] = sign_tx(tx_object, wallet)
    result = execute_tx(tx_object)
    if result==True:
        break
    else:
        continue
