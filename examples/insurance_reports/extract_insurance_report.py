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
Extract structured data from insurance solvency reports (Chinese).

This script demonstrates how to use Gemini's multimodal capabilities to extract:
1. Company name (企业名称)
2. Report period (报告期间)
3. Solvency adequacy ratio tables (偿付能力充足率表格)

The script can process PDF pages (as images) or direct image files.
"""

import argparse
import json
import os
from pathlib import Path
from typing import Any, Dict, List

from google import genai
from google.genai import types


def extract_from_image(
    image_path: str,
    api_key: str | None = None,
    model_id: str = "gemini-2.0-flash-exp",
) -> Dict[str, Any]:
  """Extract structured data from insurance report image using Gemini.

  Args:
      image_path: Path to the image file
      api_key: Google AI API key (or set LANGEXTRACT_API_KEY env var)
      model_id: Gemini model to use

  Returns:
      Dictionary containing extracted data
  """
  # Initialize Gemini client
  api_key = api_key or os.environ.get("LANGEXTRACT_API_KEY")
  if not api_key:
    raise ValueError(
        "API key required. Set LANGEXTRACT_API_KEY or pass api_key parameter"
    )

  client = genai.Client(api_key=api_key)

  # Read image
  image_path = Path(image_path)
  if not image_path.exists():
    raise FileNotFoundError(f"Image not found: {image_path}")

  # Construct prompt for extraction
  prompt = """
请从这份中国保险公司的偿付能力报告中提取以下信息，以JSON格式返回：

1. 企业名称 (company_name): 完整的公司名称
2. 报告期间 (report_period): 例如 "2025年上半年度"
3. 偿付能力表格 (solvency_tables): 提取所有与偿付能力相关的表格数据

对于表格数据，请提取：
- 表格标题
- 所有行和列的数据
- 保持数字的精确性（包括小数点）

输出格式示例：
```json
{
  "company_name": "中国人民保险集团股份有限公司",
  "report_period": "2025年上半年度",
  "solvency_tables": [
    {
      "table_title": "偿付能力充足率指标",
      "headers": ["指标名称", "本季度数", "上季度数", "上年同期数"],
      "rows": [
        {
          "指标名称": "认可资产",
          "本季度数": "14,579,965.71",
          "上季度数": "15,167,024.33",
          "上年同期数": "14,871,565.03"
        }
      ]
    },
    {
      "table_title": "保险集团偿付能力状况表",
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

请确保：
- 准确提取所有数字，保留逗号分隔符和小数点
- 识别表格的标题和单位
- 保持表格结构的完整性
- 如果图片中有多个表格，请全部提取
"""

  # Upload image and generate content
  with open(image_path, "rb") as f:
    image_bytes = f.read()

  response = client.models.generate_content(
      model=model_id,
      contents=[
          types.Part.from_bytes(
              data=image_bytes,
              mime_type=f"image/{image_path.suffix[1:]}",  # e.g., "image/png"
          ),
          prompt,
      ],
  )

  # Parse JSON response
  response_text = response.text.strip()

  # Handle code fences if present
  if response_text.startswith("```json"):
    response_text = response_text[7:]  # Remove ```json
  if response_text.startswith("```"):
    response_text = response_text[3:]  # Remove ```
  if response_text.endswith("```"):
    response_text = response_text[:-3]  # Remove trailing ```

  response_text = response_text.strip()

  try:
    extracted_data = json.loads(response_text)
  except json.JSONDecodeError as e:
    print(f"Failed to parse JSON response: {e}")
    print(f"Raw response:\n{response_text}")
    raise

  return extracted_data


