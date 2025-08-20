"""
Gmail API 认证和服务初始化
"""
import os
import pickle
import json
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from config import (
    GMAIL_CREDENTIALS_FILE, GMAIL_TOKEN_FILE, GMAIL_SCOPES,
    GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_AUTH_URI, 
    GMAIL_TOKEN_URI, GMAIL_REDIRECT_URIS
)


class GmailAuthenticator:
    """Gmail API 认证管理器"""
    
    def __init__(self):
        self.service = None
        self.creds = None
    
    def authenticate(self):
        """
        进行Gmail API认证
        返回认证后的Gmail服务实例
        """
        # 检查是否存在有效的token
        self.creds = self._load_token()
        
        # 如果没有有效凭据，或者凭据已过期，需要重新授权
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                # 刷新过期的凭据
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    print(f"刷新token失败: {e}")
                    self._get_new_credentials()
            else:
                # 获取新的凭据
                self._get_new_credentials()
            
            # 保存凭据以供下次使用
            self._save_token()
        
        try:
            # 构建Gmail服务
            self.service = build('gmail', 'v1', credentials=self.creds)
            print("Gmail API 认证成功")
            return self.service
        except HttpError as error:
            print(f"Gmail API 认证失败: {error}")
            return None
    
    def _get_new_credentials(self):
        """获取新的认证凭据"""
        # 优先使用环境变量
        if GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET:
            print("使用环境变量中的Gmail OAuth配置")
            client_config = {
                "installed": {
                    "client_id": GMAIL_CLIENT_ID,
                    "client_secret": GMAIL_CLIENT_SECRET,
                    "auth_uri": GMAIL_AUTH_URI,
                    "token_uri": GMAIL_TOKEN_URI,
                    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                    "redirect_uris": GMAIL_REDIRECT_URIS
                }
            }
            flow = InstalledAppFlow.from_client_config(client_config, GMAIL_SCOPES)
            self.creds = flow.run_local_server(port=0)
        
        # 备用：使用credentials.json文件
        elif os.path.exists(GMAIL_CREDENTIALS_FILE):
            print(f"使用凭据文件: {GMAIL_CREDENTIALS_FILE}")
            flow = InstalledAppFlow.from_client_secrets_file(
                GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES
            )
            self.creds = flow.run_local_server(port=0)
        
        else:
            raise FileNotFoundError(
                f"Gmail OAuth配置未找到！请选择以下方式之一：\n"
                f"1. 设置环境变量: GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET\n"
                f"2. 提供凭据文件: {GMAIL_CREDENTIALS_FILE}\n"
                f"请到 Google Cloud Console 获取 OAuth 2.0 客户端凭据"
            )
    
    def _load_token(self):
        """加载访问令牌"""
        # 优先从环境变量加载
        token_json = os.getenv('GMAIL_ACCESS_TOKEN')
        if token_json:
            try:
                import json
                token_data = json.loads(token_json)
                creds = Credentials(
                    token=token_data.get('token'),
                    refresh_token=token_data.get('refresh_token'),
                    token_uri=token_data.get('token_uri'),
                    client_id=token_data.get('client_id'),
                    client_secret=token_data.get('client_secret'),
                    scopes=token_data.get('scopes')
                )
                print("从环境变量加载访问令牌")
                return creds
            except Exception as e:
                print(f"环境变量令牌解析失败: {e}")
        
        # 备用：从文件加载
        if os.path.exists(GMAIL_TOKEN_FILE):
            try:
                with open(GMAIL_TOKEN_FILE, 'rb') as token:
                    creds = pickle.load(token)
                print(f"从文件加载访问令牌: {GMAIL_TOKEN_FILE}")
                return creds
            except Exception as e:
                print(f"令牌文件加载失败: {e}")
        
        return None
    
    def _save_token(self):
        """保存访问令牌"""
        if not self.creds:
            return
        
        # 如果设置了环境变量存储偏好，提示用户
        if os.getenv('GMAIL_USE_ENV_TOKEN', '').lower() == 'true':
            token_data = {
                'token': self.creds.token,
                'refresh_token': self.creds.refresh_token,
                'token_uri': self.creds.token_uri,
                'client_id': self.creds.client_id,
                'client_secret': self.creds.client_secret,
                'scopes': self.creds.scopes
            }
            token_json = json.dumps(token_data)
            print("\n🔐 请将以下令牌添加到环境变量 GMAIL_ACCESS_TOKEN:")
            print("="*60)
            print(token_json)
            print("="*60)
            print("或者设置 GMAIL_USE_ENV_TOKEN=false 使用文件存储\n")
        else:
            # 默认保存到文件
            with open(GMAIL_TOKEN_FILE, 'wb') as token:
                pickle.dump(self.creds, token)
            print(f"访问令牌已保存到文件: {GMAIL_TOKEN_FILE}")
    
    def get_user_profile(self):
        """获取用户邮箱信息"""
        if not self.service:
            raise Exception("请先进行认证")
        
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return {
                'email': profile.get('emailAddress'),
                'total_messages': profile.get('messagesTotal'),
                'total_threads': profile.get('threadsTotal')
            }
        except HttpError as error:
            print(f"获取用户信息失败: {error}")
            return None


def get_gmail_service():
    """
    获取已认证的Gmail服务实例
    这是一个便捷函数，用于快速获取Gmail服务
    """
    auth = GmailAuthenticator()
    return auth.authenticate()


if __name__ == "__main__":
    # 测试认证
    auth = GmailAuthenticator()
    service = auth.authenticate()
    
    if service:
        profile = auth.get_user_profile()
        if profile:
            print(f"已连接到邮箱: {profile['email']}")
            print(f"总邮件数: {profile['total_messages']}")
        else:
            print("获取用户信息失败")
    else:
        print("Gmail认证失败")
