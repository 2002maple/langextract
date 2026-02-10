# Quick Start Guide - 快速开始

5分钟快速上手保险报告数据提取。

## 第一步：安装依赖

```bash
# 进入示例目录
cd examples/insurance_reports

# 安装依赖
pip install -r requirements.txt
```

## 第二步：设置 API Key

从 [Google AI Studio](https://aistudio.google.com/app/apikey) 获取 API key，然后设置环境变量：

```bash
export LANGEXTRACT_API_KEY="your-api-key-here"
```

## 第三步：准备图片

将保险报告的图片（PNG、JPG 等）放在一个目录中：

```bash
# 创建目录
mkdir report_images

# 复制你的报告图片到这个目录
cp /path/to/your/reports/*.png report_images/
```

## 第四步：运行提取

### 单个文件提取

```bash
python extract_insurance_report.py \
  --image report_images/report1.png \
  --output result.jsonl
```

### 批量提取

```bash
python extract_insurance_report.py \
  --image-dir report_images \
  --output all_results.jsonl \
  --csv solvency_ratios.csv
```

## 第五步：查看结果

### JSON 格式查看

```bash
# 查看原始 JSON 数据
cat all_results.jsonl | python -m json.tool

# 或使用 jq
cat all_results.jsonl | jq '.'
```

### CSV 格式查看

直接用 Excel、Google Sheets 或命令行打开：

```bash
# 使用 column 命令美化输出
column -t -s ',' solvency_ratios.csv | less -S
```

## 结果示例

提取的数据包含：

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

## 常见问题

### 1. 如何处理 PDF 文件？

先将 PDF 转换为图片：

```bash
# 使用 ImageMagick
convert -density 300 report.pdf report_page_%d.png
```

### 2. 提取的表格不准确怎么办？

- 使用更高分辨率的图片（至少 300 DPI）
- 确保图片清晰，表格完整可见
- 尝试使用 `gemini-2.0-pro-exp` 模型（更准确但更慢）

### 3. API 调用失败

检查：
- API key 是否正确设置
- 网络连接是否正常
- 是否超过 API 配额限制

### 4. 批量处理大量文件

建议：
- 每批处理 10-20 个文件
- 使用 `gemini-2.0-flash-exp`（更快更便宜）
- 考虑升级到 Tier 2 配额

## 下一步

- 查看 [README.md](README.md) 了解详细文档
- 查看 [example_usage.py](example_usage.py) 了解代码示例
- 自定义提取逻辑以适应你的需求

## 技术支持

遇到问题？
1. 查看 [README.md](README.md) 的 Troubleshooting 部分
2. 检查图片质量和格式
3. 验证 API key 和网络连接
4. 查看错误信息中的详细日志

---

**Happy Extracting! 祝数据提取顺利！** 🚀
