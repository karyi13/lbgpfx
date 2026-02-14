# -*- coding: utf-8 -*-
"""
K线数据优化方案：
1. 筛选涨停股票的K线数据
2. 精简字段（只保留K线图需要的核心字段）
3. 合并为单个JSON文件供前端加载
"""

import os
import json
import csv
import shutil
from pathlib import Path
from typing import Set, Dict, List
from datetime import datetime

# 目录路径
HISTORY_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'history')
KLINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'kline_202410_to_now')
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'kline_backup')
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'kline_optimized')
OUTPUT_FILE = os.path.join(OUTPUT_DIR, 'kline_data.json')


def collect_limit_up_codes() -> Set[str]:
    """
    从历史涨停数据中收集所有涨停过的股票代码

    Returns:
        股票代码集合
    """
    print("=" * 60)
    print("步骤 1/4: 收集历史涨停股票代码...")
    print("=" * 60)

    codes = set()
    limit_up_dir = os.path.join(HISTORY_DIR, 'limit_up')

    if not os.path.exists(limit_up_dir):
        print(f"错误: 目录不存在 {limit_up_dir}")
        return codes

    # 遍历所有涨停数据文件
    json_files = [f for f in os.listdir(limit_up_dir) if f.endswith('.json')]
    print(f"找到 {len(json_files)} 个涨停数据文件")

    for filename in json_files:
        filepath = os.path.join(limit_up_dir, filename)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # 处理不同的数据结构
                if isinstance(data, dict) and 'data' in data:
                    stocks = data['data']
                elif isinstance(data, list):
                    stocks = data
                else:
                    continue

                for stock in stocks:
                    # 股票代码可能在 dm 字段中
                    code = stock.get('dm', '')
                    if code:
                        # 标准化代码（统一格式：6位数字+后缀）
                        code = normalize_code(code)
                        codes.add(code)

        except Exception as e:
            print(f"警告: 读取 {filename} 失败: {e}")

    print(f"共收集到 {len(codes)} 只涨停股票")
    print("=" * 60)

    return codes


def normalize_code(code: str) -> str:
    """标准化股票代码格式为 XXXXXX.SH 或 XXXXXX.SZ"""
    if not code:
        return code

    # 移除已存在的点
    clean = code.replace('.', '')

    # 根据前6位判断市场
    if len(clean) >= 6:
        prefix = clean[:6]
        if prefix.startswith('6'):
            return f"{prefix}.SH"
        elif prefix.startswith('0') or prefix.startswith('3'):
            return f"{prefix}.SZ"
        elif prefix.startswith('4') or prefix.startswith('8'):
            return f"{prefix}.BJ"

    # 无法判断，返回原代码
    return code


def filter_kline_files(limit_up_codes: Set[str]) -> List[str]:
    """
    筛选K线文件，只保留涨停股票

    Args:
        limit_up_codes: 涨停股票代码集合

    Returns:
        保留的文件列表
    """
    print("=" * 60)
    print("步骤 2/4: 筛选涨停股票的K线文件...")
    print("=" * 60)

    if not os.path.exists(KLINE_DIR):
        print(f"错误: K线目录不存在 {KLINE_DIR}")
        return []

    csv_files = [f for f in os.listdir(KLINE_DIR) if f.endswith('.csv') and f not in ['stock_list.csv', 'failed_stocks.csv', 'all_stocks_kline.csv']]

    print(f"原始K线文件: {len(csv_files)} 个")

    kept_files = []
    deleted_count = 0

    for filename in csv_files:
        # 文件名格式: 000001_SZ.csv
        code_str = filename.replace('.csv', '').replace('_', '.')
        stock_code = normalize_code(code_str)

        if stock_code in limit_up_codes:
            kept_files.append(filename)
        else:
            deleted_count += 1
            # 可选：删除文件
            # os.remove(os.path.join(KLINE_DIR, filename))

    print(f"保留文件: {len(kept_files)} 个")
    print(f"可删除文件: {deleted_count} 个 (未实际删除)")
    print("=" * 60)

    return kept_files


