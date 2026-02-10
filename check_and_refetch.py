# -*- coding: utf-8 -*-
"""
数据完整性检查脚本
检查每一天的数据，如果涨停、跌停、炸板股池中有一项为零，重新获取
"""

import os
import json
import sys
from datetime import datetime
from fetch_history_data import ZhituAPIFetcher

# 数据目录
DATA_DIR = "data/history"


def check_and_refetch_data():
    """
    检查并重新获取不完整的数据
    """
    # 确保目录存在
    if not os.path.exists(DATA_DIR):
        print(f"错误: 数据目录不存在: {DATA_DIR}")
        return

    # 获取所有日期目录
    limit_up_dir = os.path.join(DATA_DIR, "limit_up")
    limit_down_dir = os.path.join(DATA_DIR, "limit_down")
    explode_dir = os.path.join(DATA_DIR, "explode")

    # 检查目录是否存在
    for dir_path in [limit_up_dir, limit_down_dir, explode_dir]:
        if not os.path.exists(dir_path):
            print(f"警告: 目录不存在，将创建: {dir_path}")
            os.makedirs(dir_path, exist_ok=True)

    # 收集所有日期的JSON文件
    dates_with_data = set()

    # 遍历涨停目录
    for filename in os.listdir(limit_up_dir):
        if filename.endswith('.json'):
            date = filename.replace('.json', '')
            dates_with_data.add(date)

    # 需要重新获取的日期列表
    dates_to_refetch = []
    stats = {'total': 0, 'to_refetch': 0, 'already_complete': 0}

    print(f"=" * 60)
    print(f"数据完整性检查")
    print(f"=" * 60)

    # 检查每个日期的数据完整性
    for date in sorted(dates_with_data):
        stats['total'] += 1

        limit_up_file = os.path.join(limit_up_dir, f"{date}.json")
        limit_down_file = os.path.join(limit_down_dir, f"{date}.json")
        explode_file = os.path.join(explode_dir, f"{date}.json")

        limit_up_count = 0
        limit_down_count = 0
        explode_count = 0
        issues = []

        # 检查涨停数据
        if os.path.exists(limit_up_file):
            try:
                with open(limit_up_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    limit_up_count = data.get('count', 0)
                    if limit_up_count == 0:
                        issues.append("涨停为0")
            except Exception as e:
                issues.append(f"涨停文件损坏: {e}")
        else:
            issues.append("涨停文件缺失")

        # 检查跌停数据
        if os.path.exists(limit_down_file):
            try:
                with open(limit_down_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    limit_down_count = data.get('count', 0)
                    if limit_down_count == 0:
                        issues.append("跌停为0")
            except Exception as e:
                issues.append(f"跌停文件损坏: {e}")
        else:
            issues.append("跌停文件缺失")

        # 检查炸板数据
        if os.path.exists(explode_file):
            try:
                with open(explode_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    explode_count = data.get('count', 0)
                    if explode_count == 0:
                        issues.append("炸板为0")
            except Exception as e:
                issues.append(f"炸板文件损坏: {e}")
        else:
            issues.append("炸板文件缺失")

        # 如果有问题，加入重新获取列表
        if issues:
            dates_to_refetch.append(date)
            stats['to_refetch'] += 1
            print(f"[{date}] 数据不完整: {', '.join(issues)}")
            print(f"  涨停: {limit_up_count}只, 跌停: {limit_down_count}只, 炸板: {explode_count}只")
        else:
            stats['already_complete'] += 1
            print(f"[{date}] 数据完整: 涨停{limit_up_count}只, 跌停{limit_down_count}只, 炸板{explode_count}只")

    # 输出统计
    print(f"\n{'=' * 60}")
    print(f"检查完成!")
    print(f"总检查日期: {stats['total']}天")
    print(f"数据完整: {stats['already_complete']}天")
    print(f"需要重取: {stats['to_refetch']}天")

    if dates_to_refetch:
        print(f"\n需要重新获取的日期: {', '.join(dates_to_refetch)}")

        # 询问是否继续
        response = input(f"\n是否重新获取这些日期的数据? (y/N): ").strip().lower()
        if response != 'y':
            print("操作已取消")
            return

        # 开始重新获取
        refetch_data(dates_to_refetch)
    else:
        print("所有数据都完整，无需重新获取")


def refetch_data(dates_to_refetch):
    """
    重新获取指定日期的数据

    Args:
        dates_to_refetch: 需要重新获取的日期列表
    """
    fetcher = ZhituAPIFetcher()

    print(f"\n{'=' * 60}")
    print(f"开始重新获取数据")
    print(f"总计: {len(dates_to_refetch)} 天")
    print(f"{'=' * 60}")

    success_count = 0
    fail_count = 0

    for i, date in enumerate(dates_to_refetch, 1):
        print(f"\n[{i}/{len(dates_to_refetch)}] {date}")

        # 获取涨停
        print("  - 涨停股池:", end=" ")
        limit_up = fetcher.fetch_limit_up_pool(date)
        if limit_up:
            print(f"{len(limit_up)}只 [OK]")
            filename = f"{DATA_DIR}/limit_up/{date}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({"date": date, "count": len(limit_up), "data": limit_up}, f, ensure_ascii=False)
            success_count += 1
        else:
            print("无数据 [FAIL]")
            fail_count += 1

        # 请求间隔
        from time import sleep
        sleep(0.2)

        # 获取跌停
        print("  - 跌停股池:", end=" ")
        limit_down = fetcher.fetch_limit_down_pool(date)
        if limit_down:
            print(f"{len(limit_down)}只 [OK]")
            filename = f"{DATA_DIR}/limit_down/{date}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({"date": date, "count": len(limit_down), "data": limit_down}, f, ensure_ascii=False)
        else:
            print("无数据 [FAIL]")

        sleep(0.2)

        # 获取炸板
        print("  - 炸板股池:", end=" ")
        explode = fetcher.fetch_explode_pool(date)
        if explode:
            print(f"{len(explode)}只 [OK]")
            filename = f"{DATA_DIR}/explode/{date}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({"date": date, "count": len(explode), "data": explode}, f, ensure_ascii=False)
        else:
            print("无数据 [FAIL]")

        sleep(0.2)

    # 输出结果
    print(f"\n{'=' * 60}")
    print(f"重新获取完成!")
    print(f"{'=' * 60}")
    print(f"成功: {success_count}天")
    print(f"失败: {fail_count}天")
    print(f"{'=' * 60}")


def check_specific_date(date_str):
    """
    检查指定日期的数据完整性

    Args:
        date_str: 日期字符串 (yyyy-MM-dd)
    """
    limit_up_file = os.path.join(DATA_DIR, "limit_up", f"{date_str}.json")
    limit_down_file = os.path.join(DATA_DIR, "limit_down", f"{date_str}.json")
    explode_file = os.path.join(DATA_DIR, "explode", f"{date_str}.json")

    print(f"=" * 60)
    print(f"检查日期: {date_str}")
    print(f"=" * 60)

    files_to_check = [
        ("涨停", limit_up_file),
        ("跌停", limit_down_file),
        ("炸板", explode_file),
    ]

    all_ok = True
    for name, filepath in files_to_check:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    count = data.get('count', 0)
                    status = "[OK]" if count > 0 else "[FAIL] (数据为0)"
                    if count == 0:
                        all_ok = False
                    print(f"{name}: {count}只 {status}")
            except Exception as e:
                print(f"{name}: 文件损坏 [FAIL] ({e})")
                all_ok = False
        else:
            print(f"{name}: 文件缺失 [FAIL]")
            all_ok = False

    print(f"\n结论: {'数据完整' if all_ok else '数据不完整，需要重新获取'}")
    return all_ok


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="数据完整性检查脚本 - 自动检测并重新获取不完整的数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 检查所有数据并自动重新获取不完整的数据
  python check_and_refetch.py

  # 检查指定日期
  python check_and_refetch.py --date 2024-01-15

  # 仅检查不自动重取（dry-run模式）
  python check_and_refetch.py --check-only
        """
    )
    parser.add_argument("--date", type=str, help="检查指定日期 (yyyy-MM-dd)")
    parser.add_argument("--check-only", action="store_true", help="仅检查，不自动重取")
    parser.add_argument("--dir", type=str, default=DATA_DIR, help=f"数据目录 (默认: {DATA_DIR})")

    args = parser.parse_args()

    # 更新数据目录
    if args.dir:
        DATA_DIR = args.dir

    # 检查指定日期
    if args.date:
        check_specific_date(args.date)
    # 仅检查模式
    elif args.check_only:
        # 修改函数不询问直接退出
        original_input = input
        def mock_input(prompt):
            print("Dry-run模式，不执行重取")
            return 'n'
        globals()['input'] = mock_input
        check_and_refetch_data()
        globals()['input'] = original_input
    else:
        # 完整检查并自动重取
        check_and_refetch_data()
