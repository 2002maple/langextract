# Insurance Report Data Extraction (保险报告数据提取)

This example demonstrates how to extract structured data from Chinese insurance company solvency reports using Gemini's multimodal capabilities.

## Overview

The script can extract:

1. **Company Name** (企业名称): e.g., "中国人民保险集团股份有限公司"
2. **Report Period** (报告期间): e.g., "2025年上半年度"
3. **Solvency Tables** (偿付能力表格): All tables related to solvency adequacy ratios

## Why Use Multimodal Approach?

Instead of traditional OCR + text extraction, this solution leverages Gemini's vision capabilities to:

- ✅ **Direct image processing** - No need for PDF-to-text conversion
- ✅ **Table structure recognition** - Understands complex table layouts
- ✅ **Chinese character recognition** - Native support for Chinese text
- ✅ **Context awareness** - Better understanding of financial terminology
- ✅ **Simplified pipeline** - One API call instead of multiple tools

## Requirements

```bash
# Install required dependencies
pip install google-genai

# Or if you already have langextract installed:
pip install -e .
```

## API Key Setup

Get your API key from [Google AI Studio](https://aistudio.google.com/app/apikey):

```bash
# Option 1: Environment variable
export LANGEXTRACT_API_KEY="your-api-key-here"

# Option 2: .env file (recommended)
echo "LANGEXTRACT_API_KEY=your-api-key-here" >> .env
```

## Usage

### Single Image Extraction

Extract from a single report image:

```bash
python extract_insurance_report.py \
  --image report_page.png \
  --output extracted_data.jsonl
```

### Batch Processing

Process multiple report images from a directory:

```bash
python extract_insurance_report.py \
  --image-dir ./reports_images/ \
  --output all_reports.jsonl \
  --csv solvency_ratios.csv
```

This will:
1. Process all images in `./reports_images/`
2. Save raw JSON data to `all_reports.jsonl`
3. Export solvency ratios to `solvency_ratios.csv` for analysis

### Advanced Options

```bash
python extract_insurance_report.py \
  --image-dir ./reports/ \
  --model gemini-2.0-flash-exp \
  --api-key YOUR_API_KEY \
  --output results.jsonl \
  --csv analysis.csv
```

**Parameters:**
- `--image`: Single image file path
- `--image-dir`: Directory with multiple images
- `--output`: Output JSONL file (default: `extracted_reports.jsonl`)
- `--csv`: Export to CSV file for easier analysis
- `--model`: Gemini model (default: `gemini-2.0-flash-exp`)
- `--api-key`: API key (or use env var `LANGEXTRACT_API_KEY`)

## Output Format

### JSONL Format

Each line in the output `.jsonl` file contains:

```json
{
  "company_name": "中国人民保险集团股份有限公司",
  "report_period": "2025年上半年度",
  "source_file": "report_page1.png",
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

### CSV Format

When using `--csv`, the script exports a simplified view of solvency ratios:

| company_name | report_period | metric | current_quarter | previous_quarter | same_period_last_year |
|--------------|---------------|--------|-----------------|------------------|-----------------------|
| 中国人民保险集团股份有限公司 | 2025年上半年度 | 认可资产 | 14,579,965.71 | 15,167,024.33 | 14,871,565.03 |
| 中国人民保险集团股份有限公司 | 2025年上半年度 | 认可负债 | 11,132,987.93 | 11,804,911.98 | 11,423,239.93 |

## Supported Image Formats

- PNG (.png)
- JPEG (.jpg, .jpeg)
- WebP (.webp)
- GIF (.gif)

## Processing PDF Reports

If you have PDF files instead of images, first convert them to images:

### Option 1: Using pdf2image (Python)

```bash
# Install pdf2image
pip install pdf2image

# Convert PDF to images
python -c "
from pdf2image import convert_from_path
images = convert_from_path('report.pdf')
for i, img in enumerate(images):
    img.save(f'report_page_{i+1}.png', 'PNG')
"
```

### Option 2: Using ImageMagick (Command line)

```bash
# Install ImageMagick
# Ubuntu/Debian: apt-get install imagemagick
# macOS: brew install imagemagick

# Convert PDF to images
convert -density 300 report.pdf report_page_%d.png
```

### Option 3: Using pdfplumber (Python - for text-based PDFs)

If the PDF contains selectable text and tables:

```python
import pdfplumber

with pdfplumber.open('report.pdf') as pdf:
    for i, page in enumerate(pdf.pages):
        # Extract tables directly
        tables = page.extract_tables()
        for table in tables:
            print(table)

        # Or save as image
        img = page.to_image(resolution=300)
        img.save(f'page_{i+1}.png')
```

## Example Workflow

### Complete Pipeline for Multiple Reports

```bash
# 1. Organize your PDF reports
mkdir -p reports_pdf reports_images

# 2. Convert PDFs to images (if needed)
for pdf in reports_pdf/*.pdf; do
    convert -density 300 "$pdf" "reports_images/$(basename $pdf .pdf)_%d.png"
done

# 3. Extract data from all images
python extract_insurance_report.py \
  --image-dir reports_images \
  --output extracted_data.jsonl \
  --csv solvency_analysis.csv

# 4. Analyze the results
# - Open solvency_analysis.csv in Excel/Google Sheets
# - Or process extracted_data.jsonl with pandas/jq
```

## Integration with LangExtract

While this example uses Gemini's multimodal API directly, you can integrate it with LangExtract's workflow:

```python
import langextract as lx
from extract_insurance_report import extract_from_image

# 1. Extract text from image using multimodal Gemini
image_data = extract_from_image("report.png")

# 2. Convert extracted tables to text
text_content = f"""
Company: {image_data['company_name']}
Period: {image_data['report_period']}

Tables:
{json.dumps(image_data['solvency_tables'], ensure_ascii=False, indent=2)}
"""

# 3. Use LangExtract for further refinement/analysis
prompt = "Extract and normalize solvency ratios, identify trends"
examples = [...]  # Your examples

result = lx.extract(
    text_or_documents=text_content,
    prompt_description=prompt,
    examples=examples,
    model_id="gemini-2.5-flash"
)
```

## Customization

### Modify the Extraction Prompt

Edit the prompt in `extract_insurance_report.py` to extract additional fields:

```python
prompt = """
请从报告中提取以下信息：

1. 企业名称 (company_name)
2. 报告期间 (report_period)
3. 统一社会信用代码 (credit_code)  # Add new field
4. 偿付能力表格 (solvency_tables)
5. 风险评级 (risk_rating)  # Add new field

... rest of prompt ...
"""
```

### Handle Different Table Formats

Different companies may have different table structures. Adjust the extraction logic in `format_to_csv()` to handle variations:

```python
# Example: Handle different column names
for table in report.get("solvency_tables", []):
    for row in table.get("rows", []):
        # Try multiple possible column names
        metric_name = (
            row.get("指标名称") or
            row.get("项目") or
            row.get("指标")
        )
```

## Performance Tips

### 1. Use Faster Model for Simple Extraction

```bash
# Use flash model for speed
python extract_insurance_report.py \
  --model gemini-2.0-flash-exp \
  --image-dir ./reports/
```

### 2. Parallel Processing (for large batches)

Modify the script to use `concurrent.futures` for parallel API calls:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def batch_extract_parallel(image_dir, max_workers=5):
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(extract_from_image, img): img
            for img in image_files
        }
        for future in as_completed(futures):
            result = future.result()
            # Process result...
```

### 3. Cost Optimization

- Use image compression to reduce file sizes (Gemini charges by input tokens)
- Use `gemini-2.0-flash-exp` instead of `gemini-2.0-pro-exp` for routine extractions
- Batch similar reports in single prompts when possible

## Troubleshooting

### Issue: "API key required"

**Solution:**
```bash
export LANGEXTRACT_API_KEY="your-key"
# Or pass --api-key YOUR_KEY
```

### Issue: "Failed to parse JSON response"

**Cause:** The model returned non-JSON text (explanations, formatting issues)

**Solution:** The script handles code fences automatically. If issues persist, check the raw response printed in error messages and adjust the prompt to be more explicit about JSON-only output.

### Issue: Table structure not extracted correctly

**Cause:** Complex or merged cells in tables

**Solution:**
1. Use higher quality images (300 DPI minimum)
2. Provide more explicit table extraction instructions in the prompt
3. Consider using `gemini-2.0-pro-exp` for complex layouts

### Issue: Rate limits exceeded

**Solution:**
1. Upgrade to Tier 2 quota: https://ai.google.dev/gemini-api/docs/rate-limits
2. Add retry logic with exponential backoff
3. Reduce `max_workers` for parallel processing

## License

Copyright 2025 Google LLC. Licensed under Apache 2.0.

## Disclaimer

This example is for demonstration purposes. When processing financial documents:

- ✅ Verify extracted data accuracy
- ✅ Validate numerical values
- ✅ Review table structures manually
- ⚠️ Do not use for regulatory reporting without human verification
- ⚠️ Ensure compliance with data privacy regulations
