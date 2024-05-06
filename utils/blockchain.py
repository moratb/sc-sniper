from utils.common import *

from solders.transaction import VersionedTransaction
from solana.rpc.core import TransactionExpiredBlockheightExceededError
from solana.rpc.api import Client
from solana.rpc.async_api import AsyncClient
from solders.keypair import Keypair
from solana.rpc.types import TxOpts, TokenAccountOpts
from solders.pubkey import Pubkey
from solders import message
import asyncio
import httpx
import json
import base64
import uuid
from contextlib import suppress
from utils.logger import create_logger

logger = create_logger()

SOL_ca = os.getenv('SOL_ca')
USDC_ca = os.getenv('USDC_ca')
USDT_ca = os.getenv('USDT_ca')
PRIVATE_KEY = os.getenv('wallet_pk')
solana_client = Client(os.getenv('RPC'))
wallet = Keypair.from_base58_string(PRIVATE_KEY)
slippage = int(os.getenv('slippage'))


@retry(max_attempts=5, retry_delay=1)
def sendTransaction(transaction):
    return solana_client.send_transaction(transaction, opts=TxOpts(skip_preflight=True))


@retry()
def checkTransaction(tx):
    return solana_client.get_transaction(tx, commitment='confirmed', max_supported_transaction_version=0)


@retry()
def getLatestBlockhash():
    return solana_client.get_latest_blockhash(commitment='confirmed')


@retry()
def getDecimals(token):
    res = solana_client.get_account_info_json_parsed(Pubkey.from_string(token))
    return json.loads(res.to_json())['result']['value']['data']['parsed']['info']['decimals']


@retry(max_attempts=5, retry_delay=2)
def check_tx_price_amount(tx, token):
    tx_data = checkTransaction(tx)
    tx_json = json.loads(tx_data.to_json())['result']

    ##SOL change
    #ak = tx_json['transaction']['message']['accountKeys']
    #i = ak.index(str(wallet.pubkey()))
    #presol = tx_json['meta']['preBalances'][i]
    #postsol = tx_json['meta']['postBalances'][i]
    #tx_fee = tx_json['meta']['fee']
    #account_creation_fee = 2039280 # 0.00203928 * 10**9
    ## TODO: to include fees just do  (postsol - presol) / 10**9 

    ##TOKEN changes
    balances_pre = pd.DataFrame(tx_json['meta']['preTokenBalances'])
    balances_pre['uiAmount'] =balances_pre['uiTokenAmount'].apply(lambda x:x['uiAmount'])
    balances_post = pd.DataFrame(tx_json['meta']['postTokenBalances'])
    balances_post['uiAmount'] =balances_post['uiTokenAmount'].apply(lambda x:x['uiAmount'])
    comb = pd.merge(balances_pre.drop(columns=['uiTokenAmount','programId']),
            balances_post.drop(columns=['uiTokenAmount','programId']),
            on=['accountIndex','mint','owner'],
            suffixes=['_pre','_post'],how='outer').fillna(0)
    comb['change'] = comb['uiAmount_post'] - comb['uiAmount_pre']
    wchanges = comb.loc[(comb['owner']==str(wallet.pubkey())) & (np.abs(comb['change'])>0)]
    sol_change = wchanges[wchanges['mint']==SOL_ca]['change'].iloc[0]
    out_amount = wchanges[wchanges['mint']==token]['change'].iloc[0]
    
    ## get approx usd price
    cur_price = check_multi_price([SOL_ca])
    sol_price = cur_price[SOL_ca]['price']
    
    return np.abs( (sol_change * sol_price) / out_amount ), sol_change


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
    splt_df['amount_int'] = splt_df['account'].apply(lambda x: x['data']['parsed']['info']['tokenAmount']['uiAmount'])
    return splt_df.loc[splt_df['amount_int']>0]


@retry(max_attempts=10, retry_delay=2)
def get_quote(cur_in, cur_out, inamount):
    url = 'https://t0-quote-api.jup.ag/quote' #'https://quote-api.jup.ag/v6/quote'
    headers = {'Content-Type': 'application/json'}
    json_data = {
        'amount': inamount,
        'inputMint': cur_in,
        'outputMint': cur_out,
        'slippageBps':slippage
    }
    response = requests.get(url, headers=headers, params=json_data)
    if response.status_code == 200:
        logger.info('Success Quote!')
        return response.json()
    else:
        logger.error(f"{response.status_code} {response.json()}")
        response.raise_for_status()


@retry(max_attempts=10, retry_delay=2)
def get_tx(wallet, quote, fee_microlaports):
    logger.info(f'fee will be: {fee_microlaports}')
    url = 'https://t0-quote-api.jup.ag/swap' #'https://quote-api.jup.ag/v6/swap'
    headers = {'Content-Type': 'application/json'}
    json_data = {
        'quoteResponse': quote,
        'userPublicKey': str(wallet.pubkey()),
        'wrapAndUnwrapSol': False,
        'useSharedAccounts': False,
        'dynamicComputeUnitLimit': True,
        'computeUnitPriceMicroLamports':fee_microlaports
    }
    response = requests.post(url, headers=headers, json=json_data)
    if response.status_code == 200:
        logger.info('Success Txgen!')
        return response.json()
    else:
        logger.error(f"{response.status_code} {response.json()}")
        response.raise_for_status()


