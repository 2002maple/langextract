#!/usr/bin/env python3
"""
从 extracted_data.jsonl 中提取偿付能力关键指标

提取的指标包括：
- 核心偿付能力充足率
- 综合偿付能力充足率
- 实际资本
- 最低资本
- 认可资产
- 认可负债
等
"""

import json
import pandas as pd
from pathlib import Path


def extract_solvency_indicators(jsonl_file: str) -> pd.DataFrame:
    """提取偿付能力关键指标."""

    # 关键指标的名称模式
    key_indicators = {
        "核心偿付能力充足率": ["核心偿付能力充足率", "核心资本充足率", "核心偿付能力"],
        "综合偿付能力充足率": ["综合偿付能力充足率", "综合资本充足率", "综合偿付能力"],
        "实际资本": ["实际资本"],
        "核心一级资本": ["核心一级资本", "核心资本"],
        "最低资本": ["最低资本"],
        "认可资产": ["认可资产"],
        "认可负债": ["认可负债"],
        "核心偿付能力溢额": ["核心偿付能力溢额"],
        "综合偿付能力溢额": ["综合偿付能力溢额"],
    }

    results = []

    # 读取 JSONL 文件
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            report = json.loads(line)

            company = report.get('company_name', 'N/A')
            period = report.get('report_period', 'N/A')
            pdf_file = report.get('pdf_file', 'N/A')

            # 存储该公司的指标
            indicators = {
                'pdf_file': pdf_file,
                'company_name': company,
                'report_period': period,
            }

            # 遍历所有表格
            for table in report.get('solvency_tables', []):
                table_title = table.get('table_title', '')

                # 只处理偿付能力相关的表格
                if not any(keyword in table_title for keyword in
                          ['偿付能力', '实际资本', '最低资本', '认可资产', '认可负债']):
                    continue

                # 提取表格中的指标
                for row in table.get('rows', []):
                    # 遍历所有关键指标
                    for indicator_name, patterns in key_indicators.items():
                        # 检查是否匹配任何模式
                        for pattern in patterns:
                            # 检查所有可能的列名
                            row_name = (
                                row.get('指标名称', '') or
                                row.get('项目', '') or
                                row.get('指标', '') or
                                row.get('名称', '')
                            )

                            if pattern in row_name:
                                # 提取数值
                                value = (
                                    row.get('本季度数', '') or
                                    row.get('期末数', '') or
                                    row.get('本期数', '') or
                                    row.get('数值', '') or
                                    row.get('本年度累计数', '')
                                )

                                # 如果找到了值，存储
                                if value and value != '':
                                    # 使用标准化的指标名称
                                    indicators[indicator_name] = value
                                    break

            # 添加到结果列表
            if len(indicators) > 3:  # 至少有一些指标数据
                results.append(indicators)

    # 转换为 DataFrame
    df = pd.DataFrame(results)

    # 重新排列列顺序
    base_columns = ['pdf_file', 'company_name', 'report_period']
    indicator_columns = [col for col in df.columns if col not in base_columns]
    df = df[base_columns + sorted(indicator_columns)]

    return df


def extract_solvency_ratio_trends(jsonl_file: str) -> pd.DataFrame:
    """提取偿付能力充足率的时间序列数据（本季度、上季度、上年同期）."""

    results = []

    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            report = json.loads(line)

            company = report.get('company_name', 'N/A')
            period = report.get('report_period', 'N/A')

            # 查找偿付能力充足率表格
            for table in report.get('solvency_tables', []):
                if '偿付能力充足率' not in table.get('table_title', ''):
                    continue

                # 提取充足率数据
                for row in table.get('rows', []):
                    indicator = (
                        row.get('指标名称', '') or
                        row.get('项目', '')
                    )

                    if '充足率' in indicator:
                        result = {
                            'company_name': company,
                            'report_period': period,
                            'indicator': indicator,
                            'current_quarter': row.get('本季度数', ''),
                            'previous_quarter': row.get('上季度数', ''),
                            'same_period_last_year': row.get('上年同期数', ''),
                            'period_initial': row.get('期初数', ''),
                            'period_end': row.get('期末数', ''),
                        }
                        results.append(result)

    return pd.DataFrame(results)


