# 多线程 PDF 处理指南

## 概述

`process_pdf_multithreaded.py` 是一个支持多线程的 PDF 批处理工具，专为 Windows 系统优化，同时兼容 Linux 和 macOS。

### 核心特性

✅ **多线程并发处理** - 使用线程池同时处理多个 PDF 文件
✅ **API 速率限制** - 确保 Gemini API 调用间隔至少 1 秒（可配置）
✅ **实时进度显示** - 进度条 + 统计信息
✅ **自动重试机制** - 失败时自动重试（指数退避）
✅ **增量保存** - 每处理完一个文件立即保存，防止数据丢失
✅ **Windows 路径兼容** - 完全支持 Windows 文件路径
✅ **线程安全** - 使用锁机制保证多线程安全

## 为什么需要速率限制？

Gemini API 有速率限制（通常是 **60 requests/minute = 1 request/second**）。如果不加限制，多线程可能导致：
- ❌ API 请求被拒绝（429 错误）
- ❌ 账号被暂时封禁
- ❌ 浪费 API 配额

**本工具的解决方案**：
- 使用 `RateLimiter` 类确保 API 调用间隔 ≥ 1 秒
- 多线程只用于并发处理文件 I/O 和数据解析
- API 调用串行化，但其他操作并行化

## 性能对比

### 单线程版本 (process_pdf_optimized.py)

```
处理 100 个 PDF 文件
├─ 读取 PDF: 2 秒 (串行)
├─ API 调用: 100 秒 (受速率限制)
└─ 保存数据: 1 秒 (串行)
总耗时: ~103 秒
```

### 多线程版本 (process_pdf_multithreaded.py)

```
处理 100 个 PDF 文件（4 个工作线程）
├─ 读取 PDF: 0.5 秒 (并行)
├─ API 调用: 100 秒 (受速率限制，但其他操作并行)
└─ 保存数据: 0.25 秒 (并行)
总耗时: ~100.75 秒

实际提升: 文件 I/O 时间减少 75%
```

**注意**：由于 API 速率限制，总时间主要由 API 调用决定，但多线程可以：
1. 减少文件读写时间
2. 提高 CPU 利用率
3. 更快响应（先完成的先保存）

## 使用方法

### Windows 系统

```cmd
# 方法 1: 使用命令行参数传递 API Key
python process_pdf_multithreaded.py --pdf_dir "C:\Reports" --api_key YOUR_API_KEY --workers 4

# 方法 2: 设置环境变量（推荐）
set GEMINI_API_KEY=YOUR_API_KEY
python process_pdf_multithreaded.py --pdf_dir "C:\Reports" --workers 4

# 处理单个文件
python process_pdf_multithreaded.py --pdf_dir "C:\Reports\report.pdf" --workers 1
```

### Linux / macOS

```bash
# 设置环境变量
export GEMINI_API_KEY=YOUR_API_KEY

# 处理目录
python process_pdf_multithreaded.py --pdf_dir ./reports --workers 4

# 处理单个文件
python process_pdf_multithreaded.py --pdf_dir ./report.pdf --workers 1
```

## 参数说明

### 必需参数

| 参数 | 说明 | 示例 |
|------|------|------|
| `--pdf_dir` | PDF 文件或目录路径 | `./reports` 或 `report.pdf` |

### 可选参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--output` | `extracted_data.jsonl` | 输出文件路径 |
| `--api_key` | 环境变量 `GEMINI_API_KEY` | Gemini API Key |
| `--model` | `gemini-2.0-flash-exp` | Gemini 模型名称 |
| `--workers` | `4` | 工作线程数量 |
| `--rate_limit` | `1.0` | API 调用最小间隔（秒） |

## 工作线程数量建议

### 如何选择 `--workers` 参数？

| CPU 核心数 | 建议工作线程 | 说明 |
|-----------|-------------|------|
| 2 核 | `--workers 2` | 避免过载 |
| 4 核 | `--workers 4` | **推荐** |
| 8 核+ | `--workers 6` | 无需太多（API 是瓶颈） |

**重要提示**：
- ⚠️ 不要设置过多线程！由于 API 速率限制，超过 4-6 个线程意义不大
- ✅ 推荐值：**4 个工作线程**
- 📊 更多线程 ≠ 更快速度（API 调用是瓶颈）

## 速率限制配置

### 调整 API 调用频率

```bash
# 默认：每秒最多 1 次 API 调用
python process_pdf_multithreaded.py --pdf_dir ./reports --rate_limit 1.0

# 更保守：每 2 秒调用 1 次（避免触发限制）
python process_pdf_multithreaded.py --pdf_dir ./reports --rate_limit 2.0

# 更激进：每 0.5 秒调用 1 次（可能触发限制）⚠️
python process_pdf_multithreaded.py --pdf_dir ./reports --rate_limit 0.5
```

**建议**：
- 💰 **免费账户**：`--rate_limit 2.0`（保守）
- 💳 **付费账户**：`--rate_limit 1.0`（默认）
- 🚀 **高级账户**：`--rate_limit 0.5`（测试后使用）

