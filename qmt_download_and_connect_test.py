# coding=utf-8
"""
QMT连接和数据下载测试工具
集成了QMT交易接口连接、行情数据下载、实时数据获取等功能的GUI应用程序
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading
import queue
import os
import json
import sqlite3
import pandas as pd
import datetime
from datetime import timedelta
import time
import winsound  # Windows系统声音
import markdown  # MD文件渲染
import html2text  # HTML转文本
import subprocess  # 用于播放自定义音效
import json  # JSON配置文件管理

# QMT相关导入
try:
    from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
    from xtquant.xttype import StockAccount
    from xtquant import xtdata
    xtdata.enable_hello = False
    QMT_AVAILABLE = True
except ImportError:
    QMT_AVAILABLE = False


class QMTTraderCallback(XtQuantTraderCallback):
    """QMT交易回调类"""
    
    def __init__(self, log_callback):
        """
        初始化回调类
        
        Args:
            log_callback: 日志输出回调函数
        """
        super().__init__()
        self.log_callback = log_callback

    def on_disconnected(self):
        """连接断开回调"""
        self.log_callback("QMT交易接口连接断开")

    def on_account_status(self, status):
        """账户状态回调"""
        self.log_callback(f"账户状态: 账号={status.account_id}, 类型={status.account_type}, 状态={status.status}")


class QMTDataDownloadGUI:
    """QMT数据下载和连接测试GUI主类"""
    
    def __init__(self, master):
        """
        初始化GUI界面
        
        Args:
            master: tkinter主窗口
        """
        self.master = master
        self.master.title("QMT连接和数据下载测试工具")
        self.master.geometry("900x750")
        
        # 初始化基础变量（必须在其他方法调用之前）
        self.xt_trader = None
        self.log_queue = queue.Queue()
        
        # 检查并设置图标
        self.set_window_icon()
        self.is_connected = False
        self.fullpush_subscription_id = None
        self.fullpush_running = False
        self.custom_stock_list = []  # 自定义股票列表
        self.alert_count = {"rise": 0, "fall": 0}  # 预警计数
        
        # 配置文件管理
        self.config_file = "qmt_config.json"
        self.default_config = {
            "qmt": {
                "path": "",
                "stock_account": ""
            },
            "monitor": {
                "rise_threshold": 0.05,
                "fall_threshold": 0.05,
                "monitor_stocks": "全市场",
                "sound_enabled": True,
                "sound_type": "系统提示音"
            },
            "realtime": {
                "stock_code": "000001.SZ"
            }
        }
        
        # 创建GUI界面
        self.create_widgets()
        
        # 加载配置文件
        self.load_config()
        
        # 绑定变量变化事件，实现自动保存
        self.bind_config_events()
        
        # 启动日志处理
        self.process_log_queue()
        
        # 绑定窗口关闭事件
        self.master.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 检查QMT库是否可用
        if not QMT_AVAILABLE:
            self.log("警告: QMT库未安装或导入失败，部分功能将不可用")

    def set_window_icon(self):
        """设置窗口图标"""
        try:
            # 首先尝试加载ICO格式图标
            icon_path = os.path.join(os.path.dirname(__file__), "logo.ico")
            if os.path.exists(icon_path):
                self.master.iconbitmap(icon_path)
                self.log("已加载自定义ICO图标")
                return
            
            # 如果ICO不存在，检查SVG图标并提示用户
            svg_path = os.path.join(os.path.dirname(__file__), "logo.svg")
            if os.path.exists(svg_path):
                self.log("检测到SVG图标文件，建议转换为ICO格式以获得最佳显示效果")
            else:
                self.log("未找到图标文件，使用系统默认图标")
                
        except Exception as e:
            self.log(f"设置图标时发生错误: {e}")

    def create_widgets(self):
        """创建GUI组件"""
        # 创建主框架
        main_frame = ttk.Frame(self.master)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建笔记本控件（标签页）
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True)
        
        # 连接测试标签页
        self.create_connection_tab(notebook)
        
        # 数据下载标签页
        self.create_download_tab(notebook)
        
        # 批量导入标签页
        self.create_batch_tab(notebook)
        
        # 实时数据标签页
        self.create_realtime_tab(notebook)
        
        # 帮助标签页
        self.create_help_tab(notebook)
        
        # 日志输出区域
        self.create_log_area(main_frame)

    def create_connection_tab(self, notebook):
        """创建连接测试标签页"""
        conn_frame = ttk.Frame(notebook)
        notebook.add(conn_frame, text="连接测试")
        
        # QMT路径设置
        path_frame = ttk.LabelFrame(conn_frame, text="QMT配置", padding=10)
        path_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(path_frame, text="QMT路径:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.qmt_path_var = tk.StringVar(value=r'D:\jiaoyi\江海证券QMT模拟交易端\userdata_mini')
        ttk.Entry(path_frame, textvariable=self.qmt_path_var, width=60).grid(row=0, column=1, padx=5)
        ttk.Button(path_frame, text="浏览", command=self.browse_qmt_path).grid(row=0, column=2, padx=5)
        
        ttk.Label(path_frame, text="证券账号:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.account_id_var = tk.StringVar(value='1000000365')
        ttk.Entry(path_frame, textvariable=self.account_id_var, width=20).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        # 连接控制
        control_frame = ttk.LabelFrame(conn_frame, text="连接控制", padding=10)
        control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(control_frame, text="连接QMT", command=self.connect_qmt).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="断开连接", command=self.disconnect_qmt).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="查询资产", command=self.query_assets).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="查询持仓", command=self.query_positions).pack(side=tk.LEFT, padx=5)
        
        # 连接状态显示
        status_frame = ttk.LabelFrame(conn_frame, text="连接状态", padding=10)
        status_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.status_text = scrolledtext.ScrolledText(status_frame, height=4, state=tk.DISABLED)
        self.status_text.pack(fill=tk.BOTH, expand=True)

    def create_download_tab(self, notebook):
        """创建数据下载标签页"""
        download_frame = ttk.Frame(notebook)
        notebook.add(download_frame, text="数据下载")
        
        # 股票代码输入
        code_frame = ttk.LabelFrame(download_frame, text="股票代码", padding=10)
        code_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(code_frame, text="股票代码:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.stock_code_var = tk.StringVar(value='000001.SZ')
        ttk.Entry(code_frame, textvariable=self.stock_code_var, width=20).grid(row=0, column=1, padx=5)
        
        # 数据类型选择
        type_frame = ttk.LabelFrame(download_frame, text="数据类型", padding=10)
        type_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.data_type_var = tk.StringVar(value='1d')
        data_types = [('日线', '1d'), ('5分钟', '5m'), ('1分钟', '1m'), ('分笔', 'tick')]
        for i, (text, value) in enumerate(data_types):
            ttk.Radiobutton(type_frame, text=text, variable=self.data_type_var, value=value).grid(row=0, column=i, padx=10)
        
        # 时间范围
        time_frame = ttk.LabelFrame(download_frame, text="时间范围", padding=10)
        time_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(time_frame, text="开始日期:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.start_date_var = tk.StringVar(value='20240101')
        ttk.Entry(time_frame, textvariable=self.start_date_var, width=15).grid(row=0, column=1, padx=5)
        
        ttk.Label(time_frame, text="结束日期:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.end_date_var = tk.StringVar(value=datetime.datetime.now().strftime('%Y%m%d'))
        ttk.Entry(time_frame, textvariable=self.end_date_var, width=15).grid(row=0, column=3, padx=5)
        
        # 保存格式
        save_frame = ttk.LabelFrame(download_frame, text="保存格式", padding=10)
        save_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.save_format_var = tk.StringVar(value='csv')
        save_formats = [('CSV', 'csv'), ('JSON', 'json'), ('数据库', 'db')]
        for i, (text, value) in enumerate(save_formats):
            ttk.Radiobutton(save_frame, text=text, variable=self.save_format_var, value=value).grid(row=0, column=i, padx=10)
        
        # 下载选项
        option_frame = ttk.LabelFrame(download_frame, text="下载选项", padding=10)
        option_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.incremental_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(option_frame, text="增量下载（跳过已有数据）", variable=self.incremental_var).pack(side=tk.LEFT, padx=5)
        
        # 下载控制
        download_control_frame = ttk.Frame(download_frame)
        download_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(download_control_frame, text="下载数据", command=self.download_single_stock).pack(side=tk.LEFT, padx=5)
        ttk.Button(download_control_frame, text="选择保存路径", command=self.select_save_path).pack(side=tk.LEFT, padx=5)
        
        self.save_path_var = tk.StringVar(value=os.path.join(os.getcwd(), "data"))
        ttk.Label(download_control_frame, text="保存路径:").pack(side=tk.LEFT, padx=5)
        ttk.Entry(download_control_frame, textvariable=self.save_path_var, width=40).pack(side=tk.LEFT, padx=5)

    def create_batch_tab(self, notebook):
        """创建批量导入标签页"""
        batch_frame = ttk.Frame(notebook)
        notebook.add(batch_frame, text="批量导入")
        
        # 文件导入
        import_frame = ttk.LabelFrame(batch_frame, text="文件导入", padding=10)
        import_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(import_frame, text="导入Excel文件", command=self.import_excel).pack(side=tk.LEFT, padx=5)
        ttk.Button(import_frame, text="导入文本文件", command=self.import_text).pack(side=tk.LEFT, padx=5)
        ttk.Button(import_frame, text="清空列表", command=self.clear_stock_list).pack(side=tk.LEFT, padx=5)
        
        # 手动输入
        manual_frame = ttk.LabelFrame(batch_frame, text="手动输入", padding=10)
        manual_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(manual_frame, text="股票代码(多个用逗号分隔):").pack(anchor=tk.W)
        self.manual_codes_var = tk.StringVar()
        ttk.Entry(manual_frame, textvariable=self.manual_codes_var, width=80).pack(fill=tk.X, pady=5)
        ttk.Button(manual_frame, text="添加到列表", command=self.add_manual_codes).pack()
        
        # 股票列表
        list_frame = ttk.LabelFrame(batch_frame, text="股票列表", padding=10)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 创建Treeview
        columns = ('序号', '股票代码', '状态')
        self.stock_tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=6)
        
        for col in columns:
            self.stock_tree.heading(col, text=col)
            self.stock_tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.stock_tree.yview)
        self.stock_tree.configure(yscrollcommand=scrollbar.set)
        
        self.stock_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 批量下载控制
        batch_control_frame = ttk.Frame(batch_frame)
        batch_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(batch_control_frame, text="开始批量下载", command=self.start_batch_download).pack(side=tk.LEFT, padx=5)
        ttk.Button(batch_control_frame, text="停止下载", command=self.stop_batch_download).pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(batch_control_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=5)

    def create_realtime_tab(self, notebook):
        """创建实时数据标签页"""
        realtime_frame = ttk.Frame(notebook)
        notebook.add(realtime_frame, text="实时数据")
        
        # 实时行情控制
        rt_control_frame = ttk.LabelFrame(realtime_frame, text="实时行情控制", padding=10)
        rt_control_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(rt_control_frame, text="股票代码:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.rt_stock_code_var = tk.StringVar(value='000001.SZ')
        ttk.Entry(rt_control_frame, textvariable=self.rt_stock_code_var, width=20).grid(row=0, column=1, padx=5)
        
        ttk.Button(rt_control_frame, text="获取最新价", command=self.get_latest_price).grid(row=0, column=2, padx=5)
        ttk.Button(rt_control_frame, text="订阅实时行情", command=self.subscribe_realtime).grid(row=0, column=3, padx=5)
        ttk.Button(rt_control_frame, text="取消订阅", command=self.unsubscribe_realtime).grid(row=0, column=4, padx=5)
        
        # 全推数据控制
        fullpush_frame = ttk.LabelFrame(realtime_frame, text="全推数据控制", padding=10)
        fullpush_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # 第一行：阈值设置
        ttk.Label(fullpush_frame, text="涨幅阈值:").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.rise_threshold_var = tk.DoubleVar(value=0.09)
        ttk.Entry(fullpush_frame, textvariable=self.rise_threshold_var, width=8).grid(row=0, column=1, padx=5)
        
        ttk.Label(fullpush_frame, text="跌幅阈值:").grid(row=0, column=2, sticky=tk.W, padx=5)
        self.fall_threshold_var = tk.DoubleVar(value=0.09)
        ttk.Entry(fullpush_frame, textvariable=self.fall_threshold_var, width=8).grid(row=0, column=3, padx=5)
        
        # 第二行：声音设置
        ttk.Label(fullpush_frame, text="预警声音:").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.sound_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(fullpush_frame, text="启用", variable=self.sound_enabled_var).grid(row=1, column=1, sticky=tk.W, padx=5)
        
        self.sound_type_var = tk.StringVar(value="系统提示音")
        sound_combo = ttk.Combobox(fullpush_frame, textvariable=self.sound_type_var, width=12, state="readonly")
        sound_combo['values'] = ("系统提示音", "警报声", "铃声", "自定义音效")
        sound_combo.grid(row=1, column=2, columnspan=2, sticky=tk.W, padx=5)
        
        # 第三行：批量监控设置
        ttk.Label(fullpush_frame, text="监控股票:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.monitor_stocks_var = tk.StringVar(value="全市场")
        monitor_combo = ttk.Combobox(fullpush_frame, textvariable=self.monitor_stocks_var, width=12, state="readonly")
        monitor_combo['values'] = ("全市场", "沪深A股", "创业板", "科创板", "自定义列表")
        monitor_combo.grid(row=2, column=1, columnspan=2, sticky=tk.W, padx=5)
        
        ttk.Button(fullpush_frame, text="设置自定义", command=self.setup_custom_stocks).grid(row=2, column=3, padx=5)
        
        # 第四行：控制按钮
        ttk.Button(fullpush_frame, text="开始全推监控", command=self.start_fullpush_monitor).grid(row=3, column=0, padx=5, pady=5)
        ttk.Button(fullpush_frame, text="停止监控", command=self.stop_fullpush_monitor).grid(row=3, column=1, padx=5, pady=5)
        ttk.Button(fullpush_frame, text="测试声音", command=self.test_sound).grid(row=3, column=2, padx=5, pady=5)
        ttk.Button(fullpush_frame, text="清空显示", command=self.clear_realtime_display).grid(row=3, column=3, padx=5, pady=5)
        
        # 实时数据显示
        rt_display_frame = ttk.LabelFrame(realtime_frame, text="实时数据显示", padding=10)
        rt_display_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.realtime_text = scrolledtext.ScrolledText(rt_display_frame, height=10, state=tk.DISABLED)
        self.realtime_text.pack(fill=tk.BOTH, expand=True)

    def create_help_tab(self, notebook):
        """创建帮助标签页"""
        help_frame = ttk.Frame(notebook)
        notebook.add(help_frame, text="帮助")
        
        # 文档按钮
        doc_frame = ttk.LabelFrame(help_frame, text="文档", padding=10)
        doc_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(doc_frame, text="使用说明", command=self.open_usage_guide).pack(side=tk.LEFT, padx=5)
        ttk.Button(doc_frame, text="README", command=self.open_readme).pack(side=tk.LEFT, padx=5)
        
        # 配置管理按钮
        config_frame = ttk.LabelFrame(help_frame, text="配置管理", padding=10)
        config_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(config_frame, text="保存配置", command=self.save_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_frame, text="重新加载", command=self.load_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_frame, text="重置配置", command=self.reset_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(config_frame, text="打开配置文件", command=self.open_config_file).pack(side=tk.LEFT, padx=5)
        
        # 关于信息
        about_frame = ttk.LabelFrame(help_frame, text="关于", padding=10)
        about_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        about_text = """