def extract_capital_composition(jsonl_file: str) -> pd.DataFrame:
    """提取资本构成详情."""

    results = []

    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            report = json.loads(line)

            company = report.get('company_name', 'N/A')
            period = report.get('report_period', 'N/A')

            # 查找实际资本表
            for table in report.get('solvency_tables', []):
                table_title = table.get('table_title', '')

                if '实际资本' in table_title or 'S02' in table_title:
                    for row in table.get('rows', []):
                        item = row.get('项目', '') or row.get('指标名称', '')

                        if item:  # 如果有项目名称
                            result = {
                                'company_name': company,
                                'report_period': period,
                                'capital_item': item,
                                'period_end': row.get('期末数', ''),
                                'period_initial': row.get('期初数', ''),
                            }
                            results.append(result)

    return pd.DataFrame(results)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='从 JSONL 提取偿付能力关键指标'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='extracted_data.jsonl',
        help='输入 JSONL 文件路径'
    )
    parser.add_argument(
        '--output',
        type=str,
        default='solvency_indicators.xlsx',
        help='输出 Excel 文件路径'
    )

    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"❌ 错误: 文件不存在 {args.input}")
        return

    print(f"📊 从 {args.input} 提取偿付能力指标...\n")

    # 1. 提取关键指标
    print("1️⃣ 提取关键指标...")
    df_indicators = extract_solvency_indicators(args.input)
    print(f"   ✓ 提取了 {len(df_indicators)} 个报告的关键指标")

    # 显示预览
    print("\n关键指标预览:")
    print(df_indicators.to_string(index=False, max_rows=5))

    # 2. 提取充足率趋势
    print("\n2️⃣ 提取充足率时间序列...")
    df_trends = extract_solvency_ratio_trends(args.input)
    print(f"   ✓ 提取了 {len(df_trends)} 条充足率数据")

    # 3. 提取资本构成
    print("\n3️⃣ 提取资本构成详情...")
    df_capital = extract_capital_composition(args.input)
    print(f"   ✓ 提取了 {len(df_capital)} 条资本构成数据")

    # 4. 保存到 Excel
    print(f"\n4️⃣ 保存到 {args.output}...")
    with pd.ExcelWriter(args.output, engine='openpyxl') as writer:
        df_indicators.to_excel(writer, sheet_name='关键指标', index=False)
        df_trends.to_excel(writer, sheet_name='充足率趋势', index=False)
        df_capital.to_excel(writer, sheet_name='资本构成', index=False)

    print(f"   ✓ 已保存到 {args.output}")

    # 5. 同时保存 CSV
    csv_file = args.output.replace('.xlsx', '_indicators.csv')
    df_indicators.to_csv(csv_file, index=False, encoding='utf-8-sig')
    print(f"   ✓ 关键指标已保存到 {csv_file}")

    # 6. 生成汇总统计
    print("\n" + "="*60)
    print("📈 偿付能力充足率统计:")
    print("="*60)

    if '核心偿付能力充足率' in df_indicators.columns:
        print("\n核心偿付能力充足率:")
        for _, row in df_indicators.iterrows():
            ratio = row.get('核心偿付能力充足率', 'N/A')
            print(f"  {row['company_name'][:20]:20s}: {ratio}")

    if '综合偿付能力充足率' in df_indicators.columns:
        print("\n综合偿付能力充足率:")
        for _, row in df_indicators.iterrows():
            ratio = row.get('综合偿付能力充足率', 'N/A')
            print(f"  {row['company_name'][:20]:20s}: {ratio}")

    print("\n✅ 完成!")


if __name__ == '__main__':
    main()
