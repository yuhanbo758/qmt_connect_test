from xtquant import xtdata
xtdata.enable_hello = False


def get_stock_data(codes):
    """
    获取股票实时行情数据的最新价格
    
    Args:
        codes: 股票代码列表,如 ['000001.SZ']
        
    Returns:
        last_price: 第一个股票代码的最新价格
    """
    market_data = xtdata.get_full_tick(codes)
    print(market_data)
    last_price = market_data[codes[0]]['lastPrice']
    
    print(f"{codes[0]}的最新价格是: {last_price}")
    
    return last_price

if __name__ == '__main__':
    print(get_stock_data(['000001.SZ']))
