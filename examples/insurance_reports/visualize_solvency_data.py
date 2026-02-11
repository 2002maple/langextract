#!/usr/bin/env python3
"""Generate interactive HTML visualization for insurance solvency report data.

This script reads extracted JSONL data and creates an interactive HTML dashboard
to review the extracted information including:
- Company information and report periods
- Solvency adequacy ratios with trend charts
- Capital composition tables
- All extracted tables from each report

Usage:
    python visualize_solvency_data.py --input extracted_data.jsonl --output dashboard.html
"""

import argparse
import html
import json
from pathlib import Path
from typing import Any


def format_number(value: Any) -> str:
    """Format numeric values with proper formatting."""
    if value is None or value == '':
        return '-'

    value_str = str(value).strip()

    # Handle percentage values
    if '%' in value_str:
        return value_str

    # Try to parse as number
    try:
        # Remove common Chinese characters and units
        clean_value = value_str.replace(',', '').replace('元', '').replace('万', '')
        num = float(clean_value)

        # Format with thousands separator
        if abs(num) >= 10000:
            return f'{num:,.2f}'
        else:
            return f'{num:.2f}'
    except (ValueError, AttributeError):
        return value_str


def extract_key_indicators(report_data: dict) -> dict:
    """Extract key solvency indicators from report data."""
    indicators = {}

    key_patterns = {
        '核心偿付能力充足率': ['核心偿付能力充足率', '核心资本充足率'],
        '综合偿付能力充足率': ['综合偿付能力充足率', '综合资本充足率'],
        '实际资本': ['实际资本'],
        '最低资本': ['最低资本'],
    }

    for table in report_data.get('solvency_tables', []):
        for row in table.get('rows', []):
            # Get row name from various possible fields
            row_name = (
                row.get('指标名称', '') or
                row.get('项目', '') or
                row.get('指标', '') or
                row.get('名称', '')
            )

            # Get value from various possible fields
            value = (
                row.get('本季度数', '') or
                row.get('期末数', '') or
                row.get('本期数', '') or
                row.get('数值', '') or
                row.get('金额', '')
            )

            # Match against key patterns
            for indicator_name, patterns in key_patterns.items():
                if any(pattern in row_name for pattern in patterns):
                    indicators[indicator_name] = format_number(value)
                    break

    return indicators


def build_html_visualization(reports_data: list[dict]) -> str:
    """Build complete HTML visualization."""

    # Extract key indicators for all reports
    all_indicators = []
    for report in reports_data:
        indicators = extract_key_indicators(report)
        all_indicators.append({
            'company': report.get('company_name', 'Unknown'),
            'period': report.get('report_period', 'Unknown'),
            'pdf_file': report.get('pdf_file', 'Unknown'),
            'indicators': indicators,
            'tables': report.get('solvency_tables', []),
        })

    # Generate HTML
    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="zh-CN">',
        '<head>',
        '  <meta charset="UTF-8">',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0">',
        '  <title>保险偿付能力报告可视化</title>',
        _get_css_styles(),
        '</head>',
        '<body>',
        '  <div class="container">',
        '    <h1>📊 保险偿付能力报告数据可视化</h1>',
        '    <div class="report-selector">',
        '      <label for="reportSelect">选择报告：</label>',
        '      <select id="reportSelect" onchange="switchReport(this.value)">',
    ]

    # Add report options
    for idx, report_info in enumerate(all_indicators):
        company = html.escape(report_info['company'] or '未知公司')
        period = html.escape(report_info['period'] or '未知期间')
        html_parts.append(
            f'        <option value="{idx}">{company} - {period}</option>'
        )

    html_parts.extend([
        '      </select>',
        '    </div>',
        '    <div id="reportContent"></div>',
        '  </div>',
    ])

    # Add JavaScript data and logic
    html_parts.append('  <script>')
    html_parts.append(f'    const reportsData = {json.dumps(all_indicators, ensure_ascii=False)};')
    html_parts.append(_get_javascript_code())
    html_parts.append('  </script>')

    html_parts.extend([
        '</body>',
        '</html>',
    ])

    return '\n'.join(html_parts)


