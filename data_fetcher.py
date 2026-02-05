# -*- coding: utf-8 -*-
"""
数据获取模块 - 使用AKShare获取真实A股涨停数据
"""

import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# 尝试导入akshare
try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False
    print("警告: akshare未安装。请运行: pip install akshare")

import pandas as pd

# 通达信服务器列表（备用）
PYTDX_SERVERS = [
    ('180.153.18.170', 7709),
    ('218.75.126.9', 7709),
    ('60.191.117.167', 7709),
    ('60.12.136.250', 7709),
]

try:
    import pytdx.hq as hq
    PYTDX_AVAILABLE = True
except ImportError:
    PYTDX_AVAILABLE = False


class DataFetcher:
    """数据获取类 - 使用akshare获取真实数据"""

    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock
        self.last_limit_up_cache = []  # 缓存上次涨停数据
        self.last_cache_time = None

        if not use_mock and AKSHARE_AVAILABLE:
            print("数据源: AKShare")
        elif not use_mock:
            print("警告: akshare未安装，将使用模拟数据")

    def fetch_limit_up_stocks(self, date: str = None) -> List[Dict]:
        """
        获取当日涨停数据

        Args:
            date: 日期字符串，格式 YYYY-MM-DD，默认为今天

        Returns:
            涨停股票列表
        """
        if self.use_mock or not AKSHARE_AVAILABLE:
            return self._mock_limit_up_data(date)
        return self._fetch_real_limit_up(date)

    def fetch_limit_up_history(self, stock_code: str, days: int = 30) -> List[Dict]:
        """
        获取股票历史数据，用于判断连板高度

        Args:
            stock_code: 股票代码 (需转换格式，如 000017 而不是 000017.SZ)
            days: 查询天数

        Returns:
            历史数据列表
        """
        if self.use_mock or not AKSHARE_AVAILABLE:
            return self._mock_limit_history(stock_code, days)
        return self._fetch_real_limit_history(stock_code, days)

    def fetch_sector_data(self, stock_code: str) -> Dict:
        """
        获取股票所属板块信息

        Args:
            stock_code: 股票代码

        Returns:
            板块信息字典
        """
        if self.use_mock or not AKSHARE_AVAILABLE:
            return self._mock_sector_data(stock_code)
        return self._fetch_real_sector_data(stock_code)

    def fetch_stock_info(self, stock_code: str) -> Dict:
        """
        获取股票基本信息

        Args:
            stock_code: 股票代码

        Returns:
            股票信息字典
        """
        if self.use_mock or not AKSHARE_AVAILABLE:
            return self._mock_stock_info(stock_code)
        return self._fetch_real_stock_info(stock_code)

    def validate_data(self, stock: Dict) -> bool:
        """
        验证数据完整性

        Args:
            stock: 股票数据字典

        Returns:
            数据是否完整
        """
        required_fields = ['code', 'name', 'price', 'limit_up_time']
        return all(field in stock for field in required_fields) and all(stock[field] for field in required_fields)

    # ==================== 真实数据获取方法 ====================

    def _fetch_real_limit_up(self, date: str = None) -> List[Dict]:
        """使用akshare获取涨停板数据"""
        try:
            if date is None:
                date = datetime.now().strftime('%Y%m%d')

            # akshare日期格式: YYYYMMDD
            print(f"正在获取 {date} 的涨停数据...")

            # 使用akshare的涨停板接口
            # 接口1: stock_zt_pool_em (东方财富涨停板池)
            print("  - 调用 stock_zt_pool_em...")
            df_em = ak.stock_zt_pool_em(date=date)

            # 接口2: stock_limit_list_a (A股涨停列表)
            print("  - 调用 stock_limit_list_a...")
            df_limit = ak.stock_limit_list_a(date=date)

            # 优先使用东方财富数据
            if not df_em.empty:
                print(f"  成功获取到 {len(df_em)} 只涨停股票 (东方财富)")
                return self._parse_em_limit_up_data(df_em, date)
            elif not df_limit.empty:
                print(f"  成功获取到 {len(df_limit)} 只涨停股票")
                return self._parse_limit_list_data(df_limit, date)
            else:
                print("  未获取到涨停数据")
                return []

        except Exception as e:
            print(f"  获取涨停数据失败: {e}")
            print("  正在尝试备用数据源...")

            # 备用：使用市场行情数据
            return self._fetch_limit_up_by_scan()

    def _parse_em_limit_up_data(self, df: pd.DataFrame, date: str) -> List[Dict]:
        """解析东方财富涨停板数据"""
        result = []
        convert_date = datetime.strptime(date, '%Y%m%d').strftime('%Y-%m-%d')

        # 获取炸板数据用于判断情绪
        try:
            df_explode = ak.stock_zt_pool_em(date=date, em_retry=True)
            # 炸板率计算在analysis_engine中处理
        except:
            pass

        for _, row in df.iterrows():
            try:
                # stock_code 格式如 "000017"
                stock_code = str(row.get('代码', ''))
                name = str(row.get('名称', ''))
                price = float(row.get('最新价', 0))

                if price <= 0:
                    continue

                # 判断市场
                if stock_code.startswith('6'):
                    suffix = '.SH'
                elif stock_code.startswith(('0', '3')):
                    suffix = '.SZ'
                elif stock_code.startswith('4') or stock_code.startswith('8'):
                    suffix = '.BJ'  # 北交所
                else:
                    suffix = ''

                full_code = f"{stock_code}{suffix}" if suffix else stock_code

                # 判断ST
                is_st = 'ST' in name or '*ST' in name

                # 判断次新股 - 需要获取上市日期
                try:
                    df_info = ak.stock_individual_info_em(symbol=stock_code)
                    list_date = df_info[df_info['item'] == '上市时间']['value'].values[0] if len(df_info) > 0 else '2000-01-01'
                    if isinstance(list_date, str) and len(list_date) >= 10:
                        list_date_obj = datetime.strptime(list_date, '%Y-%m-%d')
                        days_listed = (datetime.now() - list_date_obj).days
                        is_new = days_listed < 60
                    else:
                        days_listed = 1000
                        is_new = False
                except:
                    days_listed = 1000
                    is_new = False

                # 获取连板天数
                history = self.fetch_limit_up_history(full_code, days=15)
                consecutive_days = self._calculate_consecutive_days(history)

                # 获取详细行情数据
                turnover = float(row.get('换手率', 0))
                market_cap = float(row.get('总市值', 0)) / 100000000  # 转换为亿

                # 封单金额
                order_amount = float(row.get('封单额', 0)) / 100000000  # 转换为亿

                # 涨停时间 (格式: 09:30:00)
                limit_time = str(row.get('首次涨停时间', '14:59:00'))

                # 封单类型判断是否一字板
                open_price = float(row.get('开盘', 0))
                is_one_word = (abs(open_price - price) < 0.01) if open_price > 0 else False

                result.append({
                    "code": full_code,
                    "name": name,
                    "price": price,
                    "open": open_price,
                    "high": price,
                    "low": float(row.get('最低', 0)),
                    "turnover": turnover,
                    "market_cap": market_cap,
                    "order_amount": order_amount,
                    "limit_up_time": limit_time,
                    "consecutive_days": consecutive_days,
                    "sector": str(row.get('行业', '')),
                    "is_st": is_st,
                    "is_new": is_new,
                    "is_one_word": is_one_word,
                    "days_listed": days_listed,
                })

            except Exception as e:
                continue

        return result

    def _parse_limit_list_data(self, df: pd.DataFrame, date: str) -> List[Dict]:
        """解析股票涨停列表数据"""
        result = []

        for _, row in df.iterrows():
            try:
                stock_code = str(row.get('代码', ''))
                name = str(row.get('名称', ''))
                price = float(row.get('最新价', 0))

                if price <= 0:
                    continue

                # 判断市场
                if stock_code.startswith('6'):
                    full_code = f"{stock_code}.SH"
                elif stock_code.startswith(('0', '3')):
                    full_code = f"{stock_code}.SZ"
                else:
                    full_code = stock_code

                is_st = 'ST' in name or '*ST' in name

                # 获取连板天数
                history = self.fetch_limit_up_history(full_code, days=15)
                consecutive_days = self._calculate_consecutive_days(history)

                result.append({
                    "code": full_code,
                    "name": name,
                    "price": price,
                    "open": float(row.get('今开', 0)),
                    "high": price,
                    "low": float(row.get('最低', 0)),
                    "turnover": float(row.get('换手率', 0)),
                    "market_cap": float(row.get('总市值', 0)) / 100000000,
                    "order_amount": float(row.get('成交额', 0)) / 100000000,
                    "limit_up_time": str(row.get('涨停时间', '14:59:00')),
                    "consecutive_days": consecutive_days,
                    "sector": "",
                    "is_st": is_st,
                    "is_new": False,
                    "is_one_word": False,
                    "days_listed": 1000,
                })

            except Exception as e:
                continue

        return result

    def _calculate_consecutive_days(self, history: List[Dict]) -> int:
        """计算连续涨停天数"""
        consecutive = 0
        for data in history[1:]:  # 跳过当天
            if data.get('is_limit_up', False):
                consecutive += 1
            else:
                break
        return consecutive

    def _fetch_limit_up_by_scan(self) -> List[Dict]:
        """备用方案：扫描市场判断涨停"""
        print("  使用备用方案：扫描市场行情...")

        if not PYTDX_AVAILABLE:
            print("  pytdx不可用，返回模拟数据")
            return self._mock_limit_up_data()

        try:
            from pytdx.hq import TdxHq_API

            # 使用东方财富接口获取涨停
            try:
                df = ak.stock_zt_pool_em(date=datetime.now().strftime('%Y%m%d'))
                if not df.empty:
                    return self._parse_em_limit_up_data(df, datetime.now().strftime('%Y%m%d'))
            except:
                pass

        except Exception as e:
            print(f"  备用方案失败: {e}")

        return []

    def _fetch_real_limit_history(self, stock_code: str, days: int = 30) -> List[Dict]:
        """获取股票历史K线数据"""
        try:
            # 转换代码格式 (000017.SZ -> 000017)
            code = stock_code.split('.')[0]

            # 使用akshare获取A股历史行情
            df = ak.stock_zh_a_hist(symbol=code, period="daily", start_date="", end_date="20251231", adjust="")

            result = []
            for _, row in df.iterrows():
                high = float(row.get('最高', 0))
                close = float(row.get('收盘', 0))
                open_price = float(row.get('开盘', 0))
                low = float(row.get('最低', 0))

                # 判断是否涨停 (收盘价等于或接近最高价)
                is_limit_up = False
                if high > 0:
                    # 简单判断：涨幅 > 9.5% 或 收盘价 = 最高价
                    pct = (close - open_price) / open_price * 100 if open_price > 0 else 0
                    is_limit_up = pct > 9.5 or close >= high * 0.995

                result.append({
                    "date": str(row.get('日期', '')),
                    "open": open_price,
                    "close": close,
                    "high": high,
                    "low": low,
                    "vol": float(row.get('成交量', 0)),
                    "is_limit_up": is_limit_up,
                })

            return result

        except Exception as e:
            return []

    def _fetch_real_sector_data(self, stock_code: str) -> Dict:
        """获取股票板块信息"""
        try:
            code = stock_code.split('.')[0]

            # 获取股票基本信息
            df_info = ak.stock_individual_info_em(symbol=code)
            if len(df_info) > 0:
                # 获取行业信息
                industry_row = df_info[df_info['item'] == '所属行业']
                main_sector = industry_row['value'].values[0] if len(industry_row) > 0 else "未知"

                return {
                    "stock_code": stock_code,
                    "main_sector": main_sector,
                    "sub_sectors": [],
                    "count_limit_up": 1,
                }
        except:
            pass

        return {
            "stock_code": stock_code,
            "main_sector": "未知",
            "sub_sectors": [],
            "count_limit_up": 1,
        }

    def _fetch_real_stock_info(self, stock_code: str) -> Dict:
        """获取股票基本信息"""
        try:
            code = stock_code.split('.')[0]

            # 获取实时行情
            df = ak.stock_zh_a_spot_em()
            stock_row = df[df['代码'] == code]

            if not stock_row.empty:
                name = str(stock_row['名称'].values[0])
                market_cap = float(stock_row['总市值'].values[0]) / 100000000

                return {
                    "code": stock_code,
                    "name": name,
                    "market_cap": market_cap,
                    "industry": "",
                    "list_days": 1000,
                    "is_st": 'ST' in name or '*ST' in name,
                }
        except:
            pass

        return {
            "code": stock_code,
            "name": "未知",
            "market_cap": 100,
            "industry": "未知",
            "list_days": 1000,
            "is_st": False,
        }

    # ==================== 模拟数据方法 (备用) ====================

    def _mock_limit_up_data(self, date: str = None) -> List[Dict]:
        """生成模拟涨停数据"""
        import random

        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')

        sectors = [
            "锂电池", "光伏", "人工智能", "半导体", "新能源车",
            "机器人", "军工", "中药", "数字经济", "游戏", "消费电子",
            "汽车电子", "新材料", "OLED", "MiniLED", "鸿蒙", "算力",
            "CPO", "存储芯片", "先进封装", "卫星导航", "飞行汽车"
        ]

        name_prefixes = ["深", "华", "中", "国", "科", "技", "新", "能", "元", "智", "龙", "宝", "盛", "通", "达", "宏", "金", "银"]
        name_suffixes = ["A", "股份", "科技", "集团", "能源", "材料", "控股", "电子", "智能", "动力", "微", "精", "达"]

        stocks = []
        num_stocks = random.randint(30, 60)

        # 预设一些高连板股
        leaders_data = [
            {"code": "000017", "name": "深中华A", "consecutive": 6, "sector": "锂电池"},
            {"code": "002641", "name": "公元股份", "consecutive": 5, "sector": "光伏"},
            {"code": "000020", "name": "深华发A", "consecutive": 5, "sector": "电子"},
            {"code": "600777", "name": "新潮能源", "consecutive": 4, "sector": "能源"},
            {"code": "002892", "name": "科力尔", "consecutive": 4, "sector": "机器人"},
            {"code": "003023", "name": "彩虹集团", "consecutive": 3, "sector": "电子"},
            {"code": "600839", "name": "四川长虹", "consecutive": 3, "sector": "消费电子"},
        ]

        # 添加龙头股
        for leader in leaders_data:
            exchange = ".SZ" if leader["code"].startswith("00") or leader["code"].startswith("30") else ".SH"
            stocks.append({
                "code": f"{leader['code']}{exchange}",
                "name": leader["name"],
                "price": random.uniform(8, 25),
                "open": random.uniform(8, 20),
                "high": random.uniform(12, 28),
                "low": random.uniform(8, 18),
                "limit_up_time": f"{random.randint(9, 10):02d}:{random.randint(10, 59):02d}:{random.randint(0, 59):02d}",
                "consecutive_days": leader["consecutive"],
                "sector": leader["sector"],
                "market_cap": random.uniform(50, 200),
                "turnover": random.uniform(10, 25),
                "order_amount": random.uniform(1, 5),
                "is_st": False,
                "is_new": False,
                "is_one_word": random.random() < 0.2,
                "days_listed": random.randint(500, 2000),
            })

        # 添加其他涨停股
        for i in range(num_stocks - len(leaders_data)):
            code_num = random.randint(1, 999)
            exchange = random.choice(["SZ", "SH"])

            # 随机分配板块
            sector = random.choice(sectsor for sector in sectors)

            # 根据板块热度调整连板数
            if sector in ["锂电池", "人工智能", "算力", "CPO"]:
                consecutive_weights = [0.25, 0.3, 0.25, 0.15, 0.05]
            else:
                consecutive_weights = [0.6, 0.25, 0.1, 0.04, 0.01]

            consecutive = random.choices([1, 2, 3, 4, 5], weights=consecutive_weights, k=1)[0]

            # 涨停时间
            if consecutive >= 4:
                hour = random.choices([9, 10, 13, 14], weights=[0.4, 0.3, 0.2, 0.1], k=1)[0]
            else:
                hour = random.choices([9, 10, 13, 14], weights=[0.2, 0.3, 0.3, 0.2], k=1)[0]

            minute = random.randint(0, 59) if hour in [9, 13] else random.randint(0, 30)

            stocks.append({
                "code": f"{code_num:06d}.{exchange}",
                "name": f"{random.choice(name_prefixes)}{random.choice(name_suffixes)}{random.choice(['A', 'B', 'C'])}",
                "price": random.uniform(5, 50),
                "open": random.uniform(5, 40),
                "high": random.uniform(6, 55),
                "low": random.uniform(5, 35),
                "limit_up_time": f"{hour:02d}:{minute:02d}:{random.randint(0, 59):02d}",
                "consecutive_days": consecutive,
                "sector": sector,
                "market_cap": random.uniform(20, 500),
                "turnover": random.uniform(3, 45),
                "order_amount": random.uniform(0.1, 3),
                "is_st": random.random() < 0.03,
                "is_new": random.random() < 0.08,
                "is_one_word": random.random() < 0.12,
                "days_listed": random.randint(60, 2000),
            })

        return stocks

    def _mock_limit_history(self, stock_code: str, days: int = 30) -> List[Dict]:
        """生成模拟历史涨停数据"""
        import random
        history = []
        base_date = datetime.now()

        for i in range(days):
            date = (base_date - timedelta(days=i)).strftime('%Y%m%d')
            is_limit_up = random.random() < 0.3
            history.append({
                "date": date,
                "open": random.uniform(8, 30),
                "close": random.uniform(8, 30),
                "high": random.uniform(8, 32),
                "low": random.uniform(8, 28),
                "vol": random.randint(1000, 500000),
                "is_limit_up": is_limit_up,
            })

        return history

    def _mock_sector_data(self, stock_code: str) -> Dict:
        """生成模拟板块数据"""
        import random
        sectors = ["锂电池", "光伏", "人工智能", "半导体", "新能源车", "机器人", "军工", "消费电子"]
        return {
            "stock_code": stock_code,
            "main_sector": random.choice(sectsor for sector in sectors),
            "sub_sectors": [],
            "count_limit_up": 1,
        }

    def _mock_stock_info(self, stock_code: str) -> Dict:
        """生成模拟股票信息"""
        return {
            "code": stock_code,
            "name": f"股票{stock_code}",
            "market_cap": 100,
            "industry": "未知",
            "list_days": 1000,
            "is_st": False,
        }

    # ==================== 工具方法 ====================

    def save_to_csv(self, data: List[Dict], file_path: str):
        """保存数据到CSV文件"""
        df = pd.DataFrame(data)
        df.to_csv(file_path, index=False, encoding='utf-8-sig')
        print(f"数据已保存到 {file_path}")

    def load_from_csv(self, file_path: str) -> List[Dict]:
        """从CSV文件加载数据"""
        try:
            df = pd.read_csv(file_path)
            return df.to_dict('records')
        except:
            return []


