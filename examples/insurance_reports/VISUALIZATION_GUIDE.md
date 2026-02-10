# 保险报告数据可视化指南

## 概述

`visualize_solvency_data.py` 脚本可以将提取的保险偿付能力数据生成为交互式 HTML 仪表板，让你可以在浏览器中方便地浏览和分析数据。

## 功能特性

### 📊 交互式仪表板
- **报告选择器**：下拉菜单快速切换不同公司和时间段的报告
- **基本信息卡片**：显示公司名称、报告期间、PDF 文件名
- **关键指标面板**：以卡片形式展示核心偿付能力指标
  - 核心偿付能力充足率
  - 综合偿付能力充足率
  - 实际资本
  - 最低资本
- **完整表格视图**：展示所有从 PDF 中提取的表格数据

### 🎨 美观的界面设计
- 渐变色背景和现代化 UI
- 响应式设计，支持移动设备
- 悬停动画效果
- 自动格式化数值（千分位分隔符）

## 使用方法

### 基本用法

```bash
python visualize_solvency_data.py --input extracted_data.jsonl --output dashboard.html
```

### 参数说明

- `--input`：输入的 JSONL 文件路径（默认：`extracted_data.jsonl`）
- `--output`：输出的 HTML 文件路径（默认：`solvency_dashboard.html`）

### 示例

```bash
# 使用默认文件名
python visualize_solvency_data.py

# 自定义输入输出文件
python visualize_solvency_data.py \
  --input my_reports.jsonl \
  --output my_dashboard.html

# 处理特定目录的数据
python visualize_solvency_data.py \
  --input /path/to/data/reports.jsonl \
  --output /path/to/output/report_dashboard.html
```

## 工作流程

### 完整的数据处理和可视化流程

```bash
# 步骤 1: 从 PDF 提取数据
python process_pdf_optimized.py \
  --pdf_dir ./reports \
  --output extracted_data.jsonl

# 步骤 2: 提取关键指标（可选）
python extract_solvency_indicators.py \
  --input extracted_data.jsonl \
  --output solvency_indicators.xlsx

# 步骤 3: 生成可视化仪表板
python visualize_solvency_data.py \
  --input extracted_data.jsonl \
  --output dashboard.html

# 步骤 4: 在浏览器中打开
# macOS
open dashboard.html

# Linux
xdg-open dashboard.html

# Windows
start dashboard.html
```

## 输出示例

生成的 HTML 文件包含：

1. **顶部报告选择器**
   ```
   选择报告：[中国人民保险集团股份有限公司 - 2025年上半年度 ▼]
   ```

2. **基本信息卡片**（紫色渐变背景）
   ```
   📋 公司名称：中国人民保险集团股份有限公司
   📅 报告期间：2025年上半年度
   📄 文件名称：专项信息_中国人民保险集团...pdf
   ```

3. **关键指标卡片**（网格布局）
   ```
   ┌─────────────────────┐  ┌─────────────────────┐
   │ 核心偿付能力充足率    │  │ 综合偿付能力充足率    │
   │ 148.54%             │  │ 198.76%             │
   └─────────────────────┘  └─────────────────────┘

   ┌─────────────────────┐  ┌─────────────────────┐
   │ 实际资本             │  │ 最低资本             │
   │ 85,234,567.89       │  │ 42,891,234.56       │
   └─────────────────────┘  └─────────────────────┘
   ```

4. **所有提取的表格**（可滚动表格视图）

## 与 LangExtract 可视化的对比

### LangExtract 原生可视化
- **适用场景**：文本实体提取
- **功能**：高亮显示文本中的实体，显示字符位置
- **交互**：播放/暂停动画，逐个查看实体
- **使用方式**：
  ```python
  import langextract as lx
  doc = lx.extract(...)
  lx.visualize(doc)  # 在 Jupyter Notebook 中显示
  ```

