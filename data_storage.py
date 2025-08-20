"""
数据存储模块
使用SQLAlchemy进行结构化数据存储
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Boolean, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from config import DATABASE_URL

Base = declarative_base()


class GoogleAlertEmail(Base):
    """Google Alert 邮件表"""
    __tablename__ = 'google_alert_emails'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(255), unique=True, nullable=False, index=True)
    subject = Column(String(500), nullable=False)
    sender = Column(String(255), nullable=False)
    date = Column(DateTime, nullable=False, index=True)
    body_html = Column(Text)
    body_text = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<GoogleAlertEmail(id={self.id}, subject='{self.subject[:50]}...', date='{self.date}')>"


class NewsArticle(Base):
    """新闻文章表"""
    __tablename__ = 'news_articles'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    email_message_id = Column(String(255), nullable=False, index=True)  # 关联的邮件ID
    title = Column(String(1000), nullable=False)
    url = Column(Text, nullable=False)
    source = Column(String(255))
    publish_time = Column(String(100))  # 原始时间字符串
    summary = Column(Text)
    alert_subject = Column(String(500))
    alert_date = Column(DateTime, index=True)
    
    # 筛选结果字段
    is_selected = Column(Boolean, default=None)  # None=未筛选，True=通过，False=未通过
    quality_score = Column(Float)
    relevance_score = Column(Float)
    filter_reason = Column(Text)
    key_points = Column(Text)  # JSON字符串存储关键要点
    category = Column(String(100))
    
    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    filtered_at = Column(DateTime)  # 筛选时间
    
    def __repr__(self):
        return f"<NewsArticle(id={self.id}, title='{self.title[:50]}...', source='{self.source}')>"


class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, database_url: str = DATABASE_URL):
        self.engine = create_engine(database_url, echo=False)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # 创建表
        self.create_tables()
    
    def create_tables(self):
        """创建数据库表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            print("数据库表创建成功")
        except SQLAlchemyError as e:
            print(f"创建数据库表失败: {e}")
            raise
    
    def get_session(self) -> Session:
        """获取数据库会话"""
        return self.SessionLocal()
    
    def save_alert_email(self, email_data: dict) -> Optional[GoogleAlertEmail]:
        """
        保存Google Alert邮件
        
        Args:
            email_data: 邮件数据字典
            
        Returns:
            保存的邮件对象，如果已存在则返回None
        """
        session = self.get_session()
        try:
            # 检查是否已存在
            existing = session.query(GoogleAlertEmail).filter_by(
                message_id=email_data['message_id']
            ).first()
            
            if existing:
                print(f"邮件 {email_data['message_id']} 已存在，跳过保存")
                return None
            
            # 创建新邮件记录
            email = GoogleAlertEmail(
                message_id=email_data['message_id'],
                subject=email_data['subject'],
                sender=email_data['sender'],
                date=email_data['date'],
                body_html=email_data.get('body_html', ''),
                body_text=email_data.get('body_text', '')
            )
            
            session.add(email)
            session.commit()
            print(f"保存邮件: {email.subject}")
            return email
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"保存邮件失败: {e}")
            return None
        finally:
            session.close()
    
    def save_articles(self, articles: List[dict]) -> List[NewsArticle]:
        """
        批量保存新闻文章
        
        Args:
            articles: 文章数据列表
            
        Returns:
            保存的文章对象列表
        """
        session = self.get_session()
        saved_articles = []
        
        try:
            for article_data in articles:
                # 检查是否已存在相同URL的文章
                existing = session.query(NewsArticle).filter_by(
                    url=article_data['url']
                ).first()
                
                if existing:
                    print(f"文章已存在，跳过: {article_data['title'][:50]}...")
                    continue
                
                # 创建新文章记录
                article = NewsArticle(
                    email_message_id=article_data.get('email_message_id', ''),
                    title=article_data['title'],
                    url=article_data['url'],
                    source=article_data.get('source', ''),
                    publish_time=article_data.get('publish_time', ''),
                    summary=article_data.get('summary', ''),
                    alert_subject=article_data.get('alert_subject', ''),
                    alert_date=article_data.get('alert_date')
                )
                
                session.add(article)
                saved_articles.append(article)
            
            session.commit()
            print(f"保存 {len(saved_articles)} 篇新文章")
            return saved_articles
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"保存文章失败: {e}")
            return []
        finally:
            session.close()
    
    def update_article_filter_result(self, article_id: int, filter_result: dict) -> bool:
        """
        更新文章筛选结果
        
        Args:
            article_id: 文章ID
            filter_result: 筛选结果字典
            
        Returns:
            是否更新成功
        """
        session = self.get_session()
        try:
            article = session.query(NewsArticle).filter_by(id=article_id).first()
            if not article:
                print(f"未找到文章 ID: {article_id}")
                return False
            
            # 更新筛选结果
            article.is_selected = filter_result.get('is_selected')
            article.quality_score = filter_result.get('quality_score')
            article.relevance_score = filter_result.get('relevance_score')
            article.filter_reason = filter_result.get('reason', '')
            article.category = filter_result.get('category', '')
            article.filtered_at = datetime.utcnow()
            
            # 处理关键要点（转换为JSON字符串）
            key_points = filter_result.get('key_points', [])
            if key_points:
                import json
                article.key_points = json.dumps(key_points, ensure_ascii=False)
            
            session.commit()
            return True
            
        except SQLAlchemyError as e:
            session.rollback()
            print(f"更新筛选结果失败: {e}")
            return False
        finally:
            session.close()
    
    def get_unfiltered_articles(self, limit: int = 100) -> List[NewsArticle]:
        """
        获取未筛选的文章
        
        Args:
            limit: 限制返回数量
            
        Returns:
            未筛选的文章列表
        """
        session = self.get_session()
        try:
            articles = session.query(NewsArticle).filter(
                NewsArticle.is_selected.is_(None)
            ).order_by(NewsArticle.created_at.desc()).limit(limit).all()
            
            return articles
        finally:
            session.close()
    
    def get_selected_articles(self, days: int = 7) -> List[NewsArticle]:
        """
        获取筛选通过的文章
        
        Args:
            days: 最近天数
            
        Returns:
            筛选通过的文章列表
        """
        session = self.get_session()
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            articles = session.query(NewsArticle).filter(
                NewsArticle.is_selected == True,
                NewsArticle.alert_date >= cutoff_date
            ).order_by(NewsArticle.quality_score.desc()).all()
            
            return articles
        finally:
            session.close()
    
    def get_statistics(self) -> dict:
        """获取数据统计信息"""
        session = self.get_session()
        try:
            total_emails = session.query(GoogleAlertEmail).count()
            total_articles = session.query(NewsArticle).count()
            filtered_articles = session.query(NewsArticle).filter(
                NewsArticle.is_selected.isnot(None)
            ).count()
            selected_articles = session.query(NewsArticle).filter(
                NewsArticle.is_selected == True
            ).count()
            
            return {
                'total_emails': total_emails,
                'total_articles': total_articles,
                'filtered_articles': filtered_articles,
                'selected_articles': selected_articles,
                'filter_rate': filtered_articles / total_articles if total_articles > 0 else 0,
                'selection_rate': selected_articles / filtered_articles if filtered_articles > 0 else 0
            }
        finally:
            session.close()


