#!/usr/bin/env python3
"""Test script to find optimal worker thread count for your CPU.

This script processes a small batch of PDFs with different worker counts
and measures performance to help determine the best configuration.

Usage:
    python test_optimal_workers.py --pdf_dir ./test_pdfs --api_key YOUR_KEY
"""

import argparse
import json
import subprocess
import time
from pathlib import Path


def run_test(pdf_dir: Path, workers: int, api_key: str) -> dict:
    """Run processing with specified worker count and measure performance."""
    output_file = f"test_output_workers_{workers}.jsonl"

    print(f"\n{'='*60}")
    print(f"测试配置: {workers} 个工作线程")
    print(f"{'='*60}")

    start_time = time.time()

    try:
        result = subprocess.run(
            [
                "python",
                "process_pdf_multithreaded.py",
                "--pdf_dir", str(pdf_dir),
                "--output", output_file,
                "--workers", str(workers),
                "--rate_limit", "0.06",
                "--api_key", api_key,
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes timeout
        )

        elapsed = time.time() - start_time

        # Count processed files
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                processed_count = sum(1 for _ in f)
        except FileNotFoundError:
            processed_count = 0

        # Clean up output file
        Path(output_file).unlink(missing_ok=True)

        return {
            'workers': workers,
            'elapsed': elapsed,
            'processed': processed_count,
            'rate': processed_count / elapsed if elapsed > 0 else 0,
            'success': result.returncode == 0,
            'error': result.stderr if result.returncode != 0 else None,
        }

    except subprocess.TimeoutExpired:
        return {
            'workers': workers,
            'elapsed': 300,
            'processed': 0,
            'rate': 0,
            'success': False,
            'error': 'Timeout (> 5 minutes)',
        }
    except Exception as e:
        return {
            'workers': workers,
            'elapsed': 0,
            'processed': 0,
            'rate': 0,
            'success': False,
            'error': str(e),
        }


def main():
    parser = argparse.ArgumentParser(
        description='Test optimal worker thread count'
    )
    parser.add_argument(
        '--pdf_dir',
        type=str,
        required=True,
        help='Directory with test PDF files (recommend 5-10 files)',
    )
    parser.add_argument(
        '--api_key',
        type=str,
        required=True,
        help='Gemini API key',
    )
    parser.add_argument(
        '--worker_counts',
        type=str,
        default='2,4,6,8,10',
        help='Comma-separated worker counts to test (default: 2,4,6,8,10)',
    )

    args = parser.parse_args()

    pdf_dir = Path(args.pdf_dir)
    if not pdf_dir.exists():
        print(f"❌ 错误：目录不存在 {pdf_dir}")
        return 1

    # Get PDF count
    pdf_files = list(pdf_dir.glob('*.pdf'))
    if len(pdf_files) < 3:
        print(f"⚠️  警告：建议至少 5-10 个 PDF 文件进行测试")
        print(f"   当前只有 {len(pdf_files)} 个文件")

    print(f"\n📊 性能测试开始")
    print(f"   PDF 文件数: {len(pdf_files)}")
    print(f"   测试线程数: {args.worker_counts}")
    print()

    # Parse worker counts
    worker_counts = [int(x.strip()) for x in args.worker_counts.split(',')]

    # Run tests
    results = []
    for workers in worker_counts:
        result = run_test(pdf_dir, workers, args.api_key)
        results.append(result)

        if result['success']:
            print(f"✅ 完成: {result['elapsed']:.1f}秒, "
                  f"{result['rate']:.2f} PDF/秒")
        else:
            print(f"❌ 失败: {result['error']}")

    # Display summary
    print(f"\n{'='*70}")
    print(f"📈 测试结果汇总")
    print(f"{'='*70}")
    print(f"{'线程数':<8} {'耗时(秒)':<12} {'速度(PDF/s)':<15} {'状态':<10}")
    print(f"{'-'*70}")

    best_result = None
    best_rate = 0

    for result in results:
        if result['success']:
            status = '✅ 成功'
            if result['rate'] > best_rate:
                best_rate = result['rate']
                best_result = result
        else:
            status = '❌ 失败'

        print(f"{result['workers']:<8} "
              f"{result['elapsed']:<12.2f} "
              f"{result['rate']:<15.2f} "
              f"{status:<10}")

    print(f"{'-'*70}")

    # Recommendation
    if best_result:
        print(f"\n🎯 推荐配置：")
        print(f"   --workers {best_result['workers']}")
        print(f"   ")
        print(f"   理由: 最快处理速度 ({best_result['rate']:.2f} PDF/秒)")
        print(f"\n💡 使用方法：")
        print(f"   python process_pdf_multithreaded.py \\")
        print(f"     --pdf_dir ./reports \\")
        print(f"     --workers {best_result['workers']}")
    else:
        print(f"\n❌ 所有测试都失败了，请检查：")
        print(f"   1. API Key 是否正确")
        print(f"   2. PDF 文件是否有效")
        print(f"   3. 网络连接是否正常")

    print()
    return 0


if __name__ == '__main__':
    exit(main())
