import sys
sys.path.insert(1,'./')
from utils.common import *
from utils.blockchain import *

def core_task(token, launch_time):
    data = get_price_data(token, int(launch_time.timestamp()), int((launch_time + dt.timedelta(minutes=20)).timestamp()))
    data_example = data['c'].sum()
    decision = np.random.choice(a=2, size=1,p=[0.9,0.1])
    tx_example = get_quote('So11111111111111111111111111111111111111112', token, 1000)
    print("Task executed. Result: ", data_example, 'DECISION: ',decision)
    print('QUOTE: ', tx_example.json())