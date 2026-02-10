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
Batch process multiple PDF insurance reports using Gemini 2.5 Flash.

This script handles the complete pipeline:
1. Convert PDF files to images
2. Extract data from each page using Gemini
3. Merge results per PDF report
4. Export to JSON/CSV formats
"""

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types
from tqdm import tqdm


# ============================================================================
# PDF to Image Conversion
# ============================================================================


def convert_pdf_to_images(
    pdf_path: str, output_dir: str, dpi: int = 300
) -> List[str]:
  """Convert PDF to images using pdf2image.

  Args:
      pdf_path: Path to PDF file
      output_dir: Directory to save images
      dpi: Resolution (default 300 for good quality)

  Returns:
      List of image file paths
  """
  try:
    from pdf2image import convert_from_path
  except ImportError:
    raise ImportError(
        "pdf2image not installed. Install with:\n"
        "  pip install pdf2image\n"
        "Also ensure poppler is installed:\n"
        "  Ubuntu/Debian: apt-get install poppler-utils\n"
        "  macOS: brew install poppler\n"
        "  Windows: Download from https://github.com/oschwartz10612/poppler-windows"
    )

  pdf_path = Path(pdf_path)
  output_dir = Path(output_dir)
  output_dir.mkdir(parents=True, exist_ok=True)

  print(f"  Converting PDF to images (DPI={dpi})...")

  # Convert PDF to images
  images = convert_from_path(str(pdf_path), dpi=dpi)

  # Save images
  image_paths = []
  for i, image in enumerate(images, 1):
    image_path = output_dir / f"{pdf_path.stem}_page_{i:03d}.png"
    image.save(str(image_path), "PNG")
    image_paths.append(str(image_path))

  print(f"  ✓ Converted to {len(image_paths)} images")
  return image_paths


def convert_pdf_with_pdfplumber(
    pdf_path: str, output_dir: str, resolution: int = 300
) -> List[str]:
  """Convert PDF to images using pdfplumber (alternative method).

  Args:
      pdf_path: Path to PDF file
      output_dir: Directory to save images
      resolution: Image resolution

  Returns:
      List of image file paths
  """
  try:
    import pdfplumber
  except ImportError:
    raise ImportError(
        "pdfplumber not installed. Install with: pip install pdfplumber"
    )

  pdf_path = Path(pdf_path)
  output_dir = Path(output_dir)
  output_dir.mkdir(parents=True, exist_ok=True)

  print(f"  Converting PDF to images (resolution={resolution})...")

  image_paths = []
  with pdfplumber.open(str(pdf_path)) as pdf:
    for i, page in enumerate(pdf.pages, 1):
      image = page.to_image(resolution=resolution)
      image_path = output_dir / f"{pdf_path.stem}_page_{i:03d}.png"
      image.save(str(image_path))
      image_paths.append(str(image_path))

  print(f"  ✓ Converted to {len(image_paths)} images")
  return image_paths


# ============================================================================
# Data Extraction with Gemini
# ============================================================================


def extract_from_image_gemini(
    image_path: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
) -> Dict[str, Any]:
  """Extract data from single image using Gemini.

  Args:
      image_path: Path to image file
      api_key: Google AI API key
      model: Gemini model name

  Returns:
      Extracted data dictionary
  """
  client = genai.Client(api_key=api_key)

  # Read image
  with open(image_path, "rb") as f:
    image_bytes = f.read()

  # Extraction prompt
  prompt = """
请从这份中国保险公司的偿付能力报告中提取以下信息，以JSON格式返回：

1. 企业名称 (company_name): 完整的公司名称
2. 报告期间 (report_period): 例如 "2025年上半年度"
3. 偿付能力表格 (solvency_tables): 提取所有与偿付能力相关的表格数据

对于表格数据，请提取：
- 表格标题
- 所有行和列的数据
- 保持数字的精确性（包括小数点和逗号）

输出JSON格式：
```json
{
  "company_name": "公司名称",
  "report_period": "报告期间",
  "solvency_tables": [
    {
      "table_title": "表格标题",
      "headers": ["列1", "列2"],
      "rows": [{"列1": "值1", "列2": "值2"}]
    }
  ]
}
```

如果这一页没有相关信息，返回：
```json
{
  "company_name": null,
  "report_period": null,
  "solvency_tables": []
}
```

