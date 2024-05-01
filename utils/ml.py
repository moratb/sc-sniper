from utils.common import *
import xgboost as xgb
import pickle
import ta
from tabulate import tabulate
from utils.logger import create_logger

logger = create_logger()


def get_static_data(token):
    with SQLiteDB('./dbs/calls.db') as conn:
        query = f'SELECT * FROM calls WHERE address="{token}"'
        df = pd.read_sql_query(query, conn)
        static_features = ['s_mm2','s_ma2','s_fa2','s_q','s_sni','mcap_num','liq_num']
        static_data = df.loc[:,['address']+static_features]
        return static_data


def get_ochl_data(token, launch_time):
    while True:
        ochl_data = get_price_data(token, 
                                   int(launch_time.timestamp()), 
                                   int((launch_time + dt.timedelta(minutes=20)).timestamp()))
        if ochl_data.shape[0] == 0:
            logger.info(f"OCHL data is empty for  {launch_time}")
            return None
        elif ochl_data.shape[0] < 21:
            diff = 21 - ochl_data.shape[0]
            logger.info(f"OCHL data is too small for {launch_time}, {diff} is difference")
            return None
        return ochl_data
    

def prepare_for_ml(static_data, ochl_data):
    ## temp fix to make ta work...
    prepared_data = pd.concat([ochl_data,pd.DataFrame({'address':'dummy'}, index=[21])])

    ## adjustments
    prepared_data['v_usd'] = prepared_data['v']*prepared_data['c']
    prepared_data['time'] = (prepared_data['unixTime'] - prepared_data.groupby('address')['unixTime'].transform(min))/60
    prepared_data = pd.merge(prepared_data, 
                        prepared_data.drop_duplicates(subset='address',keep='first')[['address','o','c','h','l']],
                        on='address', how='left', suffixes=['','_first'])
    for i in ['o','c','h','l']:
        prepared_data['normal_'+i] = prepared_data[i]/prepared_data[i+'_first']

    ##simple checks
    def accumul(x):
        last_v0c = 0
        res = []
        for v in x:
            if v == 0:
                cur_v0c = last_v0c + 1
            elif v != 0:
                cur_v0c = 0
            res += [cur_v0c]
            last_v0c = cur_v0c
        return res
    prepared_data['v_usd_0conseq'] = prepared_data.groupby('address')['v_usd'].transform(accumul)
    prepared_data['target_check'] = np.where((prepared_data['v_usd_0conseq']>=1) & (prepared_data['time']<=20), 0, 1)
    prepared_data['normal_c_delta'] = prepared_data['normal_c'] / prepared_data.groupby('address')['normal_c'].shift(1)
    prepared_data['range'] = prepared_data['normal_h']/prepared_data['normal_l']
    prepared_data['ath_c'] = prepared_data.groupby('address')['normal_c'].cummax()
    prepared_data['atl_c'] = prepared_data.groupby('address')['normal_c'].cummin()
    prepared_data['ath_h'] = prepared_data.groupby('address')['normal_h'].cummax()
    prepared_data['atl_l'] = prepared_data.groupby('address')['normal_l'].cummin()
    prepared_data['ath_c_share'] = prepared_data['normal_c']/prepared_data['ath_c']
    prepared_data['atl_c_share'] = prepared_data['normal_c']/prepared_data['atl_c']
    prepared_data['ath_h_share'] = prepared_data['normal_c']/prepared_data['ath_h']
    prepared_data['atl_l_share'] = prepared_data['normal_c']/prepared_data['atl_l']

    ##indicators
    prepared_data['ema'] = prepared_data.groupby('address').apply(lambda x: ta.trend.ema_indicator(close=x['normal_c'], window=3, fillna=True)).reset_index(level=0, drop=True)
    prepared_data['bbh'] = prepared_data.groupby('address').apply(lambda x: ta.volatility.bollinger_hband_indicator(x["c"], window=3, window_dev=2, fillna=True)).reset_index(level=0, drop=True)
    prepared_data['bbl'] = prepared_data.groupby('address').apply(lambda x: ta.volatility.bollinger_lband_indicator(x["c"], window=3, window_dev=2, fillna=True)).reset_index(level=0, drop=True)
    prepared_data['mfi'] = prepared_data.groupby('address').apply(lambda x: ta.volume.money_flow_index(high = x["h"], low= x['l'], close=x['c'], volume=x['v'], window=3, fillna=True)).reset_index(level=0, drop=True)
    prepared_data['accdist'] = prepared_data.groupby('address').apply(lambda x: ta.volume.acc_dist_index(high = x["h"], low= x['l'], close=x['c'], volume=x['v'], fillna=True)).reset_index(level=0, drop=True)
    prepared_data['vwap'] = prepared_data.groupby('address').apply(lambda x: ta.volume.volume_weighted_average_price(high = x["h"], low= x['l'], close=x['c'], volume=x['v'], fillna=True)).reset_index(level=0, drop=True)
    prepared_data['rsi'] = prepared_data.groupby('address').apply(lambda x: ta.momentum.rsi(close=x['c'], window=3, fillna=True)).reset_index(level=0, drop=True)
    prepared_data['stoch'] = prepared_data.groupby('address').apply(lambda x: ta.momentum.stoch(high = x["h"], low= x['l'], close=x['c'], window=3, smooth_window=3 , fillna=True)).reset_index(level=0, drop=True)
    prepared_data['stochs'] = prepared_data.groupby('address').apply(lambda x: ta.momentum.stoch_signal(high = x["h"], low= x['l'], close=x['c'], window=3, smooth_window=3 , fillna=True)).reset_index(level=0, drop=True)
    prepared_data['stochrsi'] = prepared_data.groupby('address').apply(lambda x: ta.momentum.stochrsi(close=x['c'], window=3, smooth1=3, smooth2=3 , fillna=True)).reset_index(level=0, drop=True)

    ## cleanup
    final_df = prepared_data.loc[(prepared_data['time']<=20)]
    #logger.info(final_df[['address','normal_c','time','unixTime','target_check']].to_markdown(headers='keys',tablefmt='psql'))
    if final_df['target_check'].min() == 0:
        return None
    final_df = final_df.drop(columns=['type','h','o','l','c','unixTime','v','o_first', 'c_first', 'h_first', 'l_first','target_check'])

    ## formating
    final_df['time'] = final_df['time'].astype(int)
    final_df['normal_c_delta'] = final_df['normal_c_delta'].fillna(1)
    final_df = pd.pivot_table(final_df, index=['address'], columns=['time']).reset_index()
    final_df.columns = [col[0]+'_'+str(col[1]) for col in final_df.columns.values]
    final_df = pd.merge(final_df.rename(columns={'address_':'address'}),
                        static_data,
                        on='address',
                        how='left')
    
    return final_df


def make_predictions(final_df):
    model_clf = pickle.load(open('./models/model_clf.sav', 'rb'))
    model_regr = pickle.load(open('./models/model_regr.sav', 'rb'))
    SCAM_PREDICTION = model_clf.predict(final_df.drop(columns='address').rename(columns={'mcap_num':'Mcap_num','liq_num':'Liq_num'}))[0]
    X_PREDICTION = model_regr.predict(final_df.drop(columns='address').rename(columns={'mcap_num':'Mcap_num','liq_num':'Liq_num'}))[0]
    return SCAM_PREDICTION, X_PREDICTION