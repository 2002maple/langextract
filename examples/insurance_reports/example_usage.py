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
Example usage of insurance report extraction.

This demonstrates how to use the extraction functions in your own code.
"""

import json
import os
from pathlib import Path

from extract_insurance_report import (
    batch_extract,
    extract_from_image,
    format_to_csv,
)


def example_single_image():
  """Example: Extract from a single image."""
  print("=" * 60)
  print("Example 1: Single Image Extraction")
  print("=" * 60)

  # Path to your report image
  image_path = "report_page.png"

  if not Path(image_path).exists():
    print(f"⚠ Image not found: {image_path}")
    print("  Please provide a valid image path")
    return

  # Extract data
  print(f"\nProcessing: {image_path}")
  result = extract_from_image(image_path)

  # Display results
  print("\n✓ Extraction complete!")
  print(f"\nCompany: {result.get('company_name', 'N/A')}")
  print(f"Period: {result.get('report_period', 'N/A')}")
  print(f"Tables found: {len(result.get('solvency_tables', []))}")

  # Show first table preview
  tables = result.get("solvency_tables", [])
  if tables:
    print(f"\nFirst table: {tables[0].get('table_title', 'N/A')}")
    print(f"Rows: {len(tables[0].get('rows', []))}")

  # Save to file
  output_file = "single_result.json"
  with open(output_file, "w", encoding="utf-8") as f:
    json.dump(result, f, ensure_ascii=False, indent=2)
  print(f"\n✓ Saved to: {output_file}")


def example_batch_processing():
  """Example: Batch process multiple images."""
  print("\n" + "=" * 60)
  print("Example 2: Batch Processing")
  print("=" * 60)

  # Directory containing report images
  image_dir = "./report_images"

  if not Path(image_dir).exists():
    print(f"\n⚠ Directory not found: {image_dir}")
    print("  Create the directory and add report images:")
    print(f"    mkdir -p {image_dir}")
    print(f"    cp your_reports/*.png {image_dir}/")
    return

  # Batch extract
  print(f"\nProcessing all images in: {image_dir}")
  results = batch_extract(
      image_dir=image_dir,
      output_file="batch_results.jsonl",
      model_id="gemini-2.0-flash-exp",
  )

  # Summary
  print(f"\n✓ Processed {len(results)} reports")

  # Show statistics
  if results:
    companies = set(r.get("company_name", "") for r in results)
    periods = set(r.get("report_period", "") for r in results)
    print(f"\nUnique companies: {len(companies)}")
    print(f"Unique periods: {len(periods)}")

    # Export to CSV
    format_to_csv("batch_results.jsonl", "batch_analysis.csv")


def example_custom_processing():
  """Example: Custom processing of extracted data."""
  print("\n" + "=" * 60)
  print("Example 3: Custom Data Processing")
  print("=" * 60)

  # Assume we have extracted data
  jsonl_file = "batch_results.jsonl"

  if not Path(jsonl_file).exists():
    print(f"\n⚠ File not found: {jsonl_file}")
    print("  Run example 2 first to generate batch results")
    return

  # Read and analyze
  print(f"\nAnalyzing: {jsonl_file}")

  reports = []
  with open(jsonl_file, "r", encoding="utf-8") as f:
    for line in f:
      reports.append(json.loads(line))

  print(f"Loaded {len(reports)} reports")

  # Example analysis: Extract core solvency ratio
  print("\n--- Core Solvency Adequacy Ratios ---")
  for report in reports:
    company = report.get("company_name", "Unknown")
    period = report.get("report_period", "Unknown")

    for table in report.get("solvency_tables", []):
      for row in table.get("rows", []):
        metric = row.get("指标名称", "")
        if "核心偿付能力" in metric:
          ratio = row.get("本季度数", "N/A")
          print(f"{company} ({period}): {metric} = {ratio}")

  # Example analysis: Calculate trends
  print("\n--- Solvency Ratio Trends ---")
  for report in reports:
    company = report.get("company_name", "Unknown")
    period = report.get("report_period", "Unknown")

    for table in report.get("solvency_tables", []):
      for row in table.get("rows", []):
        metric = row.get("指标名称", "")
        if "综合偿付能力" in metric:
          current = row.get("本季度数", "").replace("%", "")
          previous = row.get("上季度数", "").replace("%", "")

          try:
            current_val = float(current)
            previous_val = float(previous)
            change = current_val - previous_val
            trend = "↑" if change > 0 else "↓" if change < 0 else "="

            print(
                f"{company} ({period}): {metric}"
                f" {current}% {trend} (change: {change:+.1f}%)"
            )
          except (ValueError, TypeError):
            pass


def example_error_handling():
  """Example: Error handling and validation."""
  print("\n" + "=" * 60)
  print("Example 4: Error Handling")
  print("=" * 60)

  image_path = "report_page.png"

  try:
    # Check API key
    api_key = os.environ.get("LANGEXTRACT_API_KEY")
    if not api_key:
      raise ValueError(
          "LANGEXTRACT_API_KEY not set. Please set your API key:"
          "\n  export LANGEXTRACT_API_KEY='your-key'"
      )

    # Check file exists
    if not Path(image_path).exists():
      raise FileNotFoundError(f"Image not found: {image_path}")

    # Extract with error handling
    print(f"\nExtracting from: {image_path}")
    result = extract_from_image(image_path)

    # Validate results
    if not result.get("company_name"):
      print("⚠ Warning: Company name not extracted")

    if not result.get("report_period"):
      print("⚠ Warning: Report period not extracted")

    tables = result.get("solvency_tables", [])
    if not tables:
      print("⚠ Warning: No tables extracted")
    else:
      print(f"✓ Successfully extracted {len(tables)} tables")

      # Validate table structure
      for i, table in enumerate(tables):
        if not table.get("rows"):
          print(f"  ⚠ Table {i+1} has no rows")
        if not table.get("table_title"):
          print(f"  ⚠ Table {i+1} has no title")

  except ValueError as e:
    print(f"\n✗ Configuration error: {e}")
  except FileNotFoundError as e:
    print(f"\n✗ File error: {e}")
  except Exception as e:
    print(f"\n✗ Unexpected error: {e}")


def main():
  """Run all examples."""
  print("\n" + "=" * 60)
  print("Insurance Report Extraction Examples")
  print("=" * 60)

  # Example 1: Single image
  try:
    example_single_image()
  except Exception as e:
    print(f"Example 1 failed: {e}")

  # Example 2: Batch processing
  try:
    example_batch_processing()
  except Exception as e:
    print(f"Example 2 failed: {e}")

  # Example 3: Custom processing
  try:
    example_custom_processing()
  except Exception as e:
    print(f"Example 3 failed: {e}")

  # Example 4: Error handling
  try:
    example_error_handling()
  except Exception as e:
    print(f"Example 4 failed: {e}")

  print("\n" + "=" * 60)
  print("Examples complete!")
  print("=" * 60)


if __name__ == "__main__":
  main()
