"""
Gmail 邮件获取模块
专门用于获取和解析 Google Alert 邮件
"""
import base64
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from email.mime.text import MIMEText
from bs4 import BeautifulSoup
from googleapiclient.errors import HttpError

from gmail_auth import get_gmail_service
from config import GOOGLE_ALERT_SENDER, SEARCH_DAYS


class GoogleAlertEmail:
    """Google Alert 邮件数据类"""
    
    def __init__(self, message_id: str, subject: str, date: datetime, 
                 sender: str, body_html: str, body_text: str = ""):
        self.message_id = message_id
        self.subject = subject
        self.date = date
        self.sender = sender
        self.body_html = body_html
        self.body_text = body_text
        self.articles = []
        
        # 解析邮件内容获取文章列表
        self._parse_articles()
    
    def _parse_articles(self):
        """从Google Alert邮件中解析新闻文章"""
        if not self.body_html:
            return
        
        soup = BeautifulSoup(self.body_html, 'html.parser')
        
        # Google Alert邮件通常包含多个新闻条目
        # 寻找包含新闻链接的元素
        articles = []
        
        # 查找所有链接
        links = soup.find_all('a', href=True)
        
        for link in links:
            href = link.get('href', '')
            
            # 过滤Google Alert的实际新闻链接
            if 'google.com/url' in href or 'news.google.com' in href:
                # 提取实际URL
                actual_url = self._extract_actual_url(href)
                
                # 获取文章标题
                title = link.get_text(strip=True)
                
                if title and actual_url:
                    # 查找相关的来源信息
                    source = self._find_article_source(link)
                    
                    # 查找发布时间
                    publish_time = self._find_publish_time(link)
                    
                    # 查找文章摘要
                    summary = self._find_article_summary(link)
                    
                    article = {
                        'title': title,
                        'url': actual_url,
                        'source': source,
                        'publish_time': publish_time,
                        'summary': summary,
                        'alert_subject': self.subject,
                        'alert_date': self.date
                    }
                    
                    articles.append(article)
        
        self.articles = articles
    
    def _extract_actual_url(self, google_url: str) -> str:
        """从Google重定向URL中提取实际URL"""
        import urllib.parse
        
        try:
            # 解析Google URL参数
            if 'google.com/url' in google_url:
                parsed = urllib.parse.urlparse(google_url)
                params = urllib.parse.parse_qs(parsed.query)
                if 'url' in params:
                    return params['url'][0]
            
            return google_url
        except Exception:
            return google_url
    
    def _find_article_source(self, link_element) -> str:
        """查找文章来源"""
        # 在链接附近查找来源信息
        parent = link_element.parent
        if parent:
            # 查找常见的来源标识
            source_candidates = parent.find_all(text=True)
            for text in source_candidates:
                text = text.strip()
                if text and len(text) < 100 and not text.startswith('http'):
                    # 简单的来源识别逻辑
                    if any(word in text.lower() for word in ['news', '新闻', 'times', 'post', 'daily']):
                        return text
        
        return "未知来源"
    
    def _find_publish_time(self, link_element) -> Optional[str]:
        """查找发布时间"""
        # 在链接附近查找时间信息
        parent = link_element.parent
        if parent:
            time_pattern = r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d+\s*(小时|天|分钟|hours?|days?|minutes?)前'
            text_content = parent.get_text()
            
            time_match = re.search(time_pattern, text_content)
            if time_match:
                return time_match.group()
        
        return None
    
    def _find_article_summary(self, link_element) -> str:
        """查找文章摘要"""
        # 在链接附近查找摘要文本
        parent = link_element.parent
        if parent:
            # 获取父元素下的所有文本
            texts = [text.strip() for text in parent.stripped_strings]
            
            # 查找较长的文本作为摘要
            for text in texts:
                if len(text) > 50 and len(text) < 500:
                    return text
        
        return ""