if __name__ == "__main__":
    # 测试数据获取
    print("=" * 60)
    print("A股连板交易系统 - 数据获取测试")
    print("=" * 60)

    # 使用真实数据
    fetcher = DataFetcher(use_mock=False)
    stocks = fetcher.fetch_limit_up_stocks()

    print(f"\n获取到 {len(stocks)} 只涨停股票")

    # 连板统计
    consecutive_counts = {}
    for stock in stocks:
        days = stock.get("consecutive_days", 1)
        consecutive_counts[days] = consecutive_counts.get(days, 0) + 1

    print("\n连板统计:")
    for days, count in sorted(consecutive_counts.items(), reverse=True):
        print(f"  {days}板: {count}只")

    # 显示前10只股票
    if stocks:
        print("\n股票详情 (前10只):")
        print("-" * 90)
        for i, stock in enumerate(stocks[:10], 1):
            print(f"\n{i}. {stock['name']} ({stock['code']})")
            print(f"   价格: {stock['price']:.2f} | 涨停时间: {stock['limit_up_time']} | 板块: {stock.get('sector', 'N/A')}")
            print(f"   连板: {stock['consecutive_days']}天 | 换手: {stock['turnover']:.1f}%")
            print(f"   市值: {stock['market_cap']:.1f}亿 | ST: {'是' if stock['is_st'] else '否'}")
            print(f"   一字板: {'是' if stock['is_one_word'] else '否'} | 次新股: {'是' if stock['is_new'] else '否'}")