def _get_css_styles() -> str:
    """Get CSS styles for the visualization."""
    return '''  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }

    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
                   "Helvetica Neue", Arial, "Noto Sans", sans-serif,
                   "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol";
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      min-height: 100vh;
      padding: 20px;
    }

    .container {
      max-width: 1200px;
      margin: 0 auto;
      background: white;
      border-radius: 12px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.3);
      padding: 30px;
    }

    h1 {
      color: #333;
      margin-bottom: 30px;
      text-align: center;
      font-size: 28px;
    }

    h2 {
      color: #444;
      margin-top: 30px;
      margin-bottom: 15px;
      font-size: 22px;
      border-bottom: 2px solid #667eea;
      padding-bottom: 8px;
    }

    h3 {
      color: #555;
      margin-top: 20px;
      margin-bottom: 12px;
      font-size: 18px;
    }

    .report-selector {
      background: #f8f9fa;
      padding: 15px;
      border-radius: 8px;
      margin-bottom: 25px;
      display: flex;
      align-items: center;
      gap: 15px;
    }

    .report-selector label {
      font-weight: 600;
      color: #555;
    }

    .report-selector select {
      flex: 1;
      padding: 10px 15px;
      border: 2px solid #ddd;
      border-radius: 6px;
      font-size: 15px;
      background: white;
      cursor: pointer;
      transition: border-color 0.3s;
    }

    .report-selector select:hover {
      border-color: #667eea;
    }

    .report-selector select:focus {
      outline: none;
      border-color: #667eea;
      box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
    }

    .info-card {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 20px;
      border-radius: 10px;
      margin-bottom: 25px;
      box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }

    .info-card p {
      margin: 8px 0;
      font-size: 15px;
    }

    .info-card strong {
      font-weight: 600;
      margin-right: 10px;
    }

    .indicators-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
      gap: 15px;
      margin-bottom: 30px;
    }

    .indicator-card {
      background: #f8f9fa;
      padding: 20px;
      border-radius: 8px;
      border-left: 4px solid #667eea;
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .indicator-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }

    .indicator-label {
      color: #666;
      font-size: 13px;
      margin-bottom: 8px;
      font-weight: 500;
    }

    .indicator-value {
      color: #333;
      font-size: 24px;
      font-weight: 700;
    }

    .table-container {
      overflow-x: auto;
      margin-bottom: 25px;
      border-radius: 8px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      background: white;
    }

    thead {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
    }

    th {
      padding: 12px 15px;
      text-align: left;
      font-weight: 600;
      font-size: 14px;
    }

    td {
      padding: 12px 15px;
      border-bottom: 1px solid #eee;
      font-size: 14px;
      color: #333;
    }

    tbody tr:hover {
      background: #f8f9fa;
    }

    tbody tr:last-child td {
      border-bottom: none;
    }

    .table-title {
      background: #f8f9fa;
      padding: 12px 15px;
      font-weight: 600;
      color: #555;
      border-top-left-radius: 8px;
      border-top-right-radius: 8px;
      border-bottom: 2px solid #667eea;
    }

    .no-data {
      text-align: center;
      padding: 40px;
      color: #999;
      font-style: italic;
    }

    @media (max-width: 768px) {
      .container {
        padding: 20px;
      }

      h1 {
        font-size: 22px;
      }

      .indicators-grid {
        grid-template-columns: 1fr;
      }

      .report-selector {
        flex-direction: column;
        align-items: stretch;
      }
    }
  </style>'''


