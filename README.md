# Google Alert 邮件处理和筛选系统

基于 Langchain 架构的自动化系统，用于获取和筛选 Google Alert 邮件中的新闻内容。系统通过 Gmail API 获取邮件，使用 DeepSeek AI 进行内容筛选，并提供结构化的数据存储和分析功能。

## 功能特性

- 🔄 **自动邮件获取**: 通过 Gmail API 获取指定时间范围内的 Google Alert 邮件
- 📊 **结构化存储**: 使用 SQLAlchemy 将邮件和文章数据存储到数据库
- 🤖 **AI 内容筛选**: 集成 DeepSeek API 对新闻内容进行质量和相关性评估
- 📈 **数据分析**: 提供详细的统计报告和趋势分析
- 🛠️ **模块化设计**: 基于 Langchain 架构，各模块独立可配置
- 💻 **命令行接口**: 支持多种运行模式和参数配置

## 系统架构

```
Gmail API → 邮件获取 → 数据存储 → DeepSeek筛选 → 报告生成
    ↓           ↓           ↓           ↓           ↓
gmail_auth   email_fetcher data_storage deepseek_filter main.py
```

## 安装和配置

### 1. 环境要求

- Python 3.8+
- Gmail 账户
- DeepSeek API 账户

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. Gmail API 设置

运行设置向导：

```bash
python setup_gmail.py
```

或手动设置：

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建项目并启用 Gmail API
3. 创建 OAuth 2.0 客户端凭据
4. 下载凭据文件并重命名为 `credentials.json`

### 4. 配置环境变量

```bash
# 复制配置模板
cp env.example .env

# 编辑配置文件，填入您的 DeepSeek API Key
# DEEPSEEK_API_KEY=your_api_key_here
```

### 5. 初始化数据库

首次运行时会自动创建数据库表：

```bash
python main.py --stats
```

## 使用方法

### 快速开始

运行完整工作流程（获取邮件 → 筛选内容 → 生成报告）：

```bash
python main.py
```

### 命令行选项

```bash
# 获取最近3天的邮件
python main.py --days 3

# 限制筛选50篇文章
python main.py --limit 50

# 仅获取邮件，不进行筛选
python main.py --fetch-only

# 仅筛选现有文章
python main.py --filter-only

# 仅生成报告
python main.py --report-only

# 查看数据库统计信息
python main.py --stats
```

### 测试各个模块

```bash
# 测试Gmail认证
python gmail_auth.py

# 测试邮件获取
python email_fetcher.py

# 测试数据存储
python data_storage.py

# 测试内容筛选
python deepseek_filter.py
```

## 项目结构

```
google-alert-processor/
├── main.py                 # 主程序入口
├── config.py               # 配置文件
├── gmail_auth.py           # Gmail API 认证
├── email_fetcher.py        # 邮件获取模块
├── data_storage.py         # 数据存储模块
├── deepseek_filter.py      # DeepSeek 筛选模块
├── setup_gmail.py          # Gmail API 设置向导
├── requirements.txt        # Python 依赖
├── env.example            # 环境变量模板
├── README.md              # 说明文档
├── credentials.json       # Gmail API 凭据 (需要您提供)
├── token.json            # Gmail 访问令牌 (自动生成)
├── .env                  # 环境变量配置 (需要您创建)
└── google_alerts.db      # SQLite 数据库 (自动生成)
```

## 配置说明

### 主要配置项 (config.py)

- `SEARCH_DAYS`: 默认搜索天数
- `GOOGLE_ALERT_SENDER`: Google Alert 发件人邮箱
- `CONTENT_FILTER_PROMPT`: DeepSeek 筛选提示词模板

### 环境变量 (.env)

- `GMAIL_CREDENTIALS_FILE`: Gmail API 凭据文件路径
- `GMAIL_TOKEN_FILE`: Gmail 访问令牌文件路径
- `DEEPSEEK_API_KEY`: DeepSeek API 密钥
- `DATABASE_URL`: 数据库连接 URL

## 数据库结构

### google_alert_emails 表
- 存储 Google Alert 邮件的基本信息
- 字段：id, message_id, subject, sender, date, body_html, body_text

### news_articles 表
- 存储从邮件中提取的新闻文章
- 字段：id, title, url, source, summary, 筛选结果等

## DeepSeek 筛选机制

系统使用 DeepSeek API 对每篇文章进行以下维度的评估：

1. **内容质量** (1-10分): 文章的深度和价值
2. **相关性** (1-10分): 与关键词的匹配度
3. **时效性**: 新闻的时间价值
4. **可信度**: 新闻源的可靠性

筛选结果包括：
- 是否通过筛选 (boolean)
- 质量和相关性评分
- 筛选理由
- 关键要点提取
- 内容分类

## 输出示例

### 筛选报告示例

```
最近 7 天筛选报告
==================================================

总体统计:
- 筛选通过文章: 25 篇
- 平均质量评分: 7.8/10
- 平均相关性评分: 8.2/10

来源分布:
- 新浪科技: 8 篇
- 36氪: 5 篇
- 澎湃新闻: 4 篇

类别分布:
- 科技新闻: 15 篇
- 商业资讯: 8 篇
- 行业动态: 2 篇

推荐阅读 (Top 5):
1. AI技术突破：GPT-5即将发布
   来源: 新浪科技 | 质量: 9.2 | 相关性: 9.5
   链接: https://tech.sina.com.cn/...
```

## 故障排除

### 常见问题

1. **Gmail 认证失败**
   - 检查 `credentials.json` 文件是否正确
   - 确认已启用 Gmail API
   - 重新运行 `python gmail_auth.py`

2. **DeepSeek API 调用失败**
   - 检查 API Key 是否正确
   - 确认账户余额充足
   - 检查网络连接

3. **数据库连接错误**
   - 检查 `DATABASE_URL` 配置
   - 确认数据库文件权限
   - 删除 `.db` 文件重新创建

### 日志和调试

系统会在控制台输出详细的运行日志，包括：
- 邮件获取进度
- 文章筛选结果
- API 调用状态
- 错误信息

## 扩展功能

### 自定义筛选规则

可以通过修改 `config.py` 中的 `CONTENT_FILTER_PROMPT` 来自定义筛选标准。

### 添加新的数据源

系统设计为模块化，可以轻松添加其他邮件源或新闻源。

### 集成其他 AI 服务

可以替换或补充 DeepSeek，集成其他 AI 服务进行内容分析。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目。

## 许可证

MIT License

## 联系方式

如有问题或建议，请通过 GitHub Issues 联系。
