from utils.common import *

from solders.compute_budget import set_compute_unit_limit
from solders.compute_budget import set_compute_unit_price
from solders.transaction import VersionedTransaction
from solana.rpc.api import Client
from solders.keypair import Keypair
from solana.rpc.types import TxOpts, TokenAccountOpts
from solders.pubkey import Pubkey
from solders import message
import json
import base64
from dotenv import load_dotenv

load_dotenv()
SOL_ca = 'So11111111111111111111111111111111111111112'
USDC_ca = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
USDT_ca = "Es9vMFrzaCERmJfrF4H2FYD4KCoNkY11McCe8BenwNYB"

PRIVATE_KEY = os.getenv('wallet_pk')


solana_client = Client(os.getenv('RPC'))
wallet = Keypair.from_base58_string(PRIVATE_KEY)


@retry()
def sendTransaction(transaction):
    return solana_client.send_transaction(transaction) #, opts=TxOpts(skip_preflight=True))


@retry()
def checkTransaction(tx):
    return solana_client.get_transaction(tx, commitment='confirmed', max_supported_transaction_version=0)


@retry()
def getLatestBlockhash():
    return solana_client.get_latest_blockhash(commitment='finalized')


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
        wallet.pubkey(),
        opts=TokenAccountOpts(program_id=Pubkey.from_string("TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"))
    )
    splt_df = pd.DataFrame(json.loads(splt_json.to_json())['result']['value'])
    splt_df['token_address'] = splt_df['account'].apply(lambda x: x['data']['parsed']['info']['mint'])
    splt_df['decimals'] = splt_df['account'].apply(lambda x: x['data']['parsed']['info']['tokenAmount']['decimals'])
    splt_df['amount'] = splt_df['account'].apply(lambda x: x['data']['parsed']['info']['tokenAmount']['amount'])
    return splt_df


@retry(max_attempts=30, retry_delay=2)
def get_quote(cur_in, cur_out, inamount):
    url = 'https://quote-api.jup.ag/v6/quote'
    headers = {'Content-Type': 'application/json'}
    json_data = {
        'amount': inamount,
        'inputMint': cur_in,
        'outputMint': cur_out,
        'slippageBps':500
    }
    response = requests.get(url, headers=headers, params=json_data)
    if response.status_code == 200:
        print('Success Quote!')
        return response.json()
    else:
        print(response.status_code, response.json())
        return None


@retry(max_attempts=30, retry_delay=2)
def get_tx(wallet, quote, fee_microlaports):
    url = 'https://quote-api.jup.ag/v6/swap'
    headers = {'Content-Type': 'application/json'}
    json_data = {
        'quoteResponse': quote,
        'userPublicKey': str(wallet.pubkey()),
        'wrapAndUnwrapSol': True,
        'dynamicComputeUnitLimit': True,
        'computeUnitPriceMicroLamports':fee_microlaports
    }
    response = requests.post(url, headers=headers, json=json_data)
    if response.status_code == 200:
        print('Success Txgen!')
        return response.json()
    else:
        print(response.status_code, response.json())
        return None


def prepare_tx(wallet, asset_in=None, asset_out=None, amount=0, mode='sell', fee=10000):
    if mode == 'buy':
        print('attempt to buy ', asset_out, 'for ', amount, ' USDC')
        quote = get_quote(cur_in = USDC_ca, cur_out = asset_out, inamount = amount * 10 ** 6)
    elif mode == 'sell':
        tow = getSPLtokens(wallet)
        amount_owned = tow.loc[tow['token_address'] == asset_in, 'amount'].iloc[0]  ## selling all
        decimals = tow.loc[tow['token_address'] == asset_in, 'decimals'].iloc[0]
        print('attempt to sell', int(amount_owned) / 10 ** int(decimals), 'of', asset_in)
        quote = get_quote(cur_in = asset_in, cur_out = USDC_ca, inamount = int(amount_owned))

    tx_data = get_tx(wallet = wallet, quote = quote, fee_microlaports = fee)
    lvbh = getLatestBlockhash().value.last_valid_block_height
    bh = getLatestBlockhash().value.blockhash
    tx_object = {'txid': [], 's': False, 'mode': mode, 'tx_data': tx_data, 'signed_tx': None,
                 'lvbh': lvbh, 'bh': bh, 'priorityFee': tx_data['prioritizationFeeLamports']}
    return tx_object


def sign_tx(tx_object, wallet):
    tx_data = tx_object['tx_data']
    tx_bytes = base64.b64decode(tx_data['swapTransaction'])
    raw_tx = VersionedTransaction.from_bytes(tx_bytes)

    ## Gotta overwrite TX with more recent final blockhash
    new_raw_tx = message.MessageV0(
        header=raw_tx.message.header,
        account_keys=raw_tx.message.account_keys,
        recent_blockhash=tx_object['bh'],
        instructions=raw_tx.message.instructions,
        address_table_lookups=raw_tx.message.address_table_lookups
    )

    signature = wallet.sign_message(message.to_bytes_versioned(new_raw_tx))
    signed_tx = VersionedTransaction.populate(new_raw_tx, [signature])
    print('Success sign!')
    return signed_tx


def check_tx_intent(tx_object):
    ok_statuses = [
        {'Ok':None},
    ]
    if (tx_object['txid']!=[]) & (tx_object['s']==False):
        tx_list = list(dict.fromkeys(tx_object['txid'])) 
        print('checking_txs: ', [str(txid) for txid in tx_list], tx_object['s'], tx_object['mode'])
        for tx in tx_list:
            tx_result = checkTransaction(tx)
            if tx_result.value != None:
                status = json.loads(tx_result.to_json())['result']['meta']['status']
                if status in ok_statuses:
                    tx_object['s']=True
                    print('successful! ', status)
                    break


def execute_tx(tx_object):
    cbh = getBlockHeight()
    while tx_object['lvbh']>cbh:
        if (tx_object['s']==False):
            send_response = sendTransaction(tx_object['signed_tx'])
            tx_object['txid'] += [send_response.value]
        t.sleep(2)
        check_tx_intent(tx_object)
        if tx_object['s']==True:
            print('FULL SUCCSS')
            return True
        else:
            cbh = getBlockHeight()
            continue
    print('Execution Failed: ',  {key:tx_object[key] for key in ['txid','s','mode','lvbh']}) 
    return tx_object