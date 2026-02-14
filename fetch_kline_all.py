# -*- coding: utf-8 -*-
"""
获取所有A股标的2024年10月至今的K线数据
使用AKShare获取数据
"""

import os
import time
import pandas as pd
import akshare as ak
from datetime import datetime
from typing import List, Dict
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

warnings.filterwarnings('ignore')

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('fetch_kline_all.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 数据保存目录
KLINE_DIR = "data/kline_202410_to_now"

# 日期范围
START_DATE = "20241001"  # 2024年10月1日
TODAY = datetime.now().strftime("%Y%m%d")

# 请求间隔（秒）
REQUEST_INTERVAL = 0.1

# 并发线程数
MAX_WORKERS = 5

# 失败重试次数
MAX_RETRIES = 3


def get_all_stocks() -> pd.DataFrame:
    """
    获取所有A股股票列表

    Returns:
        股票列表DataFrame，包含股票代码和名称
    """
    logger.info("=" * 60)
    logger.info("获取A股股票列表...")
    logger.info("=" * 60)

    all_stocks = []

    try:
        # 方法1：使用 ak.stock_zh_a_spot_em() 获取全部A股
        logger.info("从东方财富获取A股列表...")
        sz_list = ak.stock_zh_a_spot_em()
        logger.info(f"获取到 {len(sz_list)} 只股票")

        # 处理所有股票
        for _, row in sz_list.iterrows():
            code = str(row['代码']).zfill(6)
            name = row['名称']

            # 添加市场后缀
            if code.startswith('6'):  # 沪市
                code_suffix = code + '.SH'
                if code.startswith('688'):
                    market = '科创板'
                else:
                    market = '沪市主板'
            elif code.startswith('0') or code.startswith('3'):  # 深市
                code_suffix = code + '.SZ'
                if code.startswith('300'):
                    market = '创业板'
                elif code.startswith('000') or code.startswith('001'):
                    market = '深市主板'
                else:
                    market = '其他'
            elif code.startswith('4') or code.startswith('8'):  # 北交所
                code_suffix = code + '.BJ'
                market = '北交所'
            else:
                code_suffix = code
                market = '其他'

            all_stocks.append({'code': code_suffix, 'name': name, 'market': market})

        df = pd.DataFrame(all_stocks)
        df = df.drop_duplicates(subset=['code'])

        # 统计各市场数量
        market_counts = df['market'].value_counts()
        logger.info("\n市场分布:")
        for market, count in market_counts.items():
            logger.info(f"  {market}: {count} 只")

        logger.info("=" * 60)
        logger.info(f"股票总数: {len(df)} 只")
        logger.info("=" * 60)

        return df

    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        import traceback
        traceback.print_exc()
        return pd.DataFrame()


def fetch_stock_kline(stock_info: Dict, start_date: str = None, end_date: str = None, retry: int = 0) -> Dict:
    """
    获取单只股票的K线数据

    Args:
        stock_info: 股票信息字典，含code和name
        start_date: 起始日期（格式：YYYYMMDD），为空则使用全局START_DATE
        end_date: 结束日期（格式：YYYYMMDD），为空则使用全局TODAY
        retry: 重试次数

    Returns:
        结果字典，包含状态、股票代码、数据
    """
    stock_code = stock_info['code']
    stock_name = stock_info['name']

    # 使用传入的日期或全局日期
    req_start = start_date or START_DATE
    req_end = end_date or TODAY

    try:
        # AKShare股票代码格式（去除后缀）
        clean_code = stock_code.replace('.SH', '').replace('.SZ', '').replace('.BJ', '')

        # 获取K线数据
        df = ak.stock_zh_a_hist(
            symbol=clean_code,
            period="daily",
            start_date=req_start,
            end_date=req_end,
            adjust="qfq"  # 前复权
        )

        if df is None or len(df) == 0:
            return {
                'success': False,
                'code': stock_code,
                'name': stock_name,
                'error': '无数据'
            }

        # 添加股票代码和名称
        df['stock_code'] = stock_code
        df['stock_name'] = stock_name

        return {
            'success': True,
            'code': stock_code,
            'name': stock_name,
            'data': df,
            'count': len(df),
            'start_date': req_start,
            'end_date': req_end
        }

    except Exception as e:
        error_msg = str(e)
        logger.warning(f"获取 {stock_name}({stock_code}) 数据失败: {error_msg}")

        # 如果是限流错误，等待一段时间
        if '请勿频繁请求' in error_msg or '请求过快' in error_msg:
            wait_time = 5 + retry * 5
            logger.warning(f"遇到限流，等待 {wait_time} 秒后重试...")
            time.sleep(wait_time)

        return {
            'success': False,
            'code': stock_code,
            'name': stock_name,
            'error': error_msg
        }


def save_stock_data(result: Dict, output_dir: str):
    """
    保存单只股票的K线数据

    Args:
        result: fetch_stock_kline返回的结果字典
        output_dir: 输出目录
    """
    if not result['success']:
        return False

    try:
        stock_code = result['code'].replace('.', '_')
        file_path = os.path.join(output_dir, f"{stock_code}.csv")

        df = result['data']
        df.to_csv(file_path, index=False, encoding='utf-8-sig')

        return True

    except Exception as e:
        logger.error(f"保存数据失败: {e}")
        return False


def fetch_all_klines():
    """
    获取所有股票的K线数据
    """
    # 创建保存目录
    os.makedirs(KLINE_DIR, exist_ok=True)

    # 获取股票列表
    stock_list = get_all_stocks()

    if len(stock_list) == 0:
        logger.error("没有获取到股票列表")
        return

    # 保存股票列表
    stock_list.to_csv(os.path.join(KLINE_DIR, "stock_list.csv"), index=False, encoding='utf-8-sig')
    logger.info(f"股票列表已保存: {os.path.join(KLINE_DIR, 'stock_list.csv')}")

    # 统计
    total = len(stock_list)
    success_count = 0
    fail_count = 0
    failed_stocks = []

    logger.info("=" * 60)
    logger.info(f"开始获取K线数据（{total} 只股票）")
    logger.info(f"时间范围: {START_DATE} - {TODAY}")
    logger.info(f"并发线程: {MAX_WORKERS}")
    logger.info("=" * 60)

    start_time = time.time()

    # 使用线程池并发获取数据
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # 提交所有任务
        future_to_stock = {
            executor.submit(fetch_stock_kline, stock_info): stock_info
            for _, stock_info in stock_list.iterrows()
        }

        # 处理完成的任务
        for i, future in enumerate(as_completed(future_to_stock), 1):
            stock_info = future_to_stock[future]
            stock_name = stock_info['name']
            stock_code = stock_info['code']

            try:
                result = future.result()

                if result['success']:
                    # 保存数据
                    if save_stock_data(result, KLINE_DIR):
                        success_count += 1
                        logger.info(f"[{i}/{total}] {stock_name}({stock_code}) - 成功 ({result['count']}条)")
                    else:
                        fail_count += 1
                        failed_stocks.append(stock_info)
                        logger.warning(f"[{i}/{total}] {stock_name}({stock_code}) - 保存失败")
                else:
                    fail_count += 1
                    failed_stocks.append(stock_info)
                    logger.warning(f"[{i}/{total}] {stock_name}({stock_code}) - 失败: {result['error']}")

            except Exception as e:
                fail_count += 1
                failed_stocks.append(stock_info)
                logger.error(f"[{i}/{total}] {stock_name}({stock_code}) - 异常: {e}")

            # 每处理10只股票输出进度
            if i % 10 == 0:
                elapsed = time.time() - start_time
                speed = i / elapsed if elapsed > 0 else 0
                remaining = (total - i) / speed if speed > 0 else 0
                logger.info(f"进度: {i}/{total} ({i/total*100:.1f}%) - " +
                           f"成功: {success_count}, 失败: {fail_count} - " +
                           f"速度: {speed:.1f} 只/秒 - 预计剩余: {remaining:.0f} 秒")

    # 保存失败列表
    if failed_stocks:
        failed_df = pd.DataFrame(failed_stocks)
        failed_file = os.path.join(KLINE_DIR, "failed_stocks.csv")
        failed_df.to_csv(failed_file, index=False, encoding='utf-8-sig')
        logger.info(f"失败列表已保存: {failed_file}")

    # 合并为一个大文件（可选）
    try:
        logger.info("合并K线数据...")
        all_data = []
        csv_files = [f for f in os.listdir(KLINE_DIR) if f.endswith('.csv') and f != 'stock_list.csv' and f != 'failed_stocks.csv']

        for csv_file in csv_files:
            try:
                df = pd.read_csv(os.path.join(KLINE_DIR, csv_file))
                all_data.append(df)
            except Exception as e:
                logger.warning(f"读取 {csv_file} 失败: {e}")
                continue

        if all_data:
            merged_df = pd.concat(all_data, ignore_index=True)
            merged_file = os.path.join(KLINE_DIR, "all_stocks_kline.csv")
            merged_df.to_csv(merged_file, index=False, encoding='utf-8-sig')
            logger.info(f"合并数据已保存: {merged_file} ({len(merged_df)} 行)")
    except Exception as e:
        logger.error(f"合并数据失败: {e}")

    # 输出统计
    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("K线数据获取完成!")
    logger.info("=" * 60)
    logger.info(f"股票总数: {total}")
    logger.info(f"成功: {success_count} ({success_count/total*100:.1f}%)")
    logger.info(f"失败: {fail_count} ({fail_count/total*100:.1f}%)")
    logger.info(f"耗时: {elapsed_time:.1f} 秒 ({elapsed_time/60:.1f} 分钟)")
    logger.info(f"平均速度: {total/elapsed_time:.2f} 只/秒")
    logger.info(f"数据目录: {KLINE_DIR}")
    logger.info("=" * 60)


def merge_all_klines():
    """
    合并所有K线数据为一个文件
    """
    logger.info("开始合并K线数据...")

    all_data = []
    csv_files = [f for f in os.listdir(KLINE_DIR) if f.endswith('.csv') and f != 'stock_list.csv' and f != 'failed_stocks.csv' and f != 'all_stocks_kline.csv']

    for i, csv_file in enumerate(csv_files, 1):
        try:
            df = pd.read_csv(os.path.join(KLINE_DIR, csv_file))
            all_data.append(df)

            if i % 100 == 0:
                logger.info(f"已读取 {i}/{len(csv_files)} 个文件")
        except Exception as e:
            logger.warning(f"读取 {csv_file} 失败: {e}")
            continue

    if all_data:
        merged_df = pd.concat(all_data, ignore_index=True)
        merged_file = os.path.join(KLINE_DIR, "all_stocks_kline.csv")
        merged_df.to_csv(merged_file, index=False, encoding='utf-8-sig')
        logger.info(f"合并完成: {merged_file} ({len(merged_df)} 行, {len(csv_files)} 个文件)")


def update_to_latest():
    """
    更新已有数据到最新日期
    增量更新：只获取新日期的数据并合并
    """
    logger.info("=" * 60)
    logger.info("增量更新K线数据...")
    logger.info("=" * 60)

    # 检查数据目录
    if not os.path.exists(KLINE_DIR):
        logger.error(f"数据目录不存在: {KLINE_DIR}")
        logger.info("请先运行完整数据获取：python fetch_kline_all.py")
        return

    # 获取股票列表（从已有CSV或重新获取）
    stock_list_path = os.path.join(KLINE_DIR, "stock_list.csv")
    if os.path.exists(stock_list_path):
        stock_list = pd.read_csv(stock_list_path)
        logger.info(f"从文件加载股票列表: {len(stock_list)} 只")
    else:
        stock_list = get_all_stocks()
        if len(stock_list) == 0:
            return

    # 查找每只股票的最新日期
    stock_last_dates = {}
    csv_files = [f for f in os.listdir(KLINE_DIR) if f.endswith('.csv') and f not in ['stock_list.csv', 'failed_stocks.csv', 'all_stocks_kline.csv']]

    logger.info(f"找到 {len(csv_files)} 个股票文件")

    # 统计需要更新的股票
    update_list = []
    for _, stock_info in stock_list.iterrows():
        stock_code = stock_info['code']
        stock_file = stock_code.replace('.', '_') + '.csv'

        if stock_file in csv_files:
            try:
                # 读取现有数据，获取最新日期
                df_existing = pd.read_csv(os.path.join(KLINE_DIR, stock_file))
                if len(df_existing) > 0:
                    # AKShare的日期列名是'日期'
                    if '日期' in df_existing.columns:
                        last_date = pd.to_datetime(df_existing['日期']).max()
                        # 只需要获取新数据：从最新日期的下一天开始
                        next_date = last_date + pd.Timedelta(days=1)
                        start_str = next_date.strftime('%Y%m%d')

                        # 只有当有新数据需要获取时才加入更新列表
                        if start_str <= TODAY:
                            update_list.append({
                                'code': stock_code,
                                'name': stock_info['name'],
                                'data_start': last_date.strftime('%Y-%m-%d'),
                                'fetch_start': start_str,
                                'fetch_end': TODAY
                            })
            except Exception as e:
                logger.warning(f"读取 {stock_file} 失败: {e}")
        else:
            # 没有文件，需要全量获取
            update_list.append({
                'code': stock_code,
                'name': stock_info['name'],
                'data_start': '无',
                'fetch_start': START_DATE,
                'fetch_end': TODAY
            })

    logger.info("=" * 60)
    logger.info(f"需要更新的股票: {len(update_list)} 只")
    logger.info("=" * 60)

    if len(update_list) == 0:
        logger.info("所有数据已是最新，无需更新！")
        return

    # 显示需要更新的股票列表
    logger.info("\n需要更新的股票示例（前10只）:")
    for stock in update_list[:10]:
        logger.info(f"  {stock['name']}({stock['code']}) - 数据截止: {stock['data_start']} -> 更新到: {stock['fetch_end']}")

    start_time = time.time()
    total = len(update_list)
    updated_count = 0
    failed_count = 0

    # 并发更新
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_stock = {
            executor.submit(fetch_stock_kline, stock_info, stock_info['fetch_start'], stock_info['fetch_end']): stock_info
            for stock_info in update_list
        }

        for i, future in enumerate(as_completed(future_to_stock), 1):
            update_info = future_to_stock[future]
            stock_name = update_info['name']
            stock_code = update_info['code']

            try:
                result = future.result()

                if result['success']:
                    # 保存更新后的数据
                    stock_file = stock_code.replace('.', '_') + '.csv'
                    existing_file = os.path.join(KLINE_DIR, stock_file)

                    # 读取现有数据
                    existing_data = None
                    if os.path.exists(existing_file):
                        try:
                            existing_data = pd.read_csv(existing_file)
                        except:
                            pass

                    # 合并新旧数据
                    if existing_data is not None and len(existing_data) > 0:
                        # 合并并去重（按日期去重，保留新数据）
                        merged = pd.concat([existing_data, result['data']], ignore_index=True)
                        merged['日期'] = pd.to_datetime(merged['日期'])
                        merged = merged.drop_duplicates(subset=['日期'], keep='last')
                        merged = merged.sort_values('日期')
                        result['data'] = merged

                    # 保存
                    try:
                        result['data'].to_csv(existing_file, index=False, encoding='utf-8-sig')
                        updated_count += 1
                        logger.info(f"[{i}/{total}] 更新 {stock_name}({stock_code}) - 成功 (现有{update_info['data_start']} -> 新增{result['count']}行)")
                    except Exception as e:
                        failed_count += 1
                        logger.warning(f"[{i}/{total}] 保存 {stock_name}({stock_code}) 失败: {e}")
                else:
                    failed_count += 1
                    logger.warning(f"[{i}/{total}] {stock_name}({stock_code}) - 失败: {result['error']}")

            except Exception as e:
                failed_count += 1
                logger.error(f"[{i}/{total}] {stock_name}({stock_code}) - 异常: {e}")

            if i % 10 == 0:
                elapsed = time.time() - start_time
                speed = i / elapsed if elapsed > 0 else 0
                remaining = (total - i) / speed if speed > 0 else 0
                logger.info(f"进度: {i}/{total} ({i/total*100:.1f}%) - " +
                           f"成功: {updated_count}, 失败: {failed_count} - " +
                           f"速度: {speed:.1f} 只/秒 - 预计剩余: {remaining:.0f} 秒")

    # 重新合并所有数据
    logger.info("\n重新合并所有数据...")
    merge_all_klines()

    # 输出统计
    elapsed_time = time.time() - start_time
    logger.info("=" * 60)
    logger.info("增量更新完成!")
    logger.info("=" * 60)
    logger.info(f"处理总数: {total}")
    logger.info(f"成功: {updated_count} ({updated_count/total*100:.1f}%)")
    logger.info(f"失败: {failed_count} ({failed_count/total*100:.1f}%)")
    logger.info(f"耗时: {elapsed_time:.1f} 秒 ({elapsed_time/60:.1f} 分钟)")
    logger.info("=" * 60)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="获取所有A股标的K线数据，支持增量更新",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 完整获取所有股票K线数据（从指定起始日期到今天）
  python fetch_kline_all.py

  # 增量更新到最新日期（自动检测并更新）
  python fetch_kline_all.py --update

  # 仅合并已有数据
  python fetch_kline_all.py --merge-only

  # 指定线程数
  python fetch_kline_all.py --workers 10

  # 指定起始日期（完整获取模式）
  python fetch_kline_all.py --start 20240101

  # 指定日期范围进行完整获取
  python fetch_kline_all.py --start 20240101 --end 20241231
        """
    )
    parser.add_argument("--update", action="store_true", help="增量更新模式（自动更新到最新日期）")
    parser.add_argument("--merge-only", action="store_true", help="仅合并已有数据")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS, help=f"并发线程数（默认{MAX_WORKERS}）")
    parser.add_argument("--start", type=str, default=START_DATE, help="起始日期（格式：YYYYMMDD）")
    parser.add_argument("--end", type=str, default=None, help="结束日期（格式：YYYYMMDD），为空则使用今天")

    args = parser.parse_args()

    # 更新全局变量
    MAX_WORKERS = args.workers
    START_DATE = args.start
    TODAY = args.end if args.end else datetime.now().strftime("%Y%m%d")

    if args.update:
        # 增量更新模式
        update_to_latest()
    elif args.merge_only:
        # 仅合并模式
        merge_all_klines()
    else:
        # 完整获取模式
        logger.info(f"完整获取模式: {START_DATE} - {TODAY}")
        fetch_all_klines()
