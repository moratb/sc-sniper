from solders.compute_budget import set_compute_unit_limit
from solders.compute_budget import  set_compute_unit_price
from solana.rpc.api import Client
from solders.keypair import Keypair
from solana.transaction import Transaction
from solana.rpc.types import TxOpts
from solders.pubkey import Pubkey
import json
import base64
import sys
sys.path.insert(1,'./')
from utils.common import *

SOL_ca = 'So11111111111111111111111111111111111111112'
USDC_ca = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_ca = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"
private_key = os.getenv('wallet_pk')
wallet = Keypair.from_base58_string(private_key)
solana_client = Client(os.getenv('RPC'))

@retry()
def sendTransaction(transaction, signers):
    return solana_client.send_transaction(transaction, *signers, opts=TxOpts(skip_preflight=True))

@retry()
def checkTransaction(tx):
    return solana_client.get_transaction(tx, commitment='confirmed')

@retry()
def getLatestBlockhash():
    return solana_client.get_latest_blockhash(commitment='confirmed')

@retry()
def getBlockHeight():
    return solana_client.get_block_height().value

@retry()
def getTokenAccountBalance(token):
    return solana_client.get_token_account_balance(token).value.ui_amount 


@retry(max_attempts=30, retry_delay=2)
def createOrder(wallet, quote_response):
    url = 'https://quote-api.jup.ag/v6/swap'
    json_data =  {
        ## add quote_response https://station.jup.ag/docs/apis/swap-api
        'userPublicKey': str(wallet.pubkey()),
        'wrapAndUnwrapSol': True,
    }
    response = requests.post(url, headers={'Content-Type': 'application/json'}, json=json_data)
    if (response.status_code != 200) or ('tx' not in response.json().keys()):
        raise ValueError("API response is invalid or missing tx")
    return response.json()


def createTransaction(wallet, asset_in, amount):
    quote_response = get_quote(asset_in, SOL_ca , amount) ## in common.py
    order_data = createOrder(wallet, quote_response)
    tx_base64 = order_data['tx']
    transaction = Transaction.deserialize(base64.b64decode(tx_base64))
    latest_block_hash = getLatestBlockhash()
    lvbh = latest_block_hash.value.last_valid_block_height
    txs = [
        {'txid':[],'s': False, 'mode':'sell', 'tx':transaction, 'lvbh':lvbh}
    ]
    return txs


def checkIntent(tx_intent):
    ok_statuses = [
        {'Ok':None},
        {'Err': {'InstructionError': [0, {'Custom': 0}]}}, ## already in use
        {'Err': {'InstructionError': [0, {'Custom': 1}]}}, ## not enough balance
    ]
    if (tx_intent['txid']!=[]) & (tx_intent['s']==False):
        tx_list = list(dict.fromkeys(tx_intent['txid'])) 
        print('checking_txs: ', [str(txid) for txid in tx_list], tx_intent['s'], tx_intent['mode'])
        for tx in tx_list:
            tx_result = checkTransaction(tx)
            if tx_result.value != None:
                status = json.loads(tx_result.to_json())['result']['meta']['status']
                if status in ok_statuses:
                    tx_intent['s']=True
                    print('successful! ', status)
                    break

def executeTrade(txs):
    cbh = getBlockHeight()
    while all(tx_intent['lvbh']>cbh for tx_intent in txs):
        for tx_intent in txs:
            if (tx_intent['s']==False):
                signers = [wallet, *tx_intent['base']] if tx_intent['mode'] in ['buy','sell','comb'] else [wallet]
                sendtxresp = sendTransaction(tx_intent['tx'].add(set_compute_unit_price(100000)).add(set_compute_unit_limit(110000)), signers)
                tx_intent['txid'] += [sendtxresp.value]
        t.sleep(30)
        for tx_intent in txs:
            checkIntent(tx_intent)
        if all(tx['s'] for tx in txs):
            print('FULL SUCCSS')
            return True
        else:
            cbh = getBlockHeight()
    print('Execution Failed: ',  [{v:t[v] for v in ['s','mode','lvbh']} for t in txs]) 
    return txs

## execute sell until through
while True:
    start = dt.datetime.now()
    print('attempt start', start)
    txs = createTransaction(wallet, asset_in, amount)
    result = executeTrade(txs)
    if result==True:
        break
    else:
        continue