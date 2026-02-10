# -*- coding: utf-8 -*-
"""
K线数据API服务
使用 pytdx 从通达信服务器获取A股K线数据
"""

from flask import Flask, jsonify, request, send_from_directory
from datetime import datetime, timedelta
import pytdx
from pytdx.hq import TdxHq_API
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder=None)
# 获取脚本所在目录作为静态文件根目录
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 添加 CORS 头部支持跨域请求
@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET,POST,OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

# 通达信服务器列表（按延迟排序，从低到高）
PYTDX_SERVERS = [
    ('180.153.18.170', 7709),  # 延迟: ~0.14s
    ('218.75.126.9', 7709),    # 延迟: ~0.16s
    ('60.191.117.167', 7709),  # 延迟: ~0.16s
    ('60.12.136.250', 7709),   # 延迟: ~0.17s
]

#  market code mapping: 上海=0, 深圳=1
MARKET_MAP = {
    'sh': 0,
    'sz': 1,
}


def normalize_stock_code(code):
    """
    标准化股票代码
    输入: sh603316 或 603316 或 sz000001
    输出: (market_code, pure_code) -> (0, '603316') or (1, '000001')
    """
    code = str(code).strip().lower()

    # 如果包含 sh/sz 前缀
    if code.startswith('sh'):
        return 0, code[2:]
    elif code.startswith('sz'):
        return 1, code[2:]
    else:
        # 无前缀，根据首位数字判断
        if code.startswith('6'):
            return 0, code
        elif code.startswith('0') or code.startswith('3'):
            return 1, code
        else:
            raise ValueError(f"无法识别的股票代码格式: {code}")


def connect_best_server():
    """
    尝试连接可用的通达信服务器
    返回: (api, server_info) 或 (None, None)
    """
    for server in PYTDX_SERVERS:
        ip, port = server
        api = TdxHq_API()
        try:
            if api.connect(ip, port):
                logger.info(f"成功连接服务器: {ip}:{port}")
                return api, server
        except Exception as e:
            logger.warning(f"连接服务器 {ip}:{port} 失败: {e}")
            continue
    return None, None


@app.route('/api/kline/<code>', methods=['GET', 'OPTIONS'])
def get_kline(code):
    """
    获取股票K线数据
    参数:
        code: 股票代码 (如 sh603316, 603316)
        days: 获取天数 (默认 60)
        period: 周期 (day/week/month, 默认 day)
    返回:
        {
            "code": "sh603316",
            "name": "诚邦股份",
            "data": [
                {"date": "2025-01-01", "open": 9.5, "high": 10.2, "low": 9.4, "close": 10.0, "vol": 123456},
                ...
            ]
        }
    """
    # 处理 CORS 预检请求
    if request.method == 'OPTIONS':
        return ('', 204)

    try:
        # 解析参数
        days = request.args.get('days', 60, type=int)
        period = request.args.get('period', 'day')

        # 标准化代码
        market, pure_code = normalize_stock_code(code)

        # 连接服务器
        api, server = connect_best_server()
        if api is None:
            return jsonify({
                "error": "无法连接通达信服务器",
                "code": code,
                "data": []
            }), 503

        try:
            # 获取K线数据
            # pytdx 参数: market, code, start, count, period
            # 注意: start 是偏移量，count 是数量
            # 为了方便，我们获取足够的数据然后按日期筛选

            # 计算要获取的数量（多取一些确保覆盖）
            fetch_count = min(800, days + 50)  # 通达信单次最多约800条

            data = api.get_k_data(
                market=market,
                code=pure_code,
                start=0,
                count=fetch_count,
                period=0  # 0=daily, 1=weekly, 2=monthly
            )

            if not data:
                return jsonify({
                    "code": code,
                    "name": "",
                    "data": [],
                    "message": "未找到该股票数据"
                })

            # 转换数据格式
            kline_data = []
            for row in data:
                # pytdx 返回: date, open, close, high, low, vol, amount
                kline_data.append({
                    "date": row.get('date', ''),  # 格式: YYYY-MM-DD
                    "open": float(row.get('open', 0)),
                    "close": float(row.get('close', 0)),
                    "high": float(row.get('high', 0)),
                    "low": float(row.get('low', 0)),
                    "vol": int(row.get('vol', 0)),  # 成交量（手）
                    "amount": float(row.get('amount', 0)),  # 成交额（元）
                })

            # 按日期降序排序，确保最新在前
            kline_data.sort(key=lambda x: x['date'], reverse=True)

            # 只返回指定天数
            kline_data = kline_data[:days]

            # 获取股票基本信息（从现有数据推测）
            stock_name = ""
            # TODO: 可以从本地JSON文件或另一个API获取股票名称

            return jsonify({
                "code": code,
                "name": stock_name,
                "data": kline_data,
                "server": f"{server[0]}:{server[1]}"
            })

        finally:
            api.disconnect()

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


if __name__ == '__main__':
    # 测试连接（可选）
    logger.info("正在初始化K线数据服务...")
    test_api, test_server = connect_best_server()
    if test_api:
        test_api.disconnect()
        logger.info(f"已找到可用服务器，启动服务...")
    else:
        logger.warning("未找到可用服务器，服务可能无法正常工作")

    # 启动Flask服务
    app.run(host='0.0.0.0', port=5001, debug=True)