## 实时进度显示

运行时会看到实时进度条：

```
进度: [████████████████████░░░░░░░░░░░░░░░░░░░░] 52.0% | 52/100 | ✓ 50 ✗ 2 | 用时: 1m 32s | 剩余: 1m 28s | 速度: 0.56 PDF/s
```

各部分说明：
- `[████░░░░]` - 进度条
- `52.0%` - 完成百分比
- `52/100` - 已处理/总数
- `✓ 50` - 成功数量
- `✗ 2` - 失败数量
- `用时: 1m 32s` - 已用时间
- `剩余: 1m 28s` - 预计剩余时间
- `速度: 0.56 PDF/s` - 当前处理速度

## 完整示例

### 示例 1: Windows 批量处理

```cmd
@echo off
REM 设置 API Key
set GEMINI_API_KEY=your-api-key-here

REM 处理 PDF 目录
python process_pdf_multithreaded.py ^
  --pdf_dir "C:\Users\YourName\Documents\Reports" ^
  --output "C:\Users\YourName\Documents\extracted_data.jsonl" ^
  --workers 4 ^
  --rate_limit 1.0 ^
  --model gemini-2.0-flash-exp

REM 处理完成后生成可视化
python visualize_solvency_data.py ^
  --input "C:\Users\YourName\Documents\extracted_data.jsonl" ^
  --output "C:\Users\YourName\Documents\dashboard.html"

REM 自动打开浏览器
start "" "C:\Users\YourName\Documents\dashboard.html"

echo 处理完成！
pause
```

### 示例 2: Linux/macOS 批量处理

```bash
#!/bin/bash

# 设置 API Key
export GEMINI_API_KEY=your-api-key-here

# 处理 PDF 目录
python process_pdf_multithreaded.py \
  --pdf_dir ~/Documents/Reports \
  --output ~/Documents/extracted_data.jsonl \
  --workers 4 \
  --rate_limit 1.0 \
  --model gemini-2.0-flash-exp

# 处理完成后生成可视化
python visualize_solvency_data.py \
  --input ~/Documents/extracted_data.jsonl \
  --output ~/Documents/dashboard.html

# 自动打开浏览器
open ~/Documents/dashboard.html  # macOS
# xdg-open ~/Documents/dashboard.html  # Linux

echo "处理完成！"
```

### 示例 3: 处理大量文件（分批）

如果有超过 500 个 PDF 文件，建议分批处理：

```python
# batch_process.py
import subprocess
from pathlib import Path

pdf_dir = Path("./reports")
pdf_files = list(pdf_dir.glob("*.pdf"))

# 每批处理 100 个文件
batch_size = 100
for i in range(0, len(pdf_files), batch_size):
    batch = pdf_files[i:i+batch_size]

    # 创建临时目录
    batch_dir = Path(f"./temp_batch_{i//batch_size}")
    batch_dir.mkdir(exist_ok=True)

    # 复制文件到临时目录
    for pdf in batch:
        import shutil
        shutil.copy(pdf, batch_dir / pdf.name)

    # 处理这一批
    output_file = f"batch_{i//batch_size}.jsonl"
    subprocess.run([
        "python", "process_pdf_multithreaded.py",
        "--pdf_dir", str(batch_dir),
        "--output", output_file,
        "--workers", "4"
    ])

    print(f"完成批次 {i//batch_size + 1}")

# 合并所有输出文件
with open("all_extracted_data.jsonl", "w", encoding="utf-8") as outfile:
    for i in range(0, len(pdf_files), batch_size):
        batch_file = f"batch_{i//batch_size}.jsonl"
        with open(batch_file, "r", encoding="utf-8") as infile:
            outfile.write(infile.read())
```

## 技术实现细节

### 线程安全的速率限制器

```python
class RateLimiter:
    def __init__(self, min_interval: float = 1.0):
        self.min_interval = min_interval
        self.last_call_time = 0
        self.lock = Lock()  # 线程锁

    def wait(self):
        with self.lock:  # 确保只有一个线程通过
            current_time = time.time()
            time_since_last_call = current_time - self.last_call_time

            if time_since_last_call < self.min_interval:
                sleep_time = self.min_interval - time_since_last_call
                time.sleep(sleep_time)

            self.last_call_time = time.time()
```

**工作原理**：
1. 每次 API 调用前调用 `rate_limiter.wait()`
2. 如果距离上次调用 < 1 秒，则等待
3. 使用线程锁确保多线程安全
4. 记录最后调用时间

### 线程安全的文件写入

```python
output_lock = Lock()

# 在每个线程中
with output_lock:
    with open(output_file, 'a', encoding='utf-8') as f:
        f.write(json.dumps(result, ensure_ascii=False) + '\n')
```

**防止问题**：
- ❌ 多线程同时写入 → 数据混乱
- ✅ 使用锁机制 → 一次只有一个线程写入

### 自动重试机制