# 全局数据库管理器实例
db_manager = DatabaseManager()


if __name__ == "__main__":
    # 测试数据库功能
    from datetime import timedelta
    
    print("测试数据库连接...")
    
    # 创建测试数据
    test_email_data = {
        'message_id': 'test_message_123',
        'subject': 'Google 快讯 - 测试主题',
        'sender': 'googlealerts-noreply@google.com',
        'date': datetime.now(),
        'body_html': '<html><body>测试邮件内容</body></html>',
        'body_text': '测试邮件内容'
    }
    
    # 保存测试邮件
    saved_email = db_manager.save_alert_email(test_email_data)
    if saved_email:
        print(f"保存测试邮件成功: {saved_email.id}")
        
        # 创建测试文章
        test_articles = [
            {
                'email_message_id': test_email_data['message_id'],
                'title': '测试新闻文章1',
                'url': 'https://example.com/news1',
                'source': '测试新闻源',
                'publish_time': '1小时前',
                'summary': '这是一篇测试新闻的摘要内容',
                'alert_subject': test_email_data['subject'],
                'alert_date': test_email_data['date']
            },
            {
                'email_message_id': test_email_data['message_id'],
                'title': '测试新闻文章2',
                'url': 'https://example.com/news2',
                'source': '另一个新闻源',
                'publish_time': '2小时前',
                'summary': '这是另一篇测试新闻的摘要内容',
                'alert_subject': test_email_data['subject'],
                'alert_date': test_email_data['date']
            }
        ]
        
        # 保存测试文章
        saved_articles = db_manager.save_articles(test_articles)
        print(f"保存测试文章: {len(saved_articles)} 篇")
        
        # 测试筛选结果更新
        if saved_articles:
            test_filter_result = {
                'is_selected': True,
                'quality_score': 8.5,
                'relevance_score': 9.0,
                'reason': '内容质量高，相关性强',
                'key_points': ['关键点1', '关键点2', '关键点3'],
                'category': '科技新闻'
            }
            
            success = db_manager.update_article_filter_result(
                saved_articles[0].id, test_filter_result
            )
            print(f"更新筛选结果: {'成功' if success else '失败'}")
    
    # 获取统计信息
    stats = db_manager.get_statistics()
    print(f"\n数据库统计:")
    print(f"总邮件数: {stats['total_emails']}")
    print(f"总文章数: {stats['total_articles']}")
    print(f"已筛选文章数: {stats['filtered_articles']}")
    print(f"筛选通过文章数: {stats['selected_articles']}")
    print(f"筛选率: {stats['filter_rate']:.2%}")
    print(f"通过率: {stats['selection_rate']:.2%}")
    
    print("\n数据库测试完成")
