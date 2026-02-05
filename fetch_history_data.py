# -*- coding: utf-8 -*-
"""
获取最近两个月涨跌停股池数据
API: zhituapi.com
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from typing import List, Dict
import pandas as pd


# API配置
API_CONFIG = {
    "token": "BA43E6E1-A30D-4FEA-BD23-7B2376FD6114",
    "base_url": "https://api.zhituapi.com",
    "timeout": 30,
}

# 请求间隔（秒）
REQUEST_INTERVAL = 0.2  # 避免频率限制


class ZhituAPIFetcher:
    """智图API数据获取器"""

    def __init__(self, token: str = None):
        self.token = token or API_CONFIG["token"]
        self.base_url = API_CONFIG["base_url"]

    def fetch_limit_up_pool(self, date: str) -> List[Dict]:
        """
        获取涨停股池

        Args:
            date: 交易日期 (yyyy-MM-dd)

        Returns:
            涨停股票列表
        """
        url = f"{self.base_url}/hs/pool/ztgc/{date}?token={self.token}"
        return self._fetch(url)

    def fetch_limit_down_pool(self, date: str) -> List[Dict]:
        """
        获取跌停股池

        Args:
            date: 交易日期 (yyyy-MM-dd)

        Returns:
            跌停股票列表
        """
        url = f"{self.base_url}/hs/pool/dtgc/{date}?token={self.token}"
        return self._fetch(url)

    def fetch_explode_pool(self, date: str) -> List[Dict]:
        """
        获取炸板股池

        Args:
            date: 交易日期 (yyyy-MM-dd)

        Returns:
            炸板股票列表
        """
        url = f"{self.base_url}/hs/pool/zbgc/{date}?token={self.token}"
        return self._fetch(url)

    def _fetch(self, url: str) -> List[Dict]:
        """
        执行API请求

        Args:
            url: 请求URL

        Returns:
            数据列表
        """
        try:
            response = requests.get(url, timeout=API_CONFIG["timeout"])
            response.raise_for_status()

            data = response.json()

            # API直接返回数组格式
            if isinstance(data, list):
                return data
            # 兼容可能的对象格式 {code: 200, data: {list: [...]}}
            if isinstance(data, dict):
                if data.get("code") == 200:
                    data_field = data.get("data", {})
                    if isinstance(data_field, list):
                        return data_field
                    elif isinstance(data_field, dict):
                        return data_field.get("list", [])
                    return []
                else:
                    print(f"    请求失败: {data.get('msg', '未知错误')}")
                    return []
            return []

        except requests.exceptions.Timeout:
            print(f"    请求超时")
            return []
        except requests.exceptions.RequestException as e:
            print(f"    请求错误: {e}")
            return []
        except json.JSONDecodeError:
            print(f"    JSON解析失败")
            return []
        except Exception as e:
            print(f"    未知错误: {e}")
            return []


def get_trading_dates(start_date: str = None, end_date: str = None, days: int = 60) -> List[str]:
    """
    获取交易日期列表

    Args:
        start_date: 起始日期 (yyyy-MM-dd)，为空时使用今天往前推days天
        end_date: 结束日期 (yyyy-MM-dd)，为空时使用今天
        days: 当start_date为空时，获取的天数

    Returns:
        日期列表 (yyyy-MM-dd)
    """
    dates = []
    today = datetime.now()

    # 基准日期和天数计算
    if start_date:
        base_start = datetime.strptime(start_date, "%Y-%m-%d")
        base_end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else today
    else:
        base_end = datetime.strptime(end_date, "%Y-%m-%d") if end_date else today
        days_count = (base_end - datetime.now()).days + days
        base_start = base_end - timedelta(days=days_count)

    # 遍历日期范围
    current = base_start
    while current <= base_end:
        # 排除周末 (5=周六, 6=周日)
        if current.weekday() < 5:
            dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)

    return dates


def fetch_two_months_data(start_date: str = None, end_date: str = None, days: int = 60, save_dir: str = "data/history"):
    """
    获取涨跌停数据（支持日期区间或最近N天）

    Args:
        start_date: 起始日期 (yyyy-MM-dd)，为空时使用最近days天
        end_date: 结束日期 (yyyy-MM-dd)，为空则使用今天
        days: 获取天数（当start_date为空时有效）
        save_dir: 保存目录
    """
    # 创建保存目录
    os.makedirs(save_dir, exist_ok=True)
    os.makedirs(f"{save_dir}/limit_up", exist_ok=True)
    os.makedirs(f"{save_dir}/limit_down", exist_ok=True)
    os.makedirs(f"{save_dir}/explode", exist_ok=True)

    fetcher = ZhituAPIFetcher()

    # 获取交易日期
    trading_dates = get_trading_dates(start_date=start_date, end_date=end_date, days=days)

    print(f"=" * 60)
    print(f"获取最近两个月涨跌停股池数据")
    print(f"=" * 60)
    print(f"交易日期数量: {len(trading_dates)}")
    print(f"起始日期: {trading_dates[0]}")
    print(f"结束日期: {trading_dates[-1]}")
    print(f"=" * 60)

    # 统计数据
    stats = {
        "limit_up": 0,
        "limit_down": 0,
        "explode": 0,
        "dates": 0,
        "errors": 0,
    }

    # 涨停数据汇总
    all_limit_up = []
    all_limit_down = []
    all_explode = []

    # 遍历每个交易日
    for i, date in enumerate(trading_dates, 1):
        print(f"\n[{i}/{len(trading_dates)}] {date}")

        # 获取涨停股池
        print("  - 涨停股池:", end="")
        limit_up = fetcher.fetch_limit_up_pool(date)
        if limit_up:
            print(f" {len(limit_up)}只")
            stats["limit_up"] += len(limit_up)
            all_limit_up.extend(limit_up)

            # 保存每日数据
            filename = f"{save_dir}/limit_up/{date}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({"date": date, "count": len(limit_up), "data": limit_up}, f, ensure_ascii=False)
        else:
            print(" 无数据")

        # 请求间隔
        time.sleep(REQUEST_INTERVAL)

        # 获取跌停股池
        print("  - 跌停股池:", end="")
        limit_down = fetcher.fetch_limit_down_pool(date)
        if limit_down:
            print(f" {len(limit_down)}只")
            stats["limit_down"] += len(limit_down)
            all_limit_down.extend(limit_down)

            # 保存每日数据
            filename = f"{save_dir}/limit_down/{date}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({"date": date, "count": len(limit_down), "data": limit_down}, f, ensure_ascii=False)
        else:
            print(" 无数据")

        time.sleep(REQUEST_INTERVAL)

        # 获取炸板股池
        print("  - 炸板股池:", end="")
        explode = fetcher.fetch_explode_pool(date)
        if explode:
            print(f" {len(explode)}只")
            stats["explode"] += len(explode)
            all_explode.extend(explode)

            # 保存每日数据
            filename = f"{save_dir}/explode/{date}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({"date": date, "count": len(explode), "data": explode}, f, ensure_ascii=False)
        else:
            print(" 无数据")

        stats["dates"] += 1

        # 请求间隔
        time.sleep(REQUEST_INTERVAL)

    # 保存汇总数据（CSV格式）
    print(f"\n{'=' * 60}")
    print("保存汇总数据...")

    if all_limit_up:
        df_limit_up = pd.DataFrame(all_limit_up)
        csv_file = f"{save_dir}/limit_up_all.csv"
        df_limit_up.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"  涨停汇总: {csv_file}")

    if all_limit_down:
        df_limit_down = pd.DataFrame(all_limit_down)
        csv_file = f"{save_dir}/limit_down_all.csv"
        df_limit_down.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"  跌停汇总: {csv_file}")

    if all_explode:
        df_explode = pd.DataFrame(all_explode)
        csv_file = f"{save_dir}/explode_all.csv"
        df_explode.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"  炸板汇总: {csv_file}")

    # 保存每日统计
    daily_stats = []
    for date in trading_dates:
        stat_entry = {
            "date": date,
            "limit_up_count": 0,
            "limit_down_count": 0,
            "explode_count": 0,
        }

        # 读取每日数据
        try:
            with open(f"{save_dir}/limit_up/{date}.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
                stat_entry["limit_up_count"] = data.get("count", 0)
        except:
            pass

        try:
            with open(f"{save_dir}/limit_down/{date}.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
                stat_entry["limit_down_count"] = data.get("count", 0)
        except:
            pass

        try:
            with open(f"{save_dir}/explode/{date}.json", 'r', encoding='utf-8') as f:
                data = json.load(f)
                stat_entry["explode_count"] = data.get("count", 0)
        except:
            pass

        daily_stats.append(stat_entry)

    if daily_stats:
        df_daily = pd.DataFrame(daily_stats)
        csv_file = f"{save_dir}/daily_stats.csv"
        df_daily.to_csv(csv_file, index=False, encoding='utf-8-sig')
        print(f"  每日统计: {csv_file}")

        # 计算情绪指标
        df_daily["explode_rate"] = (df_daily["explode_count"] / (df_daily["limit_up_count"] + df_daily["explode_count"]) * 100).round(2)
        emotion_file = f"{save_dir}/sentiment_index.csv"
        df_daily.to_csv(emotion_file, index=False, encoding='utf-8-sig')
        print(f"  情绪指标: {emotion_file}")

    # 输出统计信息
    print(f"\n{'=' * 60}")
    print("数据获取完成!")
    print(f"{'=' * 60}")
    print(f"交易日期: {stats['dates']}天")
    print(f"涨停总数: {stats['limit_up']}只")
    print(f"跌停总数: {stats['limit_down']}只")
    print(f"炸板总数: {stats['explode']}只")
    print(f"平均涨停/天: {stats['limit_up'] / stats['dates']:.1f}只" if stats['dates'] > 0 else "")
    print(f"平均跌停/天: {stats['limit_down'] / stats['dates']:.1f}只" if stats['dates'] > 0 else "")
    print(f"平均炸板/天: {stats['explode'] / stats['dates']:.1f}只" if stats['dates'] > 0 else "")
    print(f"{'=' * 60}")


def fetch_single_date(date: str, save_dir: str = "data/today"):
    """
    获取单个交易日的涨跌停数据

    Args:
        date: 交易日期 (yyyy-MM-dd)
        save_dir: 保存目录
    """
    os.makedirs(save_dir, exist_ok=True)

    fetcher = ZhituAPIFetcher()

    print(f"=" * 60)
    print(f"获取 {date} 涨跌停数据")
    print(f"=" * 60)

    # 涨停
    print("涨停股池:")
    limit_up = fetcher.fetch_limit_up_pool(date)
    print(f"  共 {len(limit_up)} 只")
    if limit_up:
        # 显示前5只
        for stock in limit_up[:5]:
            print(f"    {stock['mc']}({stock['dm']}) - 连板: {stock.get('lbc', 0)} - 封板时间: {stock.get('fbt', 'N/A')}")
        if len(limit_up) > 5:
            print(f"    ... 还有 {len(limit_up) - 5} 只")

        # 保存
        with open(f"{save_dir}/limit_up_{date}.json", 'w', encoding='utf-8') as f:
            json.dump({"date": date, "count": len(limit_up), "data": limit_up}, f, ensure_ascii=False)

        # 保存CSV
        df = pd.DataFrame(limit_up)
        df.to_csv(f"{save_dir}/limit_up_{date}.csv", index=False, encoding='utf-8-sig')

    time.sleep(0.5)

    # 跌停
    print("\n跌停股池:")
    limit_down = fetcher.fetch_limit_down_pool(date)
    print(f"  共 {len(limit_down)} 只")
    if limit_down:
        for stock in limit_down[:5]:
            print(f"    {stock['mc']}({stock['dm']}) - 跌幅: {stock.get('zf', 0):.2f}%")
        if len(limit_down) > 5:
            print(f"    ... 还有 {len(limit_down) - 5} 只")

        with open(f"{save_dir}/limit_down_{date}.json", 'w', encoding='utf-8') as f:
            json.dump({"date": date, "count": len(limit_down), "data": limit_down}, f, ensure_ascii=False)

        df = pd.DataFrame(limit_down)
        df.to_csv(f"{save_dir}/limit_down_{date}.csv", index=False, encoding='utf-8-sig')

    time.sleep(0.5)

    # 炸板
    print("\n炸板股池:")
    explode = fetcher.fetch_explode_pool(date)
    print(f"  共 {len(explode)} 只")
    if explode:
        for stock in explode[:5]:
            print(f"    {stock['mc']}({stock['dm']}) - 炸板次数: {stock.get('zbc', 0)}")
        if len(explode) > 5:
            print(f"    ... 还有 {len(explode) - 5} 只")

        with open(f"{save_dir}/explode_{date}.json", 'w', encoding='utf-8') as f:
            json.dump({"date": date, "count": len(explode), "data": explode}, f, ensure_ascii=False)

        df = pd.DataFrame(explode)
        df.to_csv(f"{save_dir}/explode_{date}.csv", index=False, encoding='utf-8-sig')

    # 输出情绪指标
    print(f"\n{'=' * 60}")
    print("情绪指标")
    print(f"{'=' * 60}")
    print(f"涨停数量: {len(limit_up)}")
    print(f"跌停数量: {len(limit_down)}")
    print(f"炸板数量: {len(explode)}")
    total = len(limit_up) + len(explode)
    print(f"炸板率: {len(explode) / total * 100:.1f}%" if total > 0 else "炸板率: N/A")

    # 连板统计
    consecutive = {}
    for s in limit_up:
        days = s.get('lbc', 0)
        consecutive[days] = consecutive.get(days, 0) + 1

    print("\n连板统计:")
    for days in sorted(consecutive.keys(), reverse=True)[:10]:
        print(f"  {days}板: {consecutive[days]}只")

    print(f"{'=' * 60}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="智图API涨跌停数据获取",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 获取最近60天数据（默认）
  python fetch_history_data.py

  # 获取最近30天数据
  python fetch_history_data.py --days 30

  # 获取指定日期区间数据
  python fetch_history_data.py --start 2024-01-01 --end 2024-01-31

  # 获取单个日期数据
  python fetch_history_data.py --date 2024-01-15

  # 获取今日数据
  python fetch_history_data.py --today
        """
    )
    parser.add_argument("--date", type=str, help="获取单个日期的数据 (yyyy-MM-dd)")
    parser.add_argument("--days", type=int, default=60, help="获取历史数据天数（默认60天）")
    parser.add_argument("--today", action="store_true", help="获取今日数据")
    parser.add_argument("--start", type=str, help="起始日期 (yyyy-MM-dd)")
    parser.add_argument("--end", type=str, help="结束日期 (yyyy-MM-dd)")

    args = parser.parse_args()

    if args.date:
        fetch_single_date(args.date)
    elif args.today:
        fetch_single_date(datetime.now().strftime("%Y-%m-%d"))
    else:
        fetch_two_months_data(start_date=args.start, end_date=args.end, days=args.days)
