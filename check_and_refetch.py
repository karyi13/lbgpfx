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
# 已核查标记文件（记录已经核查且数据确实为0的日期）
CHECKED_MARKER_FILE = "data/.checked_dates.json"


def load_checked_markers():
    """
    加载已核查标记

    Returns:
        dict: {date: reason} 格式，reason说明为什么跳过（如"跌停接口404"）
    """
    if os.path.exists(CHECKED_MARKER_FILE):
        try:
            with open(CHECKED_MARKER_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"警告: 无法加载标记文件: {e}")
    return {}


def save_checked_markers(markers):
    """
    保存已核查标记

    Args:
        markers: {date: reason} 字典
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(CHECKED_MARKER_FILE), exist_ok=True)
        with open(CHECKED_MARKER_FILE, 'w', encoding='utf-8') as f:
            json.dump(markers, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"警告: 无法保存标记文件: {e}")


def mark_date_checked(date, reason):
    """
    标记日期为已核查

    Args:
        date: 日期字符串
        reason: 标记原因（如"跌停接口404"）
    """
    markers = load_checked_markers()
    markers[date] = reason
    save_checked_markers(markers)
    print(f"  [标记] {date} 已标记为: {reason}")


def check_and_refetch_data():
    """
    检查并重新获取不完整的数据
    """
    # 确保目录存在
    if not os.path.exists(DATA_DIR):
        print(f"错误: 数据目录不存在: {DATA_DIR}")
        return

    # 加载已核查标记
    checked_dates = load_checked_markers()

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
    stats = {'total': 0, 'to_refetch': 0, 'already_complete': 0, 'skipped_checked': 0}

    print(f"=" * 60)
    print(f"数据完整性检查")
    print(f"=" * 60)

    # 检查每个日期的数据完整性
    for date in sorted(dates_with_data):
        # 跳过已核查标记的日期
        if date in checked_dates:
            stats['skipped_checked'] += 1
            print(f"[{date}] 已核查过，跳过 (标记: {checked_dates[date]})")
            continue

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
    print(f"跳过已核查: {stats['skipped_checked']}天")

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
    still_failed_dates = []  # 记录仍然失败的日期

    for i, date in enumerate(dates_to_refetch, 1):
        print(f"\n[{i}/{len(dates_to_refetch)}] {date}")

        limit_up_count = 0
        limit_down_count = 0
        explode_count = 0

        # 获取涨停
        print("  - 涨停股池:", end=" ")
        limit_up = fetcher.fetch_limit_up_pool(date)
        if limit_up:
            print(f"{len(limit_up)}只 [OK]")
            filename = f"{DATA_DIR}/limit_up/{date}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({"date": date, "count": len(limit_up), "data": limit_up}, f, ensure_ascii=False)
            limit_up_count = len(limit_up)
        else:
            print("无数据 [FAIL]")

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
            limit_down_count = len(limit_down)
        else:
            print("无数据 [FAIL]")
            # 明确记录为0
            limit_down_count = 0

        sleep(0.2)

        # 获取炸板
        print("  - 炸板股池:", end=" ")
        explode = fetcher.fetch_explode_pool(date)
        if explode:
            print(f"{len(explode)}只 [OK]")
            filename = f"{DATA_DIR}/explode/{date}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump({"date": date, "count": len(explode), "data": explode}, f, ensure_ascii=False)
            explode_count = len(explode)
        else:
            print("无数据 [FAIL]")
            # 明确记录为0
            explode_count = 0

        sleep(0.2)

        # 判断是否仍有问题：如果任何一个池的数据为0，就视为失败
        has_issue = (limit_up_count == 0 or limit_down_count == 0 or explode_count == 0)

        if not has_issue:
            success_count += 1
        else:
            fail_count += 1
            still_failed_dates.append(date)

        # DEBUG: 打印判断结果（可删除）
        # print(f"    调试: LU={limit_up_count}, LD={limit_down_count}, EX={explode_count} -> has_issue={has_issue}")

    # 输出结果
    print(f"\n{'=' * 60}")
    print(f"重新获取完成!")
    print(f"{'=' * 60}")
    print(f"成功: {success_count}天")
    print(f"失败: {fail_count}天")
    print(f"{'=' * 60}")

    # 标记仍然失败的日期（下次不再核查）
    if still_failed_dates:
        print("\n以下日期仍然无法获取完整数据，将被标记为'已确认无数据'以免重复核查:")
        markers_to_save = {}  # 收集每个日期的具体失败原因
        for date in still_failed_dates:
            # 分析失败原因
            marker_reason = "接口无数据"

            # 尝试读取该日期的文件判断哪些接口失败
            limit_up_file = os.path.join(DATA_DIR, "limit_up", f"{date}.json")
            limit_down_file = os.path.join(DATA_DIR, "limit_down", f"{date}.json")
            explode_file = os.path.join(DATA_DIR, "explode", f"{date}.json")

            issues = []
            if os.path.exists(limit_up_file):
                try:
                    with open(limit_up_file, 'r') as f:
                        data = json.load(f)
                        if data.get('count', 0) == 0:
                            issues.append("涨停为0")
                except:
                    issues.append("涨停文件损坏")
            else:
                issues.append("涨停缺失")

            if os.path.exists(limit_down_file):
                try:
                    with open(limit_down_file, 'r') as f:
                        data = json.load(f)
                        if data.get('count', 0) == 0:
                            issues.append("跌停为0")
                except:
                    issues.append("跌停文件损坏")
            else:
                issues.append("跌停缺失")

            if os.path.exists(explode_file):
                try:
                    with open(explode_file, 'r') as f:
                        data = json.load(f)
                        if data.get('count', 0) == 0:
                            issues.append("炸板为0")
                except:
                    issues.append("炸板文件损坏")
            else:
                issues.append("炸板缺失")

            if issues:
                marker_reason = " | ".join(issues)

            print(f"  - {date}: {marker_reason}")
            markers_to_save[date] = marker_reason

        # 询问是否标记
        response = input("\n是否将这些日期标记为'已确认无数据'以免下次重复核查? (Y/n): ").strip().lower()
        if response != 'n':
            markers = load_checked_markers()
            markers.update(markers_to_save)  # 批量添加，保留已有的其他标记
            save_checked_markers(markers)
            print(f"✓ 已标记 {len(markers_to_save)} 个日期，下次将自动跳过")
        else:
            print("未标记，下次仍会核查")


def check_specific_date(date_str):
    """
    检查指定日期的数据完整性

    Args:
        date_str: 日期字符串 (yyyy-MM-dd)
    """
    # 检查是否已标记
    checked_dates = load_checked_markers()
    if date_str in checked_dates:
        print(f"=" * 60)
        print(f"检查日期: {date_str}")
        print(f"=" * 60)
        print(f"该日期已标记为: {checked_dates[date_str]}")
        print("跳过检查。如需强制检查，请先删除标记文件或使用其他日期。")
        return True  # 视为"完整"以简化返回

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
