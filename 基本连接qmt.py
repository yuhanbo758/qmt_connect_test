#coding=utf-8
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
import random
import time


# 定义回调类
class MyXtQuantTraderCallback(XtQuantTraderCallback):
    
    # 连接断开时的回调
    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        print("连接断开，交易接口断开，即将重连")
        
        global xt_trader
        xt_trader = None

    # 账户状态回调
    def on_account_status(self, status):
        """
        :param status: XtAccountStatus 对象
        :return:
        """
        print(f"账户状态: 账号={status.account_id}, 类型={status.account_type}, 状态={status.status}")






if __name__ == '__main__':
    # 全局变量
    xt_trader = None
    
    print("开始连接交易接口...")
    
    while True:
        try:
            # 基本配置
            path = r'D:\jiaoyi\江海证券QMT模拟交易端\userdata_mini'
            acc = StockAccount('18014745')

            # 初始化交易接口
            session_id = int(random.randint(100000, 999999))
            if xt_trader is None:
                xt_trader = XtQuantTrader(path, session_id)
                xt_trader.start()

            # 连接交易接口
            connect_result = xt_trader.connect()
            if connect_result != 0:
                print('连接失败，程序将重试')
                time.sleep(5)  # 等待5秒后重试
                continue
            
            # 连接成功，注册回调并订阅账户
            print('连接成功，正在订阅账户...')
            callback = MyXtQuantTraderCallback()
            xt_trader.register_callback(callback)
            subscribe_result = xt_trader.subscribe(acc)
            
            if subscribe_result != 0:
                print(f'账号订阅失败: {subscribe_result}')
                time.sleep(5)  # 等待5秒后重试
                continue
            
            # 账户订阅成功，查询资产
            print('账户订阅成功!')
            # 查询资产信息
            asset = xt_trader.query_stock_asset(acc)
            if asset:
                print(f"账户资产信息: 现金={asset.cash}, 冻结资金={asset.frozen_cash}, 市值={asset.market_value}, 总资产={asset.total_asset}")
            
            # 查询并打印持仓信息
            positions = xt_trader.query_stock_positions(acc)
            if positions:
                print("\n持仓信息:")
                for position in positions:
                    print(f"证券代码: {position.stock_code}, 持仓数量: {position.volume}, 可用数量: {position.can_use_volume}, 成本价: {position.open_price:.2f}, 市值: {position.market_value:.2f}")
            else:
                print("当前没有持仓")
            
            # 保持连接
            print("连接已建立并保持中...")
            while xt_trader:
                time.sleep(10)  # 每10秒检查一次连接状态
            
        except Exception as e:
            print(f"运行过程中发生错误: {e}")
            # 遇到错误等待5秒后重试
            time.sleep(5)
            
            # 如果交易对象存在，尝试重新连接
            if xt_trader:
                try:
                    xt_trader = None
                except:
                    pass