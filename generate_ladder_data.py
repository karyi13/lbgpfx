# -*- coding: utf-8 -*-
"""
将 data 文件夹的 JSON 数据转换为 JavaScript 变量文件
"""

import json
import os
from datetime import datetime


def load_json_file(filepath):
    """加载 JSON 文件，处理不同的数据结构"""
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # 如果数据有 data 字段，提取 data；否则返回整个对象
            if isinstance(data, dict) and 'data' in data:
                return data['data']
            return data if isinstance(data, list) else []
    return []


def generate_javascript_data(data_dir):
    """生成 JavaScript 数据文件内容"""

    merged_data = {}

    # 定义数据类型目录
    data_types = ['limit_up', 'limit_down', 'explode']

    # 扫描 history 目录
    history_dir = os.path.join(data_dir, 'history')
    for data_type in data_types:
        type_dir = os.path.join(history_dir, data_type)
        if os.path.exists(type_dir):
            for filename in os.listdir(type_dir):
                if filename.endswith('.json'):
                    date_str = filename.replace('.json', '')

                    if date_str not in merged_data:
                        merged_data[date_str] = {}

                    filepath = os.path.join(type_dir, filename)
                    merged_data[date_str][data_type] = load_json_file(filepath)

    # 扫描 today 目录
    today_dir = os.path.join(data_dir, 'today')
    if os.path.exists(today_dir):
        for filename in os.listdir(today_dir):
            if filename.endswith('.json'):
                # 解析文件名: limit_up_2026-02-03.json
                parts = filename.replace('.json', '').split('_')
                if len(parts) >= 3:
                    date_str = '_'.join(parts[2:])  # 2026-02-03
                    data_type = '_'.join(parts[:2])  # limit_up

                    if date_str not in merged_data:
                        merged_data[date_str] = {}

                    filepath = os.path.join(today_dir, filename)
                    merged_data[date_str][data_type] = load_json_file(filepath)

    # 按日期排序
    sorted_dates = sorted(merged_data.keys(), reverse=True)
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # 构建 JavaScript 输出
    js_content = """/**
 * 连板天梯图数据
 * 自动生成时间: """ + timestamp + """
 */

const ladderData = {
"""

    # 将数据按日期添加
    for date_str in sorted_dates:
        date_data = merged_data[date_str]
        js_data = json.dumps(date_data, ensure_ascii=False, indent=2)
        js_content += f'\n    "{date_str}": {js_data},'

    js_content = js_content.rstrip(',')  # 移除最后一个逗号
    js_content += "\n};\n"

    # 添加获取日期列表的助手函数
    js_content += """
/**
 * 获取所有可用日期列表（从新到旧）
 */
function getDateList() {
    return Object.keys(ladderData).sort((a, b) => new Date(b) - new Date(a));
}

/**
 * 获取指定日期的数据
 */
function getDataByDate(date) {
    return ladderData[date] || null;
}

/**
 * 获取日期的涨停数据
 */
function getLimitUpData(date) {
    const data = getDataByDate(date);
    return data ? (data.limit_up || []) : [];
}

/**
 * 获取日期的跌停数据
 */
function getLimitDownData(date) {
    const data = getDataByDate(date);
    return data ? (data.limit_down || []) : [];
}

/**
 * 获取日期的炸板数据
 */
function getExplodeData(date) {
    const data = getDataByDate(date);
    return data ? (data.explode || []) : [];
}
"""

    return js_content


def main():
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(script_dir, 'data')
    output_file = os.path.join(script_dir, 'ladder_data.js')

    print(f"Scanning data directory: {data_dir}")
    print("Processing data...")

    try:
        js_content = generate_javascript_data(data_dir)

        # 写入 JavaScript 文件
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(js_content)

        # 输出统计信息
        with open(output_file, 'r', encoding='utf-8') as f:
            file_size = len(f.read())

        print(f"\nData conversion completed!")
        print(f"  Output file: {output_file}")
        print(f"  File size: {file_size / 1024:.1f} KB")
        print(f"\nAdd this to ladder.html:")
        print(f'  <script src="ladder_data.js"></script>')

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
