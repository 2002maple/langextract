#!/usr/bin/env python3
"""Test script to verify table extraction from your specific PDF images.

This script tests whether the extraction logic can correctly identify
the solvency tables from your uploaded images.

Usage:
    python test_table_extraction.py --pdf your_report.pdf --api_key YOUR_KEY
"""

import argparse
import json
import os
from pathlib import Path

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("错误：需要安装 google-genai 库")
    print("安装命令: pip install google-genai")
    exit(1)


EXTRACTION_PROMPT = """请从这份中国保险公司偿付能力报告中提取以下信息，以JSON格式返回：

1. 公司名称 (company_name)
2. 报告期间 (report_period)，例如"2024年第二季度"
3. 偿付能力相关的所有表格 (solvency_tables)，每个表格包括：
   - 表格标题 (table_title)
   - 表格数据 (rows)，以对象数组形式，每行是一个对象，键是列名，值是单元格内容

请特别关注包含以下关键词的表格：
- 偿付能力充足率
- 实际资本
- 最低资本
- 核心偿付能力
- 综合偿付能力
- 认可资产
- 认可负债

返回格式示例：
{
  "company_name": "XX保险公司",
  "report_period": "2024年第二季度",
  "solvency_tables": [
    {
      "table_title": "偿付能力充足率",
      "rows": [
        {"指标名称": "核心偿付能力充足率", "本季度数": "150%", "上季度数": "148%"}
      ]
    }
  ]
}

只返回JSON，不要其他说明文字。"""


def extract_and_analyze(pdf_path: Path, api_key: str):
    """Extract data and provide detailed analysis."""

    print(f"\n{'='*70}")
    print(f"📄 测试文件: {pdf_path.name}")
    print(f"{'='*70}\n")

    # Read PDF
    print("1️⃣ 读取 PDF 文件...")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()
    print(f"   ✓ 文件大小: {len(pdf_bytes) / 1024:.2f} KB\n")

    # Call API
    print("2️⃣ 调用 Gemini API 进行分析...")
    client = genai.Client(api_key=api_key)

    response = client.models.generate_content(
        model="gemini-2.0-flash-exp",
        contents=[
            types.Part.from_bytes(
                data=pdf_bytes,
                mime_type="application/pdf",
            ),
            EXTRACTION_PROMPT,
        ],
    )

    print(f"   ✓ API 调用成功\n")

    # Parse response
    print("3️⃣ 解析响应...")
    response_text = response.text

    # Remove markdown code blocks
    import re
    cleaned = re.sub(r'^```(?:json)?\s*', '', response_text.strip())
    cleaned = re.sub(r'\s*```$', '', cleaned)

    try:
        result = json.loads(cleaned)
        print(f"   ✓ JSON 解析成功\n")
    except json.JSONDecodeError as e:
        print(f"   ❌ JSON 解析失败: {e}\n")
        print("原始响应（前 500 字符）：")
        print(response_text[:500])
        return None

    # Analyze results
    print(f"{'='*70}")
    print(f"📊 提取结果分析")
    print(f"{'='*70}\n")

    print(f"🏢 公司名称: {result.get('company_name', '未识别')}")
    print(f"📅 报告期间: {result.get('report_period', '未识别')}\n")

    tables = result.get('solvency_tables', [])
    print(f"📋 识别到的表格数量: {len(tables)}\n")

    if not tables:
        print("⚠️  警告：未识别到任何偿付能力表格！\n")
        return result

    # Analyze each table
    for idx, table in enumerate(tables, 1):
        title = table.get('table_title', '无标题')
        rows = table.get('rows', [])

        print(f"表格 {idx}: {title}")
        print(f"   行数: {len(rows)}")

        if rows:
            # Show column names
            columns = list(rows[0].keys())
            print(f"   列名: {', '.join(columns)}")

            # Show first 3 rows as sample
            print(f"   示例数据（前3行）:")
            for i, row in enumerate(rows[:3], 1):
                print(f"      行{i}: {row}")

        print()

    # Check for key indicators
    print(f"{'='*70}")
    print(f"🔍 关键指标检查")
    print(f"{'='*70}\n")

    key_indicators = {
        '核心偿付能力充足率': False,
        '综合偿付能力充足率': False,
        '实际资本': False,
        '最低资本': False,
        '认可资产': False,
        '认可负债': False,
    }

    for table in tables:
        for row in table.get('rows', []):
            row_text = ' '.join(str(v) for v in row.values())
            for indicator in key_indicators:
                if indicator in row_text:
                    key_indicators[indicator] = True

    for indicator, found in key_indicators.items():
        status = "✅ 已识别" if found else "❌ 未识别"
        print(f"{indicator}: {status}")

    print()

    # Save results
    output_file = pdf_path.parent / f"{pdf_path.stem}_extracted.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"💾 完整结果已保存到: {output_file}\n")

    return result


def main():
    parser = argparse.ArgumentParser(
        description='Test table extraction from insurance solvency reports'
    )
    parser.add_argument(
        '--pdf',
        type=str,
        required=True,
        help='PDF file to test',
    )
    parser.add_argument(
        '--api_key',
        type=str,
        help='Gemini API key (or set GEMINI_API_KEY env var)',
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        print('❌ 错误：需要提供 Gemini API key')
        print('   方法1: --api_key YOUR_API_KEY')
        print('   方法2: 设置环境变量 GEMINI_API_KEY')
        return 1

    # Check PDF file
    pdf_path = Path(args.pdf)
    if not pdf_path.exists():
        print(f'❌ 错误：文件不存在 {pdf_path}')
        return 1

    # Extract and analyze
    result = extract_and_analyze(pdf_path, api_key)

    if result:
        print(f"{'='*70}")
        print(f"✅ 测试完成！")
        print(f"{'='*70}\n")

        tables_count = len(result.get('solvency_tables', []))
        if tables_count > 0:
            print(f"👍 成功识别 {tables_count} 个表格")
            print(f"💡 建议：检查 *_extracted.json 文件确认数据准确性")
        else:
            print(f"⚠️  未识别到表格，可能原因：")
            print(f"   1. PDF 格式不标准（扫描版、图片 PDF）")
            print(f"   2. 表格不包含关键词")
            print(f"   3. API 返回格式异常")
    else:
        print(f"❌ 测试失败")

    return 0


if __name__ == '__main__':
    exit(main())