QMT连接和数据下载测试工具 v1.0

功能特性:
• QMT交易接口连接测试
• 历史行情数据下载 (支持tick、1分钟、5分钟、日线)
• 批量股票代码导入 (Excel、文本文件)
• 多种数据保存格式 (CSV、JSON、数据库)
• 实时行情数据获取
• 全推数据监控

使用前请确保:
1. 已安装QMT客户端
2. 已安装xtquant库
3. QMT客户端已登录并处于极简模式

技术支持: 请查看使用说明和README文档
        """
        
        about_label = tk.Label(about_frame, text=about_text, justify=tk.LEFT, anchor=tk.NW)
        about_label.pack(fill=tk.BOTH, expand=True)

    def create_log_area(self, parent):
        """创建日志输出区域"""
        log_frame = ttk.LabelFrame(parent, text="日志输出", padding=5)
        log_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=12, state=tk.DISABLED)
        self.log_text.pack(fill=tk.BOTH, expand=True)

    def log(self, message):
        """添加日志消息到队列"""
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.log_queue.put(f"[{timestamp}] {message}")

    def process_log_queue(self):
        """处理日志队列中的消息"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.config(state=tk.NORMAL)
                self.log_text.insert(tk.END, message + "\n")
                self.log_text.config(state=tk.DISABLED)
                self.log_text.see(tk.END)
        except queue.Empty:
            pass
        
        # 每100ms检查一次队列
        self.master.after(100, self.process_log_queue)

    def browse_qmt_path(self):
        """浏览QMT路径"""
        path = filedialog.askdirectory(title="选择QMT userdata_mini路径")
        if path:
            self.qmt_path_var.set(path)

    def select_save_path(self):
        """选择保存路径"""
        path = filedialog.askdirectory(title="选择数据保存路径")
        if path:
            self.save_path_var.set(path)

    def connect_qmt(self):
        """连接QMT"""
        if not QMT_AVAILABLE:
            self.log("错误: QMT库不可用")
            return
        
        def connect_thread():
            try:
                path = self.qmt_path_var.get()
                account_id = self.account_id_var.get()
                
                if not path or not account_id:
                    self.log("错误: 请填写QMT路径和证券账号")
                    return
                
                self.log("开始连接QMT...")
                
                # 创建交易接口，使用时间戳生成唯一的session_id
                import time
                session_id = int(time.time())
                self.log(f"生成会话ID: {session_id}")
                self.xt_trader = XtQuantTrader(path, session_id)
                
                # 注册回调
                callback = QMTTraderCallback(self.log)
                self.xt_trader.register_callback(callback)
                
                # 启动交易线程
                self.xt_trader.start()
                self.log("交易线程启动成功")
                
                # 连接交易服务器
                connect_result = self.xt_trader.connect()
                if connect_result != 0:
                    self.log(f"连接失败，错误码: {connect_result}")
                    return
                
                self.log("连接QMT成功")
                
                # 订阅账户
                acc = StockAccount(account_id)
                subscribe_result = self.xt_trader.subscribe(acc)
                if subscribe_result != 0:
                    self.log(f"账户订阅失败，错误码: {subscribe_result}")
                    return
                
                self.log(f"账户 {account_id} 订阅成功")
                self.is_connected = True
                
            except Exception as e:
                self.log(f"连接QMT时发生错误: {e}")
        
        threading.Thread(target=connect_thread, daemon=True).start()

    def disconnect_qmt(self):
        """断开QMT连接"""
        if self.xt_trader:
            try:
                self.xt_trader = None
                self.is_connected = False
                self.log("已断开QMT连接")
            except Exception as e:
                self.log(f"断开连接时发生错误: {e}")
        else:
            self.log("当前没有活动的连接")

    def query_assets(self):
        """查询资产信息"""
        if not self.is_connected or not self.xt_trader:
            self.log("错误: 请先连接QMT")
            return
        
        def query_thread():
            try:
                account_id = self.account_id_var.get()
                acc = StockAccount(account_id)
                
                assets = self.xt_trader.query_stock_asset(acc)
                if assets:
                    self.update_status_display(f"""
资产信息查询结果:
账户ID: {account_id}
可用资金: {assets.cash:.2f}
冻结资金: {assets.frozen_cash:.2f}
持仓市值: {assets.market_value:.2f}
总资产: {assets.total_asset:.2f}
查询时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
                    self.log("资产信息查询成功")
                else:
                    self.log("资产信息查询失败")
                    
            except Exception as e:
                self.log(f"查询资产时发生错误: {e}")
        
        threading.Thread(target=query_thread, daemon=True).start()

    def query_positions(self):
        """查询持仓信息"""
        if not self.is_connected or not self.xt_trader:
            self.log("错误: 请先连接QMT")
            return
        
        def query_thread():
            try:
                account_id = self.account_id_var.get()
                acc = StockAccount(account_id)
                
                positions = self.xt_trader.query_stock_positions(acc)
                if positions:
                    position_info = f"持仓信息查询结果 (共{len(positions)}只股票):\n"
                    position_info += f"{'股票代码':<12} {'持仓量':<10} {'可用量':<10} {'成本价':<10} {'市值':<12}\n"
                    position_info += "-" * 60 + "\n"
                    
                    total_value = 0
                    for pos in positions:
                        if pos.volume > 0:
                            position_info += f"{pos.stock_code:<12} {pos.volume:<10} {pos.can_use_volume:<10} {pos.open_price:<10.2f} {pos.market_value:<12.2f}\n"
                            total_value += pos.market_value
                    
                    position_info += "-" * 60 + "\n"
                    position_info += f"总持仓市值: {total_value:.2f}\n"
                    position_info += f"查询时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    
                    self.update_status_display(position_info)
                    self.log("持仓信息查询成功")
                else:
                    self.update_status_display("当前没有持仓")
                    self.log("当前没有持仓")
                    
            except Exception as e:
                self.log(f"查询持仓时发生错误: {e}")
        
        threading.Thread(target=query_thread, daemon=True).start()

    def update_status_display(self, text):
        """更新状态显示区域"""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        self.status_text.insert(tk.END, text)
        self.status_text.config(state=tk.DISABLED)
    
    def check_existing_data(self, stock_code, data_type, start_date, end_date, save_format, save_path):
        """检查已有数据，返回需要下载的日期范围"""
        if not self.incremental_var.get():
            # 如果不启用增量下载，返回原始日期范围
            return start_date, end_date
        
        try:
            # 根据保存格式确定文件路径
            if save_format == 'csv':
                file_path = os.path.join(save_path, f"{stock_code}_{data_type}.csv")
                if os.path.exists(file_path):
                    # 读取CSV文件的最后一行，获取最新日期
                    import pandas as pd
                    df = pd.read_csv(file_path)
                    if not df.empty:
                        if data_type == 'tick':
                            # tick数据使用time列
                            if 'time' in df.columns:
                                last_time = df['time'].iloc[-1]
                                # 提取日期部分
                                if isinstance(last_time, str):
                                    last_date = last_time[:8]  # 取前8位作为日期
                                else:
                                    last_date = str(int(last_time))[:8]
                                
                                # 计算下一天作为新的开始日期
                                last_dt = datetime.datetime.strptime(last_date, '%Y%m%d')
                                next_dt = last_dt + timedelta(days=1)
                                new_start_date = next_dt.strftime('%Y%m%d')
                                
                                if new_start_date <= end_date:
                                    self.log(f"检测到已有数据到 {last_date}，从 {new_start_date} 开始增量下载")
                                    return new_start_date, end_date
                                else:
                                    self.log(f"数据已是最新，无需下载")
                                    return None, None
                        else:
                            # K线数据使用time列
                            if 'time' in df.columns:
                                last_time = df['time'].iloc[-1]
                                last_date = str(last_time)
                                
                                # 根据数据类型计算下一个时间点
                                if data_type == '1d':
                                    last_dt = datetime.datetime.strptime(last_date, '%Y%m%d')
                                    next_dt = last_dt + timedelta(days=1)
                                    new_start_date = next_dt.strftime('%Y%m%d')
                                else:
                                    # 对于分钟数据，使用下一天
                                    last_dt = datetime.datetime.strptime(last_date[:8], '%Y%m%d')
                                    next_dt = last_dt + timedelta(days=1)
                                    new_start_date = next_dt.strftime('%Y%m%d')
                                
                                if new_start_date <= end_date:
                                    self.log(f"检测到已有数据到 {last_date}，从 {new_start_date} 开始增量下载")
                                    return new_start_date, end_date
                                else:
                                    self.log(f"数据已是最新，无需下载")
                                    return None, None
            
            elif save_format == 'db':
                # 检查数据库中的最新数据
                db_path = os.path.join(save_path, 'stock_data.db')
                if os.path.exists(db_path):
                    import sqlite3
                    conn = sqlite3.connect(db_path)
                    table_name = f"{stock_code}_{data_type}"
                    
                    # 检查表是否存在
                    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
                    if cursor.fetchone():
                        # 获取最新的时间
                        cursor = conn.execute(f"SELECT MAX(time) FROM {table_name}")
                        result = cursor.fetchone()
                        if result and result[0]:
                            last_time = str(result[0])
                            if data_type == 'tick':
                                last_date = last_time[:8]
                                last_dt = datetime.datetime.strptime(last_date, '%Y%m%d')
                                next_dt = last_dt + timedelta(days=1)
                                new_start_date = next_dt.strftime('%Y%m%d')
                            else:
                                last_date = last_time[:8] if len(last_time) >= 8 else last_time
                                last_dt = datetime.datetime.strptime(last_date, '%Y%m%d')
                                next_dt = last_dt + timedelta(days=1)
                                new_start_date = next_dt.strftime('%Y%m%d')
                            
                            if new_start_date <= end_date:
                                self.log(f"检测到数据库中已有数据到 {last_date}，从 {new_start_date} 开始增量下载")
                                conn.close()
                                return new_start_date, end_date
                            else:
                                self.log(f"数据库中数据已是最新，无需下载")
                                conn.close()
                                return None, None
                    conn.close()
            
        except Exception as e:
            self.log(f"检查已有数据时出错: {e}，将进行完整下载")
        
        # 如果检查失败或没有已有数据，返回原始日期范围
        return start_date, end_date
    
    def validate_data_integrity(self, file_path, data_type):
        """验证保存文件的数据完整性"""
        try:
            if not os.path.exists(file_path):
                return False, "文件不存在"
            
            if file_path.endswith('.csv'):
                import pandas as pd
                df = pd.read_csv(file_path)
                
                if df.empty:
                    return False, "文件为空"
                
                # 检查必要的列
                if data_type == 'tick':
                    required_columns = ['stock_code', 'time', 'lastPrice']
                else:
                    required_columns = ['time', 'open', 'high', 'low', 'close', 'volume']
                
                missing_columns = [col for col in required_columns if col not in df.columns]
                if missing_columns:
                    return False, f"缺少必要列: {missing_columns}"
                
                # 检查数据是否有重复的时间戳
                if 'time' in df.columns:
                    duplicate_count = df['time'].duplicated().sum()
                    if duplicate_count > 0:
                        self.log(f"警告: 发现 {duplicate_count} 条重复时间戳的数据")
                
                return True, f"验证通过，共 {len(df)} 条记录"
            
            return True, "文件存在"
            
        except Exception as e:
            return False, f"验证时出错: {e}"

    def download_single_stock(self):
        """下载单只股票数据"""
        if not QMT_AVAILABLE:
            self.log("错误: QMT库不可用")
            return
        
        def download_thread():
            try:
                stock_code = self.stock_code_var.get()
                data_type = self.data_type_var.get()
                start_date = self.start_date_var.get()
                end_date = self.end_date_var.get()
                save_format = self.save_format_var.get()
                save_path = self.save_path_var.get()
                
                if not stock_code:
                    self.log("错误: 请输入股票代码")
                    return
                
                # 检查已有数据，确定实际需要下载的日期范围
                actual_start_date, actual_end_date = self.check_existing_data(
                    stock_code, data_type, start_date, end_date, save_format, save_path
                )
                
                if actual_start_date is None or actual_end_date is None:
                    self.log(f"{stock_code} 的 {data_type} 数据已是最新，无需下载")
                    return
                
                self.log(f"开始下载 {stock_code} 的 {data_type} 数据，时间范围: {actual_start_date} 到 {actual_end_date}")
                
                # 确保保存目录存在
                os.makedirs(save_path, exist_ok=True)
                
                # 下载历史数据
                if data_type == 'tick':
                    # 对于tick数据，需要按天下载
                    self.log(f"开始下载 {stock_code} 的tick数据")
                    
                    # 将日期字符串转换为datetime对象
                    start_dt = datetime.datetime.strptime(actual_start_date, '%Y%m%d')
                    end_dt = datetime.datetime.strptime(actual_end_date, '%Y%m%d')
                    
                    # 按天下载tick数据
                    current_dt = start_dt
                    all_tick_data = []
                    
                    while current_dt <= end_dt:
                        current_date_str = current_dt.strftime('%Y%m%d')
                        self.log(f"下载 {stock_code} {current_date_str} 的tick数据")
                        
                        try:
                            # 下载当天的tick数据
                            xtdata.download_history_data(stock_code, period='tick', 
                                                       start_time=current_date_str, 
                                                       end_time=current_date_str)
                            
                            # 获取当天的tick数据
                            daily_data = xtdata.get_market_data_ex([], [stock_code], period='tick',
                                                                 start_time=current_date_str, 
                                                                 end_time=current_date_str)
                            
                            if daily_data and stock_code in daily_data:
                                tick_df = daily_data[stock_code]
                                if not tick_df.empty:
                                    # 将DataFrame转换为字典列表格式
                                    tick_records = tick_df.to_dict('records')
                                    all_tick_data.extend(tick_records)
                                    self.log(f"{current_date_str} 获取到 {len(tick_records)} 条tick数据")
                                else:
                                    self.log(f"{current_date_str} 无tick数据")
                            else:
                                self.log(f"{current_date_str} 无tick数据")
                                
                        except Exception as e:
                            self.log(f"下载 {current_date_str} tick数据时出错: {e}")
                        
                        # 移动到下一天
                        current_dt += timedelta(days=1)
                        
                        # 添加短暂延迟，避免请求过于频繁
                        time.sleep(0.1)
                    
                    # 将所有tick数据组织成标准格式
                    if all_tick_data:
                        data = {stock_code: all_tick_data}
                        self.log(f"总共获取到 {len(all_tick_data)} 条tick数据")
                    else:
                        data = None
                        self.log(f"未获取到任何tick数据")
                else:
                    # K线数据的下载逻辑
                    xtdata.download_history_data(stock_code, period=data_type, start_time=actual_start_date, end_time=actual_end_date)
                    
                    # K线数据
                    fields = ['time', 'open', 'high', 'low', 'close', 'volume', 'amount']
                    data = xtdata.get_market_data(field_list=fields, stock_list=[stock_code],
                                                period=data_type, start_time=actual_start_date, end_time=actual_end_date)
                
                if not data:
                    self.log(f"未获取到 {stock_code} 的数据")
                    return
                
                # 保存数据
                filename = f"{stock_code}_{data_type}_{actual_start_date}_{actual_end_date}"
                self.save_data(data, stock_code, filename, save_format, save_path)
                
                self.log(f"{stock_code} 数据下载完成")
                
            except Exception as e:
                self.log(f"下载数据时发生错误: {e}")
        
        threading.Thread(target=download_thread, daemon=True).start()

    def save_data(self, data, stock_code, filename, save_format, save_path):
        """保存数据到指定格式"""
        try:
            # 数据验证
            if not data:
                self.log(f"错误: {stock_code} 数据为空，无法保存")
                return False
            
            # 检查数据类型并确定是tick数据还是K线数据
            is_tick_data = False
            data_count = 0
            
            if isinstance(data, dict) and stock_code in data:
                # 检查是否为tick数据格式
                tick_list = data[stock_code]
                if isinstance(tick_list, list) and len(tick_list) > 0:
                    data_count = len(tick_list)
                    # 检查第一个元素是否包含tick数据的典型字段
                    first_item = tick_list[0]
                    if isinstance(first_item, dict) and 'lastPrice' in first_item:
                        is_tick_data = True
                        # 验证tick数据完整性
                        required_fields = ['time', 'lastPrice', 'volume']
                        missing_fields = [field for field in required_fields if field not in first_item]
                        if missing_fields:
                            self.log(f"警告: {stock_code} tick数据缺少字段: {missing_fields}")
                else:
                    # 检查K线数据
                    for field, values in data.items():
                        if hasattr(values, 'values') and len(values.values) > 0:
                            if data_count == 0:
                                data_count = len(values.values[0])
                            break
            
            if save_format == 'csv':
                # 使用统一的文件名格式，不包含日期范围
                csv_path = os.path.join(save_path, f"{stock_code}_{self.data_type_var.get()}.csv")
                
                if is_tick_data:
                    # 处理tick数据
                    tick_list = data[stock_code]
                    df = pd.DataFrame(tick_list)
                    
                    # 转换时间戳为可读格式
                    if 'time' in df.columns:
                        df['time'] = pd.to_datetime(df['time'], unit='ms')
                    
                    # 添加股票代码列
                    df['stock_code'] = stock_code
                    
                    # 重新排列列的顺序，将股票代码和时间放在前面
                    cols = ['stock_code', 'time'] + [col for col in df.columns if col not in ['stock_code', 'time']]
                    df = df[cols]
                    
                    # 检查文件是否存在，决定是否追加
                    if os.path.exists(csv_path) and self.incremental_var.get():
                        # 追加模式，不写入表头
                        df.to_csv(csv_path, mode='a', header=False, index=False, encoding='utf-8-sig')
                        self.log(f"tick数据已追加到: {csv_path} (新增{len(df)}条记录)")
                    else:
                        # 新建文件或覆盖模式
                        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                        self.log(f"tick数据已保存到: {csv_path} (共{len(df)}条记录)")
                    
                    # 验证保存的数据完整性
                    is_valid, message = self.validate_data_integrity(csv_path, 'tick')
                    if not is_valid:
                        self.log(f"数据完整性验证失败: {message}")
                    else:
                        self.log(f"数据完整性验证: {message}")
                    
                else:
                    # 处理K线数据
                    df = pd.DataFrame()
                    for field, values in data.items():
                        if hasattr(values, 'values') and len(values.values) > 0:
                            df[field] = values.values[0]
                    
                    if 'time' in df.columns:
                        df['time'] = pd.to_datetime(df['time'], unit='ms')
                    
                    # 检查文件是否存在，决定是否追加
                    if os.path.exists(csv_path) and self.incremental_var.get():
                        # 追加模式，不写入表头
                        df.to_csv(csv_path, mode='a', header=False, index=False, encoding='utf-8-sig')
                        self.log(f"K线数据已追加到: {csv_path} (新增{len(df)}条记录)")
                    else:
                        # 新建文件或覆盖模式
                        df.to_csv(csv_path, index=False, encoding='utf-8-sig')
                        self.log(f"K线数据已保存到: {csv_path} (共{len(df)}条记录)")
                    
                    # 验证保存的数据完整性
                    is_valid, message = self.validate_data_integrity(csv_path, 'kline')
                    if not is_valid:
                        self.log(f"数据完整性验证失败: {message}")
                    else:
                        self.log(f"数据完整性验证: {message}")
                
            elif save_format == 'json':
                json_path = os.path.join(save_path, f"{filename}.json")
                
                if is_tick_data:
                    # 处理tick数据
                    tick_list = data[stock_code]
                    
                    # 转换时间戳为可读格式
                    processed_data = []
                    for tick in tick_list:
                        tick_copy = tick.copy()
                        if 'time' in tick_copy:
                            tick_copy['time'] = datetime.datetime.fromtimestamp(tick_copy['time'] / 1000).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                        tick_copy['stock_code'] = stock_code
                        processed_data.append(tick_copy)
                    
                    json_data = {
                        'stock_code': stock_code,
                        'data_type': 'tick',
                        'total_records': len(processed_data),
                        'data': processed_data
                    }
                    
                else:
                    # 处理K线数据
                    json_data = {}
                    for field, values in data.items():
                        if hasattr(values, 'values') and len(values.values) > 0:
                            json_data[field] = values.values[0].tolist()
                
                with open(json_path, 'w', encoding='utf-8') as f:
                    json.dump(json_data, f, ensure_ascii=False, indent=2)
                
                self.log(f"数据已保存到: {json_path}")
                
            elif save_format == 'db':
                # 保存到SQLite数据库
                db_path = os.path.join(save_path, "stock_data.db")
                conn = sqlite3.connect(db_path)
                
                if is_tick_data:
                    # 处理tick数据
                    tick_list = data[stock_code]
                    df = pd.DataFrame(tick_list)
                    
                    # 转换时间戳为可读格式
                    if 'time' in df.columns:
                        df['time'] = pd.to_datetime(df['time'], unit='ms')
                    
                    # 添加股票代码列
                    df['stock_code'] = stock_code
                    
                    # 保存到数据库
                    table_name = "tick_data"
                    df.to_sql(table_name, conn, if_exists='append', index=False)
                    self.log(f"tick数据已保存到数据库: {db_path} (共{len(df)}条记录)")
                    
                else:
                    # 处理K线数据
                    df = pd.DataFrame()
                    for field, values in data.items():
                        if hasattr(values, 'values') and len(values.values) > 0:
                            df[field] = values.values[0]
                    
                    if 'time' in df.columns:
                        df['time'] = pd.to_datetime(df['time'], unit='ms')
                    
                    # 添加股票代码列
                    df['stock_code'] = stock_code
                    
                    # 保存到数据库
                    table_name = f"data_{self.data_type_var.get()}"
                    df.to_sql(table_name, conn, if_exists='append', index=False)
                    self.log(f"K线数据已保存到数据库: {db_path}")
                
                conn.close()
            
            # 保存成功后的验证
            self.log(f"数据保存完成: {stock_code} ({data_count}条记录)")
            return True
                
        except Exception as e:
            self.log(f"保存数据时发生错误: {e}")
            import traceback
            self.log(f"详细错误信息: {traceback.format_exc()}")
            return False

    def import_excel(self):
        """导入Excel文件"""
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        
        if file_path:
            try:
                df = pd.read_excel(file_path)
                # 假设第一列是股票代码
                codes = df.iloc[:, 0].astype(str).tolist()
                self.add_codes_to_tree(codes)
                self.log(f"从Excel文件导入了 {len(codes)} 个股票代码")
            except Exception as e:
                self.log(f"导入Excel文件时发生错误: {e}")

    def import_text(self):
        """导入文本文件"""
        file_path = filedialog.askopenfilename(
            title="选择文本文件",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # 按行分割，去除空行
                codes = [line.strip() for line in content.split('\n') if line.strip()]
                self.add_codes_to_tree(codes)
                self.log(f"从文本文件导入了 {len(codes)} 个股票代码")
            except Exception as e:
                self.log(f"导入文本文件时发生错误: {e}")

    def add_manual_codes(self):
        """添加手动输入的股票代码"""
        codes_text = self.manual_codes_var.get()
        if codes_text:
            codes = [code.strip() for code in codes_text.split(',') if code.strip()]
            self.add_codes_to_tree(codes)
            self.manual_codes_var.set('')
            self.log(f"手动添加了 {len(codes)} 个股票代码")

    def add_codes_to_tree(self, codes):
        """添加股票代码到树形控件"""
        for code in codes:
            # 检查是否已存在
            exists = False
            for item in self.stock_tree.get_children():
                if self.stock_tree.item(item)['values'][1] == code:
                    exists = True
                    break
            
            if not exists:
                index = len(self.stock_tree.get_children()) + 1
                self.stock_tree.insert('', tk.END, values=(index, code, '待下载'))

    def clear_stock_list(self):
        """清空股票列表"""
        for item in self.stock_tree.get_children():
            self.stock_tree.delete(item)
        self.log("已清空股票列表")

    def start_batch_download(self):
        """开始批量下载"""
        if not QMT_AVAILABLE:
            self.log("错误: QMT库不可用")
            return
        
        items = self.stock_tree.get_children()
        if not items:
            self.log("错误: 股票列表为空")
            return
        
        def batch_download_thread():
            try:
                total_count = len(items)
                completed_count = 0
                
                data_type = self.data_type_var.get()
                start_date = self.start_date_var.get()
                end_date = self.end_date_var.get()
                save_format = self.save_format_var.get()
                save_path = self.save_path_var.get()
                
                # 确保保存目录存在
                os.makedirs(save_path, exist_ok=True)
                
                for item in items:
                    values = self.stock_tree.item(item)['values']
                    stock_code = values[1]
                    
                    try:
                        # 更新状态为下载中
                        self.stock_tree.item(item, values=(values[0], stock_code, '下载中'))
                        
                        self.log(f"正在下载 {stock_code} ({completed_count + 1}/{total_count})")
                        
                        # 检查已有数据，确定实际需要下载的日期范围
                        actual_start_date, actual_end_date = self.check_existing_data(
                            stock_code, data_type, start_date, end_date, save_format, save_path
                        )
                        
                        if actual_start_date is None or actual_end_date is None:
                            self.log(f"{stock_code} 的 {data_type} 数据已是最新，跳过下载")
                            self.stock_tree.item(item, values=(values[0], stock_code, '已是最新'))
                            completed_count += 1
                            continue
                        
                        # 下载数据
                        if data_type == 'tick':
                            # 对于tick数据，需要按天下载
                            self.log(f"开始下载 {stock_code} 的tick数据，时间范围: {actual_start_date} 到 {actual_end_date}")
                            
                            # 将日期字符串转换为datetime对象
                            start_dt = datetime.datetime.strptime(actual_start_date, '%Y%m%d')
                            end_dt = datetime.datetime.strptime(actual_end_date, '%Y%m%d')
                            
                            # 按天下载tick数据
                            current_dt = start_dt
                            all_tick_data = []
                            
                            while current_dt <= end_dt:
                                current_date_str = current_dt.strftime('%Y%m%d')
                                
                                try:
                                    # 下载当天的tick数据
                                    xtdata.download_history_data(stock_code, period='tick', 
                                                               start_time=current_date_str, 
                                                               end_time=current_date_str)
                                    
                                    # 获取当天的tick数据
                                    daily_data = xtdata.get_market_data_ex([], [stock_code], period='tick',
                                                                         start_time=current_date_str, 
                                                                         end_time=current_date_str)
                                    
                                    if daily_data and stock_code in daily_data:
                                        tick_df = daily_data[stock_code]
                                        if not tick_df.empty:
                                            # 将DataFrame转换为字典列表格式
                                            tick_records = tick_df.to_dict('records')
                                            all_tick_data.extend(tick_records)
                                            
                                except Exception as e:
                                    self.log(f"下载 {stock_code} {current_date_str} tick数据时出错: {e}")
                                
                                # 移动到下一天
                                current_dt += timedelta(days=1)
                                
                                # 添加短暂延迟，避免请求过于频繁
                                time.sleep(0.1)
                            
                            # 将所有tick数据组织成标准格式
                            if all_tick_data:
                                data = {stock_code: all_tick_data}
                            else:
                                data = None
                        else:
                            # K线数据的下载逻辑
                            xtdata.download_history_data(stock_code, period=data_type, start_time=actual_start_date, end_time=actual_end_date)
                            
                            fields = ['time', 'open', 'high', 'low', 'close', 'volume', 'amount']
                            data = xtdata.get_market_data(field_list=fields, stock_list=[stock_code],
                                                        period=data_type, start_time=actual_start_date, end_time=actual_end_date)
                        
                        if data:
                            # 保存数据
                            filename = f"{stock_code}_{data_type}_{actual_start_date}_{actual_end_date}"
                            self.save_data(data, stock_code, filename, save_format, save_path)
                            
                            # 更新状态为完成
                            self.stock_tree.item(item, values=(values[0], stock_code, '完成'))
                        else:
                            # 更新状态为失败
                            self.stock_tree.item(item, values=(values[0], stock_code, '无数据'))
                        
                        completed_count += 1
                        
                        # 更新进度条
                        progress = (completed_count / total_count) * 100
                        self.progress_var.set(progress)
                        
                        # 短暂延迟，避免请求过于频繁
                        time.sleep(0.5)
                        
                    except Exception as e:
                        self.log(f"下载 {stock_code} 时发生错误: {e}")
                        self.stock_tree.item(item, values=(values[0], stock_code, '错误'))
                        completed_count += 1
                        progress = (completed_count / total_count) * 100
                        self.progress_var.set(progress)
                
                self.log(f"批量下载完成，共处理 {total_count} 只股票")
                
            except Exception as e:
                self.log(f"批量下载时发生错误: {e}")
        
        threading.Thread(target=batch_download_thread, daemon=True).start()

    def stop_batch_download(self):
        """停止批量下载"""
        # 这里可以添加停止下载的逻辑
        self.log("批量下载停止请求已发送")

    def get_latest_price(self):
        """获取最新价格"""
        if not QMT_AVAILABLE:
            self.log("错误: QMT库不可用")
            return
        
        def get_price_thread():
            try:
                stock_code = self.rt_stock_code_var.get()
                if not stock_code:
                    self.log("错误: 请输入股票代码")
                    return
                
                market_data = xtdata.get_full_tick([stock_code])
                if market_data and stock_code in market_data:
                    last_price = market_data[stock_code]['lastPrice']
                    
                    price_info = f"""
{stock_code} 最新行情:
最新价: {last_price}
查询时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                    self.update_realtime_display(price_info)
                    self.log(f"{stock_code} 最新价: {last_price}")
                else:
                    self.log(f"获取 {stock_code} 最新价失败")
                    
            except Exception as e:
                self.log(f"获取最新价时发生错误: {e}")
        
        threading.Thread(target=get_price_thread, daemon=True).start()

    def subscribe_realtime(self):
        """订阅实时行情"""
        if not QMT_AVAILABLE:
            self.log("错误: QMT库不可用")
            return
        
        try:
            stock_code = self.rt_stock_code_var.get()
            if not stock_code:
                self.log("错误: 请输入股票代码")
                return
            
            # 订阅实时行情
            xtdata.subscribe_quote(stock_code, period='1m', count=-1, callback=self.realtime_callback)
            self.log(f"已订阅 {stock_code} 的实时行情")
            
        except Exception as e:
            self.log(f"订阅实时行情时发生错误: {e}")

    def unsubscribe_realtime(self):
        """取消订阅实时行情"""
        try:
            stock_code = self.rt_stock_code_var.get()
            if not stock_code:
                self.log("错误: 请输入股票代码")
                return
            
            # 取消订阅
            xtdata.unsubscribe_quote(stock_code)
            self.log(f"已取消订阅 {stock_code} 的实时行情")
            
        except Exception as e:
            self.log(f"取消订阅时发生错误: {e}")

    def realtime_callback(self, data):
        """实时行情回调函数"""
        try:
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            callback_info = f"[{timestamp}] 收到实时行情推送: {data}\n"
            self.update_realtime_display(callback_info, append=True)
        except Exception as e:
            self.log(f"处理实时行情回调时发生错误: {e}")

    def start_fullpush_monitor(self):
        """开始全推监控"""
        if not QMT_AVAILABLE:
            self.log("错误: QMT库不可用")
            return
        
        # 如果已经在运行，先停止
        if self.fullpush_running:
            self.stop_fullpush_monitor()
            time.sleep(1)  # 等待停止完成
        
        try:
            rise_threshold = self.rise_threshold_var.get()
            fall_threshold = self.fall_threshold_var.get()
            monitor_type = self.monitor_stocks_var.get()
            
            # 在后台线程中处理数据下载和订阅
            def start_monitor_thread():
                try:
                    # 获取要监控的股票列表
                    monitor_stocks = self.get_monitor_stock_list()
                    
                    if not monitor_stocks:
                        self.log("警告: 未获取到监控股票列表")
                        return
                    
                    self.log(f"获取到 {len(monitor_stocks)} 只股票用于监控")
                    
                    # 订阅全推数据
                    def fullpush_callback(data_dict):
                        if self.fullpush_running:  # 检查是否仍在运行
                            # 使用线程池处理数据，避免阻塞
                            threading.Thread(target=self.process_fullpush_data, 
                                           args=(data_dict, rise_threshold, fall_threshold, monitor_stocks), 
                                           daemon=True).start()
                    
                    subscription_id = xtdata.subscribe_whole_quote(["SH", "SZ"], callback=fullpush_callback)
                    
                    if subscription_id > 0:
                        self.fullpush_subscription_id = subscription_id
                        self.fullpush_running = True
                        self.alert_count = {"rise": 0, "fall": 0}  # 重置计数
                        
                        status_msg = f"全推监控已启动\n监控范围: {monitor_type} ({len(monitor_stocks)}只股票)\n涨幅阈值: {rise_threshold:.1%}, 跌幅阈值: {fall_threshold:.1%}\n声音预警: {'启用' if self.sound_enabled_var.get() else '禁用'}\n"
                        self.log(f"全推监控已启动 - {monitor_type}")
                        self.update_realtime_display(status_msg, append=True)
                    else:
                        self.log("全推监控启动失败")
                        
                except Exception as e:
                    self.log(f"启动全推监控时发生错误: {e}")
            
            # 在后台线程中启动监控
            threading.Thread(target=start_monitor_thread, daemon=True).start()
                
        except Exception as e:
            self.log(f"启动全推监控时发生错误: {e}")

    def stop_fullpush_monitor(self):
        """停止全推监控"""
        try:
            if not self.fullpush_running:
                self.log("全推监控未在运行")
                return
                
            # 设置停止标志
            self.fullpush_running = False
            
            # 取消订阅
            if self.fullpush_subscription_id and QMT_AVAILABLE:
                try:
                    xtdata.unsubscribe_quote(self.fullpush_subscription_id)
                    self.log(f"已取消全推订阅 (ID: {self.fullpush_subscription_id})")
                except Exception as e:
                    self.log(f"取消订阅时发生错误: {e}")
                finally:
                    self.fullpush_subscription_id = None
            
            self.log("全推监控已停止")
            self.update_realtime_display("全推监控已停止\n", append=True)
            
        except Exception as e:
            self.log(f"停止全推监控时发生错误: {e}")

    def process_fullpush_data(self, data_dict, rise_threshold, fall_threshold, monitor_stocks):
        """处理全推数据，支持涨跌双向监控
        
        Args:
            data_dict (dict): 全推数据字典
            rise_threshold (float): 涨幅阈值
            fall_threshold (float): 跌幅阈值
            monitor_stocks (list): 要监控的股票列表
        """
        try:
            # 检查是否仍在运行
            if not self.fullpush_running:
                return
                
            rise_count = 0
            fall_count = 0
            timestamp = datetime.datetime.now().strftime('%H:%M:%S')
            rise_alerts = []  # 涨幅警报
            fall_alerts = []  # 跌幅警报
            
            # 限制处理的股票数量，避免处理过多数据导致卡顿
            processed_count = 0
            max_process_per_batch = 1000  # 每批最多处理1000只股票
            
            for code, tick_data in data_dict.items():
                if not self.fullpush_running:  # 再次检查运行状态
                    break
                    
                if code not in monitor_stocks:
                    continue
                
                processed_count += 1
                if processed_count > max_process_per_batch:
                    break  # 限制处理数量，避免阻塞
                
                try:
                    # 提取价格数据
                    if isinstance(tick_data, list) and tick_data:
                        last_price = tick_data[0]['lastPrice']
                        pre_close = tick_data[0]['lastClose']
                    else:
                        last_price = tick_data['lastPrice']
                        pre_close = tick_data['lastClose']
                    
                    # 计算涨跌幅
                    if pre_close > 0:
                        change_ratio = last_price / pre_close - 1
                        
                        # 检查涨幅预警
                        if change_ratio > rise_threshold:
                            rise_count += 1
                            self.alert_count["rise"] += 1
                            alert_info = f"[{timestamp}] 📈 {code} 涨幅 {change_ratio:.2%}，最新价 {last_price:.2f}\n"
                            rise_alerts.append(alert_info)
                            
                            # 播放涨幅预警声音
                            if self.sound_enabled_var.get():
                                threading.Thread(target=self.play_alert_sound, args=("rise",), daemon=True).start()
                        
                        # 检查跌幅预警
                        elif change_ratio < -fall_threshold:
                            fall_count += 1
                            self.alert_count["fall"] += 1
                            alert_info = f"[{timestamp}] 📉 {code} 跌幅 {abs(change_ratio):.2%}，最新价 {last_price:.2f}\n"
                            fall_alerts.append(alert_info)
                            
                            # 播放跌幅预警声音
                            if self.sound_enabled_var.get():
                                threading.Thread(target=self.play_alert_sound, args=("fall",), daemon=True).start()
                            
                except Exception:
                    continue
            
            # 批量更新UI，减少UI更新频率
            if (rise_alerts or fall_alerts) and self.fullpush_running:
                all_alerts = []
                
                # 处理涨幅警报
                if rise_alerts:
                    if len(rise_alerts) > 5:
                        all_alerts.extend(rise_alerts[:5])
                        all_alerts.append(f"[{timestamp}] ... 还有 {len(rise_alerts) - 5} 只股票涨幅超过阈值\n")
                    else:
                        all_alerts.extend(rise_alerts)
                
                # 处理跌幅警报
                if fall_alerts:
                    if len(fall_alerts) > 5:
                        all_alerts.extend(fall_alerts[:5])
                        all_alerts.append(f"[{timestamp}] ... 还有 {len(fall_alerts) - 5} 只股票跌幅超过阈值\n")
                    else:
                        all_alerts.extend(fall_alerts)
                
                # 更新UI显示
                for alert in all_alerts:
                    self.master.after(0, lambda text=alert: self.update_realtime_display(text, append=True))
                
                # 显示汇总信息
                if rise_count > 0 or fall_count > 0:
                    summary = f"[{timestamp}] 本次推送: 涨幅预警 {rise_count} 只, 跌幅预警 {fall_count} 只 (累计: 涨 {self.alert_count['rise']}, 跌 {self.alert_count['fall']})\n"
                    self.master.after(0, lambda text=summary: self.update_realtime_display(text, append=True))
                
        except Exception as e:
            self.log(f"处理全推数据时发生错误: {e}")

    def play_alert_sound(self, alert_type="rise"):
        """播放预警声音
        
        Args:
            alert_type (str): 预警类型，'rise'表示涨幅预警，'fall'表示跌幅预警
        """
        if not self.sound_enabled_var.get():
            return
            
        try:
            sound_type = self.sound_type_var.get()
            
            if sound_type == "系统提示音":
                # 使用不同的系统声音区分涨跌
                if alert_type == "rise":
                    winsound.MessageBeep(winsound.MB_OK)  # 上涨用OK声音
                else:
                    winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)  # 下跌用警告声音
                    
            elif sound_type == "警报声":
                # 播放系统警报声
                winsound.MessageBeep(winsound.MB_ICONHAND)
                
            elif sound_type == "铃声":
                # 播放系统铃声
                winsound.MessageBeep(winsound.MB_ICONASTERISK)
                
            elif sound_type == "自定义音效":
                # 这里可以扩展为播放自定义音频文件
                winsound.MessageBeep(winsound.MB_ICONQUESTION)
                
        except Exception as e:
            self.log(f"播放声音时发生错误: {e}")

    def test_sound(self):
        """测试声音功能"""
        try:
            self.log("测试涨幅预警声音...")
            self.play_alert_sound("rise")
            
            # 延迟一下再播放跌幅声音
            self.master.after(1000, lambda: self.play_alert_sound("fall"))
            self.master.after(1000, lambda: self.log("测试跌幅预警声音..."))
            
        except Exception as e:
            self.log(f"测试声音时发生错误: {e}")

    def setup_custom_stocks(self):
        """设置自定义股票列表"""
        try:
            # 创建自定义股票设置窗口
            custom_window = tk.Toplevel(self.master)
            custom_window.title("自定义股票列表")
            custom_window.geometry("500x400")
            custom_window.transient(self.master)
            custom_window.grab_set()
            
            # 说明标签
            info_label = tk.Label(custom_window, 
                                text="请输入股票代码，每行一个（如：000001.SZ, 600000.SH）",
                                font=("Arial", 10))
            info_label.pack(pady=10)
            
            # 文本输入框
            text_frame = ttk.Frame(custom_window)
            text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            stock_text = scrolledtext.ScrolledText(text_frame, height=15)
            stock_text.pack(fill=tk.BOTH, expand=True)
            
            # 如果已有自定义列表，显示出来
            if self.custom_stock_list:
                stock_text.insert(tk.END, '\n'.join(self.custom_stock_list))
            
            # 按钮框架
            button_frame = ttk.Frame(custom_window)
            button_frame.pack(fill=tk.X, padx=10, pady=10)
            
            def save_custom_stocks():
                """保存自定义股票列表"""
                content = stock_text.get(1.0, tk.END).strip()
                if content:
                    # 解析股票代码
                    stocks = []
                    for line in content.split('\n'):
                        line = line.strip()
                        if line and ('.' in line):  # 简单验证格式
                            stocks.append(line.upper())
                    
                    self.custom_stock_list = stocks
                    self.log(f"已保存 {len(stocks)} 只自定义股票")
                    messagebox.showinfo("成功", f"已保存 {len(stocks)} 只股票到自定义列表")
                else:
                    self.custom_stock_list = []
                    self.log("已清空自定义股票列表")
                
                custom_window.destroy()
            
            def load_from_file():
                """从文件加载股票列表"""
                file_path = filedialog.askopenfilename(
                    title="选择股票列表文件",
                    filetypes=[("文本文件", "*.txt"), ("CSV文件", "*.csv"), ("所有文件", "*.*")]
                )
                
                if file_path:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        stock_text.delete(1.0, tk.END)
                        stock_text.insert(tk.END, content)
                        self.log(f"已从文件加载股票列表: {file_path}")
                    except Exception as e:
                        messagebox.showerror("错误", f"加载文件失败: {e}")
            
            # 按钮
            ttk.Button(button_frame, text="从文件加载", command=load_from_file).pack(side=tk.LEFT, padx=5)
            ttk.Button(button_frame, text="保存", command=save_custom_stocks).pack(side=tk.RIGHT, padx=5)
            ttk.Button(button_frame, text="取消", command=custom_window.destroy).pack(side=tk.RIGHT, padx=5)
            
        except Exception as e:
            self.log(f"设置自定义股票列表时发生错误: {e}")

    def clear_realtime_display(self):
        """清空实时数据显示"""
        try:
            self.realtime_text.config(state=tk.NORMAL)
            self.realtime_text.delete(1.0, tk.END)
            self.realtime_text.config(state=tk.DISABLED)
            self.alert_count = {"rise": 0, "fall": 0}
            self.log("已清空实时数据显示")
        except Exception as e:
            self.log(f"清空显示时发生错误: {e}")

    def get_monitor_stock_list(self):
        """获取要监控的股票列表
        
        Returns:
            list: 股票代码列表
        """
        try:
            monitor_type = self.monitor_stocks_var.get()
            
            if monitor_type == "全市场":
                # 获取全市场股票
                if QMT_AVAILABLE:
                    xtdata.download_sector_data()
                    sh_stocks = xtdata.get_stock_list_in_sector('上海A股')
                    sz_stocks = xtdata.get_stock_list_in_sector('深圳A股')
                    return sh_stocks + sz_stocks
                else:
                    return []
                    
            elif monitor_type == "沪深A股":
                if QMT_AVAILABLE:
                    xtdata.download_sector_data()
                    return xtdata.get_stock_list_in_sector('沪深A股')
                else:
                    return []
                    
            elif monitor_type == "创业板":
                if QMT_AVAILABLE:
                    xtdata.download_sector_data()
                    return xtdata.get_stock_list_in_sector('创业板')
                else:
                    return []
                    
            elif monitor_type == "科创板":
                if QMT_AVAILABLE:
                    xtdata.download_sector_data()
                    return xtdata.get_stock_list_in_sector('科创板')
                else:
                    return []
                    
            elif monitor_type == "自定义列表":
                return self.custom_stock_list
                
            else:
                return []
                
        except Exception as e:
            self.log(f"获取监控股票列表时发生错误: {e}")
            return []

    def on_closing(self):
        """窗口关闭时的清理工作"""
        try:
            # 保存配置
            self.save_config()
            
            # 停止全推监控
            if self.fullpush_running:
                self.stop_fullpush_monitor()
            
            # 断开QMT连接
            if self.is_connected and QMT_AVAILABLE:
                try:
                    xtdata.disconnect()
                    self.log("已断开QMT连接")
                except Exception as e:
                    self.log(f"断开连接时发生错误: {e}")
            
            # 销毁窗口
            self.master.destroy()
            
        except Exception as e:
            print(f"程序退出时发生错误: {e}")
            self.master.destroy()

    def update_realtime_display(self, text, append=False):
        """更新实时数据显示区域"""
        self.realtime_text.config(state=tk.NORMAL)
        if not append:
            self.realtime_text.delete(1.0, tk.END)
        self.realtime_text.insert(tk.END, text)
        self.realtime_text.config(state=tk.DISABLED)
        self.realtime_text.see(tk.END)

    def open_usage_guide(self):
        """打开使用说明"""
        try:
            guide_path = os.path.join(os.path.dirname(__file__), "使用说明.md")
            if os.path.exists(guide_path):
                self.open_markdown_file(guide_path)
            else:
                self.create_usage_guide()
                self.open_markdown_file(guide_path)
        except Exception as e:
            self.log(f"打开使用说明时发生错误: {e}")

    def open_readme(self):
        """打开README"""
        try:
            readme_path = os.path.join(os.path.dirname(__file__), "README.md")
            if os.path.exists(readme_path):
                self.open_markdown_file(readme_path)
            else:
                self.create_readme()
                self.open_markdown_file(readme_path)
        except Exception as e:
            self.log(f"打开README时发生错误: {e}")

    def open_markdown_file(self, file_path):
        """打开并渲染Markdown文件"""
        try:
            # 创建新窗口显示Markdown内容
            md_window = tk.Toplevel(self.master)
            md_window.title(f"文档查看器 - {os.path.basename(file_path)}")
            md_window.geometry("800x600")
            
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 创建文本显示区域
            text_area = scrolledtext.ScrolledText(md_window, wrap=tk.WORD, font=("Consolas", 10))
            text_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # 使用markdown库渲染，然后转换为纯文本显示
            try:
                # 将Markdown转换为HTML
                html_content = markdown.markdown(content, extensions=['tables', 'fenced_code', 'toc'])
                # 将HTML转换为格式化的纯文本
                h = html2text.HTML2Text()
                h.ignore_links = False
                h.body_width = 80
                rendered_content = h.handle(html_content)
            except ImportError:
                # 如果markdown库不可用，使用简单渲染
                rendered_content = self.simple_markdown_render(content)
            
            text_area.insert(tk.END, rendered_content)
            text_area.config(state=tk.DISABLED)
            
        except Exception as e:
            self.log(f"打开Markdown文件时发生错误: {e}")

    def simple_markdown_render(self, content):
        """简单的Markdown渲染"""
        lines = content.split('\n')
        rendered_lines = []
        
        for line in lines:
            # 处理标题
            if line.startswith('# '):
                rendered_lines.append(f"\n{'='*50}")
                rendered_lines.append(f"{line[2:].upper()}")
                rendered_lines.append(f"{'='*50}\n")
            elif line.startswith('## '):
                rendered_lines.append(f"\n{'-'*30}")
                rendered_lines.append(f"{line[3:]}")
                rendered_lines.append(f"{'-'*30}")
            elif line.startswith('### '):
                rendered_lines.append(f"\n{line[4:]}:")
                rendered_lines.append(f"{'-'*len(line[4:])}")
            # 处理列表
            elif line.startswith('- '):
                rendered_lines.append(f"  • {line[2:]}")
            elif line.startswith('* '):
                rendered_lines.append(f"  • {line[2:]}")
            # 处理代码块
            elif line.startswith('```'):
                rendered_lines.append(f"\n{'-'*40}")
                rendered_lines.append("代码:")
                rendered_lines.append(f"{'-'*40}")
            else:
                rendered_lines.append(line)
        
        return '\n'.join(rendered_lines)

    def create_usage_guide(self):
        """创建使用说明文档"""
        guide_content = """# QMT连接和数据下载测试工具使用说明

## 概述
本工具是一个集成的QMT（迅投量化交易终端）连接和数据下载测试工具，提供了图形化界面来简化QMT的使用和数据获取操作。

## 功能特性
- QMT交易接口连接测试
- 历史行情数据下载（支持tick、1分钟、5分钟、日线）
- 批量股票代码导入（Excel、文本文件）
- 多种数据保存格式（CSV、JSON、SQLite数据库）
- 实时行情数据获取
- 全推数据监控

## 使用前准备

### 1. 环境要求
- Python 3.6+
- 已安装QMT客户端
- 已安装xtquant库
- 相关Python依赖包：tkinter, pandas, sqlite3

### 2. QMT客户端设置
- 启动QMT客户端
- 登录时勾选"极简模式"
- 确保客户端正常运行

### 3. 路径配置
- 券商端：指定到安装目录下的 `userdata_mini` 文件夹
- 投研端：指定到安装目录下的 `userdata` 文件夹

## 详细使用说明

### 连接测试标签页

#### QMT配置
1. **QMT路径**: 输入QMT客户端的userdata路径
   - 示例：`D:\\\\qmt\\\\userdata_mini`
2. **账户ID**: 输入您的交易账户ID

#### 连接控制
- **连接QMT**: 建立与QMT的连接
- **断开连接**: 断开当前连接
- **查询资产**: 查询账户资产信息
- **查询持仓**: 查询当前持仓情况

### 数据下载标签页

#### 基本设置
1. **股票代码**: 输入要下载的股票代码（如：000001.SZ）
2. **数据类型**: 选择数据周期
   - 日线（1d）
   - 5分钟（5m）
   - 1分钟（1m）
   - 分笔（tick）
3. **时间范围**: 设置开始和结束日期（格式：YYYYMMDD）
4. **保存格式**: 选择数据保存格式
   - CSV：逗号分隔值文件
   - JSON：JavaScript对象表示法
   - 数据库：SQLite数据库

#### 下载操作
1. 配置好参数后，点击"下载数据"
2. 选择保存路径
3. 等待下载完成

### 批量导入标签页

#### 文件导入
- **导入Excel文件**: 支持.xlsx和.xls格式，第一列应为股票代码
- **导入文本文件**: 每行一个股票代码的文本文件

#### 手动输入
- 在输入框中输入股票代码，多个代码用逗号分隔
- 点击"添加到列表"将代码添加到批量下载列表

#### 批量下载
1. 确保股票列表不为空
2. 设置数据类型、时间范围和保存格式
3. 点击"开始批量下载"
4. 观察进度条和状态更新

### 实时数据标签页

#### 实时行情
1. 输入股票代码
2. 点击"获取最新价"查看当前价格
3. 点击"订阅实时行情"接收实时推送
4. 点击"取消订阅"停止接收推送

#### 全推数据监控
1. 设置涨幅阈值（如：0.09表示9%）
2. 点击"开始全推监控"
3. 系统将监控所有沪深A股，当涨幅超过阈值时发出提醒
4. 点击"停止监控"结束监控

## 常见问题

### 连接失败
1. 检查QMT客户端是否正常运行
2. 确认是否以极简模式登录
3. 检查路径是否正确
4. 尝试更换session ID（重新连接）

### 数据下载失败
1. 确认网络连接正常
2. 检查股票代码格式是否正确
3. 确认时间范围设置合理
4. 检查保存路径是否有写入权限

### 权限问题
- 如果QMT安装在C盘，需要以管理员权限运行程序
- 建议将QMT安装在非系统盘

## 注意事项

1. **数据频率限制**: 避免过于频繁的数据请求，建议批量下载时设置适当延迟
2. **存储空间**: 大量历史数据可能占用较多存储空间，请合理规划
3. **网络稳定性**: 确保网络连接稳定，避免下载中断
4. **账户安全**: 妥善保管账户信息，不要在不安全的环境中使用

## 技术支持

如遇到问题，请：
1. 查看日志输出区域的错误信息
2. 检查QMT客户端状态
3. 参考QMT官方文档
4. 联系技术支持

## 更新日志

### v1.0
- 初始版本发布
- 基础连接和数据下载功能
- GUI界面实现
- 批量处理支持
"""
        
        guide_path = os.path.join(os.path.dirname(__file__), "使用说明.md")
        with open(guide_path, 'w', encoding='utf-8') as f:
            f.write(guide_content)

    def create_readme(self):
        """创建README文档"""
        readme_content = """# QMT连接和数据下载测试工具

## 项目简介

这是一个基于Python和tkinter开发的QMT（迅投量化交易终端）连接和数据下载测试工具。该工具提供了友好的图形用户界面，集成了QMT的主要功能，包括交易接口连接、历史数据下载、实时行情获取等。

## 主要功能

### 🔗 连接管理
- QMT交易接口连接测试
- 账户资产查询
- 持仓信息查询
- 连接状态监控

### 📊 数据下载
- 支持多种数据周期：tick、1分钟、5分钟、日线
- 灵活的时间范围设置
- 多种保存格式：CSV、JSON、SQLite数据库
- 单只股票和批量下载

### 📁 批量处理
- Excel文件导入股票代码
- 文本文件导入股票代码
- 手动输入股票代码
- 批量下载进度监控

### 📈 实时数据
- 实时行情数据获取
- 行情数据订阅
- 全市场推送监控
- 涨幅阈值提醒

## 技术架构

### 核心技术栈
- **GUI框架**: tkinter
- **数据处理**: pandas
- **数据存储**: sqlite3, json, csv
- **QMT接口**: xtquant
- **多线程**: threading
- **队列通信**: queue

### 项目结构
```
qmt_connect_test/
├── qmt_download_and_connect_test.py  # 主程序文件
├── 基本连接qmt.py                    # 原始连接测试
├── 获取qmt实时和历史行情数据.py        # 原始数据获取
├── 获取小QMT的最新价.py              # 原始价格获取
├── 连接qmt获取全推数据.py             # 原始全推数据
├── 连接qmt获取持仓数据测试.py          # 原始持仓测试
├── 使用说明.md                       # 使用说明文档
├── README.md                        # 项目说明文档
└── logo.ico                         # 应用图标（可选）
```

## 安装和配置

### 环境要求
- Python 3.6 或更高版本
- QMT客户端（迅投量化交易终端）
- 必要的Python依赖包

### 依赖安装
```bash
pip install pandas xtquant
```

### QMT客户端配置
1. 下载并安装QMT客户端
2. 启动客户端并登录（勾选"极简模式"）
3. 记录userdata路径和账户ID

## 快速开始

### 1. 运行程序
```bash
python qmt_download_and_connect_test.py
```

### 2. 配置连接
- 在"连接测试"标签页输入QMT路径和账户ID
- 点击"连接QMT"建立连接

### 3. 下载数据
- 切换到"数据下载"标签页
- 输入股票代码和时间范围
- 选择数据类型和保存格式
- 点击"下载数据"

### 4. 批量处理
- 在"批量导入"标签页导入股票代码列表
- 配置下载参数
- 点击"开始批量下载"

## 使用示例

### 连接QMT
```python
# 配置参数
qmt_path = r'D:\\qmt\\userdata_mini'
account_id = '18014745'

# 建立连接
connect_qmt()
```

### 下载历史数据
```python
# 下载平安银行日线数据
stock_code = '000001.SZ'
data_type = '1d'
start_date = '20240101'
end_date = '20241201'
save_format = 'csv'
```

### 批量下载
```python
# 导入股票列表
stock_list = ['000001.SZ', '000002.SZ', '600000.SH']
# 批量下载数据
start_batch_download()
```

## 注意事项

### 使用限制
- 需要有效的QMT账户
- 遵守数据使用协议
- 避免过于频繁的请求

### 常见问题
1. **连接失败**: 检查QMT客户端状态和路径配置
2. **数据为空**: 确认股票代码格式和时间范围
3. **权限错误**: 以管理员权限运行程序

## 开发说明

### 代码结构
- `QMTDataDownloadGUI`: 主GUI类
- `QMTTraderCallback`: 交易回调类
- 多线程处理避免界面阻塞
- 队列机制处理日志输出

### 扩展开发
- 可添加更多数据源
- 支持更多保存格式
- 增加数据分析功能
- 优化用户界面

## 许可证

本项目仅供学习和研究使用，请遵守相关法律法规和数据使用协议。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 查看使用说明文档
- 检查日志输出信息
- 参考QMT官方文档

---

**免责声明**: 本工具仅用于技术学习和测试，使用者需自行承担使用风险。
"""
        
        readme_path = os.path.join(os.path.dirname(__file__), "README.md")
        with open(readme_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)

    def load_config(self):
        """加载JSON配置文件
        
        从JSON配置文件中加载用户设置，如果文件不存在则使用默认配置
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                self.log("配置文件加载成功")
                
                # 应用QMT配置
                if 'qmt' in config_data:
                    qmt_config = config_data['qmt']
                    if 'path' in qmt_config:
                        self.qmt_path_var.set(qmt_config['path'])
                    if 'stock_account' in qmt_config:
                        self.account_id_var.set(qmt_config['stock_account'])
                    # 兼容旧配置文件
                    elif 'account_id' in qmt_config:
                        self.account_id_var.set(qmt_config['account_id'])
                
                # 应用监控配置
                if 'monitor' in config_data:
                    monitor_config = config_data['monitor']
                    if 'rise_threshold' in monitor_config:
                        self.rise_threshold_var.set(monitor_config['rise_threshold'])
                    if 'fall_threshold' in monitor_config:
                        self.fall_threshold_var.set(monitor_config['fall_threshold'])
                    if 'monitor_stocks' in monitor_config:
                        self.monitor_stocks_var.set(monitor_config['monitor_stocks'])
                    if 'sound_enabled' in monitor_config:
                        self.sound_enabled_var.set(monitor_config['sound_enabled'])
                    if 'sound_type' in monitor_config:
                        self.sound_type_var.set(monitor_config['sound_type'])
                
                # 应用实时行情配置
                if 'realtime' in config_data:
                    realtime_config = config_data['realtime']
                    if 'stock_code' in realtime_config:
                        self.rt_stock_code_var.set(realtime_config['stock_code'])
                        
            else:
                self.log("配置文件不存在，使用默认配置")
                self.create_default_config()
                
        except Exception as e:
            self.log(f"加载配置文件时发生错误: {e}")
            self.create_default_config()

    def save_config(self):
        """保存当前配置到JSON文件
        
        将用户当前的设置保存到JSON配置文件中
        """
        try:
            # 构建配置数据
            config_data = {
                "qmt": {
                    "path": self.qmt_path_var.get(),
                    "stock_account": self.account_id_var.get()
                },
                "monitor": {
                    "rise_threshold": self.rise_threshold_var.get(),
                    "fall_threshold": self.fall_threshold_var.get(),
                    "monitor_stocks": self.monitor_stocks_var.get(),
                    "sound_enabled": self.sound_enabled_var.get(),
                    "sound_type": self.sound_type_var.get()
                },
                "realtime": {
                    "stock_code": self.rt_stock_code_var.get()
                }
            }
            
            # 写入JSON文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=4)
            
            self.log("配置已保存")
            
        except Exception as e:
            self.log(f"保存配置时发生错误: {e}")

    def create_default_config(self):
        """创建默认JSON配置文件
        
        当配置文件不存在或损坏时，创建包含默认设置的JSON配置文件
        """
        try:
            # 写入默认配置到JSON文件
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.default_config, f, ensure_ascii=False, indent=4)
            
            self.log("已创建默认配置文件")
            
        except Exception as e:
            self.log(f"创建默认配置时发生错误: {e}")

    def reset_config(self):
        """重置配置为默认值
        
        将所有设置重置为默认值并保存
        """
        try:
            # 重置界面控件为默认值
            self.qmt_path_var.set(self.default_config['qmt']['path'])
            self.account_id_var.set(self.default_config['qmt']['stock_account'])
            self.rise_threshold_var.set(self.default_config['monitor']['rise_threshold'])
            self.fall_threshold_var.set(self.default_config['monitor']['fall_threshold'])
            self.monitor_stocks_var.set(self.default_config['monitor']['monitor_stocks'])
            self.sound_enabled_var.set(self.default_config['monitor']['sound_enabled'])
            self.sound_type_var.set(self.default_config['monitor']['sound_type'])
            self.rt_stock_code_var.set(self.default_config['realtime']['stock_code'])
            
            # 保存配置
            self.save_config()
            self.log("配置已重置为默认值")
            
        except Exception as e:
            self.log(f"重置配置时发生错误: {e}")

    def auto_save_config(self):
        """自动保存配置
        
        在用户修改设置时自动保存配置，避免丢失设置
        """
        # 延迟保存，避免频繁写入文件
        if hasattr(self, '_save_timer'):
            self.master.after_cancel(self._save_timer)
        self._save_timer = self.master.after(1000, self.save_config)  # 1秒后保存

    def open_config_file(self):
        """打开配置文件
        
        使用系统默认编辑器打开配置文件，方便用户手动编辑
        """
        try:
            if not os.path.exists(self.config_file):
                self.create_default_config()
            
            # 使用系统默认程序打开配置文件
            if os.name == 'nt':  # Windows
                os.startfile(self.config_file)
            else:  # Linux/Mac
                subprocess.run(['xdg-open', self.config_file])
            
            self.log(f"已打开配置文件: {self.config_file}")
            
        except Exception as e:
            self.log(f"打开配置文件时发生错误: {e}")

    def bind_config_events(self):
        """绑定配置变量的变化事件
        
        为主要的配置变量绑定变化事件，实现自动保存
        """
        try:
            # QMT配置变量
            self.qmt_path_var.trace('w', lambda *args: self.auto_save_config())
            self.account_id_var.trace('w', lambda *args: self.auto_save_config())
            
            # 监控配置变量
            self.rise_threshold_var.trace('w', lambda *args: self.auto_save_config())
            self.fall_threshold_var.trace('w', lambda *args: self.auto_save_config())
            self.monitor_stocks_var.trace('w', lambda *args: self.auto_save_config())
            self.sound_enabled_var.trace('w', lambda *args: self.auto_save_config())
            self.sound_type_var.trace('w', lambda *args: self.auto_save_config())
            
            # 实时行情配置变量
            self.rt_stock_code_var.trace('w', lambda *args: self.auto_save_config())
            
        except Exception as e:
            self.log(f"绑定配置事件时发生错误: {e}")


def main():
    """主函数"""
    root = tk.Tk()
    app = QMTDataDownloadGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()