def _get_javascript_code() -> str:
    """Get JavaScript code for interactive functionality."""
    return '''
    function switchReport(index) {
      const report = reportsData[index];
      if (!report) return;

      const container = document.getElementById('reportContent');

      // Build HTML for the selected report
      let html = '';

      // Basic information card
      html += '<div class="info-card">';
      html += '<p><strong>📋 公司名称：</strong>' + escapeHtml(report.company || '未知公司') + '</p>';
      html += '<p><strong>📅 报告期间：</strong>' + escapeHtml(report.period || '未知期间') + '</p>';
      html += '<p><strong>📄 文件名称：</strong>' + escapeHtml(report.pdf_file || '未知文件') + '</p>';
      html += '</div>';

      // Key indicators
      html += '<h2>📈 关键偿付能力指标</h2>';

      if (Object.keys(report.indicators).length > 0) {
        html += '<div class="indicators-grid">';

        const indicatorOrder = [
          '核心偿付能力充足率',
          '综合偿付能力充足率',
          '实际资本',
          '最低资本'
        ];

        for (const key of indicatorOrder) {
          if (report.indicators[key]) {
            html += '<div class="indicator-card">';
            html += '<div class="indicator-label">' + escapeHtml(key) + '</div>';
            html += '<div class="indicator-value">' + escapeHtml(report.indicators[key]) + '</div>';
            html += '</div>';
          }
        }

        html += '</div>';
      } else {
        html += '<p class="no-data">未提取到关键指标</p>';
      }

      // All tables
      if (report.tables && report.tables.length > 0) {
        html += '<h2>📊 所有提取的表格</h2>';

        for (let i = 0; i < report.tables.length; i++) {
          const table = report.tables[i];
          const tableTitle = table.table_title || `表格 ${i + 1}`;

          html += '<div class="table-container">';
          html += '<div class="table-title">' + escapeHtml(tableTitle) + '</div>';
          html += '<table>';

          // Table headers
          if (table.rows && table.rows.length > 0) {
            const firstRow = table.rows[0];
            const headers = Object.keys(firstRow);

            html += '<thead><tr>';
            for (const header of headers) {
              html += '<th>' + escapeHtml(header) + '</th>';
            }
            html += '</tr></thead>';

            // Table body
            html += '<tbody>';
            for (const row of table.rows) {
              html += '<tr>';
              for (const header of headers) {
                const value = row[header] || '-';
                html += '<td>' + escapeHtml(String(value)) + '</td>';
              }
              html += '</tr>';
            }
            html += '</tbody>';
          } else {
            html += '<tbody><tr><td class="no-data">空表格</td></tr></tbody>';
          }

          html += '</table>';
          html += '</div>';
        }
      } else {
        html += '<h2>📊 所有提取的表格</h2>';
        html += '<p class="no-data">未提取到表格数据</p>';
      }

      container.innerHTML = html;
    }

    function escapeHtml(text) {
      if (text === null || text === undefined) {
        return '';
      }
      const div = document.createElement('div');
      div.textContent = String(text);
      return div.innerHTML;
    }

    // Load first report on page load
    window.addEventListener('DOMContentLoaded', function() {
      switchReport(0);
    });
'''


def main():
    parser = argparse.ArgumentParser(
        description='Generate interactive HTML visualization for insurance solvency data'
    )
    parser.add_argument(
        '--input',
        type=str,
        default='extracted_data.jsonl',
        help='Input JSONL file with extracted data (default: extracted_data.jsonl)',
    )
    parser.add_argument(
        '--output',
        type=str,
        default='solvency_dashboard.html',
        help='Output HTML file (default: solvency_dashboard.html)',
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)

    if not input_path.exists():
        print(f'❌ 错误：输入文件不存在 {input_path}')
        return 1

    print(f'📖 读取数据文件: {input_path}')

    # Load JSONL data
    reports_data = []
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                reports_data.append(json.loads(line))

    if not reports_data:
        print(f'❌ 错误：文件中没有数据')
        return 1

    print(f'✓ 成功加载 {len(reports_data)} 个报告')

    # Generate HTML
    print('🎨 生成 HTML 可视化...')
    html_content = build_html_visualization(reports_data)

    # Save to file
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f'✅ 可视化已保存到: {output_path}')
    print(f'\n💡 在浏览器中打开此文件即可查看交互式仪表板')
    print(f'   file://{output_path.absolute()}')

    return 0


if __name__ == '__main__':
    exit(main())
