"""
配置检查工具
快速检查系统配置是否正确
"""
import os
import json
from pathlib import Path
from dotenv import load_dotenv


def check_file_exists(filepath: str, name: str) -> bool:
    """检查文件是否存在"""
    if Path(filepath).exists():
        print(f"✅ {name}: {filepath}")
        return True
    else:
        print(f"❌ {name}: {filepath} (文件不存在)")
        return False


def check_env_var(var_name: str, required: bool = True) -> bool:
    """检查环境变量"""
    value = os.getenv(var_name)
    if value and value != f"your_{var_name.lower()}_here":
        print(f"✅ {var_name}: 已设置")
        return True
    elif required:
        print(f"❌ {var_name}: 未设置或使用默认值")
        return False
    else:
        print(f"ℹ️ {var_name}: 未设置 (可选)")
        return True


def check_gmail_credentials():
    """检查Gmail凭据文件格式"""
    try:
        with open('credentials.json', 'r') as f:
            creds = json.load(f)
            if 'installed' in creds or 'web' in creds:
                print("✅ Gmail 凭据格式: 正确")
                return True
            else:
                print("❌ Gmail 凭据格式: 不正确")
                return False
    except FileNotFoundError:
        print("❌ Gmail 凭据: credentials.json 不存在")
        return False
    except json.JSONDecodeError:
        print("❌ Gmail 凭据: JSON 格式错误")
        return False


def check_database_connection():
    """检查数据库连接"""
    try:
        from data_storage import db_manager
        stats = db_manager.get_statistics()
        print(f"✅ 数据库连接: 成功 (邮件: {stats['total_emails']}, 文章: {stats['total_articles']})")
        return True
    except Exception as e:
        print(f"❌ 数据库连接: 失败 ({e})")
        return False


def check_deepseek_api():
    """检查DeepSeek API连接"""
    api_key = os.getenv('DEEPSEEK_API_KEY')
    if not api_key or api_key == 'your_deepseek_api_key_here':
        print("❌ DeepSeek API: 未配置")
        return False
    
    try:
        from openai import OpenAI
        client = OpenAI(
            api_key=api_key,
            base_url="https://api.deepseek.com"
        )
        # 进行一个简单的测试调用
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Hello"}],
            max_tokens=10
        )
        print("✅ DeepSeek API: 连接成功")
        return True
    except Exception as e:
        print(f"❌ DeepSeek API: 连接失败 ({e})")
        return False


def main():
    """主检查函数"""
    print("系统配置检查")
    print("=" * 50)
    
    # 加载环境变量
    load_dotenv()
    
    all_ok = True
    
    print("\n文件检查:")
    all_ok &= check_file_exists("requirements.txt", "依赖文件")
    all_ok &= check_file_exists(".env", "环境配置")
    all_ok &= check_file_exists("credentials.json", "Gmail凭据")
    
    print("\n环境变量检查:")
    all_ok &= check_env_var("DEEPSEEK_API_KEY", required=True)
    all_ok &= check_env_var("GMAIL_API_KEY", required=False)
    all_ok &= check_env_var("GMAIL_CREDENTIALS_FILE", required=False)
    all_ok &= check_env_var("DATABASE_URL", required=False)
    
    print("\n服务连接检查:")
    all_ok &= check_gmail_credentials()
    all_ok &= check_database_connection()
    all_ok &= check_deepseek_api()
    
    print("\n" + "=" * 50)
    if all_ok:
        print("✅ 所有检查通过，系统配置正确！")
        print("\n可以开始使用:")
        print("  python main.py")
    else:
        print("❌ 发现配置问题，请按照上述提示进行修复")
        print("\n获取帮助:")
        print("  python setup_gmail.py  # Gmail API 设置向导")
        print("  python quick_start.py  # 快速启动向导")
    
    return all_ok


if __name__ == "__main__":
    main()
