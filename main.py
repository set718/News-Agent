"""
主要工作流程
整合Gmail邮件获取、数据存储和DeepSeek筛选功能
"""
import argparse
import sys
from datetime import datetime, timedelta
from typing import List

from email_fetcher import EmailFetcher, GoogleAlertEmail
from data_storage import db_manager
from deepseek_filter import DeepSeekFilter, ContentAnalyzer
from excel_exporter import excel_exporter
from config import DEEPSEEK_API_KEY


class GoogleAlertProcessor:
    """Google Alert 处理器主类"""
    
    def __init__(self):
        self.email_fetcher = None
        self.content_filter = None
        self.content_analyzer = None
        
        self._initialize_components()
    
    def _initialize_components(self):
        """初始化各个组件"""
        try:
            # 初始化邮件获取器
            print("初始化Gmail连接...")
            self.email_fetcher = EmailFetcher()
            print("✓ Gmail连接成功")
            
            # 初始化内容筛选器
            if DEEPSEEK_API_KEY:
                print("初始化DeepSeek筛选器...")
                self.content_filter = DeepSeekFilter()
                self.content_analyzer = ContentAnalyzer(self.content_filter)
                print("✓ DeepSeek筛选器初始化成功")
            else:
                print("⚠ 未设置DEEPSEEK_API_KEY，跳过筛选功能")
            
            # 检查数据库连接
            print("检查数据库连接...")
            stats = db_manager.get_statistics()
            print(f"✓ 数据库连接成功 (现有 {stats['total_emails']} 封邮件, {stats['total_articles']} 篇文章)")
            
        except Exception as e:
            print(f"✗ 初始化失败: {e}")
            sys.exit(1)
    
    def fetch_and_store_emails(self, days: int = 7) -> List[GoogleAlertEmail]:
        """
        获取并存储Google Alert邮件
        
        Args:
            days: 获取最近几天的邮件
            
        Returns:
            邮件列表
        """
        print(f"\n{'='*50}")
        print(f"步骤 1: 获取最近 {days} 天的 Google Alert 邮件")
        print(f"{'='*50}")
        
        try:
            # 获取邮件
            alert_emails = self.email_fetcher.fetch_google_alerts(days=days)
            
            if not alert_emails:
                print("没有找到新的Google Alert邮件")
                return []
            
            # 存储邮件和文章
            total_new_articles = 0
            
            for email in alert_emails:
                # 保存邮件
                saved_email = db_manager.save_alert_email({
                    'message_id': email.message_id,
                    'subject': email.subject,
                    'sender': email.sender,
                    'date': email.date,
                    'body_html': email.body_html,
                    'body_text': email.body_text
                })
                
                if saved_email and email.articles:
                    # 为文章添加邮件ID
                    for article in email.articles:
                        article['email_message_id'] = email.message_id
                    
                    # 保存文章
                    saved_articles = db_manager.save_articles(email.articles)
                    total_new_articles += len(saved_articles)
            
            print(f"✓ 处理完成: {len(alert_emails)} 封邮件, {total_new_articles} 篇新文章")
            return alert_emails
            
        except Exception as e:
            print(f"✗ 邮件获取失败: {e}")
            return []
    
    def filter_articles(self, limit: int = 50) -> dict:
        """
        筛选文章内容
        
        Args:
            limit: 每次处理的文章数量上限
            
        Returns:
            筛选统计信息
        """
        print(f"\n{'='*50}")
        print(f"步骤 2: 使用 DeepSeek 筛选文章内容")
        print(f"{'='*50}")
        
        if not self.content_filter:
            print("✗ DeepSeek筛选器未初始化，跳过筛选步骤")
            return {}
        
        try:
            # 筛选未处理的文章
            stats = self.content_filter.filter_unprocessed_articles(limit=limit)
            
            if stats['total'] == 0:
                print("没有找到需要筛选的文章")
            else:
                print(f"✓ 筛选完成:")
                print(f"  - 处理文章: {stats['processed']}/{stats['total']}")
                print(f"  - 筛选通过: {stats['selected']}")
                print(f"  - 筛选未通过: {stats['rejected']}")
                if stats['failed'] > 0:
                    print(f"  - 处理失败: {stats['failed']}")
            
            return stats
            
        except Exception as e:
            print(f"✗ 文章筛选失败: {e}")
            return {}
    
    def generate_report(self, days: int = 7) -> str:
        """
        生成筛选报告
        
        Args:
            days: 报告时间范围（天）
            
        Returns:
            报告内容
        """
        print(f"\n{'='*50}")
        print(f"步骤 3: 生成筛选报告")
        print(f"{'='*50}")
        
        try:
            # 获取数据库统计
            stats = db_manager.get_statistics()
            
            print(f"数据库统计:")
            print(f"  - 总邮件数: {stats['total_emails']}")
            print(f"  - 总文章数: {stats['total_articles']}")
            print(f"  - 已筛选: {stats['filtered_articles']}")
            print(f"  - 筛选通过: {stats['selected_articles']}")
            
            # 生成详细报告
            if self.content_analyzer:
                report = self.content_analyzer.generate_summary_report(days=days)
                return report
            else:
                return "未启用内容分析功能"
                
        except Exception as e:
            print(f"✗ 报告生成失败: {e}")
            return ""
    
    def run_full_workflow(self, days: int = 7, filter_limit: int = 50):
        """
        运行完整工作流程
        
        Args:
            days: 邮件获取天数
            filter_limit: 筛选文章数量限制
        """
        print(f"Google Alert 处理工作流程启动")
        print(f"处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 步骤1: 获取和存储邮件
        emails = self.fetch_and_store_emails(days=days)
        
        # 步骤2: 筛选文章
        filter_stats = self.filter_articles(limit=filter_limit)
        
        # 步骤3: 生成报告
        report = self.generate_report(days=days)
        
        # 输出最终结果
        print(f"\n{'='*50}")
        print(f"工作流程完成")
        print(f"{'='*50}")
        
        if report:
            print(report)
        
        return {
            'emails_processed': len(emails),
            'filter_stats': filter_stats,
            'report': report
        }


def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(description='Google Alert 邮件处理和筛选系统')
    parser.add_argument('--days', type=int, default=7, help='获取最近几天的邮件 (默认: 7)')
    parser.add_argument('--limit', type=int, default=50, help='筛选文章数量限制 (默认: 50)')
    parser.add_argument('--fetch-only', action='store_true', help='仅获取邮件，不进行筛选')
    parser.add_argument('--filter-only', action='store_true', help='仅筛选现有文章，不获取新邮件')
    parser.add_argument('--report-only', action='store_true', help='仅生成报告')
    parser.add_argument('--stats', action='store_true', help='显示数据库统计信息')
    parser.add_argument('--export-excel', action='store_true', help='导出Excel报告')
    parser.add_argument('--excel-days', type=int, default=7, help='Excel导出天数 (默认: 7)')
    
    args = parser.parse_args()
    
    # 初始化处理器
    processor = GoogleAlertProcessor()
    
    if args.stats:
        # 显示统计信息
        stats = db_manager.get_statistics()
        print(f"\n数据库统计信息:")
        print(f"总邮件数: {stats['total_emails']}")
        print(f"总文章数: {stats['total_articles']}")
        print(f"已筛选文章数: {stats['filtered_articles']}")
        print(f"筛选通过文章数: {stats['selected_articles']}")
        print(f"筛选率: {stats['filter_rate']:.2%}")
        print(f"通过率: {stats['selection_rate']:.2%}")
        return
    
    if args.fetch_only:
        # 仅获取邮件
        processor.fetch_and_store_emails(days=args.days)
    elif args.filter_only:
        # 仅筛选文章
        processor.filter_articles(limit=args.limit)
    elif args.report_only:
        # 仅生成报告
        report = processor.generate_report(days=args.days)
        if report:
            print(report)
    elif args.export_excel:
        # 仅导出Excel
        try:
            print(f"📊 导出最近 {args.excel_days} 天的筛选结果到Excel...")
            excel_file = excel_exporter.export_selected_articles(days=args.excel_days)
            if excel_file:
                print(f"✅ Excel报告已生成: {excel_file}")
            else:
                print("⚠️ 没有找到筛选通过的文章")
        except Exception as e:
            print(f"❌ Excel导出失败: {e}")
    else:
        # 运行完整工作流程
        processor.run_full_workflow(days=args.days, filter_limit=args.limit)


if __name__ == "__main__":
    main()
