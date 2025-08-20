"""
配置文件
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# Gmail API 配置
GMAIL_CREDENTIALS_FILE = os.getenv('GMAIL_CREDENTIALS_FILE', 'credentials.json')
GMAIL_TOKEN_FILE = os.getenv('GMAIL_TOKEN_FILE', 'token.json')
GMAIL_API_KEY = os.getenv('GMAIL_API_KEY')  # 备用 API Key（如果需要）

# Gmail OAuth 2.0 环境变量配置（推荐方式）
GMAIL_CLIENT_ID = os.getenv('GMAIL_CLIENT_ID')
GMAIL_CLIENT_SECRET = os.getenv('GMAIL_CLIENT_SECRET')
GMAIL_AUTH_URI = os.getenv('GMAIL_AUTH_URI', 'https://accounts.google.com/o/oauth2/auth')
GMAIL_TOKEN_URI = os.getenv('GMAIL_TOKEN_URI', 'https://oauth2.googleapis.com/token')
GMAIL_REDIRECT_URIS = os.getenv('GMAIL_REDIRECT_URIS', 'http://localhost').split(',')

GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# DeepSeek API 配置
DEEPSEEK_API_KEY = os.getenv('DEEPSEEK_API_KEY')
DEEPSEEK_BASE_URL = "https://api.deepseek.com"

# 数据存储配置
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///google_alerts.db')

# 项目路径
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / 'data'
DATA_DIR.mkdir(exist_ok=True)

# Google Alert 邮件筛选配置
GOOGLE_ALERT_SENDER = 'googlealerts-noreply@google.com'
SEARCH_DAYS = 1  # 搜索最近1天的邮件（每日运行模式）

# DeepSeek 筛选提示词模板
CONTENT_FILTER_PROMPT = """
你是一位汽车行业制造工程师的专业信息筛选助手。请根据以下专业标准筛选新闻内容：

【目标用户】：汽车行业制造工程师
【关注领域】：汽车工厂建设、AI技术、先进制造技术

【筛选标准】：
1. 优先保留：
   - 汽车工厂建设、扩建、技术升级相关
   - 汽车制造流程、生产线、质量控制
   - 可应用于汽车工厂的AI技术（工业机器人、机器视觉、数字孪生、预测性维护等）
   - 先进制造技术（增材制造/3D打印、自动化、智能制造、工业4.0等）
   - 汽车供应链、材料技术、新能源汽车制造

2. 保留但降低优先级：
   - 通用制造技术（如果可应用于汽车工厂）
   - 其他行业的先进制造案例（如果技术可借鉴）

3. 明确剔除：
   - 政治、社会、娱乐新闻
   - 仅涉及非汽车行业制造的内容（如电子产品、航空制造，除非技术通用）
   - 汽车销售、市场营销、金融投资类新闻
   - 与制造工程无关的汽车新闻（如车型发布、测评等）

【分析内容】：
标题：{title}
来源：{source}
内容摘要：{summary}
发布时间：{publish_time}
原文链接：{url}

请按照以下JSON格式返回筛选结果：
{{
    "is_selected": true/false,
    "quality_score": 1-10的评分（内容深度和价值）,
    "relevance_score": 1-10的评分（与汽车制造工程的相关性）,
    "reason": "详细的筛选理由，说明为什么选择或拒绝",
    "key_points": ["提取的关键技术要点或制造信息"],
    "category": "分类：汽车工厂建设/AI制造技术/先进制造/供应链技术/其他"
}}
"""
