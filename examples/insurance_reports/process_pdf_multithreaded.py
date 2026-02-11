#!/usr/bin/env python3
"""Multi-threaded PDF processing with API rate limiting for Windows.

This script processes multiple insurance PDF files in parallel while respecting
Gemini API rate limits.

Gemini API Rate Limits (as of 2025):
- RPM (Requests per minute): 1000 → 16.67 requests/second
- TPM (Tokens per minute): 1,000,000
- RPD (Requests per day): 10,000
- Concurrent batch requests: 100

Features:
- Thread pool for concurrent file I/O operations
- Rate limiter optimized for 1000 RPM (0.06s/request)
- Progress bar with real-time statistics
- Windows path compatibility
- Automatic retry on failures
- Incremental JSONL output

Usage:
    python process_pdf_multithreaded.py --pdf_dir ./reports --output extracted_data.jsonl --workers 10
"""

import argparse
import json
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Any, Optional

try:
    from google import genai
    from google.genai import types
except ImportError:
    print("错误：需要安装 google-genai 库")
    print("安装命令: pip install google-genai")
    exit(1)


class RateLimiter:
    """Thread-safe rate limiter that ensures minimum interval between calls.

    Optimized for Gemini API limits:
    - 1000 RPM = 16.67 requests/second
    - Default: 0.06 seconds/request (safe margin below limit)
    """

    def __init__(self, min_interval: float = 0.06):
        """
        Initialize rate limiter.

        Args:
            min_interval: Minimum seconds between calls (default: 0.06 for 1000 RPM)
        """
        self.min_interval = min_interval
        self.last_call_time = 0
        self.lock = Lock()

    def wait(self):
        """Wait if necessary to maintain the rate limit."""
        with self.lock:
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time

            if time_since_last_call < self.min_interval:
                sleep_time = self.min_interval - time_since_last_call
                time.sleep(sleep_time)

            self.last_call_time = time.time()


class ProgressTracker:
    """Thread-safe progress tracker for multi-threaded processing."""

    def __init__(self, total: int):
        self.total = total
        self.completed = 0
        self.succeeded = 0
        self.failed = 0
        self.lock = Lock()
        self.start_time = time.time()

    def update(self, success: bool = True):
        """Update progress counters."""
        with self.lock:
            self.completed += 1
            if success:
                self.succeeded += 1
            else:
                self.failed += 1

    def get_stats(self) -> dict:
        """Get current statistics."""
        with self.lock:
            elapsed = time.time() - self.start_time
            rate = self.completed / elapsed if elapsed > 0 else 0
            remaining = self.total - self.completed
            eta = remaining / rate if rate > 0 else 0

            return {
                'total': self.total,
                'completed': self.completed,
                'succeeded': self.succeeded,
                'failed': self.failed,
                'elapsed': elapsed,
                'rate': rate,
                'eta': eta,
            }

    def print_progress(self):
        """Print progress bar and statistics."""
        stats = self.get_stats()
        percentage = (stats['completed'] / stats['total'] * 100) if stats['total'] > 0 else 0

        # Progress bar
        bar_length = 40
        filled = int(bar_length * stats['completed'] / stats['total'])
        bar = '█' * filled + '░' * (bar_length - filled)

        # Format time
        elapsed_str = f"{int(stats['elapsed'] // 60)}m {int(stats['elapsed'] % 60)}s"
        eta_str = f"{int(stats['eta'] // 60)}m {int(stats['eta'] % 60)}s"

        # Print (use \r to overwrite the same line)
        print(
            f"\r进度: [{bar}] {percentage:.1f}% | "
            f"{stats['completed']}/{stats['total']} | "
            f"✓ {stats['succeeded']} ✗ {stats['failed']} | "
            f"用时: {elapsed_str} | 剩余: {eta_str} | "
            f"速度: {stats['rate']:.2f} PDF/s",
            end='',
            flush=True
        )


# Extraction prompt (same as process_pdf_optimized.py)
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
        {"指标名称": "核心偿付能力充足率", "本季度数": "150%", "上季度数": "148%"},
        {"指标名称": "综合偿付能力充足率", "本季度数": "200%", "上季度数": "198%"}
      ]
    }
  ]
}

只返回JSON，不要其他说明文字。"""


def parse_json_response(response_text: str) -> Optional[dict]:
    """Parse JSON from LLM response, handling markdown code blocks."""
    try:
        # Remove markdown code blocks if present
        cleaned = re.sub(r'^```(?:json)?\s*', '', response_text.strip())
        cleaned = re.sub(r'\s*```$', '', cleaned)
        cleaned = cleaned.strip()

        # Parse JSON
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print(f"\n⚠️  JSON 解析错误: {e}")
        print(f"响应文本: {response_text[:200]}...")
        return None


def extract_from_pdf_with_rate_limit(
    pdf_path: Path,
    api_key: str,
    rate_limiter: RateLimiter,
    model: str = "gemini-2.0-flash-exp",
    max_retries: int = 3,
) -> Optional[dict]:
    """
    Extract data from PDF using Gemini API with rate limiting.

    Args:
        pdf_path: Path to PDF file
        api_key: Gemini API key
        rate_limiter: Rate limiter instance
        model: Gemini model name
        max_retries: Maximum number of retry attempts

    Returns:
        Extracted data dict or None if failed
    """
    for attempt in range(max_retries):
        try:
            # Wait for rate limit before making API call
            rate_limiter.wait()

            # Read PDF file
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()

            # Call Gemini API
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=model,
                contents=[
                    types.Part.from_bytes(
                        data=pdf_bytes,
                        mime_type="application/pdf",
                    ),
                    EXTRACTION_PROMPT,
                ],
            )

            # Parse response
            result = parse_json_response(response.text)

            if result:
                # Add metadata
                result["pdf_file"] = pdf_path.name
                return result
            else:
                if attempt < max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    return None

        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                print(f"\n❌ 处理失败 {pdf_path.name}: {e}")
                return None

    return None


def process_single_pdf(
    pdf_path: Path,
    api_key: str,
    rate_limiter: RateLimiter,
    output_file: Path,
    output_lock: Lock,
    progress: ProgressTracker,
    model: str = "gemini-2.0-flash-exp",
) -> bool:
    """
    Process a single PDF file and append result to output file.

    Args:
        pdf_path: Path to PDF file
        api_key: Gemini API key
        rate_limiter: Rate limiter instance
        output_file: Output JSONL file path
        output_lock: Lock for thread-safe file writing
        progress: Progress tracker
        model: Gemini model name

    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract data
        result = extract_from_pdf_with_rate_limit(
            pdf_path=pdf_path,
            api_key=api_key,
            rate_limiter=rate_limiter,
            model=model,
        )

        if result:
            # Thread-safe write to output file
            with output_lock:
                with open(output_file, 'a', encoding='utf-8') as f:
                    f.write(json.dumps(result, ensure_ascii=False) + '\n')

            progress.update(success=True)
            progress.print_progress()
            return True
        else:
            progress.update(success=False)
            progress.print_progress()
            return False

    except Exception as e:
        print(f"\n❌ 错误处理 {pdf_path.name}: {e}")
        progress.update(success=False)
        progress.print_progress()
        return False


