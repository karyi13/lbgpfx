# A股连板交易分析系统

一个完整的A股连板交易分析系统，支持数据获取、连板梯队分析、买入信号生成、模拟交易执行和Web界面展示。

## 功能特性

### 1. 数据获取与清洗
- 支持模拟数据和真实数据
- 自动过滤ST股票、次新股
- 数据完整性验证

### 2. 连板梯队分析
- 生成连板天梯图
- 识别各梯队龙头股
- 板块效应分析

### 3. 买入信号生成
综合评分系统（满分100分）：

| 指标 | 权重 | 评分标准 |
|-----|------|----------|
| 连板高度 | 20% | 3-4板最佳(40分)，5板以上谨慎(20分) |
| 封单强度 | 25% | 封单/流通市值>10%(25分) |
| 板块热度 | 20% | 同板块涨停>5家(20分) |
| 换手健康 | 15% | 10%<换手<30%(15分) |
| 时间优势 | 10% | 早盘涨停(10分) |
| 市值适中 | 10% | 50-200亿(10分) |

买入阈值：综合评分 >= 75分

### 4. 模拟交易执行
- 自动根据信号买入
- 止损止盈自动化
- 持仓管理
- 盈亏计算
- 收益率曲线

### 5. 红旗规则（禁止事项）
- 不参与一字板
- 不参与尾盘板
- 不参与独立妖股
- 单票仓位不超过20%
- 连续亏损3次后强制休息1天

### 6. Web界面
- 实时市场情绪监控
- 连板梯队可视化
- 买入信号列表
- 持仓盈亏展示
- 收益曲线图表

## 安装

```bash
# 安装依赖
pip install -r requirements.txt
```

## 使用方法

### 命令行模式

```bash
# 每日分析（模拟数据）
python main.py --mode analyze

# 每日分析并执行交易
python main.py --mode analyze --trade

# 指定日期分析
python main.py --mode analyze --date 2024-01-15

# 历史回测
python main.py --mode backtest --days 30

# 指定回测开始日期
python main.py --mode backtest --days 30 --start-date 2024-01-01

# 使用真实数据
python main.py --mode analyze --real-data

# Web界面
python main.py --mode web --port 5000
```

### Python API

```python
from main import ConsecutiveLimitUpSystem

# 创建系统实例
system = ConsecutiveLimitUpSystem(use_mock_data=True, initial_capital=500000)

# 执行每日分析
result = system.run_daily_analysis()

# 执行每日分析并交易
result = system.run_daily_analysis(execute_trade=True)

# 运行回测
backtest_result = system.run_backtest(days=30)
```

## 目录结构

```
lbgpfx/
├── config.py              # 配置文件
├── data_fetcher.py        # 数据获取模块
├── analysis_engine.py     # 分析引擎
├── report_generator.py    # 报告生成模块
├── trading_simulator.py   # 交易模拟模块
├── web_app.py            # Web界面
├── main.py               # 主程序
├── requirements.txt      # 依赖包
└── reports/              # 输出报告目录
```

## 输出格式

### 1. Markdown复盘报告 (`reports/YYYY-MM-DD.md`)

```markdown
# 2024-01-15 连板复盘

## 市场情绪
- 涨停家数：45（昨日32）
- 连板高度：6板（深中华A）
- 炸板率：25%（健康）
- 情绪判断：升温期

## 连板梯队
| 高度 | 数量 | 代表股 | 板块 |
|-----|------|--------|------|
| 6板 | 1 | 深中华A | 锂电池 |
| 5板 | 2 | 公元股份 | 光伏 |

## 明日策略
**目标股**：
1. **深中华A**（6进7）- 评分：82分
   - 逻辑：锂电池龙头，板块跟风足
   - 策略：竞价观察，高开5%以内且带量则介入
```

### 2. JSON交易信号 (`reports/YYYY-MM-DD_signals.json`)

```json
{
    "date": "2024-01-16",
    "signals": [
        {
            "code": "000017.SZ",
            "name": "深中华A",
            "action": "buy",
            "price": 12.50,
            "position": 0.20,
            "score": 82,
            "reason": "6进7,锂电池龙头,评分82分",
            "stop_loss": 11.60,
            "take_profit": {
                "tier1": 14.38,
                "tier2": 15.63
            }
        }
    ],
    "cash_ratio": 0.40
}
```

## 真实数据接入

要接入真实数据，修改 `data_fetcher.py` 中的以下方法：

- `_fetch_real_limit_up()` - 获取涨停数据
- `_fetch_real_limit_history()` - 获取历史涨停
- `_fetch_real_sector_data()` - 获取板块数据
- `_fetch_real_stock_info()` - 获取股票信息

推荐数据源：
- AKShare: `https://akshare.akfamily.xyz/`
- Tushare: `https://tushare.pro/`
-  东方财富、同花顺API

## 风险提示

本系统分析结果仅供参考，不构成投资建议。股市有风险，投资需谨慎。

## 许可证

MIT License
