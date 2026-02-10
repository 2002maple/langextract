#!/usr/bin/env python3
# Copyright 2025 Google LLC.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
优化版：直接处理 PDF，一个文件只调用一次 Gemini API

相比原版本的优势：
- 成本降低 90%+（30 页 PDF：30 次调用 → 1 次调用）
- 速度更快（无需 PDF 转图片）
- 更简单（不需要 poppler）
- Gemini 能看到完整文档上下文
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from tqdm import tqdm


# ============================================================================
# 直接处理 PDF（推荐方式）
# ============================================================================


def extract_from_pdf_direct(
    pdf_path: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
  """直接从 PDF 文件提取数据（一次 API 调用）.

  Args:
      pdf_path: PDF 文件路径
      api_key: Google AI API key
      model: Gemini 模型名称

  Returns:
      提取的数据字典
  """
  client = genai.Client(api_key=api_key)

  # 读取 PDF 文件
  pdf_path = Path(pdf_path)
  with open(pdf_path, "rb") as f:
    pdf_bytes = f.read()

  # 构建提取提示词
  prompt = """
请分析这份完整的中国保险公司偿付能力报告PDF，提取以下信息并以JSON格式返回：

1. **企业名称** (company_name): 完整的公司名称
2. **报告期间** (report_period): 例如 "2025年上半年度"
3. **偿付能力表格** (solvency_tables): 提取所有与偿付能力相关的表格数据

对于每个表格，请提取：
- table_title: 表格标题
- source_page: 表格所在页码（如果能识别）
- headers: 表头列表
- rows: 表格行数据（每行是一个字典，键为表头）

重要要求：
- 保持数字的精确性（包括小数点、逗号分隔符、百分号）
- 完整提取所有偿付能力相关表格（不要遗漏）
- 表格行数据要完整，包含所有列

输出JSON格式：
```json
{
  "company_name": "中国人民保险集团股份有限公司",
  "report_period": "2025年上半年度",
  "solvency_tables": [
    {
      "table_title": "偿付能力充足率指标",
      "source_page": 11,
      "headers": ["指标名称", "本季度数", "上季度数", "上年同期数"],
      "rows": [
        {
          "指标名称": "认可资产",
          "本季度数": "14,579,965.71",
          "上季度数": "15,167,024.33",
          "上年同期数": "14,871,565.03"
        },
        {
          "指标名称": "认可负债",
          "本季度数": "11,132,987.93",
          "上季度数": "11,804,911.98",
          "上年同期数": "11,423,239.93"
        }
      ]
    },
    {
      "table_title": "保险集团偿付能力状况表",
      "source_page": 10,
      "date": "2025-06-30",
      "unit": "万元",
      "headers": ["项目", "行次", "期末数", "期初数"],
      "rows": [
        {
          "项目": "实际资本",
          "行次": "(1)-(2)+(3)+(4)+(5)",
          "期末数": "56,325,739",
          "期初数": "53,377,274"
        }
      ]
    }
  ]
}
```

只返回JSON，不要其他解释。
"""

  print(f"  上传 PDF 文件（{pdf_path.stat().st_size / 1024:.1f} KB）...")

  # 调用 Gemini API（一次调用处理整个 PDF！）
  response = client.models.generate_content(
      model=model,
      contents=[
          types.Part.from_bytes(
              data=pdf_bytes,
              mime_type="application/pdf",  # PDF MIME 类型
          ),
          prompt,
      ],
  )

  print("  ✓ API 调用完成")

  # 解析响应
  return parse_json_response(response.text)


def parse_json_response(response_text: str) -> Dict[str, Any]:
  """解析 JSON 响应."""
  text = response_text.strip()

  # 移除代码围栏
  if text.startswith("```json"):
    text = text[7:]
  elif text.startswith("```"):
    text = text[3:]

  if text.endswith("```"):
    text = text[:-3]

  text = text.strip()

  try:
    return json.loads(text)
  except json.JSONDecodeError as e:
    print(f"⚠ 警告: JSON 解析失败: {e}")
    print(f"原始响应:\n{text[:500]}...")
    return {
        "company_name": None,
        "report_period": None,
        "solvency_tables": [],
        "parse_error": str(e),
    }


# ============================================================================
# 批量处理
# ============================================================================


def batch_process_pdfs(
    pdf_dir: str,
    output_file: str = "extracted_reports.jsonl",
    api_key: Optional[str] = None,
    model: str = "gemini-2.5-flash",
    max_pdfs: Optional[int] = None,
) -> List[Dict[str, Any]]:
  """批量处理 PDF 文件（每个 PDF 一次 API 调用）.

  Args:
      pdf_dir: PDF 文件目录
      output_file: 输出 JSONL 文件路径
      api_key: Google AI API key
      model: Gemini 模型名称
      max_pdfs: 最大处理数量（用于测试）

  Returns:
      提取结果列表
  """
  api_key = api_key or os.environ.get("LANGEXTRACT_API_KEY")
  if not api_key:
    raise ValueError(
        "需要 API key。请设置 LANGEXTRACT_API_KEY 或传递 --api-key 参数"
    )

  pdf_dir = Path(pdf_dir)
  if not pdf_dir.is_dir():
    raise ValueError(f"不是有效目录: {pdf_dir}")

  # 查找所有 PDF 文件
  pdf_files = sorted(pdf_dir.glob("*.pdf"))

  if not pdf_files:
    print(f"在 {pdf_dir} 中未找到 PDF 文件")
    return []

  if max_pdfs:
    pdf_files = pdf_files[:max_pdfs]

  print(f"\n{'='*60}")
  print(f"批量处理: {len(pdf_files)} 个 PDF 文件")
  print(f"模型: {model}")
  print(f"输出: {output_file}")
  print(f"优化模式: 每个 PDF 仅调用 1 次 API ✨")
  print(f"{'='*60}\n")

  # 处理每个 PDF
  results = []
  for i, pdf_path in enumerate(pdf_files, 1):
    print(f"[{i}/{len(pdf_files)}] 处理: {pdf_path.name}")

    try:
      # 提取数据（一次 API 调用！）
      result = extract_from_pdf_direct(str(pdf_path), api_key, model)

      # 添加元数据
      result["pdf_file"] = pdf_path.name
      result["file_size_kb"] = pdf_path.stat().st_size / 1024

      # 显示摘要
      print(f"  ✓ 提取完成!")
      print(f"    公司: {result.get('company_name', '未找到')}")
      print(f"    期间: {result.get('report_period', '未找到')}")
      print(
          f"    表格数: {len(result.get('solvency_tables', []))} 个\n"
      )

      results.append(result)

      # 增量保存
      with open(output_file, "w", encoding="utf-8") as f:
        for r in results:
          f.write(json.dumps(r, ensure_ascii=False) + "\n")

    except Exception as e:
      print(f"  ✗ 处理失败: {e}\n")
      # 保存错误信息
      results.append(
          {
              "pdf_file": pdf_path.name,
              "error": str(e),
              "company_name": None,
              "report_period": None,
              "solvency_tables": [],
          }
      )
      continue

  # 最终统计
  print(f"\n{'='*60}")
  print(f"批量处理完成!")
  print(f"{'='*60}")
  print(f"成功处理: {len([r for r in results if not r.get('error')])}/{len(pdf_files)}")
  successful_results = [r for r in results if not r.get("error")]
  total_tables = sum(
      len(r.get("solvency_tables", [])) for r in successful_results
  )
  print(f"提取表格总数: {total_tables}")
  print(f"API 调用总数: {len(pdf_files)} 次")
  print(f"结果保存至: {output_file}\n")

  return results


# ============================================================================
# CSV 导出
# ============================================================================


def export_to_csv(jsonl_file: str, csv_file: str = "solvency_data.csv"):
  """导出为 CSV 格式."""
  import csv

  # 读取 JSONL
  reports = []
  with open(jsonl_file, "r", encoding="utf-8") as f:
    for line in f:
      reports.append(json.loads(line))

  # 提取表格行
  csv_rows = []
  for report in reports:
    if report.get("error"):
      continue

    pdf_file = report.get("pdf_file", "")
    company = report.get("company_name", "")
    period = report.get("report_period", "")

    for table in report.get("solvency_tables", []):
      table_title = table.get("table_title", "")
      source_page = table.get("source_page", "")

      for row in table.get("rows", []):
        csv_row = {
            "pdf_file": pdf_file,
            "company_name": company,
            "report_period": period,
            "table_title": table_title,
            "source_page": source_page,
        }
        csv_row.update(row)
        csv_rows.append(csv_row)

  if not csv_rows:
    print("没有数据可导出到 CSV")
    return

  # 收集所有唯一的字段名（不同 PDF 的表格列名可能不同）
  all_fieldnames = set()
  for row in csv_rows:
    all_fieldnames.update(row.keys())

  # 字段排序：固定列在前，动态列按字母排序
  fixed_columns = ["pdf_file", "company_name", "report_period", "table_title", "source_page"]
  dynamic_columns = sorted(all_fieldnames - set(fixed_columns))
  fieldnames = fixed_columns + dynamic_columns

  # 写入 CSV
  with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(csv_rows)

  print(f"✓ 导出 {len(csv_rows)} 行数据到 {csv_file}")


# ============================================================================
# 成本估算
# ============================================================================


def estimate_cost(pdf_files: List[Path], model: str = "gemini-2.5-flash"):
  """估算处理成本."""
  total_size = sum(f.stat().st_size for f in pdf_files)

  # Gemini 2.5 Flash 定价（2025年）
  # 输入: $0.075 / 1M tokens
  # 输出: $0.30 / 1M tokens

  # 估算：每 1KB PDF ≈ 100 tokens（粗略估计）
  estimated_input_tokens = (total_size / 1024) * 100
  estimated_output_tokens = len(pdf_files) * 2000  # 每个 PDF 约 2K tokens 输出

  input_cost = (estimated_input_tokens / 1_000_000) * 0.075
  output_cost = (estimated_output_tokens / 1_000_000) * 0.30
  total_cost = input_cost + output_cost

  print(f"\n{'='*60}")
  print("成本估算（Gemini 2.5 Flash）")
  print(f"{'='*60}")
  print(f"PDF 文件数: {len(pdf_files)}")
  print(f"总大小: {total_size / 1024 / 1024:.2f} MB")
  print(f"API 调用次数: {len(pdf_files)} 次")
  print(f"预计输入 tokens: {estimated_input_tokens:,.0f}")
  print(f"预计输出 tokens: {estimated_output_tokens:,.0f}")
  print(f"预计成本: ${total_cost:.4f} USD")
  print(f"{'='*60}\n")


# ============================================================================
# Main
# ============================================================================


def main():
  parser = argparse.ArgumentParser(
      description="优化版PDF批处理：每个PDF仅调用1次Gemini API",
      formatter_class=argparse.RawDescriptionHelpFormatter,
      epilog="""
示例:
  # 基本用法
  python process_pdf_optimized.py --pdf-dir reports_pdf

  # 导出 CSV
  python process_pdf_optimized.py --pdf-dir reports_pdf --csv analysis.csv

  # 测试模式（只处理 3 个文件）
  python process_pdf_optimized.py --pdf-dir reports_pdf --max-pdfs 3

  # 估算成本
  python process_pdf_optimized.py --pdf-dir reports_pdf --estimate-only
""",
  )

  # 输入/输出
  parser.add_argument(
      "--pdf-dir", type=str, required=True, help="包含 PDF 文件的目录"
  )
  parser.add_argument(
      "--output",
      type=str,
      default="extracted_reports.jsonl",
      help="输出 JSONL 文件（默认: extracted_reports.jsonl）",
  )
  parser.add_argument("--csv", type=str, help="同时导出到 CSV 文件")

  # 处理选项
  parser.add_argument(
      "--model",
      type=str,
      default="gemini-2.5-flash",
      help="Gemini 模型（默认: gemini-2.5-flash）",
  )
  parser.add_argument(
      "--api-key", type=str, help="Google AI API key（或设置 LANGEXTRACT_API_KEY）"
  )
  parser.add_argument(
      "--max-pdfs", type=int, help="最大处理 PDF 数量（用于测试）"
  )
  parser.add_argument(
      "--estimate-only", action="store_true", help="仅估算成本，不实际处理"
  )

  args = parser.parse_args()

  # 查找 PDF 文件
  pdf_dir = Path(args.pdf_dir)
  pdf_files = sorted(pdf_dir.glob("*.pdf"))

  if not pdf_files:
    print(f"错误: 在 {pdf_dir} 中未找到 PDF 文件")
    return

  if args.max_pdfs:
    pdf_files = pdf_files[: args.max_pdfs]

  # 仅估算成本
  if args.estimate_only:
    estimate_cost(pdf_files, args.model)
    return

  # 批量处理
  results = batch_process_pdfs(
      pdf_dir=args.pdf_dir,
      output_file=args.output,
      api_key=args.api_key,
      model=args.model,
      max_pdfs=args.max_pdfs,
  )

  # 导出 CSV
  if args.csv and results:
    export_to_csv(args.output, args.csv)


if __name__ == "__main__":
  main()
