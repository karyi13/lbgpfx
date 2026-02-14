# -*- coding: utf-8 -*-
"""
简单的 HTTP 服务器，提供 K 线 JSON 数据和静态文件
"""

import os
import sys
import json
from http.server import HTTPServer, SimpleHTTPRequestHandler

# K线数据JSON文件路径
KLINE_JSON_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'kline_optimized', 'kline_data.json')


class KLineHandler(SimpleHTTPRequestHandler):
    """自定义 HTTP 处理器"""

    def __init__(self, *args, **kwargs):
        # 文件在当前目录下提供
        self.directory = os.path.dirname(os.path.abspath(__file__))
        super().__init__(*args, **kwargs)

    def do_GET(self):
        """处理 GET 请求"""
        if self.path == '/api/kline':
            return self.handle_kline_api()
        return super().do_GET()

    def handle_kline_api(self):
        """返回完整的K线JSON数据"""
        if not os.path.exists(KLINE_JSON_FILE):
            self.send_json_response({'success': False, 'error': 'K线数据文件不存在'}, 404)
            return

        try:
            with open(KLINE_JSON_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            self.send_json_response({'success': True, 'data': data})
        except Exception as e:
            self.send_json_response({'success': False, 'error': str(e)}, 500)

    def send_json_response(self, data, status=200):
        """发送 JSON 响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def log_message(self, format, *args):
        print(f"[{self.log_date_time_string()}] {format % args}")


def run_server(port=8000):
    server_address = ('', port)
    httpd = HTTPServer(server_address, KLineHandler)

    print("=" * 60)
    print("连板天梯 + K线图服务器")
    print("=" * 60)
    print(f"访问: http://localhost:{port}/ladder.html")
    print(f"API: http://localhost:{port}/api/kline")
    print(f"数据: {os.path.getsize(KLINE_JSON_FILE)/1024/1024:.1f} MB")
    print("=" * 60)
    print("按 Ctrl+C 停止")
    print("=" * 60)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n服务器已停止")
        httpd.server_close()


if __name__ == '__main__':
    port = 8000 if len(sys.argv) < 2 else int(sys.argv[1])
    run_server(port)