def prepare_tx(wallet, asset_in=USDC_ca, asset_out=USDC_ca, amount=0, mode='sell', fee=10000):
    if mode == 'buy':
        logger.info(f'attempt to buy {asset_out} for {amount} {asset_in}')
        d = getDecimals(asset_in)
        quote = get_quote(cur_in = asset_in, cur_out = asset_out, inamount = int(amount * 10 ** d))
    elif mode == 'sell':
        tow = getSPLtokens(wallet)
        amount_owned = tow.loc[tow['token_address'] == asset_in, 'amount'].iloc[0]  ## selling all
        d = tow.loc[tow['token_address'] == asset_in, 'decimals'].iloc[0]
        logger.info(f'attempt to sell {int(amount_owned) / 10 ** int(d)} of {asset_in}')
        quote = get_quote(cur_in = asset_in, cur_out = asset_out, inamount = int(amount_owned))

    tx_data = get_tx(wallet = wallet, quote = quote, fee_microlaports = fee)
    lvbh = getLatestBlockhash().value.last_valid_block_height
    tx_object = {'txid': None, 'mode': mode, 'tx_data': tx_data, 'signed_tx':None, 'lvbh': lvbh}
    return tx_object


def sign_tx(tx_object, wallet):
    tx_data = tx_object['tx_data']
    tx_bytes = base64.b64decode(tx_data['swapTransaction'])
    raw_tx = VersionedTransaction.from_bytes(tx_bytes)
    signature = wallet.sign_message(message.to_bytes_versioned(raw_tx.message))
    signed_tx = VersionedTransaction.populate(raw_tx.message, [signature])
    logger.info('Success sign!')
    return signed_tx


## ASYNC TRANSACTION SENDER
async def manual_send(tx):
    headers = {
        "Content-Type": "application/json"
    }
    data = {
        "method": "sendTransaction",
        "jsonrpc": "2.0",
        "id": str(uuid.uuid4()),
        "params": [
            tx,
            {
                "skipPreflight": True,
                "encoding": "base64",
                "maxRetries": None,
                "minContextSlot": None
            }
        ]
    }
    async with httpx.AsyncClient() as client:
        tx_response = await client.post(os.getenv('RPC'), headers=headers, json=data)
        return tx_response 


async def resender(encoded_tx, abort_signal):
    retry_id = 0
    while not abort_signal.is_set():
        try:
            retry_id += 1
            logger.info(f'Attempt: {retry_id}')
            await manual_send(encoded_tx)
        except Exception as e:
            logger.error(f"Failed to resend transaction: {e}")
        await asyncio.sleep(2)


async def confirm_transaction(sca, tx_sig, lvbh, abort_signal):
    while not abort_signal.is_set():
        try:
            res = await sca.confirm_transaction(tx_sig=tx_sig, commitment='confirmed', last_valid_block_height=lvbh)
            return res
        except TransactionExpiredBlockheightExceededError as e:
            abort_signal.set()
            logger.info(f"Block height exceeded: {e}")
        except Exception as e:
            logger.info(f"Confirmation issue: {e}")
            return None


async def check_transaction_status(sca, tx_sig, abort_signal):
    while not abort_signal.is_set():
        try:
            res = await sca.get_signature_statuses([tx_sig], search_transaction_history=False)
            if res.value[0]:
                tx_status = json.loads(res.value[0].to_json())
                if tx_status['confirmationStatus'] in ('confirmed','finalized'):
                    return res
        except Exception as e:
            logger.error(f"Get signatures issue: {e}")
            return None
        await asyncio.sleep(2)


async def txsender(tx_object):
    logger.info('attempting to send tx: ')
    logger.info(f"""txid: {tx_object['txid']},
                  fee: {tx_object['tx_data']['prioritizationFeeLamports']},
                  lvbh: {tx_object['lvbh']}""")
    encoded_tx = base64.b64encode(bytes(tx_object['signed_tx'])).decode('utf-8')
    tx_sig = tx_object['txid']
    lvbh = tx_object['lvbh']
    sca = AsyncClient(os.getenv('RPC'))
    abort_signal = asyncio.Event()
    try:
        resender_task = asyncio.create_task(resender(encoded_tx, abort_signal))
        confirmation_task = asyncio.create_task(confirm_transaction(sca, tx_sig, lvbh, abort_signal))
        status_check_task = asyncio.create_task(check_transaction_status(sca, tx_sig, abort_signal))
        done, pending = await asyncio.wait(
            [confirmation_task, status_check_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        # Process the result of the first completed task
        for task in done:
            res = task.result() ## * FIX case when rpc is not synced (add get_transction check) 
            if res:
                tx_status = json.loads(res.value[0].to_json())
                logger.info('Transaction sent!', tx_status)
                return tx_status['status']

    except Exception as e:
        logger.error(f"An error occurred: {e}")

    finally:
        abort_signal.set()  # Ensure all tasks are cancelled
        task_set = asyncio.all_tasks()
        for task in task_set:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task 
        logger.info(f"{confirmation_task.done()}, {resender_task.done()}, {status_check_task.done()}")
        await sca.close()

    return None


def tx_procedure(wallet, asset_in=USDC_ca, asset_out=USDC_ca, amount=0, mode='sell', fee=0):
    tx_object = prepare_tx(wallet=wallet, asset_in=asset_in, asset_out=asset_out,
                            amount=amount, mode=mode, fee=fee)
    tx_object['signed_tx'] = sign_tx(tx_object, wallet)
    send_response = sendTransaction(tx_object['signed_tx'])
    tx_object['txid'] = send_response.value
    result = asyncio.run(txsender(tx_object))
    ## TODO: FIX case when rpc is not synced (add get_transction check)
    ## 2wa3SePx7Nj8LckdPN29Wm5HoGY5pQEfmVVnGKwkVbuLmParhUUGAsbfF6S8n7R3AtTMPhH73YwVi1emYDYYPZrj
    return result, tx_object['txid']