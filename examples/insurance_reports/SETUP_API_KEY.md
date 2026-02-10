# API Key 设置指南

## 方式 1: .env 文件（推荐 ⭐）

在项目根目录或工作目录创建 `.env` 文件：

```bash
# 在 langextract 根目录
cd /home/user/langextract

# 创建 .env 文件
cat > .env << 'EOF'
LANGEXTRACT_API_KEY=your-actual-api-key-here
EOF

# 确保 .env 文件不被提交到 git
echo '.env' >> .gitignore
```

**获取 API Key:**
- Gemini: https://aistudio.google.com/app/apikey
- OpenAI: https://platform.openai.com/api-keys
- Claude: https://console.anthropic.com/

**使用:**
脚本会自动读取 `.env` 文件（通过 `python-dotenv` 库）

```bash
# 不需要 export，直接运行脚本即可
python examples/insurance_reports/process_pdf_reports.py --pdf-dir ./reports
```

---

## 方式 2: 环境变量（临时）

### Linux/macOS:

```bash
# 仅当前终端会话有效
export LANGEXTRACT_API_KEY="your-api-key-here"

# 验证设置成功
echo $LANGEXTRACT_API_KEY

# 运行脚本
python process_pdf_reports.py --pdf-dir ./reports
```

### Windows CMD:

```cmd
set LANGEXTRACT_API_KEY=your-api-key-here
python process_pdf_reports.py --pdf-dir ./reports
```

### Windows PowerShell:

```powershell
$env:LANGEXTRACT_API_KEY="your-api-key-here"
python process_pdf_reports.py --pdf-dir ./reports
```

---

## 方式 3: Shell 配置文件（永久）

### Linux/macOS:

编辑你的 shell 配置文件：

```bash
# Bash 用户
echo 'export LANGEXTRACT_API_KEY="your-api-key-here"' >> ~/.bashrc
source ~/.bashrc

# Zsh 用户
echo 'export LANGEXTRACT_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc

# Fish 用户
echo 'set -gx LANGEXTRACT_API_KEY "your-api-key-here"' >> ~/.config/fish/config.fish
source ~/.config/fish/config.fish
```

**注意:** 这会在所有终端会话中生效，但 API key 会明文存储在配置文件中。

---

## 方式 4: 命令行参数

直接在命令中传递（不推荐，因为会暴露在命令历史中）：

```bash
python process_pdf_reports.py \
  --pdf-dir ./reports \
  --api-key "your-api-key-here"
```

---

## 验证设置

### 检查环境变量是否设置:

```bash
# Linux/macOS
echo $LANGEXTRACT_API_KEY

# Windows CMD
echo %LANGEXTRACT_API_KEY%

# Windows PowerShell
echo $env:LANGEXTRACT_API_KEY
```

### Python 中验证:

```python
import os
api_key = os.environ.get('LANGEXTRACT_API_KEY')
if api_key:
    print(f"✓ API key found: {api_key[:10]}...")
else:
    print("✗ API key not set")
```

---

## 快速设置脚本

### Linux/macOS:

```bash
#!/bin/bash
# setup_api_key.sh

echo "🔑 API Key Setup for LangExtract"
echo ""
echo "Choose a method:"
echo "1) Create .env file (recommended)"
echo "2) Add to .bashrc/.zshrc (permanent)"
echo "3) Set for current session only"
echo ""
read -p "Enter choice [1-3]: " choice

case $choice in
  1)
    read -p "Enter your Gemini API key: " api_key
    echo "LANGEXTRACT_API_KEY=$api_key" > .env
    echo "✓ Created .env file"
    echo "✓ API key saved"
    ;;
  2)
    read -p "Enter your Gemini API key: " api_key
    if [[ $SHELL == *"zsh"* ]]; then
      echo "export LANGEXTRACT_API_KEY=\"$api_key\"" >> ~/.zshrc
      echo "✓ Added to ~/.zshrc"
      echo "Run: source ~/.zshrc"
    else
      echo "export LANGEXTRACT_API_KEY=\"$api_key\"" >> ~/.bashrc
      echo "✓ Added to ~/.bashrc"
      echo "Run: source ~/.bashrc"
    fi
    ;;
  3)
    read -p "Enter your Gemini API key: " api_key
    export LANGEXTRACT_API_KEY="$api_key"
    echo "✓ API key set for current session"
    echo "Run this in your terminal:"
    echo "  export LANGEXTRACT_API_KEY=\"$api_key\""
    ;;
esac
```

**使用:**
```bash
chmod +x setup_api_key.sh
./setup_api_key.sh
```

---

## 安全提示

✅ **推荐做法:**
- 使用 `.env` 文件并将其加入 `.gitignore`
- 不要将 API key 提交到 git 仓库
- 定期轮换 API key

❌ **避免:**
- 在代码中硬编码 API key
- 在公共仓库中暴露 API key
- 在命令行参数中传递（会留在历史记录中）

---

## 多个 API Key 管理

如果你需要使用多个服务（Gemini + OpenAI + Claude）：

**.env 文件:**
```bash
# Gemini (主要使用)
LANGEXTRACT_API_KEY=your-gemini-key

# OpenAI (可选)
OPENAI_API_KEY=your-openai-key

# Claude (可选)
ANTHROPIC_API_KEY=your-claude-key
```

**使用时指定后端:**
```bash
# 使用 Gemini (默认)
python extract_multi_llm.py --image report.png --backend gemini

# 使用 OpenAI
python extract_multi_llm.py --image report.png --backend openai-vision

# 使用 Claude
python extract_multi_llm.py --image report.png --backend claude-vision
```

---

## 常见问题

### Q: 我的 API key 在哪里？
- **Gemini**: https://aistudio.google.com/app/apikey
- **OpenAI**: https://platform.openai.com/api-keys
- **Claude**: https://console.anthropic.com/

### Q: .env 文件应该放在哪里？
- 项目根目录（`/home/user/langextract/.env`）
- 或工作目录（你运行脚本的地方）

### Q: 为什么脚本找不到 API key？
检查：
```bash
# 1. 确认 .env 文件存在
ls -la .env

# 2. 查看内容
cat .env

# 3. 确认环境变量
echo $LANGEXTRACT_API_KEY

# 4. Python 中检查
python -c "import os; print(os.environ.get('LANGEXTRACT_API_KEY'))"
```

### Q: 可以在代码中直接设置吗？
可以，但不推荐：
```python
# 不推荐 - 仅用于测试
result = extract_from_image(
    "report.png",
    api_key="your-api-key-here"  # 直接传递
)
```