def load_and_simplify_kline(filepath: str, stock_code: str) -> List[Dict]:
    """
    加载并精简K线数据

    只保留K线图需要的核心字段：
    - date: 日期
    - open, close, high, low: 价格
    - volume: 成交量

    Args:
        filepath: CSV文件路径
        stock_code: 股票代码

    Returns:
        精简后的K线数据列表
    """
    kline_data = []

    try:
        with open(filepath, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                kline_data.append({
                    'date': row['日期'],
                    'open': float(row['开盘']),
                    'close': float(row['收盘']),
                    'low': float(row['最低']),
                    'high': float(row['最高']),
                    'volume': int(row['成交量'])
                })

        # 按日期排序
        kline_data.sort(key=lambda x: x['date'])

    except Exception as e:
        print(f"警告: 加载 {filepath} 失败: {e}")

    return kline_data


def merge_to_json(kept_files: List[str], output_file: str):
    """
    合并所有K线数据为单个JSON文件

    Args:
        kept_files: 保留的K线文件列表
        output_file: 输出JSON文件路径
    """
    print("=" * 60)
    print("步骤 3/4: 合并K线数据为JSON...")
    print("=" * 60)

    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    merged_data = {}
    total_records = 0

    for i, filename in enumerate(kept_files, 1):
        stock_code = filename.replace('.csv', '').replace('_', '.')
        stock_code_normalized = normalize_code(stock_code)

        filepath = os.path.join(KLINE_DIR, filename)

        # 加载并精简K线数据
        kline = load_and_simplify_kline(filepath, stock_code_normalized)

        if kline:
            merged_data[stock_code_normalized] = kline
            total_records += len(kline)

        if i % 100 == 0:
            print(f"处理进度: {i}/{len(kept_files)}")

    # 保存JSON文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=None)

    file_size_mb = os.path.getsize(output_file) / (1024 * 1024)

    print(f"合并完成!")
    print(f"股票数量: {len(merged_data)}")
    print(f"K线记录: {total_records} 条")
    print(f"文件大小: {file_size_mb:.1f} MB")
    print(f"输出文件: {output_file}")
    print("=" * 60)


def generate_summary(kline_dir: str, output_dir: str):
    """
    生成数据汇总报告

    Args:
        kline_dir: 原始K线目录
        output_dir: 优化后的输出目录
    """
    print("=" * 60)
    print("步骤 4/4: 生成数据汇总...")
    print("=" * 60)

    # 原始数据统计
    original_files = [f for f in os.listdir(kline_dir) if f.endswith('.csv') and
                     f not in ['stock_list.csv', 'failed_stocks.csv', 'all_stocks_kline.csv']]
    original_size = sum(os.path.getsize(os.path.join(kline_dir, f)) for f in original_files)

    # 优化后统计
    if os.path.exists(output_dir):
        json_file = os.path.join(output_dir, 'kline_data.json')
        if os.path.exists(json_file):
            optimized_size = os.path.getsize(json_file)

            # 加载JSON统计
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                stock_count = len(data)
                record_count = sum(len(v) for v in data.values())

    print(f"原始数据:")
    print(f"  文件数量: {len(original_files)}")
    print(f"  总大小: {original_size / (1024 * 1024):.1f} MB")
    print(f"优化后数据:")
    print(f"  股票数量: {stock_count}")
    print(f"  K线记录: {record_count} 条")
    print(f"  总大小: {optimized_size / (1024 * 1024):.1f} MB")
    print(f"压缩比: {original_size / optimized_size:.1f}x")
    print("=" * 60)


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("K线数据优化工具")
    print("执行步骤:")
    print("  1. 收集历史涨停股票代码")
    print("  2. 筛选涨停股票的K线文件")
    print("  3. 精简字段并合并为JSON")
    print("  4. 生成数据汇总报告")
    print("=" * 60 + "\n")

    # 步骤1: 收集涨停股票代码
    limit_up_codes = collect_limit_up_codes()

    if not limit_up_codes:
        print("错误: 未找到涨停股票数据")
        return

    # 步骤2: 筛选K线文件
    kept_files = filter_kline_files(limit_up_codes)

    if not kept_files:
        print("错误: 未匹配到K线文件")
        return

    # 步骤3: 合并为JSON
    merge_to_json(kept_files, OUTPUT_FILE)

    # 步骤4: 生成汇总
    generate_summary(KLINE_DIR, OUTPUT_DIR)

    print("\n优化完成!")
    print(f"\n下一步:")
    print(f"  1. 查看优化后的数据: {OUTPUT_FILE}")
    print(f"  2. 在 HTML 或服务器中使用此JSON文件")


if __name__ == '__main__':
    main()