class EmailFetcher:
    """邮件获取器"""
    
    def __init__(self):
        self.service = get_gmail_service()
        if not self.service:
            raise Exception("无法连接到Gmail服务")
    
    def fetch_google_alerts(self, days: int = SEARCH_DAYS) -> List[GoogleAlertEmail]:
        """
        获取指定天数内的Google Alert邮件
        
        Args:
            days: 搜索天数，默认为配置中的天数
            
        Returns:
            Google Alert 邮件列表
        """
        print(f"正在获取最近 {days} 天的 Google Alert 邮件...")
        
        # 计算搜索日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 构建搜索查询
        query = f'from:{GOOGLE_ALERT_SENDER} after:{start_date.strftime("%Y/%m/%d")}'
        
        try:
            # 搜索邮件
            results = self.service.users().messages().list(
                userId='me', q=query
            ).execute()
            
            messages = results.get('messages', [])
            print(f"找到 {len(messages)} 封 Google Alert 邮件")
            
            alert_emails = []
            
            for message in messages:
                try:
                    # 获取邮件详情
                    msg = self.service.users().messages().get(
                        userId='me', id=message['id'], format='full'
                    ).execute()
                    
                    # 解析邮件
                    alert_email = self._parse_message(msg)
                    if alert_email:
                        alert_emails.append(alert_email)
                        print(f"解析邮件: {alert_email.subject} ({len(alert_email.articles)} 篇文章)")
                
                except HttpError as error:
                    print(f"获取邮件 {message['id']} 失败: {error}")
                    continue
            
            print(f"成功解析 {len(alert_emails)} 封邮件")
            return alert_emails
        
        except HttpError as error:
            print(f"搜索邮件失败: {error}")
            return []
    
    def _parse_message(self, message: dict) -> Optional[GoogleAlertEmail]:
        """解析邮件消息"""
        try:
            payload = message['payload']
            headers = payload.get('headers', [])
            
            # 提取邮件头信息
            subject = ""
            sender = ""
            date_str = ""
            
            for header in headers:
                name = header['name'].lower()
                value = header['value']
                
                if name == 'subject':
                    subject = value
                elif name == 'from':
                    sender = value
                elif name == 'date':
                    date_str = value
            
            # 解析日期
            try:
                from email.utils import parsedate_to_datetime
                date = parsedate_to_datetime(date_str)
            except Exception:
                date = datetime.now()
            
            # 提取邮件正文
            body_html, body_text = self._extract_message_body(payload)
            
            if body_html or body_text:
                return GoogleAlertEmail(
                    message_id=message['id'],
                    subject=subject,
                    date=date,
                    sender=sender,
                    body_html=body_html,
                    body_text=body_text
                )
            
        except Exception as e:
            print(f"解析邮件失败: {e}")
            return None
    
    def _extract_message_body(self, payload: dict) -> tuple:
        """提取邮件正文内容"""
        body_html = ""
        body_text = ""
        
        def extract_from_parts(parts):
            nonlocal body_html, body_text
            
            for part in parts:
                mime_type = part.get('mimeType', '')
                
                if mime_type == 'text/html':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        body_html = base64.urlsafe_b64decode(data).decode('utf-8')
                
                elif mime_type == 'text/plain':
                    data = part.get('body', {}).get('data', '')
                    if data:
                        body_text = base64.urlsafe_b64decode(data).decode('utf-8')
                
                elif 'parts' in part:
                    extract_from_parts(part['parts'])
        
        # 检查是否有多部分内容
        if 'parts' in payload:
            extract_from_parts(payload['parts'])
        else:
            # 单部分邮件
            mime_type = payload.get('mimeType', '')
            data = payload.get('body', {}).get('data', '')
            
            if data:
                decoded_data = base64.urlsafe_b64decode(data).decode('utf-8')
                if mime_type == 'text/html':
                    body_html = decoded_data
                else:
                    body_text = decoded_data
        
        return body_html, body_text


if __name__ == "__main__":
    # 测试邮件获取
    try:
        fetcher = EmailFetcher()
        alerts = fetcher.fetch_google_alerts(days=7)
        
        print(f"\n获取到 {len(alerts)} 封 Google Alert 邮件")
        
        total_articles = 0
        for alert in alerts:
            total_articles += len(alert.articles)
            print(f"\n邮件: {alert.subject}")
            print(f"日期: {alert.date}")
            print(f"文章数量: {len(alert.articles)}")
            
            for i, article in enumerate(alert.articles[:3], 1):  # 只显示前3篇
                print(f"  {i}. {article['title']}")
                print(f"     来源: {article['source']}")
                print(f"     链接: {article['url'][:100]}...")
        
        print(f"\n总共提取到 {total_articles} 篇文章")
        
    except Exception as e:
        print(f"测试失败: {e}")