只返回JSON，不要其他解释。
"""

  # Generate content
  response = client.models.generate_content(
      model=model,
      contents=[
          types.Part.from_bytes(
              data=image_bytes,
              mime_type=f"image/{Path(image_path).suffix[1:]}",
          ),
          prompt,
      ],
  )

  # Parse response
  return parse_json_response(response.text)


def parse_json_response(response_text: str) -> Dict[str, Any]:
  """Parse JSON from LLM response."""
  text = response_text.strip()

  # Remove code fences
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
    print(f"⚠ Warning: Failed to parse JSON: {e}")
    print(f"Raw response:\n{text[:200]}...")
    # Return empty structure on parse error
    return {
        "company_name": None,
        "report_period": None,
        "solvency_tables": [],
    }


# ============================================================================
# PDF Processing Pipeline
# ============================================================================


def process_single_pdf(
    pdf_path: str,
    api_key: str,
    model: str = "gemini-2.5-flash",
    dpi: int = 300,
    temp_dir: Optional[str] = None,
    keep_images: bool = False,
) -> Dict[str, Any]:
  """Process a single PDF report.

  Args:
      pdf_path: Path to PDF file
      api_key: Google AI API key
      model: Gemini model name
      dpi: Image resolution
      temp_dir: Temporary directory for images
      keep_images: Whether to keep converted images

  Returns:
      Combined extraction results from all pages
  """
  pdf_path = Path(pdf_path)
  print(f"\n{'='*60}")
  print(f"Processing: {pdf_path.name}")
  print(f"{'='*60}")

  # Create temp directory for images
  if temp_dir:
    image_dir = Path(temp_dir) / pdf_path.stem
    image_dir.mkdir(parents=True, exist_ok=True)
  else:
    image_dir = Path(tempfile.mkdtemp(prefix=f"{pdf_path.stem}_"))

  try:
    # Step 1: Convert PDF to images
    try:
      image_paths = convert_pdf_to_images(str(pdf_path), str(image_dir), dpi)
    except ImportError:
      # Fallback to pdfplumber
      print("  Falling back to pdfplumber...")
      image_paths = convert_pdf_with_pdfplumber(
          str(pdf_path), str(image_dir), resolution=dpi
      )

    # Step 2: Extract data from each page
    print(f"  Extracting data from {len(image_paths)} pages...")

    all_extractions = []
    company_name = None
    report_period = None

    for i, image_path in enumerate(tqdm(image_paths, desc="  Pages"), 1):
      try:
        result = extract_from_image_gemini(image_path, api_key, model)

        # Collect company name and period from first page that has them
        if not company_name and result.get("company_name"):
          company_name = result["company_name"]
        if not report_period and result.get("report_period"):
          report_period = result["report_period"]

        # Collect all tables
        tables = result.get("solvency_tables", [])
        for table in tables:
          table["source_page"] = i  # Add page number
          all_extractions.append(table)

      except Exception as e:
        print(f"    ⚠ Error on page {i}: {e}")
        continue

    # Step 3: Combine results
    combined_result = {
        "pdf_file": pdf_path.name,
        "company_name": company_name,
        "report_period": report_period,
        "total_pages": len(image_paths),
        "tables_found": len(all_extractions),
        "solvency_tables": all_extractions,
    }

    print(f"\n  ✓ Extraction complete!")
    print(f"    Company: {company_name or 'Not found'}")
    print(f"    Period: {report_period or 'Not found'}")
    print(f"    Tables found: {len(all_extractions)}")

    return combined_result

  finally:
    # Cleanup temp images unless keep_images is True
    if not keep_images and not temp_dir:
      shutil.rmtree(image_dir, ignore_errors=True)


def batch_process_pdfs(
    pdf_dir: str,
    output_file: str = "extracted_reports.jsonl",
    api_key: Optional[str] = None,
    model: str = "gemini-2.5-flash",
    dpi: int = 300,
    keep_images: bool = False,
    max_pdfs: Optional[int] = None,
) -> List[Dict[str, Any]]:
  """Batch process multiple PDF files.

  Args:
      pdf_dir: Directory containing PDF files
      output_file: Output JSONL file path
      api_key: Google AI API key
      model: Gemini model name
      dpi: Image resolution
      keep_images: Whether to keep converted images
      max_pdfs: Maximum number of PDFs to process (for testing)

  Returns:
      List of extraction results
  """
  api_key = api_key or os.environ.get("LANGEXTRACT_API_KEY")
  if not api_key:
    raise ValueError(
        "API key required. Set LANGEXTRACT_API_KEY or pass --api-key"
    )

  pdf_dir = Path(pdf_dir)
  if not pdf_dir.is_dir():
    raise ValueError(f"Not a directory: {pdf_dir}")

  # Find all PDF files
  pdf_files = sorted(pdf_dir.glob("*.pdf"))

  if not pdf_files:
    print(f"No PDF files found in {pdf_dir}")
    return []

  if max_pdfs:
    pdf_files = pdf_files[:max_pdfs]

  print(f"\n{'='*60}")
  print(f"Batch Processing: {len(pdf_files)} PDF files")
  print(f"Model: {model}")
  print(f"Output: {output_file}")
  print(f"{'='*60}")

  # Create temp directory for all images if keep_images
  temp_dir = None
  if keep_images:
    temp_dir = pdf_dir / "converted_images"
    temp_dir.mkdir(exist_ok=True)
    print(f"Images will be saved to: {temp_dir}")

  # Process each PDF
  results = []
  for i, pdf_path in enumerate(pdf_files, 1):
    print(f"\n[{i}/{len(pdf_files)}]")
    try:
      result = process_single_pdf(
          str(pdf_path),
          api_key,
          model,
          dpi,
          str(temp_dir) if temp_dir else None,
          keep_images,
      )
      results.append(result)

      # Save incrementally
      with open(output_file, "w", encoding="utf-8") as f:
        for r in results:
          f.write(json.dumps(r, ensure_ascii=False) + "\n")

    except Exception as e:
      print(f"  ✗ Failed to process {pdf_path.name}: {e}")
      continue

  # Final summary
  print(f"\n{'='*60}")
  print(f"Batch Processing Complete!")
  print(f"{'='*60}")
  print(f"Total PDFs processed: {len(results)}/{len(pdf_files)}")
  print(f"Total tables extracted: {sum(r['tables_found'] for r in results)}")
  print(f"Results saved to: {output_file}")

  return results


# ============================================================================
# Export to CSV
# ============================================================================


def export_to_csv(jsonl_file: str, csv_file: str = "solvency_data.csv"):
  """Export extracted data to CSV format.

  Args:
      jsonl_file: Input JSONL file
      csv_file: Output CSV file
  """
  import csv

  # Read JSONL
  reports = []
  with open(jsonl_file, "r", encoding="utf-8") as f:
    for line in f:
      reports.append(json.loads(line))

  # Extract all table rows
  csv_rows = []
  for report in reports:
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
    print("No data to export to CSV")
    return

  # Collect all unique field names from all rows
  # (different PDFs may have different table column names)
  all_fieldnames = set()
  for row in csv_rows:
    all_fieldnames.update(row.keys())

  # Sort fieldnames: fixed columns first, then dynamic columns
  fixed_columns = ["pdf_file", "company_name", "report_period", "table_title", "source_page"]
  dynamic_columns = sorted(all_fieldnames - set(fixed_columns))
  fieldnames = fixed_columns + dynamic_columns

  # Write CSV
  with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    writer.writerows(csv_rows)

  print(f"✓ Exported {len(csv_rows)} rows to {csv_file}")


# ============================================================================
# Main
# ============================================================================


def main():
  parser = argparse.ArgumentParser(
      description="Batch process PDF insurance reports with Gemini 2.5 Flash"
  )

  # Input/output
  parser.add_argument(
      "--pdf-dir",
      type=str,
      required=True,
      help="Directory containing PDF files",
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
      help="Also export to CSV file",
  )

  # Processing options
  parser.add_argument(
      "--model",
      type=str,
      default="gemini-2.5-flash",
      help="Gemini model (default: gemini-2.5-flash)",
  )
  parser.add_argument(
      "--api-key",
      type=str,
      help="Google AI API key (or set LANGEXTRACT_API_KEY)",
  )
  parser.add_argument(
      "--dpi",
      type=int,
      default=300,
      help="Image resolution for PDF conversion (default: 300)",
  )
  parser.add_argument(
      "--keep-images",
      action="store_true",
      help="Keep converted images (saved to pdf-dir/converted_images/)",
  )
  parser.add_argument(
      "--max-pdfs",
      type=int,
      help="Maximum number of PDFs to process (for testing)",
  )

  args = parser.parse_args()

  # Process PDFs
  results = batch_process_pdfs(
      pdf_dir=args.pdf_dir,
      output_file=args.output,
      api_key=args.api_key,
      model=args.model,
      dpi=args.dpi,
      keep_images=args.keep_images,
      max_pdfs=args.max_pdfs,
  )

  # Export to CSV if requested
  if args.csv and results:
    export_to_csv(args.output, args.csv)


if __name__ == "__main__":
  main()
