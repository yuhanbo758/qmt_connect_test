import random
import time
from xtquant.xttrader import XtQuantTrader
from xtquant.xttype import StockAccount

def test_real_asset_query():
    try:
        # 配置参数
        qmt_path = r'D:\jiaoyi\江海证券QMT模拟交易端\userdata_mini'
        account_id = StockAccount('18014745')
        
        print("开始测试真实资产查询...")
        
        # 连接交易接口
        session_id = random.randint(100000, 999999)
        trader = XtQuantTrader(qmt_path, session_id)
        
        # 启动交易接口
        trader.start()
        print("启动交易接口成功")
        
        # 连接交易服务器
        connect_result = trader.connect()
        if connect_result != 0:
            print(f"连接交易服务器失败，错误码：{connect_result}")
            return
        print("连接交易服务器成功")
        
        # 订阅账户
        acc = StockAccount(account_id)
        subscribe_result = trader.subscribe(acc)
        if subscribe_result != 0:
            print(f"订阅账户失败，错误码：{subscribe_result}")
            return
        print(f"订阅账户 {account_id} 成功")
        
        # 等待一会儿，确保数据已经准备好
        print("等待数据准备...")
        time.sleep(2)
        
        # 查询资产信息 - 这是验证的核心部分
        print("\n===== 资产信息查询 =====")
        assets = trader.query_stock_asset(acc)
        if assets:
            print(f"可用资金: {assets.cash:.2f}")
            print(f"总持仓市值: {assets.market_value:.2f}")
            print(f"总资产: {assets.total_asset:.2f}")
            
            # 模拟保留持仓市值判断
            reserve_position_value = assets.market_value * 0.9  # 假设保留90%的持仓市值
            print(f"\n模拟保留持仓市值（当前市值的90%）: {reserve_position_value:.2f}")
            
            if assets.market_value <= reserve_position_value:
                print("当前持仓市值小于等于保留持仓市值，跳过卖出操作")
            else:
                print("当前持仓市值大于保留持仓市值，可以执行卖出操作")
        else:
            print("获取资产信息失败")
        
        # 查询持仓明细 - 验证个股持仓市值
        print("\n===== 持仓明细查询 =====")
        positions = trader.query_stock_positions(acc)
        if positions:
            total_calculated_value = 0.0
            
            # 打印持仓对象的所有属性，帮助了解正确的属性名
            first_position = positions[0]
            print("Position对象的属性列表:")
            for attr in dir(first_position):
                if not attr.startswith('_'):  # 跳过私有属性
                    try:
                        value = getattr(first_position, attr)
                        if not callable(value):  # 跳过方法，只显示属性
                            print(f"  {attr}: {value}")
                    except:
                        pass
            print("\n详细持仓信息:")
            
            # 使用正确的属性名计算市值
            for pos in positions:
                if pos.volume <= 0:
                    continue
                
                # 使用 last_price 或 average_price 作为价格参考
                # 实际查看打印的属性后确定使用哪个更准确
                # 这里先用 market_value/volume 来反推价格
                try:
                    price = pos.market_value / pos.volume if pos.volume > 0 else 0
                    position_value = pos.market_value
                    total_calculated_value += position_value
                    print(f"股票代码: {pos.stock_code}, 持仓量: {pos.volume}, "
                          f"估计价格: {price:.4f}, 市值: {position_value:.2f}")
                except Exception as e:
                    print(f"处理持仓 {pos.stock_code} 时出错: {str(e)}")
            
            print(f"\n手动累加的总持仓市值: {total_calculated_value:.2f}")
            print(f"系统返回的总持仓市值: {assets.market_value:.2f}")
            print(f"差额: {abs(total_calculated_value - assets.market_value):.2f}")
        else:
            print("获取持仓信息失败或没有持仓")
        
        # 关闭连接
        trader.stop()
        print("\n交易接口已关闭")
        
    except Exception as e:
        print(f"测试过程中发生错误: {str(e)}")

if __name__ == "__main__":
    test_real_asset_query()