def batch_extract(
    image_dir: str,
    output_file: str = "extracted_reports.jsonl",
    api_key: str | None = None,
    model_id: str = "gemini-2.0-flash-exp",
) -> List[Dict[str, Any]]:
  """Batch extract from multiple insurance report images.

  Args:
      image_dir: Directory containing image files
      output_file: Output JSONL file path
      api_key: Google AI API key
      model_id: Gemini model to use

  Returns:
      List of extracted data dictionaries
  """
  image_dir = Path(image_dir)
  if not image_dir.is_dir():
    raise ValueError(f"Not a directory: {image_dir}")

  # Find all image files
  image_extensions = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
  image_files = [
      f
      for f in image_dir.iterdir()
      if f.suffix.lower() in image_extensions
  ]

  if not image_files:
    print(f"No image files found in {image_dir}")
    return []

  print(f"Found {len(image_files)} image files")

  results = []
  for i, image_path in enumerate(image_files, 1):
    print(f"\n[{i}/{len(image_files)}] Processing {image_path.name}...")
    try:
      extracted = extract_from_image(
          str(image_path), api_key=api_key, model_id=model_id
      )
      extracted["source_file"] = image_path.name
      results.append(extracted)
      print(
          f"  ✓ Extracted: {extracted.get('company_name', 'N/A')} -"
          f" {extracted.get('report_period', 'N/A')}"
      )
    except Exception as e:
      print(f"  ✗ Error: {e}")
      continue

  # Save to JSONL
  if results:
    with open(output_file, "w", encoding="utf-8") as f:
      for result in results:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(f"\n✓ Saved {len(results)} results to {output_file}")

  return results


def format_to_csv(
    jsonl_file: str, csv_file: str = "solvency_ratios.csv"
) -> None:
  """Convert extracted JSONL data to CSV format for analysis.

  Args:
      jsonl_file: Input JSONL file path
      csv_file: Output CSV file path
  """
  import csv

  # Read JSONL
  reports = []
  with open(jsonl_file, "r", encoding="utf-8") as f:
    for line in f:
      reports.append(json.loads(line))

  # Extract key metrics for CSV
  csv_rows = []
  for report in reports:
    company = report.get("company_name", "")
    period = report.get("report_period", "")

    # Find solvency ratio table
    for table in report.get("solvency_tables", []):
      if "偿付能力充足率" in table.get("table_title", ""):
        for row in table.get("rows", []):
          csv_rows.append(
              {
                  "company_name": company,
                  "report_period": period,
                  "metric": row.get("指标名称", ""),
                  "current_quarter": row.get("本季度数", ""),
                  "previous_quarter": row.get("上季度数", ""),
                  "same_period_last_year": row.get("上年同期数", ""),
              }
          )

  # Write CSV
  if csv_rows:
    with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
      fieldnames = [
          "company_name",
          "report_period",
          "metric",
          "current_quarter",
          "previous_quarter",
          "same_period_last_year",
      ]
      writer = csv.DictWriter(f, fieldnames=fieldnames)
      writer.writeheader()
      writer.writerows(csv_rows)
    print(f"✓ Saved CSV with {len(csv_rows)} rows to {csv_file}")
  else:
    print("No solvency ratio data found to export to CSV")


def main():
  parser = argparse.ArgumentParser(
      description="Extract data from insurance solvency reports"
  )
  parser.add_argument(
      "--image",
      type=str,
      help="Single image file to process",
  )
  parser.add_argument(
      "--image-dir",
      type=str,
      help="Directory containing multiple image files",
  )
  parser.add_argument(
      "--output",
      type=str,
      default="extracted_reports.jsonl",
      help="Output JSONL file (default: extracted_reports.jsonl)",
  )
  parser.add_argument(
      "--csv",
      type=str,
      help="Also export solvency ratios to CSV file",
  )
  parser.add_argument(
      "--model",
      type=str,
      default="gemini-2.0-flash-exp",
      help="Gemini model to use (default: gemini-2.0-flash-exp)",
  )
  parser.add_argument(
      "--api-key",
      type=str,
      help="Google AI API key (or set LANGEXTRACT_API_KEY env var)",
  )

  args = parser.parse_args()

  if not args.image and not args.image_dir:
    parser.error("Must specify --image or --image-dir")

  # Single image processing
  if args.image:
    print(f"Processing single image: {args.image}")
    result = extract_from_image(args.image, args.api_key, args.model)
    print("\nExtracted data:")
    print(json.dumps(result, ensure_ascii=False, indent=2))

    # Save to JSONL
    with open(args.output, "w", encoding="utf-8") as f:
      f.write(json.dumps(result, ensure_ascii=False) + "\n")
    print(f"\n✓ Saved to {args.output}")

  # Batch processing
  elif args.image_dir:
    print(f"Batch processing directory: {args.image_dir}")
    batch_extract(args.image_dir, args.output, args.api_key, args.model)

  # Export to CSV if requested
  if args.csv and os.path.exists(args.output):
    format_to_csv(args.output, args.csv)


if __name__ == "__main__":
  main()
