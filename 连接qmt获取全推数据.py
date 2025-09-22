# coding: utf-8
import datetime
import time
import json
from xtquant import xtdata

# 定义我们感兴趣的涨幅阈值
RISE_THRESHOLD = 0.09  # 9%涨幅

# 格式化时间的工具函数
def format_current_time():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

# 下载并准备数据
def prepare_data():
    print("正在下载板块数据...")
    xtdata.download_sector_data()
    hsa_list = xtdata.get_stock_list_in_sector('沪深A股')
    print(f"沪深A股共有 {len(hsa_list)} 只股票")
    return hsa_list

# 回调函数：收到全市场分笔数据推送后触发
def on_full_push_tick(data_dict):
    now = format_current_time()
    count = 0
    
    # 打印接收到的数据类型便于调试
    # print(f"接收到全推数据，数据类型: {type(data_dict)}, 数据项数量: {len(data_dict)}")
    
    for code, tick_data in data_dict.items():
        # 检查是否为沪深A股
        if code not in hsa_stocks:
            continue
        
        try:
            # 调试信息，可以用于了解具体的数据结构
            # 如果需要调试，可以取消下面的注释
            # print(f"股票代码: {code}, 数据类型: {type(tick_data)}")
            # if isinstance(tick_data, list):
            #     print(f"列表长度: {len(tick_data)}")
            #     if tick_data:
            #         print(f"第一项内容: {tick_data[0]}")
            # else:
            #     print(f"数据内容: {tick_data}")
            
            # 根据数据格式提取最新价和前收盘价
            if isinstance(tick_data, list) and tick_data:
                last_price = tick_data[0]['lastPrice']
                pre_close = tick_data[0]['lastClose']
            else:
                # 单个对象情况
                last_price = tick_data['lastPrice']
                pre_close = tick_data['lastClose']
            
            # 检查价格有效性
            if not isinstance(last_price, (int, float)) or not isinstance(pre_close, (int, float)):
                continue
            
            # 计算涨幅并打印超过阈值的股票
            if pre_close > 0:
                change_ratio = last_price / pre_close - 1
                if change_ratio > RISE_THRESHOLD:
                    count += 1
                    print(f"{now} {code} 涨幅 {change_ratio:.2%}，最新价 {last_price:.2f}")
        except Exception as e:
            # 错误处理，打印异常信息和有问题的数据
            print(f"处理 {code} 数据时出错: {e}")
            print(f"数据内容: {type(tick_data)}")
            if isinstance(tick_data, (list, dict)):
                print(json.dumps(tick_data, default=str)[:200] + "...")  # 只打印前200个字符
    
    if count > 0:
        print(f"本次推送共发现 {count} 只股票涨幅超过 {RISE_THRESHOLD:.0%}")

if __name__ == "__main__":
    try:
        # 准备数据
        hsa_stocks = prepare_data()
        
        print(f"开始订阅全市场行情，监控涨幅超过 {RISE_THRESHOLD:.0%} 的股票...")
        
        # 使用正确的全推行情订阅API
        # subscribe_whole_quote接受市场代码列表和回调函数
        subscription_id = xtdata.subscribe_whole_quote(["SH", "SZ"], callback=on_full_push_tick)
        
        if subscription_id > 0:
            print(f"全推行情订阅成功，订阅号: {subscription_id}")
            
            # 可以获取当前全推数据查看数据格式
            print("获取当前全推数据...")
            full_tick_data = xtdata.get_full_tick(["SH", "SZ"])
            sample_count = 0
            for code in full_tick_data:
                if sample_count < 3 and code in hsa_stocks:  # 只打印3个样本
                    print(f"样本数据 {code}: {full_tick_data[code]}")
                    sample_count += 1
            print(f"当前全推数据包含 {len(full_tick_data)} 只股票")
        else:
            print("全推行情订阅失败!")
            exit(1)
        
        # 启动事件循环，开始接收并回调
        print("事件循环已启动，等待行情推送...")
        xtdata.run()
        
    except KeyboardInterrupt:
        print("\n程序被用户中断")
    except Exception as e:
        print(f"发生错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 取消订阅
        try:
            if 'subscription_id' in locals() and subscription_id > 0:
                xtdata.unsubscribe_quote(subscription_id)
                print("已取消订阅")
        except Exception as e:
            print(f"取消订阅时出错: {e}")
        print("已退出程序")