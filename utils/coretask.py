import sys
from utils.common import *
import numpy as np
from utils.blockchain import *

def core_task(token, launch_time):
    data = get_price_data(token, int(launch_time.timestamp()), int((launch_time + dt.timedelta(minutes=20)).timestamp()))
    data_example = data['c'].sum()
    decision = np.random.choice(a=2, size=1,p=[0.9,0.1])
    tx_example = get_quote(USDC_ca, token, 100*10**6)
    print("Task executed. Result: ", data_example, 'DECISION: ',decision)
    print('QUOTE: ', tx_example)