```python
for attempt in range(max_retries):
    try:
        # API 调用
        result = call_api()
        return result
    except Exception as e:
        if attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # 指数退避: 2s, 4s, 8s
            continue
        else:
            return None
```

**重试策略**：
- 最多重试 3 次
- 使用指数退避：2秒 → 4秒 → 8秒
- 避免立即重试导致更多失败

## 故障排查

### 问题 1: 速度没有提升

**症状**：多线程版本和单线程版本速度相同

**原因**：API 速率限制是瓶颈，而非文件 I/O

**解决方法**：
- 这是**正常现象**！API 调用时间占 95%+
- 多线程主要优势是减少文件 I/O 等待时间
- 如果 PDF 文件很小，提升可能不明显

### 问题 2: 出现 429 错误（Too Many Requests）

**症状**：API 返回 429 错误

**原因**：速率限制设置太激进

**解决方法**：
```bash
# 增加 rate_limit 值
python process_pdf_multithreaded.py --pdf_dir ./reports --rate_limit 2.0
```

### 问题 3: 内存占用过高

**症状**：程序占用大量内存

**原因**：工作线程太多，同时读取多个大型 PDF

**解决方法**：
```bash
# 减少工作线程数量
python process_pdf_multithreaded.py --pdf_dir ./reports --workers 2
```

### 问题 4: Windows 路径错误

**症状**：`FileNotFoundError` 或路径错误

**解决方法**：
```cmd
REM 使用双引号包裹路径
python process_pdf_multithreaded.py --pdf_dir "C:\Program Files\Reports"

REM 或使用原始字符串（反斜杠不转义）
python process_pdf_multithreaded.py --pdf_dir C:/Program Files/Reports
```

### 问题 5: 进度条显示乱码

**症状**：Windows CMD 中进度条显示为 `?` 或乱码

**解决方法**：
```cmd
REM 切换到 UTF-8 代码页
chcp 65001

REM 然后运行脚本
python process_pdf_multithreaded.py --pdf_dir ./reports
```

## 性能优化建议

### 1. 使用 SSD 存储 PDF 文件
- HDD: ~100 MB/s
- SSD: ~500 MB/s
- **提升**: 文件读取速度 5x

### 2. 合理设置工作线程数
- CPU 密集型：线程数 = CPU 核心数
- I/O 密集型：线程数 = CPU 核心数 × 2
- **本场景**：API 调用是瓶颈，推荐 4 个线程

### 3. 使用更快的 Gemini 模型
```bash
# gemini-2.0-flash-exp (最快，推荐)
--model gemini-2.0-flash-exp

# gemini-1.5-flash (快速)
--model gemini-1.5-flash

# gemini-1.5-pro (准确但慢)
--model gemini-1.5-pro
```

### 4. 批量处理策略
- 小文件（< 100 个）：直接处理
- 中等文件（100-500 个）：单批处理
- 大量文件（> 500 个）：分批处理

## 成本估算

### Gemini API 定价（2024年参考）

| 模型 | 输入成本 | 输出成本 |
|------|---------|---------|
| gemini-2.0-flash-exp | 免费（有限额） | 免费（有限额） |
| gemini-1.5-flash | $0.075/1M tokens | $0.30/1M tokens |
| gemini-1.5-pro | $1.25/1M tokens | $5.00/1M tokens |

### 成本计算示例

假设：
- 每个 PDF 平均 30 页
- 每次 API 调用平均消耗 50K tokens（输入）+ 2K tokens（输出）

```
处理 100 个 PDF:
输入: 100 × 50K = 5M tokens → $0.375 (flash) 或 $6.25 (pro)
输出: 100 × 2K = 0.2M tokens → $0.06 (flash) 或 $1.00 (pro)

总成本:
- gemini-1.5-flash: ~$0.44
- gemini-1.5-pro: ~$7.25
- gemini-2.0-flash-exp: 免费（有限额）
```

**建议**：使用 `gemini-2.0-flash-exp` 进行测试，满意后可切换到付费模型。

## 总结

### 适用场景

✅ **适合使用多线程版本**：
- 处理大量 PDF 文件（> 10 个）
- PDF 文件较大（> 5MB）
- 需要实时进度反馈
- Windows 系统环境

✅ **适合使用单线程版本**：
- 处理少量 PDF 文件（< 5 个）
- PDF 文件较小（< 1MB）
- 简单脚本，不需要复杂配置

### 关键要点

1. **速率限制是必需的** - 保护你的 API 配额
2. **4 个工作线程最优** - 更多线程不会更快
3. **使用 gemini-2.0-flash-exp** - 免费且快速
4. **增量保存** - 防止数据丢失
5. **自动重试** - 提高成功率

### 下一步

处理完 PDF 后，使用可视化工具：
```bash
python visualize_solvency_data.py --input extracted_data.jsonl --output dashboard.html
```

或提取关键指标：
```bash
python extract_solvency_indicators.py --input extracted_data.jsonl --output indicators.xlsx
```
