import sys
sys.path.insert(1,'./')
from utils.common import *
from utils.blockchain import *

## first GET PRICES FROM CURRENT TOKENS IN THE WALLET - getSPLtokens(wallet)
## via - https://public-api.birdeye.so/defi/multi_price and compare with buy prices.
## If any are price = 2x, or price <=0.9x THEN TRIGGER SELL JOB!

## execute sell until through
while True:
    start = dt.datetime.now()
    print('attempt start', start)
    #txs = prepare_tx(wallet=wallet, asset_in=asset_in)
    #result = executeTrade(txs)
    if True:
        break
    else:
        continue