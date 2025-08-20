"""
Excel导出模块
将筛选通过的新闻导出为Excel文件
"""
import pandas as pd
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional
from data_storage import db_manager, NewsArticle


class ExcelExporter:
    """Excel导出器"""
    
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
    
    def export_selected_articles(self, days: int = 7, filename: Optional[str] = None) -> str:
        """
        导出筛选通过的文章到Excel
        
        Args:
            days: 最近天数
            filename: 自定义文件名
            
        Returns:
            生成的Excel文件路径
        """
        # 获取筛选通过的文章
        articles = db_manager.get_selected_articles(days=days)
        
        if not articles:
            print(f"最近 {days} 天没有筛选通过的文章")
            return ""
        
        # 生成文件名
        if not filename:
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"汽车制造新闻筛选_{date_str}_{days}天.xlsx"
        
        filepath = self.output_dir / filename
        
        # 转换为DataFrame
        data = []
        for article in articles:
            # 解析关键要点
            key_points = []
            if article.key_points:
                try:
                    key_points = json.loads(article.key_points)
                    if isinstance(key_points, list):
                        key_points = '; '.join(key_points)
                    else:
                        key_points = str(key_points)
                except:
                    key_points = article.key_points or ""
            
            data.append({
                '序号': len(data) + 1,
                '文章标题': article.title,
                '原文链接': article.url,
                '质量评分': article.quality_score or 0,
                '相关性评分': article.relevance_score or 0,
                '筛选理由': article.filter_reason or "",
                '关键要点': key_points,
                '新闻分类': article.category or "",
                'Alert主题': article.alert_subject or "",
                '筛选时间': article.filtered_at.strftime("%Y-%m-%d %H:%M") if article.filtered_at else ""
            })
        
        df = pd.DataFrame(data)
        
        # 创建Excel写入器
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # 写入主要数据
            df.to_excel(writer, sheet_name='筛选通过文章', index=False)
            
            # 创建统计表
            self._create_summary_sheet(writer, articles, days)
            
            # 创建分类统计表
            self._create_category_sheet(writer, articles)
            
            # 格式化工作表
            self._format_worksheets(writer, df)
        
        print(f"✅ Excel报告已生成: {filepath}")
        print(f"📊 共导出 {len(articles)} 篇筛选通过的文章")
        
        return str(filepath)
    
    def _create_summary_sheet(self, writer, articles: List[NewsArticle], days: int):
        """创建统计摘要表"""
        # 计算统计数据
        total_articles = len(articles)
        avg_quality = sum(a.quality_score for a in articles if a.quality_score) / total_articles if total_articles > 0 else 0
        avg_relevance = sum(a.relevance_score for a in articles if a.relevance_score) / total_articles if total_articles > 0 else 0
        
        # Alert主题统计
        alert_stats = {}
        for article in articles:
            alert = article.alert_subject or "未知Alert"
            alert_stats[alert] = alert_stats.get(alert, 0) + 1
        
        # 创建摘要数据
        summary_data = [
            ['统计项目', '数值'],
            ['统计时间范围', f'最近 {days} 天'],
            ['报告生成时间', datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
            ['筛选通过文章总数', total_articles],
            ['平均质量评分', f'{avg_quality:.1f}/10'],
            ['平均相关性评分', f'{avg_relevance:.1f}/10'],
            ['', ''],  # 空行
            ['主要Alert主题', '文章数量']
        ]
        
        # 添加Alert主题统计（按数量排序）
        for alert, count in sorted(alert_stats.items(), key=lambda x: x[1], reverse=True):
            summary_data.append([alert, count])
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_excel(writer, sheet_name='统计摘要', index=False, header=False)
    
    def _create_category_sheet(self, writer, articles: List[NewsArticle]):
        """创建分类统计表"""
        category_stats = {}
        category_details = {}
        
        for article in articles:
            category = article.category or "未分类"
            category_stats[category] = category_stats.get(category, 0) + 1
            
            if category not in category_details:
                category_details[category] = []
            
            category_details[category].append({
                '标题': article.title[:50] + '...' if len(article.title) > 50 else article.title,
                '质量评分': article.quality_score or 0,
                '相关性评分': article.relevance_score or 0
            })
        
        # 创建分类汇总
        category_data = []
        for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
            avg_quality = sum(a['质量评分'] for a in category_details[category]) / count
            avg_relevance = sum(a['相关性评分'] for a in category_details[category]) / count
            
            category_data.append({
                '新闻分类': category,
                '文章数量': count,
                '平均质量评分': f'{avg_quality:.1f}',
                '平均相关性评分': f'{avg_relevance:.1f}'
            })
        
        category_df = pd.DataFrame(category_data)
        category_df.to_excel(writer, sheet_name='分类统计', index=False)
    
    def _format_worksheets(self, writer, main_df: pd.DataFrame):
        """格式化Excel工作表"""
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils.dataframe import dataframe_to_rows
        
        # 获取工作簿
        workbook = writer.book
        
        # 格式化主要数据表
        main_sheet = workbook['筛选通过文章']
        
        # 设置标题行格式
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="366092", end_color="366092", fill_type="solid")
        
        for cell in main_sheet[1]:
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        # 调整列宽
        column_widths = {
            'A': 8,   # 序号
            'B': 45,  # 标题 (加宽)
            'C': 50,  # 链接
            'D': 10,  # 质量评分
            'E': 10,  # 相关性评分
            'F': 30,  # 筛选理由
            'G': 35,  # 关键要点 (加宽)
            'H': 15,  # 分类
            'I': 20,  # Alert主题
            'J': 15   # 筛选时间
        }
        
        for column, width in column_widths.items():
            main_sheet.column_dimensions[column].width = width
        
        # 设置链接列为超链接样式
        link_font = Font(color="0000FF", underline="single")
        for row in range(2, len(main_df) + 2):
            main_sheet[f'C{row}'].font = link_font
    
    def export_daily_report(self, date: Optional[datetime] = None) -> str:
        """
        导出每日报告
        
        Args:
            date: 指定日期，默认为今天
            
        Returns:
            生成的Excel文件路径
        """
        if date is None:
            date = datetime.now()
        
        date_str = date.strftime("%Y%m%d")
        filename = f"每日汽车制造新闻_{date_str}.xlsx"
        
        return self.export_selected_articles(days=1, filename=filename)
    
    def export_weekly_report(self) -> str:
        """导出周报"""
        date_str = datetime.now().strftime("%Y年第%U周")
        filename = f"汽车制造新闻周报_{date_str}.xlsx"
        
        return self.export_selected_articles(days=7, filename=filename)
    
    def export_monthly_report(self) -> str:
        """导出月报"""
        date_str = datetime.now().strftime("%Y年%m月")
        filename = f"汽车制造新闻月报_{date_str}.xlsx"
        
        return self.export_selected_articles(days=30, filename=filename)


# 全局导出器实例
excel_exporter = ExcelExporter()


if __name__ == "__main__":
    # 测试Excel导出功能
    import argparse
    
    parser = argparse.ArgumentParser(description='Excel导出测试')
    parser.add_argument('--days', type=int, default=7, help='导出最近几天的数据')
    parser.add_argument('--daily', action='store_true', help='导出今日报告')
    parser.add_argument('--weekly', action='store_true', help='导出周报')
    parser.add_argument('--monthly', action='store_true', help='导出月报')
    
    args = parser.parse_args()
    
    try:
        if args.daily:
            filepath = excel_exporter.export_daily_report()
        elif args.weekly:
            filepath = excel_exporter.export_weekly_report()
        elif args.monthly:
            filepath = excel_exporter.export_monthly_report()
        else:
            filepath = excel_exporter.export_selected_articles(days=args.days)
        
        if filepath:
            print(f"\n📁 文件位置: {filepath}")
            print("🎉 Excel导出完成！")
        
    except Exception as e:
        print(f"❌ 导出失败: {e}")
