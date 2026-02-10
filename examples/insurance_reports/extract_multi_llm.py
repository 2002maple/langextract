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
Multi-LLM insurance report extraction with support for:
1. Vision LLMs (Gemini, GPT-4V, Claude)
2. OCR + Text LLMs (local models via Ollama, etc.)
"""

import argparse
import base64
import json
import os
from pathlib import Path
from typing import Any, Dict, Optional


# ============================================================================
# Vision LLM Extractors (Direct Image Processing)
# ============================================================================


def extract_with_gemini(
    image_path: str, api_key: Optional[str] = None
) -> Dict[str, Any]:
  """Extract using Google Gemini vision models."""
  from google import genai
  from google.genai import types

  api_key = api_key or os.environ.get("LANGEXTRACT_API_KEY")
  if not api_key:
    raise ValueError("LANGEXTRACT_API_KEY required for Gemini")

  client = genai.Client(api_key=api_key)

  with open(image_path, "rb") as f:
    image_bytes = f.read()

  response = client.models.generate_content(
      model="gemini-2.0-flash-exp",
      contents=[
          types.Part.from_bytes(
              data=image_bytes,
              mime_type=f"image/{Path(image_path).suffix[1:]}",
          ),
          get_extraction_prompt(),
      ],
  )

  return parse_json_response(response.text)


def extract_with_openai_vision(
    image_path: str, api_key: Optional[str] = None
) -> Dict[str, Any]:
  """Extract using OpenAI GPT-4V/GPT-4o."""
  try:
    from openai import OpenAI
  except ImportError:
    raise ImportError(
        "OpenAI not installed. Install with: pip install openai"
    )

  api_key = api_key or os.environ.get("OPENAI_API_KEY")
  if not api_key:
    raise ValueError("OPENAI_API_KEY required")

  client = OpenAI(api_key=api_key)

  # Encode image to base64
  with open(image_path, "rb") as f:
    image_data = base64.b64encode(f.read()).decode("utf-8")

  image_ext = Path(image_path).suffix[1:].lower()
  mime_type = f"image/{image_ext if image_ext != 'jpg' else 'jpeg'}"

  response = client.chat.completions.create(
      model="gpt-4o",  # or "gpt-4-vision-preview"
      messages=[
          {
              "role": "user",
              "content": [
                  {"type": "text", "text": get_extraction_prompt()},
                  {
                      "type": "image_url",
                      "image_url": {
                          "url": f"data:{mime_type};base64,{image_data}"
                      },
                  },
              ],
          }
      ],
      max_tokens=4096,
  )

  return parse_json_response(response.choices[0].message.content)


def extract_with_claude_vision(
    image_path: str, api_key: Optional[str] = None
) -> Dict[str, Any]:
  """Extract using Anthropic Claude vision models."""
  try:
    import anthropic
  except ImportError:
    raise ImportError(
        "Anthropic SDK not installed. Install with: pip install anthropic"
    )

  api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
  if not api_key:
    raise ValueError("ANTHROPIC_API_KEY required")

  client = anthropic.Anthropic(api_key=api_key)

  # Read and encode image
  with open(image_path, "rb") as f:
    image_data = base64.standard_b64encode(f.read()).decode("utf-8")

  image_ext = Path(image_path).suffix[1:].lower()
  media_type = f"image/{image_ext if image_ext != 'jpg' else 'jpeg'}"

  message = client.messages.create(
      model="claude-3-5-sonnet-20241022",  # or claude-3-opus-20240229
      max_tokens=4096,
      messages=[
          {
              "role": "user",
              "content": [
                  {
                      "type": "image",
                      "source": {
                          "type": "base64",
                          "media_type": media_type,
                          "data": image_data,
                      },
                  },
                  {"type": "text", "text": get_extraction_prompt()},
              ],
          }
      ],
  )

  return parse_json_response(message.content[0].text)


def extract_with_ollama_vision(
    image_path: str, model: str = "llava:13b"
) -> Dict[str, Any]:
  """Extract using local vision models via Ollama (e.g., LLaVA)."""
  try:
    import ollama
  except ImportError:
    raise ImportError("Ollama not installed. Install with: pip install ollama")

  # Read image
  with open(image_path, "rb") as f:
    image_data = f.read()

  response = ollama.chat(
      model=model,
      messages=[
          {
              "role": "user",
              "content": get_extraction_prompt(),
              "images": [image_data],
          }
      ],
  )

  return parse_json_response(response["message"]["content"])


# ============================================================================
# OCR + Text LLM Pipeline (Two-Step Approach)
# ============================================================================


def extract_text_with_paddleocr(image_path: str) -> str:
  """Extract text from image using PaddleOCR (best for Chinese)."""
  try:
    from paddleocr import PaddleOCR
  except ImportError:
    raise ImportError(
        "PaddleOCR not installed. Install with:\n"
        "  pip install paddleocr paddlepaddle"
    )

  # Initialize PaddleOCR (Chinese + English)
  ocr = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)

  result = ocr.ocr(image_path, cls=True)

  # Extract text from OCR results
  text_lines = []
  for line_result in result[0]:
    text = line_result[1][0]  # Get recognized text
    text_lines.append(text)

  return "\n".join(text_lines)


def extract_text_with_easyocr(image_path: str) -> str:
  """Extract text using EasyOCR."""
  try:
    import easyocr
  except ImportError:
    raise ImportError("EasyOCR not installed. Install with: pip install easyocr")

  reader = easyocr.Reader(["ch_sim", "en"])  # Chinese simplified + English
  result = reader.readtext(image_path)

  # Extract text
  text_lines = [text for (_, text, _) in result]
  return "\n".join(text_lines)


def extract_text_with_tesseract(image_path: str) -> str:
  """Extract text using Tesseract OCR."""
  try:
    import pytesseract
    from PIL import Image
  except ImportError:
    raise ImportError(
        "Tesseract dependencies not installed. Install with:\n"
        "  pip install pytesseract pillow\n"
        "  And install Tesseract: apt-get install tesseract-ocr tesseract-ocr-chi-sim"
    )

  image = Image.open(image_path)
  # Use Chinese simplified + English
  text = pytesseract.image_to_string(image, lang="chi_sim+eng")
  return text


def extract_with_ocr_and_llm(
    image_path: str,
    ocr_backend: str = "paddleocr",
    llm_backend: str = "ollama",
    model: str = "qwen2.5:7b",
    api_key: Optional[str] = None,
) -> Dict[str, Any]:
  """Two-step extraction: OCR then LLM processing.

  Args:
      image_path: Path to image
      ocr_backend: 'paddleocr', 'easyocr', or 'tesseract'
      llm_backend: 'ollama', 'gemini', 'openai', or 'claude'
      model: Model name for the LLM
      api_key: API key (if needed)

  Returns:
      Extracted structured data
  """
  # Step 1: OCR to extract text
  print(f"Step 1: Extracting text with {ocr_backend}...")
  if ocr_backend == "paddleocr":
    text = extract_text_with_paddleocr(image_path)
  elif ocr_backend == "easyocr":
    text = extract_text_with_easyocr(image_path)
  elif ocr_backend == "tesseract":
    text = extract_text_with_tesseract(image_path)
  else:
    raise ValueError(f"Unknown OCR backend: {ocr_backend}")

  print(f"Extracted {len(text)} characters of text")

  # Step 2: Use LLM to structure the text
  print(f"Step 2: Structuring with {llm_backend} ({model})...")
  prompt = get_extraction_prompt() + f"\n\nDocument text:\n{text}"

  if llm_backend == "ollama":
    result = extract_with_ollama_text(prompt, model)
  elif llm_backend == "gemini":
    result = extract_with_gemini_text(prompt, model, api_key)
  elif llm_backend == "openai":
    result = extract_with_openai_text(prompt, model, api_key)
  elif llm_backend == "claude":
    result = extract_with_claude_text(prompt, model, api_key)
  else:
    raise ValueError(f"Unknown LLM backend: {llm_backend}")

  return result


def extract_with_ollama_text(prompt: str, model: str) -> Dict[str, Any]:
  """Extract using local Ollama text model."""
  try:
    import ollama
  except ImportError:
    raise ImportError("Ollama not installed. Install with: pip install ollama")

  response = ollama.chat(
      model=model, messages=[{"role": "user", "content": prompt}]
  )

  return parse_json_response(response["message"]["content"])


def extract_with_gemini_text(
    prompt: str, model: str, api_key: Optional[str]
) -> Dict[str, Any]:
  """Extract using Gemini text model."""
  from google import genai

  api_key = api_key or os.environ.get("LANGEXTRACT_API_KEY")
  client = genai.Client(api_key=api_key)

  response = client.models.generate_content(model=model, contents=prompt)

  return parse_json_response(response.text)


def extract_with_openai_text(
    prompt: str, model: str, api_key: Optional[str]
) -> Dict[str, Any]:
  """Extract using OpenAI text model."""
  from openai import OpenAI

  api_key = api_key or os.environ.get("OPENAI_API_KEY")
  client = OpenAI(api_key=api_key)

  response = client.chat.completions.create(
      model=model, messages=[{"role": "user", "content": prompt}]
  )

  return parse_json_response(response.choices[0].message.content)


def extract_with_claude_text(
    prompt: str, model: str, api_key: Optional[str]
) -> Dict[str, Any]:
  """Extract using Claude text model."""
  import anthropic

  api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
  client = anthropic.Anthropic(api_key=api_key)

  message = client.messages.create(
      model=model, max_tokens=4096, messages=[{"role": "user", "content": prompt}]
  )

  return parse_json_response(message.content[0].text)


# ============================================================================
# Shared Utilities
# ============================================================================


def get_extraction_prompt() -> str:
  """Get the extraction prompt for insurance reports."""
  return """
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
      "headers": ["指标名称", "本季度数", "上季度数"],
      "rows": [
        {
          "指标名称": "核心偿付能力充足率",
          "本季度数": "148.54%",
          "上季度数": "147.71%"
        }
      ]
    }
  ]
}
```

请只返回JSON，不要包含其他解释文字。
"""


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
    print(f"Failed to parse JSON: {e}")
    print(f"Raw response:\n{text}")
    raise


# ============================================================================
# Main Entry Point
# ============================================================================


def main():
  parser = argparse.ArgumentParser(
      description="Extract insurance report data using various LLMs"
  )
  parser.add_argument("--image", type=str, required=True, help="Image file path")
  parser.add_argument(
      "--backend",
      type=str,
      choices=[
          "gemini",
          "openai-vision",
          "claude-vision",
          "ollama-vision",
          "ocr-llm",
      ],
      default="gemini",
      help="Extraction backend to use",
  )

  # OCR + LLM specific options
  parser.add_argument(
      "--ocr",
      type=str,
      choices=["paddleocr", "easyocr", "tesseract"],
      default="paddleocr",
      help="OCR backend (for ocr-llm mode)",
  )
  parser.add_argument(
      "--llm",
      type=str,
      choices=["ollama", "gemini", "openai", "claude"],
      default="ollama",
      help="LLM backend (for ocr-llm mode)",
  )
  parser.add_argument(
      "--model",
      type=str,
      help="Model name (e.g., qwen2.5:7b, llava:13b, gpt-4o)",
  )
  parser.add_argument("--api-key", type=str, help="API key for cloud services")
  parser.add_argument(
      "--output",
      type=str,
      default="result.json",
      help="Output JSON file",
  )

  args = parser.parse_args()

  # Set default models if not specified
  if not args.model:
    model_defaults = {
        "gemini": "gemini-2.0-flash-exp",
        "openai-vision": "gpt-4o",
        "claude-vision": "claude-3-5-sonnet-20241022",
        "ollama-vision": "llava:13b",
        "ocr-llm": "qwen2.5:7b" if args.llm == "ollama" else None,
    }
    args.model = model_defaults.get(args.backend)

  print(f"Processing: {args.image}")
  print(f"Backend: {args.backend}")
  if args.backend == "ocr-llm":
    print(f"OCR: {args.ocr}, LLM: {args.llm}, Model: {args.model}")
  elif args.model:
    print(f"Model: {args.model}")

  # Extract based on backend
  try:
    if args.backend == "gemini":
      result = extract_with_gemini(args.image, args.api_key)
    elif args.backend == "openai-vision":
      result = extract_with_openai_vision(args.image, args.api_key)
    elif args.backend == "claude-vision":
      result = extract_with_claude_vision(args.image, args.api_key)
    elif args.backend == "ollama-vision":
      result = extract_with_ollama_vision(args.image, args.model)
    elif args.backend == "ocr-llm":
      result = extract_with_ocr_and_llm(
          args.image, args.ocr, args.llm, args.model, args.api_key
      )
    else:
      raise ValueError(f"Unknown backend: {args.backend}")

    # Display and save results
    print("\n✓ Extraction complete!")
    print(f"\nCompany: {result.get('company_name', 'N/A')}")
    print(f"Period: {result.get('report_period', 'N/A')}")
    print(f"Tables: {len(result.get('solvency_tables', []))}")

    with open(args.output, "w", encoding="utf-8") as f:
      json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved to: {args.output}")

  except Exception as e:
    print(f"\n✗ Error: {e}")
    raise


if __name__ == "__main__":
  main()
