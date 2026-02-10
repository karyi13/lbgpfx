# -*- coding: utf-8 -*-
"""
K线数据API服务
使用 AKShare 获取A股K线数据（稳定可靠）
"""

from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime, timedelta
import akshare as ak
import logging
import os
import pandas as pd

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=None)
# 获取脚本所在目录作为静态文件根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def normalize_stock_code(code):
    """
    标准化股票代码为 AKShare 格式
    去掉市场前缀，保留6位数字代码
    """
    code = str(code).strip()
    # 去掉任何市场前缀（sh/sz/SH/SZ）
    if code.lower().startswith(('sh', 'sz')):
        code = code[2:]
    return code


def fetch_kline_akshare(code, days=60):
    """
    使用 AKShare 获取K线数据
    返回: DataFrame with columns: date, open, high, low, close, volume
    """
    try:
        symbol = normalize_stock_code(code)

        # 计算日期范围
        end_date = datetime.now().strftime('%Y%m%d')
        start_date = (datetime.now() - timedelta(days=int(days) * 2)).strftime('%Y%m%d')  # 多取一些避免节假日缺失

        # 使用 stock_zh_a_hist 获取历史数据
        # 注意：AKShare 需要股票带市场前缀（.sh 或 .sz）
        market_prefix = 'sh' if symbol.startswith('6') else 'sz'
        full_symbol = f"{market_prefix}{symbol}"

        df = ak.stock_zh_a_hist(
            symbol=full_symbol,
            period="daily",
            start_date=start_date,
            end_date=end_date,
            adjust=""  # 不复权
        )

        if df.empty:
            return None

        # 重命名列以匹配我们的格式
        df = df.rename(columns={
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'vol',
            '成交额': 'amount'
        })

        # 只保留需要的列
        df = df[['date', 'open', 'high', 'low', 'close', 'vol', 'amount']].copy()

        # 转换数据类型
        df['date'] = pd.to_datetime(df['date']).dt.strftime('%Y-%m-%d')
        for col in ['open', 'high', 'low', 'close', 'vol', 'amount']:
            df[col] = pd.to_numeric(df[col], errors='coerce')

        # 排除停牌日（成交量为0或开盘=收盘=0）
        df = df[df['vol'] > 0]

        # 按日期降序排序
        df = df.sort_values('date', ascending=False)

        # 只返回指定天数
        df = df.head(days)

        return df

    except Exception as e:
        logger.error(f"AKShare 获取失败: {code}, 错误: {e}")
        return None


@app.route('/api/kline/<code>', methods=['GET', 'OPTIONS'])
def get_kline(code):
    """
    获取股票K线数据
    参数:
        code: 股票代码 (如 sh603316, 603316)
        days: 获取天数 (默认 60)
    返回:
        {
            "code": "sh603316",
            "name": "",
            "data": [
                {"date": "2025-01-01", "open": 9.5, "high": 10.2, "low": 9.4, "close": 10.0, "vol": 123456, "amount": 12345678},
                ...
            ]
        }
    """
    # 处理 CORS 预检请求
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        days = request.args.get('days', 60, type=int)

        # 使用 AKShare 获取数据
        df = fetch_kline_akshare(code, days)

        if df is None or df.empty:
            return jsonify({
                "code": code,
                "name": "",
                "data": [],
                "message": "未找到该股票数据（可能已退市或停牌）"
            })

        # 转换为 JSON 格式
        data = df.to_dict('records')

        return jsonify({
            "code": code,
            "name": "",  # AKShare 返回的 name 在列中，暂不填充
            "data": data,
            "source": "akshare"
        })

    except ValueError as e:
        return jsonify({
            "error": str(e),
            "code": code,
            "data": []
        }), 400
    except Exception as e:
        logger.error(f"获取K线失败: {e}", exc_info=True)
        return jsonify({
            "error": f"服务器错误: {str(e)}",
            "code": code,
            "data": []
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})


@app.route('/')
def index():
    """重定向到天梯图首页"""
    return send_from_directory(BASE_DIR, 'ladder.html')


@app.route('/ladder.html')
def ladder_page():
    """天梯图页面"""
    return send_from_directory(BASE_DIR, 'ladder.html')


@app.route('/kline.html')
def kline_page():
    """K线图页面"""
    return send_from_directory(BASE_DIR, 'kline.html')


@app.route('/<path:filename>')
def static_files(filename):
    """提供其他静态文件"""
    return send_from_directory(BASE_DIR, filename)


if __name__ == '__main__':
    logger.info("正在初始化K线数据服务（使用 AKShare）...")
    logger.info("服务将运行在 http://127.0.0.1:5001")
    app.run(host='0.0.0.0', port=5001, debug=True)
