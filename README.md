# QMT连接和数据下载测试工具

![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)

一个基于Python和tkinter开发的QMT（迅投量化交易终端）连接和数据下载测试工具，提供友好的图形用户界面，集成了QMT的主要功能。

## 🚀 主要特性

- **🔗 QMT连接管理**: 支持QMT交易接口连接、断开和状态监控
- **📊 历史数据下载**: 支持单股票和批量股票历史数据下载
- **📈 实时行情监控**: 实时获取股票价格和行情数据
- **🔔 智能预警系统**: 支持涨跌幅预警和声音提醒
- **⚙️ 配置管理**: JSON格式配置文件，支持自动保存和恢复
- **📱 现代化界面**: 基于tkinter的美观GUI界面
- **📚 文档支持**: 内置Markdown文档渲染器

## 📋 系统要求

- **操作系统**: Windows 7/8/10/11
- **Python版本**: 3.7 或更高版本
- **QMT客户端**: 需要安装并配置QMT交易终端

## 🛠️ 安装说明

### 1. 克隆项目
```bash
git clone https://github.com/your-username/qmt-connect-test.git
cd qmt-connect-test
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 安装QMT相关库
```bash
# 如果使用QMT官方Python接口
pip install xtquant
```

### 4. 运行程序
```bash
python qmt_download_and_connect_test.py
```

## 📦 依赖包

### 核心依赖
- `tkinter` - GUI框架（Python内置）
- `pandas` - 数据处理
- `json` - 配置文件管理
- `threading` - 多线程支持
- `queue` - 队列机制

### 可选依赖
- `xtquant` - QMT官方Python接口
- `markdown` - Markdown文档渲染
- `html2text` - HTML转文本
- `openpyxl` - Excel文件支持

## 🎯 快速开始

### 1. 配置QMT连接
1. 启动QMT客户端并登录
2. 在程序中设置QMT路径（通常为`userdata_mini`目录）
3. 输入账户ID
4. 点击"连接QMT"

### 2. 下载历史数据
1. 切换到"数据下载"标签页
2. 输入股票代码（如：000001.SZ）
3. 选择数据类型和时间范围
4. 点击"下载数据"

### 3. 实时监控
1. 切换到"实时行情"标签页
2. 设置监控参数
3. 点击"开始全推监控"

## 📖 功能模块

### 连接管理
- QMT路径配置
- 账户信息设置
- 连接状态监控
- 资产和持仓查询

### 数据下载
- 支持多种K线周期（1分钟到日线）
- CSV和Excel格式导出
- 自定义时间范围
- 批量下载功能

### 实时监控
- 实时价格获取
- 行情数据订阅
- 全市场监控
- 涨跌幅预警

### 配置管理
- JSON格式配置
- 自动保存机制
- 配置重置功能
- 参数持久化

## 🔧 配置文件

程序使用`qmt_config.json`文件存储配置信息：

```json
{
    "qmt": {
        "path": "D:\\QMT\\userdata_mini",
        "account_id": "your_account_id",
        "account_key": ""
    },
    "monitor": {
        "rise_threshold": 0.05,
        "fall_threshold": 0.05,
        "monitor_stocks": "全市场",
        "sound_enabled": true,
        "sound_type": "系统提示音"
    },
    "realtime": {
        "stock_code": "000001.SZ"
    }
}
```

## 📊 数据格式

### 股票代码格式
- 深圳股票：`000001.SZ`
- 上海股票：`600000.SH`
- 创业板：`300001.SZ`
- 科创板：`688001.SH`

### 数据类型
- `1m` - 1分钟K线
- `5m` - 5分钟K线
- `15m` - 15分钟K线
- `30m` - 30分钟K线
- `1h` - 1小时K线
- `1d` - 日K线

## 🎨 界面预览

程序采用现代化的标签页设计，包含以下主要界面：

1. **连接管理** - QMT连接配置和状态监控
2. **数据下载** - 单股票历史数据下载
3. **批量下载** - 多股票批量数据下载
4. **实时行情** - 实时监控和预警设置
5. **帮助配置** - 文档查看和配置管理

## 🔍 故障排除

### 常见问题

**Q: 连接QMT失败**
- 确保QMT客户端已启动并登录
- 检查QMT路径设置是否正确
- 验证账户ID是否有效

**Q: 下载数据失败**
- 检查股票代码格式
- 确认时间范围设置
- 验证网络连接状态

**Q: 实时监控无数据**
- 确认QMT连接状态
- 检查是否在交易时间内
- 验证股票代码有效性

### 日志查看
程序底部的日志输出区域会显示详细的运行信息和错误提示，有助于问题诊断。

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

### 开发环境设置
1. Fork项目到你的GitHub账户
2. 克隆你的Fork到本地
3. 创建新的功能分支
4. 提交你的更改
5. 创建Pull Request

### 代码规范
- 遵循PEP 8代码风格
- 添加适当的注释和文档字符串
- 确保代码通过测试

## 📄 许可证

本项目采用MIT许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。


## 👨‍💻 作者信息

**余汉波** - 编程爱好者-量化交易和效率工具开发

- **GitHub**: [@yuhanbo758](https://github.com/yuhanbo758)

- **Email**: yuhanbo@sanrenjz.com

- **Website**: [三人聚智](https://www.sanrenjz.com)

## 🌐 相关链接

- 🏠 [项目主页](https://www.sanrenjz.com)

- 📚 [在线文档](https://docs.sanrenjz.com)（财经、代码和库文档等）

- 🛒 [插件商店](https://shop.sanrenjz.com)（个人开发的所有程序，包括开源和不开源）


## 联系我们

[联系我们 - 三人聚智-余汉波](https://www.sanrenjz.com/contact_us/)

python 程序管理工具下载：[sanrenjz - 三人聚智-余汉波](https://www.sanrenjz.com/sanrenjz/)

效率工具程序管理下载：[sanrenjz-tools - 三人聚智-余汉波](https://www.sanrenjz.com/sanrenjz-tools/)

![三码合一](https://gdsx.sanrenjz.com/image/sanrenjz_yuhanbolh_yuhanbo758.png?imageSlim&t=1ab9b82c-e220-8022-beff-e265a194292a)

![余汉波打赏码](https://gdsx.sanrenjz.com/PicGo/%E6%89%93%E8%B5%8F%E7%A0%81500.png)

## 🙏 致谢

感谢所有为本项目贡献代码和想法的开发者们！

---

**⭐ 如果这个项目对您有帮助，请给它一个 Star！**
