# -*- coding: utf-8 -*-
"""
配置文件 - 连板交易系统配置
"""

# 评分权重配置
SCORING_WEIGHTS = {
    "consecutive_high": 0.20,   # 连板高度 20%
    "order_strength": 0.25,     # 封单强度 25%
    "sector_heat": 0.20,        # 板块热度 20%
    "turnover_health": 0.15,    # 换手健康 15%
    "time_advantage": 0.10,     # 时间优势 10%
    "market_cap": 0.10,         # 市值适中 10%
}

# 评分阈值
BUY_THRESHOLD = 75.0  # 买入阈值：综合评分 >= 75分

# 评分标准
SCORING_CRITERIA = {
    "consecutive_high": {
        "3-4板": 40,  # 3-4板最佳
        "5板": 25,
        "6板+": 20,   # 6板以上谨慎
        "1-2板": 15,
    },
    "order_strength": {
        "封单/流通市值 > 10%": 25,
        "封单/流通市值 5-10%": 18,
        "封单/流通市值 2-5%": 10,
        "封单/流通市值 < 2%": 5,
    },
    "sector_heat": {
        "同板块涨停 > 8家": 25,
        "同板块涨停 5-8家": 20,
        "同板块涨停 3-5家": 12,
        "同板块涨停 < 3家": 5,
    },
    "turnover_health": {
        "10% < 换手 < 30%": 15,
        "5% < 换手 <= 10%": 10,
        "30% <= 换手 < 50%": 8,
        "换手 >= 50%": 3,
        "换手 <= 5%": 5,
    },
    "time_advantage": {
        "早盘涨停(9:30-10:30)": 10,
        "上午涨停(10:30-11:30)": 8,
        "下午涨停(13:00-14:30)": 5,
        "尾盘涨停(14:30+)": 0,  # 尾盘板不参与
    },
    "market_cap": {
        "50-200亿": 10,
        "20-50亿": 8,
        "200-500亿": 6,
        "<20亿": 4,
        ">500亿": 3,
    }
}

# 红旗规则 - 禁止事项
RED_FLAGS = {
    "is_one_word_limit_up": True,      # 一字板不参与
    "is_late_limit_up": True,          # 尾盘板不参与(14:30后)
    "is_independent_freak": True,      # 独立妖股不参与
    "max_single_position": 0.20,       # 单票仓位不超过20%
    "max_consecutive_losses": 3,       # 连续亏损3次强制休息
    "rest_days": 1,                    # 强制休息天数
}

# 市值单位（亿）
MARKET_CAP_UNIT = 100000000

# 新股定义（上市天数）
NEW_STOCK_DAYS = 60  # 次新股定义为上市60天内

# 输出目录配置
OUTPUT_DIRS = {
    "reports": "reports",
    "data": "data",
    "logs": "logs",
}

# 时间配置
TRADING_HOURS = {
    "morning_start": "09:30",
    "morning_end": "11:30",
    "afternoon_start": "13:00",
    "afternoon_end": "15:00",
    "late_limit_up": "14:30",  # 尾盘板起始时间
}

# 情绪指标阈值
SENTIMENT = {
    "freezing": 30,      # 冰点 threshold
    "heating": 50,       # 升温 threshold
    "boiling": 80,       # 沸腾 threshold
}

# 止损配置
STOP_LOSS = {
    "default": -0.07,    # 默认止损 -7%
    "high_risk": -0.05,  # 高风险止损 -5%
}

# 止盈配置
TAKE_PROFIT = {
    "tier1": 0.15,       # 第一止盈 15%
    "tier2": 0.25,       # 第二止盈 25%
    "tier3": 0.40,       # 完全止盈 40%
}
