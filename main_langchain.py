"""
主程序 - 基于Langchain架构的Google Alert处理系统
使用Langchain的Chain、Agent和Memory系统
"""
import argparse
import sys
from datetime import datetime

from langchain_chains import NewsProcessingWorkflow
from data_storage import db_manager
from excel_exporter import excel_exporter
from config import DEEPSEEK_API_KEY


class LangchainNewsProcessor:
    """基于Langchain的新闻处理器"""
    
    def __init__(self):
        """初始化处理器"""
        self.workflow = None
        self._initialize_workflow()
    
    def _initialize_workflow(self):
        """初始化Langchain工作流"""
        try:
            print("🔧 初始化Langchain工作流...")
            
            # 检查必要配置
            if not DEEPSEEK_API_KEY:
                print("⚠️ 未设置DEEPSEEK_API_KEY，筛选功能将不可用")
                
            # 检查数据库连接
            print("🔍 检查数据库连接...")
            stats = db_manager.get_statistics()
            print(f"✅ 数据库连接成功 (现有 {stats['total_emails']} 封邮件, {stats['total_articles']} 篇文章)")
            
            # 初始化工作流
            self.workflow = NewsProcessingWorkflow()
            print("✅ Langchain工作流初始化成功")
            
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            sys.exit(1)
    
    def run_full_workflow(self, days: int = 1, filter_limit: int = 50) -> dict:
        """运行完整工作流程"""
        if not self.workflow:
            raise RuntimeError("工作流未初始化")
        
        return self.workflow.run_full_workflow(days=days, filter_limit=filter_limit)
    
    def fetch_emails_only(self, days: int = 1) -> dict:
        """仅获取邮件"""
        if not self.workflow:
            raise RuntimeError("工作流未初始化")
        
        print(f"\n🔄 仅执行邮件获取任务...")
        return self.workflow.run_email_only(days=days)
    
    def filter_articles_only(self, limit: int = 50) -> dict:
        """仅筛选文章"""
        if not self.workflow:
            raise RuntimeError("工作流未初始化")
        
        print(f"\n🤖 仅执行文章筛选任务...")
        return self.workflow.run_filter_only(limit=limit)
    
    def generate_report_only(self, days: int = 1) -> dict:
        """仅生成报告"""
        if not self.workflow:
            raise RuntimeError("工作流未初始化")
        
        print(f"\n📊 仅执行报告生成任务...")
        return self.workflow.run_report_only(days=days)
    
    def show_statistics(self):
        """显示统计信息"""
        print(f"\n📈 数据库统计信息:")
        stats = db_manager.get_statistics()
        print(f"📧 总邮件数: {stats['total_emails']}")
        print(f"📰 总文章数: {stats['total_articles']}")
        print(f"🔍 已筛选文章数: {stats['filtered_articles']}")
        print(f"✅ 筛选通过文章数: {stats['selected_articles']}")
        print(f"📊 筛选率: {stats['filter_rate']:.2%}")
        print(f"🎯 通过率: {stats['selection_rate']:.2%}")
    
    def export_excel_report(self, days: int = 1) -> str:
        """导出Excel报告"""
        print(f"📊 导出最近 {days} 天的筛选结果到Excel...")
        try:
            excel_file = excel_exporter.export_selected_articles(days=days)
            if excel_file:
                print(f"✅ Excel报告已生成: {excel_file}")
                return excel_file
            else:
                print("⚠️ 没有找到筛选通过的文章")
                return ""
        except Exception as e:
            print(f"❌ Excel导出失败: {e}")
            return ""
    
    def get_workflow_memory(self) -> dict:
        """获取工作流内存信息"""
        if not self.workflow:
            return {}
        return self.workflow.get_memory_variables()


def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(
        description='Google Alert 邮件处理和筛选系统 (Langchain架构)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  python main_langchain.py                    # 运行完整工作流
  python main_langchain.py --days 3          # 获取3天内的邮件
  python main_langchain.py --fetch-only      # 仅获取邮件
  python main_langchain.py --filter-only     # 仅筛选文章
  python main_langchain.py --report-only     # 仅生成报告
  python main_langchain.py --stats           # 显示统计信息
  python main_langchain.py --export-excel    # 导出Excel报告
        """
    )
    
    # 基本选项
    parser.add_argument('--days', type=int, default=1, 
                       help='获取最近几天的邮件 (默认: 1)')
    parser.add_argument('--limit', type=int, default=50, 
                       help='筛选文章数量限制 (默认: 50)')
    
    # 执行模式选项
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--fetch-only', action='store_true', 
                           help='仅获取邮件，不进行筛选')
    mode_group.add_argument('--filter-only', action='store_true', 
                           help='仅筛选现有文章，不获取新邮件')
    mode_group.add_argument('--report-only', action='store_true', 
                           help='仅生成报告')
    mode_group.add_argument('--stats', action='store_true', 
                           help='显示数据库统计信息')
    mode_group.add_argument('--export-excel', action='store_true', 
                           help='导出Excel报告')
    
    # Excel相关选项
    parser.add_argument('--excel-days', type=int, default=1, 
                       help='Excel导出天数 (默认: 1)')
    
    # 调试选项
    parser.add_argument('--memory', action='store_true', 
                       help='显示工作流内存信息')
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='详细输出模式')
    
    args = parser.parse_args()
    
    # 设置详细输出
    if args.verbose:
        print("🔧 详细输出模式已启用")
    
    try:
        # 初始化处理器
        processor = LangchainNewsProcessor()
        
        # 根据参数执行相应功能
        if args.stats:
            processor.show_statistics()
            
        elif args.fetch_only:
            result = processor.fetch_emails_only(days=args.days)
            if args.verbose:
                print(f"📧 邮件获取结果: {len(result.get('emails', []))} 封邮件")
                
        elif args.filter_only:
            result = processor.filter_articles_only(limit=args.limit)
            if args.verbose:
                print(f"🤖 筛选结果: {result.get('filter_stats', {})}")
                
        elif args.report_only:
            result = processor.generate_report_only(days=args.days)
            if result.get('report'):
                print(result['report'])
            else:
                print("⚠️ 报告生成失败或无数据")
                
        elif args.export_excel:
            excel_file = processor.export_excel_report(days=args.excel_days)
            if excel_file and args.verbose:
                print(f"📁 文件路径: {excel_file}")
                
        else:
            # 默认: 运行完整工作流程
            result = processor.run_full_workflow(days=args.days, filter_limit=args.limit)
            
            if args.verbose:
                print(f"\n🔍 详细结果:")
                print(f"  📧 处理邮件数: {result.get('emails_processed', 0)}")
                print(f"  🤖 筛选统计: {result.get('filter_stats', {})}")
                print(f"  📊 工作流状态: {result.get('workflow_status', 'unknown')}")
        
        # 显示内存信息（如果请求）
        if args.memory:
            memory_info = processor.get_workflow_memory()
            if memory_info:
                print(f"\n🧠 工作流内存信息:")
                for key, value in memory_info.items():
                    print(f"  {key}: {value}")
            else:
                print(f"\n🧠 工作流内存为空")
        
        print(f"\n✅ 程序执行完成!")
        
    except KeyboardInterrupt:
        print(f"\n⚠️ 用户中断程序执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 程序执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
