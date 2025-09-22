from xtquant import xtdata
xtdata.enable_hello = False
import pandas as pd
from datetime import datetime, timedelta


# 获取股票历史行情数据，比如日线，分钟线等
def get_stock_history_data(stock_code, period='1d', start_time=None, end_time=None):
    """
    获取股票历史行情数据
    
    Args:
        stock_code: 股票代码，如'000001.SZ'
        period: 周期，'1d'为日线，'1m'为1分钟线
        start_time: 开始时间，格式'20240301'
        end_time: 结束时间，格式'20240314'
        
    Returns:
        DataFrame格式的行情数据
    """
    # 如果没有指定时间，默认获取近10个交易日的数据
    if not start_time or not end_time:
        end_time = datetime.now().strftime('%Y%m%d')
        start_time = (datetime.now() - timedelta(days=7*365)).strftime('%Y%m%d')
    
    # 下载历史数据
    xtdata.download_history_data(stock_code, period=period, start_time=start_time)
    
    # 获取历史行情数据
    fields = ['time', 'open', 'high', 'low', 'close', 'volume', 'amount']
    market_data = xtdata.get_market_data(field_list=fields,
                                       stock_list=[stock_code],
                                       period=period,
                                       start_time=start_time,
                                       end_time=end_time)
    
    if not market_data:
        print(f"未获取到{stock_code}的数据")
        return None
    
    # 转换成DataFrame格式
    df = pd.DataFrame()
    for field in fields:
        if field in market_data:
            df[field] = market_data[field].values[0]  # 使用values[0]获取数据
    
    # 将time列转换为日期时间格式
    if 'time' in df.columns:
        df['time'] = pd.to_datetime(df['time'], unit='ms')
    
    return df



# 获取股票实时行情tick数据和最新价格
def get_stock_data(codes):
    """
    获取股票实时行情数据和最新价格
    
    Args:
        codes: 股票代码列表,如 ['000001.SZ']
        
    Returns:
        market_data: 行情数据字典
        df: 行情数据DataFrame格式
        last_price: 第一个股票代码的最新价格
    """
    market_data = xtdata.get_full_tick(codes)
    print(market_data)
    df = pd.DataFrame.from_dict(market_data, orient='index').reset_index().rename(columns={'index': '证券代码'})
    last_price = market_data[codes[0]]['lastPrice']
    
    print(market_data)
    print(f"{codes[0]}的最新价格是: {last_price}")
    
    return market_data, df, last_price





if __name__ == "__main__":
    stock_code = '000001.SZ'
    
    # 获取日线数据
    # print("获取近10日日线行情:")
    daily_data = get_stock_history_data(stock_code, period='1d')
    if daily_data is not None:
        print(daily_data)
        print("\n")
    
    # 获取1分钟线数据
    start_time = '20241101'  # 指定具体的开始时间
    end_time = '20241108'    # 指定具体的结束时间
    print(f"获取{start_time}至{end_time}的1分钟行情:")
    min_data = get_stock_history_data(stock_code, period='1m', start_time=start_time, end_time=end_time)
    if min_data is not None:
        print(f"获取到的1分钟行情数据条数: {len(min_data)}")
        print(min_data)

    # 示例使用
    codes = ['000001.SZ']
    market_data, df, last_price = get_stock_data(codes)
    print(market_data)