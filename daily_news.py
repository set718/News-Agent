#!/usr/bin/env python3
"""
每日新闻处理脚本
专门用于每天运行，只处理当天的Google Alert邮件
"""
import sys
from datetime import datetime, timedelta
from main import GoogleAlertProcessor
from excel_exporter import excel_exporter


def run_daily_processing():
    """运行每日新闻处理"""
    print(f"🌅 每日新闻处理开始")
    print(f"📅 处理日期: {datetime.now().strftime('%Y年%m月%d日')}")
    print(f"⏰ 运行时间: {datetime.now().strftime('%H:%M:%S')}")
    print("="*60)
    
    try:
        # 初始化处理器
        processor = GoogleAlertProcessor()
        
        # 只处理最近1天的邮件
        print("📧 获取今日Google Alert邮件...")
        emails = processor.fetch_and_store_emails(days=1)
        
        if not emails:
            print("📭 今日没有新的Google Alert邮件")
            return
        
        # 统计今日新增文章
        total_articles = sum(len(email.articles) for email in emails)
        print(f"📰 今日新增文章: {total_articles} 篇")
        
        if total_articles == 0:
            print("📝 今日邮件中没有提取到新文章")
            return
        
        # 筛选今日文章
        print("\n🤖 开始AI智能筛选...")
        filter_stats = processor.filter_articles(limit=total_articles)
        
        # 生成今日报告
        print("\n📊 生成今日筛选报告...")
        report = processor.generate_report(days=1)
        
        # 输出结果摘要
        print("\n" + "="*60)
        print("📈 今日处理结果摘要:")
        print(f"  • 处理邮件: {len(emails)} 封")
        print(f"  • 新增文章: {total_articles} 篇")
        if filter_stats:
            print(f"  • 筛选处理: {filter_stats.get('processed', 0)} 篇")
            print(f"  • 筛选通过: {filter_stats.get('selected', 0)} 篇")
            print(f"  • 通过率: {filter_stats.get('selected', 0) / max(filter_stats.get('processed', 1), 1) * 100:.1f}%")
        
        # 如果有筛选通过的文章，显示详细报告并导出Excel
        if filter_stats and filter_stats.get('selected', 0) > 0:
            print("\n" + "="*60)
            print("📄 今日精选汽车制造新闻:")
            print("="*60)
            print(report)
            
            # 导出今日Excel报告
            print("\n📊 导出Excel报告...")
            try:
                excel_file = excel_exporter.export_daily_report()
                if excel_file:
                    print(f"✅ Excel报告已生成: {excel_file}")
                else:
                    print("⚠️ Excel导出未生成文件")
            except Exception as e:
                print(f"❌ Excel导出失败: {e}")
        else:
            print("\n💡 今日暂无符合汽车制造工程师关注的精选内容")
        
        print("\n✅ 今日新闻处理完成！")
        
    except Exception as e:
        print(f"\n❌ 处理过程中出现错误: {e}")
        sys.exit(1)


def show_daily_stats():
    """显示每日统计信息"""
    from data_storage import db_manager
    
    print("📊 数据库统计信息:")
    stats = db_manager.get_statistics()
    print(f"  • 总邮件数: {stats['total_emails']}")
    print(f"  • 总文章数: {stats['total_articles']}")
    print(f"  • 已筛选文章: {stats['filtered_articles']}")
    print(f"  • 筛选通过文章: {stats['selected_articles']}")
    
    if stats['total_articles'] > 0:
        print(f"  • 总筛选率: {stats['filter_rate']:.1%}")
    if stats['filtered_articles'] > 0:
        print(f"  • 总通过率: {stats['selection_rate']:.1%}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='每日Google Alert新闻处理')
    parser.add_argument('--stats-only', action='store_true', help='仅显示统计信息')
    parser.add_argument('--today-only', action='store_true', help='仅处理今日邮件（默认行为）')
    
    args = parser.parse_args()
    
    if args.stats_only:
        show_daily_stats()
    else:
        run_daily_processing()


if __name__ == "__main__":
    main()