### 保险报告可视化（本工具）
- **适用场景**：结构化表格数据
- **功能**：仪表板式展示，关键指标卡片，完整表格
- **交互**：报告切换，表格浏览，数值格式化
- **使用方式**：
  ```bash
  python visualize_solvency_data.py --input data.jsonl --output dashboard.html
  # 在浏览器中打开 HTML 文件
  ```

### 选择建议

- **如果你的数据包含原始文本和字符位置**：使用 LangExtract 的 `lx.visualize()`
- **如果你的数据是从 PDF/图片提取的结构化数据**：使用本工具 `visualize_solvency_data.py`

## 技术细节

### 数据格式要求

输入的 JSONL 文件应该包含以下结构：

```json
{
  "pdf_file": "报告文件名.pdf",
  "company_name": "公司名称",
  "report_period": "报告期间",
  "solvency_tables": [
    {
      "table_title": "表格标题",
      "rows": [
        {
          "指标名称": "核心偿付能力充足率",
          "本季度数": "148.54%"
        }
      ]
    }
  ]
}
```

### 智能字段匹配

脚本会自动识别不同报告中的不同字段名称：

- **指标名称**：`指标名称`, `项目`, `指标`, `名称`
- **数值**：`本季度数`, `期末数`, `本期数`, `数值`, `金额`

### 数值格式化

- 自动添加千分位分隔符：`12345678.90` → `12,345,678.90`
- 保留百分号：`148.54%` → `148.54%`
- 处理中文单位：自动去除 `元`, `万` 等单位

## 浏览器兼容性

支持所有现代浏览器：
- ✅ Chrome / Edge (推荐)
- ✅ Firefox
- ✅ Safari
- ✅ Opera

无需安装任何浏览器插件，生成的 HTML 是完全独立的文件。

## 故障排查

### 问题：打开 HTML 显示空白

**原因**：JSONL 文件格式错误或数据为空

**解决方法**：
```bash
# 检查 JSONL 文件是否有内容
wc -l extracted_data.jsonl

# 查看文件前几行
head -n 3 extracted_data.jsonl

# 验证 JSON 格式
python -c "import json; [json.loads(line) for line in open('extracted_data.jsonl')]"
```

### 问题：指标未显示

**原因**：表格中的字段名称与脚本的匹配模式不同

**解决方法**：
1. 检查你的 JSONL 文件中的字段名称
2. 如需添加更多字段匹配模式，编辑脚本中的 `key_patterns` 字典

### 问题：中文显示乱码

**原因**：浏览器编码设置问题

**解决方法**：
- 确保以 UTF-8 编码打开文件
- Chrome：右键 → Encoding → UTF-8
- 或在脚本中已设置 `<meta charset="UTF-8">`

## 扩展功能

### 添加图表

如果需要添加趋势图表，可以集成 Chart.js 或 ECharts：

```html
<!-- 在 HTML head 中添加 -->
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

<!-- 在需要显示图表的地方 -->
<canvas id="ratioChart"></canvas>
<script>
  // 绘制充足率趋势图
  const ctx = document.getElementById('ratioChart').getContext('2d');
  new Chart(ctx, {
    type: 'line',
    data: { /* 你的数据 */ }
  });
</script>
```

### 导出功能

可以添加导出为 PDF 或图片的功能：

```javascript
// 使用 html2canvas 库
<script src="https://cdn.jsdelivr.net/npm/html2canvas@1.4.1/dist/html2canvas.min.js"></script>
<button onclick="exportToPDF()">导出为 PDF</button>
```

## 性能优化

- 对于超过 100 个报告，建议分批可视化
- 大型表格会自动启用滚动条
- 移动端自适应布局

## 总结

这个可视化工具让你能够：
1. ✅ 快速浏览多个报告的关键指标
2. ✅ 在浏览器中交互式查看所有数据
3. ✅ 无需 Excel 即可查看表格数据
4. ✅ 美观的界面和用户体验
5. ✅ 完全离线工作（生成后无需网络）

配合 `extract_solvency_indicators.py`（导出 Excel）和本工具（HTML 可视化），你可以从多个角度分析保险偿付能力数据！
