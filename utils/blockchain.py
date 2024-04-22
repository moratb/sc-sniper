import sys
sys.path.insert(1,'./')
from utils.common import *

from solders.compute_budget import set_compute_unit_limit
from solders.compute_budget import  set_compute_unit_price
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client
from solders.keypair import Keypair
from solana.rpc.types import TxOpts, TokenAccountOpts
from solders.pubkey import Pubkey
import json
import base64

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

@retry()
def getDecimals(token):
    res = solana_client.get_account_info_json_parsed(Pubkey.from_string(token))
    return json.loads(res.to_json())['result']['value']['data']['parsed']['info']['decimals']

@retry()
def getSPLtokens(wallet):
    splt_json = solana_client.get_token_accounts_by_owner_json_parsed(
        Pubkey.from_string(wallet),
        opts=TokenAccountOpts(program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
    )
    splt_df = pd.DataFrame(json.loads(splt_json.to_json())['result']['value'])
    splt_df['token_address'] = splt_df['account'].apply(lambda x:x['data']['parsed']['info']['mint'])
    splt_df['decimals'] = splt_df['account'].apply(lambda x:x['data']['parsed']['info']['tokenAmount']['decimals'])
    splt_df['amount'] = splt_df['account'].apply(lambda x:x['data']['parsed']['info']['tokenAmount']['amount'])
    return splt_df

@retry(max_attempts=30, retry_delay=2)
def get_quote(cur_in, cur_out, inamount):
    url = 'https://quote-api.jup.ag/v6/quote'
    headers = {'Content-Type': 'application/json'}
    json_data = {
        'amount': inamount,
        'inputMint': cur_in,
        'outputMint': cur_out
    }
    response = requests.get(url, headers=headers, params=json_data)
    if response.status_code == 200:
        print('Success Quote!')
        return response.json()
    else:
        print(response.status_code, response.json())
        return None
    
@retry(max_attempts=30, retry_delay=2)
def get_tx(wallet, quote):
    url = 'https://quote-api.jup.ag/v6/swap'
    headers = {'Content-Type': 'application/json'}
    json_data =  {
        'quoteResponse':quote,
        'userPublicKey': str(wallet.pubkey()),
        'wrapAndUnwrapSol': True,
    }
    response = requests.post(url, headers=headers, json=json_data)
    if response.status_code == 200:
        return response.json()
    else:
        print(response.status_code, response.json())
        return None
    
def prepare_tx(wallet, asset_in=None, asset_out=None, amount=0, mode='sell'):
    if mode == 'buy':
        print('attempt to buy ',asset_out, 'for ',amount,' USDC')
        quote = get_quote(USDC_ca, asset_out, amount*10**6)
    elif mode == 'sell':
        tokensinwallet = getSPLtokens(wallet)
        amount_owned = tokensinwallet[tokensinwallet['token_address']==asset_in]['amount'][0] ## selling all
        decimals = tokensinwallet[tokensinwallet['token_address']==asset_in]['decimals'][0]
        print('attempt to sell', int(amount_owned)/int(decimals), 'of', asset_in)
        quote = get_quote(asset_in, USDC_ca, int(amount_owned))

    tx_data = get_tx(wallet, quote)
    transaction = VersionedTransaction.from_bytes(base64.b64decode(tx_data['swapTransaction']))
    latest_block_hash = getLatestBlockhash()
    lvbh = latest_block_hash.value.last_valid_block_height
    txs = [
        {'txid':[],'s': False, 'mode':'sell', 'tx':transaction, 'lvbh':lvbh}
    ]
    return txs