def get_pdf_files(pdf_dir: Path) -> list[Path]:
    """Get all PDF files from directory."""
    pdf_files = []

    if pdf_dir.is_file() and pdf_dir.suffix.lower() == '.pdf':
        # Single file
        pdf_files.append(pdf_dir)
    elif pdf_dir.is_dir():
        # Directory - find all PDFs
        pdf_files = list(pdf_dir.glob('**/*.pdf'))
    else:
        raise ValueError(f"路径不存在或不是有效的 PDF 文件/目录: {pdf_dir}")

    return sorted(pdf_files)


def main():
    parser = argparse.ArgumentParser(
        description='Multi-threaded PDF processing with API rate limiting (Windows compatible)'
    )
    parser.add_argument(
        '--pdf_dir',
        type=str,
        required=True,
        help='PDF file or directory containing PDF files',
    )
    parser.add_argument(
        '--output',
        type=str,
        default='extracted_data.jsonl',
        help='Output JSONL file (default: extracted_data.jsonl)',
    )
    parser.add_argument(
        '--api_key',
        type=str,
        help='Gemini API key (or set GEMINI_API_KEY environment variable)',
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gemini-2.0-flash-exp',
        help='Gemini model name (default: gemini-2.0-flash-exp)',
    )
    parser.add_argument(
        '--workers',
        type=int,
        default=10,
        help='Number of worker threads (default: 10, optimized for 1000 RPM)',
    )
    parser.add_argument(
        '--rate_limit',
        type=float,
        default=0.06,
        help='Minimum seconds between API calls (default: 0.06 for 1000 RPM limit)',
    )

    args = parser.parse_args()

    # Get API key
    api_key = args.api_key or os.getenv('GEMINI_API_KEY')
    if not api_key:
        print('❌ 错误：需要提供 Gemini API key')
        print('   方法1: --api_key YOUR_API_KEY')
        print('   方法2: 设置环境变量 GEMINI_API_KEY')
        return 1

    # Convert paths (Windows compatible)
    pdf_dir = Path(args.pdf_dir)
    output_file = Path(args.output)

    # Get PDF files
    print(f'📂 扫描 PDF 文件: {pdf_dir}')
    try:
        pdf_files = get_pdf_files(pdf_dir)
    except ValueError as e:
        print(f'❌ {e}')
        return 1

    if not pdf_files:
        print(f'❌ 未找到 PDF 文件')
        return 1

    print(f'✓ 找到 {len(pdf_files)} 个 PDF 文件')
    print(f'⚙️  配置: {args.workers} 个工作线程, API 限速 {args.rate_limit} 秒/次')
    print(f'📤 输出文件: {output_file}')
    print()

    # Create output file (overwrite if exists)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    output_file.write_text('', encoding='utf-8')

    # Initialize components
    rate_limiter = RateLimiter(min_interval=args.rate_limit)
    output_lock = Lock()
    progress = ProgressTracker(total=len(pdf_files))

    print('🚀 开始处理...\n')

    # Process PDFs using thread pool
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # Submit all tasks
        futures = {
            executor.submit(
                process_single_pdf,
                pdf_path=pdf_file,
                api_key=api_key,
                rate_limiter=rate_limiter,
                output_file=output_file,
                output_lock=output_lock,
                progress=progress,
                model=args.model,
            ): pdf_file
            for pdf_file in pdf_files
        }

        # Wait for completion
        for future in as_completed(futures):
            pdf_file = futures[future]
            try:
                future.result()
            except Exception as e:
                print(f"\n❌ 未预期的错误 {pdf_file.name}: {e}")
                progress.update(success=False)

    # Final statistics
    print('\n\n' + '=' * 70)
    stats = progress.get_stats()
    print(f'✅ 处理完成！')
    print(f'   总数: {stats["total"]}')
    print(f'   成功: {stats["succeeded"]} ✓')
    print(f'   失败: {stats["failed"]} ✗')
    print(f'   用时: {int(stats["elapsed"] // 60)}m {int(stats["elapsed"] % 60)}s')
    print(f'   平均速度: {stats["rate"]:.2f} PDF/s')
    print(f'   输出: {output_file}')
    print('=' * 70)

    return 0


if __name__ == '__main__':
    exit(main())
