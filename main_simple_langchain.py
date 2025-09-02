"""
主程序 - 基于简化Langchain架构的Google Alert处理系统
"""
import argparse
import sys
from datetime import datetime

from simple_langchain import LangchainProcessor
from data_storage import db_manager
from excel_exporter import excel_exporter
from config import DEEPSEEK_API_KEY


def main():
    """主函数 - 命令行接口"""
    parser = argparse.ArgumentParser(
        description='Google Alert 邮件处理和筛选系统 (简化Langchain架构)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
基于Langchain架构的新闻处理系统

使用示例:
  python main_simple_langchain.py                    # 运行完整Langchain工作流
  python main_simple_langchain.py --days 3          # 获取3天内的邮件
  python main_simple_langchain.py --fetch-only      # 仅获取邮件(Chain 1)
  python main_simple_langchain.py --filter-only     # 仅筛选文章(Chain 2)
  python main_simple_langchain.py --report-only     # 仅生成报告(Chain 3)
  python main_simple_langchain.py --stats           # 显示统计信息
  python main_simple_langchain.py --export-excel    # 导出Excel报告

Langchain架构特点:
  - 使用PromptTemplate进行提示管理
  - 模块化的Chain设计
  - 结构化的输出解析
  - 可扩展的工作流设计
        """
    )
    
    # 基本选项
    parser.add_argument('--days', type=int, default=1, 
                       help='获取最近几天的邮件 (默认: 1)')
    parser.add_argument('--limit', type=int, default=None, 
                       help='筛选文章数量限制 (默认: 无限制，处理所有未筛选文章)')
    
    # 执行模式选项
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--fetch-only', action='store_true', 
                           help='仅执行邮件获取链 (Chain 1)')
    mode_group.add_argument('--filter-only', action='store_true', 
                           help='仅执行文章筛选链 (Chain 2)')
    mode_group.add_argument('--report-only', action='store_true', 
                           help='仅执行报告生成链 (Chain 3)')
    mode_group.add_argument('--stats', action='store_true', 
                           help='显示数据库统计信息')
    mode_group.add_argument('--export-excel', action='store_true', 
                           help='导出Excel报告')
    
    # Excel相关选项
    parser.add_argument('--excel-days', type=int, default=1, 
                       help='Excel导出天数 (默认: 1)') 
    parser.add_argument('--no-auto-excel', action='store_true',
                       help='完整工作流时不自动导出当日Excel文件')
    
    # 调试选项
    parser.add_argument('--verbose', '-v', action='store_true', 
                       help='详细输出模式')
    
    args = parser.parse_args()
    
    # 显示系统信息
    print("Google Alert 处理系统 (简化Langchain架构)")
    print(f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"架构: Langchain (简化版)")
    
    if args.verbose:
        print("详细输出模式已启用")
    
    # 检查API配置
    if not DEEPSEEK_API_KEY:
        print("未设置DEEPSEEK_API_KEY，筛选功能将不可用")
        if not args.stats and not args.fetch_only and not args.export_excel:
            print("筛选和报告功能需要DEEPSEEK_API_KEY")
            sys.exit(1)
    
    try:
        # 初始化Langchain处理器
        print("初始化Langchain处理器...")
        processor = LangchainProcessor()
        
        # 根据参数执行相应功能
        if args.stats:
            # 显示统计信息
            print(f"\n数据库统计信息:")
            stats = db_manager.get_statistics()
            print(f"总邮件数: {stats['total_emails']}")
            print(f"总文章数: {stats['total_articles']}")
            print(f"已筛选文章数: {stats['filtered_articles']}")
            print(f"筛选通过文章数: {stats['selected_articles']}")
            print(f"筛选率: {stats['filter_rate']:.2%}")
            print(f"通过率: {stats['selection_rate']:.2%}")
            
        elif args.fetch_only:
            # 仅执行邮件获取链
            print(f"\n 执行Langchain邮件获取链...")
            result = processor.fetch_emails_chain(days=args.days)
            
            print(f"\n 邮件获取链执行结果:")
            print(f" 获取邮件数: {len(result.get('emails', []))}")
            print(f" 新增文章数: {result.get('articles_count', 0)}")
            
            if args.verbose:
                print(f" 详细信息: {result}")
                
        elif args.filter_only:
            # 仅执行文章筛选链
            limit_msg = f"限制 {args.limit} 篇" if args.limit else "所有未筛选文章"
            print(f"\n 执行Langchain文章筛选链 ({limit_msg})...")
            result = processor.filter_articles_chain(limit=args.limit)
            
            print(f"\n 文章筛选链执行结果:")
            print(f" 处理文章数: {result.get('processed', 0)}/{result.get('total', 0)}")
            print(f" 筛选通过: {result.get('selected', 0)}")
            print(f" 筛选未通过: {result.get('rejected', 0)}")
            print(f" 处理失败: {result.get('failed', 0)}")
            
            if args.verbose:
                print(f" 详细统计: {result}")
                
        elif args.report_only:
            # 仅执行报告生成链
            print(f"\n 执行Langchain报告生成链...")
            report = processor.generate_report_chain(days=args.days)
            
            if report:
                print(f"\n 生成的报告:")
                print(report)
            else:
                print(" 报告生成失败或无数据")
                
        elif args.export_excel:
            # Excel导出
            print(f"\n 导出Excel报告...")
            try:
                excel_file = excel_exporter.export_selected_articles(days=args.excel_days)
                if excel_file:
                    print(f" Excel报告已生成: {excel_file}")
                    if args.verbose:
                        print(f" 文件路径: {excel_file}")
                else:
                    print(" 没有找到筛选通过的文章")
            except Exception as e:
                print(f" Excel导出失败: {e}")
                
        else:
            # 默认: 运行完整的Langchain工作流
            print(f"\n 执行完整Langchain工作流...")
            
            # 决定是否自动导出Excel
            auto_export = not args.no_auto_excel
            if auto_export:
                print(f" 将自动导出当日Excel文件")
            else:
                print(f" 已禁用自动Excel导出")
            
            result = processor.run_full_workflow(
                days=args.days, 
                filter_limit=args.limit,
                auto_export_excel=auto_export
            )
            
            # 显示工作流结果摘要
            print(f"\n Langchain工作流执行摘要:")
            print(f" 架构: {result.get('architecture', 'unknown')}")
            print(f" 状态: {result.get('workflow_status', 'unknown')}")
            print(f" 处理邮件数: {result.get('emails_processed', 0)}")
            print(f" 新增文章数: {result.get('articles_added', 0)}")
            
            # 显示Excel文件信息
            excel_file = result.get('excel_file', '')
            if excel_file:
                print(f" Excel文件: {excel_file}")
            
            filter_stats = result.get('filter_stats', {})
            if filter_stats:
                print(f" 筛选统计:")
                print(f"  - 处理: {filter_stats.get('processed', 0)}/{filter_stats.get('total', 0)}")
                print(f"  - 通过: {filter_stats.get('selected', 0)}")
                print(f"  - 未通过: {filter_stats.get('rejected', 0)}")
                print(f"  - 失败: {filter_stats.get('failed', 0)}")
            
            if args.verbose:
                print(f"\n 完整结果:")
                for key, value in result.items():
                    if key != 'report':  # 报告已经在工作流中显示了
                        print(f"  {key}: {value}")
        
        print(f"\n 程序执行完成!")
        print(f" 结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except KeyboardInterrupt:
        print(f"\n 用户中断程序执行")
        sys.exit(1)
    except Exception as e:
        print(f"\n 程序执行失败: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
