"""
简化的Langchain架构实现
避免复杂的依赖冲突，使用核心Langchain概念重构系统
"""
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from openai import OpenAI
from langchain.prompts import PromptTemplate
from pydantic import BaseModel, Field

from email_fetcher import EmailFetcher
from data_storage import db_manager
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, CONTENT_FILTER_PROMPT


class FilterResult(BaseModel):
    """筛选结果模型"""
    is_selected: bool = Field(description="是否通过筛选")
    quality_score: float = Field(description="质量评分(1-10)", ge=1, le=10)
    relevance_score: float = Field(description="相关性评分(1-10)", ge=1, le=10)
    reason: str = Field(description="筛选理由")
    key_points: List[str] = Field(description="关键要点", default=[])
    category: str = Field(description="文章分类", default="其他")


class LangchainProcessor:
    """基于Langchain的简化处理器"""
    
    def __init__(self):
        # 初始化LLM客户端
        self.llm = OpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL
        )
        
        # 初始化提示模板
        self.filter_prompt = PromptTemplate(
            template=CONTENT_FILTER_PROMPT,
            input_variables=["title", "source", "summary", "publish_time", "url"]
        )
        
        # 初始化邮件获取器
        self.email_fetcher = EmailFetcher()
        
        print("✅ 简化Langchain处理器初始化成功")
    
    def fetch_emails_chain(self, days: int = 1) -> Dict[str, Any]:
        """邮件获取链"""
        print(f"\n🔄 执行邮件获取链 (最近 {days} 天)")
        
        try:
            # 获取邮件
            alert_emails = self.email_fetcher.fetch_google_alerts(days=days)
            
            if not alert_emails:
                print("没有找到新的Google Alert邮件")
                return {"emails": [], "articles_count": 0}
            
            # 存储邮件和文章
            total_new_articles = 0
            stored_emails = []
            
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
                    for article in email.articles:
                        article['email_message_id'] = email.message_id
                    
                    saved_articles = db_manager.save_articles(email.articles)
                    total_new_articles += len(saved_articles)
                    stored_emails.append(email)
            
            result = {
                "emails": stored_emails,
                "articles_count": total_new_articles
            }
            
            print(f"✅ 邮件获取完成: {len(stored_emails)} 封邮件, {total_new_articles} 篇新文章")
            return result
            
        except Exception as e:
            print(f"❌ 邮件获取失败: {e}")
            return {"emails": [], "articles_count": 0}
    
    def filter_articles_chain(self, limit: int = None) -> Dict[str, Any]:
        """文章筛选链"""
        if limit:
            print(f"\n🤖 执行文章筛选链 (限制 {limit} 篇)")
        else:
            print(f"\n🤖 执行文章筛选链 (处理所有未筛选文章)")
        
        # 获取未筛选的文章
        unfiltered_articles = db_manager.get_unfiltered_articles(limit=limit)
        
        if not unfiltered_articles:
            print("没有找到需要筛选的文章")
            return {'total': 0, 'processed': 0, 'selected': 0, 'rejected': 0, 'failed': 0}
        
        print(f"开始筛选 {len(unfiltered_articles)} 篇文章...")
        
        stats = {
            'total': len(unfiltered_articles),
            'processed': 0,
            'selected': 0,
            'rejected': 0,
            'failed': 0
        }
        
        for i, article in enumerate(unfiltered_articles, 1):
            print(f"处理第 {i}/{len(unfiltered_articles)} 篇: {article.title[:50]}...")
            
            try:
                # 使用Langchain进行筛选
                filter_result = self._filter_single_article(article)
                
                if filter_result:
                    # 更新数据库
                    success = db_manager.update_article_filter_result(article.id, filter_result)
                    if success:
                        stats['processed'] += 1
                        if filter_result.get('is_selected'):
                            stats['selected'] += 1
                            print(f"  ✅ 通过筛选")
                        else:
                            stats['rejected'] += 1
                            print(f"  ❌ 未通过筛选")
                    else:
                        stats['failed'] += 1
                        print(f"  ⚠️ 数据库更新失败")
                else:
                    stats['failed'] += 1
                    print(f"  ❌ 筛选失败")
                
            except Exception as e:
                print(f"  ❌ 处理异常: {e}")
                stats['failed'] += 1
        
        print(f"\n✅ 筛选完成:")
        print(f"  - 总计: {stats['total']}")
        print(f"  - 成功处理: {stats['processed']}")
        print(f"  - 筛选通过: {stats['selected']}")
        print(f"  - 筛选未通过: {stats['rejected']}")
        print(f"  - 处理失败: {stats['failed']}")
        
        return stats
    
    def _filter_single_article(self, article) -> Optional[Dict]:
        """使用Langchain筛选单篇文章"""
        try:
            # 准备输入数据
            input_data = {
                "title": article.title,
                "source": article.source or "未知来源",
                "summary": article.summary or "无摘要",
                "publish_time": article.publish_time or "未知时间",
                "url": article.url[:100] + "..." if len(article.url) > 100 else article.url
            }
            
            # 使用提示模板生成完整提示
            prompt = self.filter_prompt.format(**input_data)
            
            # 调用LLM
            response = self.llm.chat.completions.create(
                model="deepseek-chat",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一个专业的新闻内容分析师，负责评估和筛选新闻文章的质量和相关性。请严格按照JSON格式返回分析结果。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,
                max_tokens=1000
            )
            
            # 解析响应
            return self._parse_llm_response(response.choices[0].message.content)
            
        except Exception as e:
            print(f"筛选文章时出错: {e}")
            return None
    
    def _parse_llm_response(self, response: str) -> Optional[Dict]:
        """解析LLM响应"""
        try:
            # 查找JSON部分
            response = response.strip()
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                
                # 验证必需字段
                required_fields = ['is_selected', 'quality_score', 'relevance_score', 'reason']
                if all(field in result for field in required_fields):
                    # 确保分数在有效范围内
                    result['quality_score'] = max(1, min(10, float(result.get('quality_score', 5))))
                    result['relevance_score'] = max(1, min(10, float(result.get('relevance_score', 5))))
                    
                    # 确保列表字段存在
                    if 'key_points' not in result:
                        result['key_points'] = []
                    if 'category' not in result:
                        result['category'] = "其他"
                    
                    return result
                else:
                    print(f"响应缺少必需字段: {result}")
                    return None
            else:
                print(f"无法找到有效JSON: {response}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            return None
        except Exception as e:
            print(f"解析响应时出错: {e}")
            return None
    
    def generate_report_chain(self, days: int = 1) -> str:
        """报告生成链"""
        print(f"\n📊 执行报告生成链 (最近 {days} 天)")
        
        try:
            # 获取数据库统计
            stats = db_manager.get_statistics()
            
            print(f"数据库统计:")
            print(f"  - 总邮件数: {stats['total_emails']}")
            print(f"  - 总文章数: {stats['total_articles']}")
            print(f"  - 已筛选: {stats['filtered_articles']}")
            print(f"  - 筛选通过: {stats['selected_articles']}")
            
            # 获取筛选通过的文章
            selected_articles = db_manager.get_selected_articles(days=days)
            
            if not selected_articles:
                report = f"最近 {days} 天没有筛选通过的文章。"
                return report
            
            # 生成详细报告
            report = self._generate_detailed_report(selected_articles, days)
            
            print("✅ 报告生成完成")
            return report
            
        except Exception as e:
            print(f"❌ 报告生成失败: {e}")
            return ""
    
    def _generate_detailed_report(self, articles, days: int) -> str:
        """生成详细报告"""
        # 统计分析
        source_stats = {}
        category_stats = {}
        quality_scores = []
        relevance_scores = []
        
        for article in articles:
            # 来源统计
            source = article.source or "未知来源"
            source_stats[source] = source_stats.get(source, 0) + 1
            
            # 类别统计
            if article.category:
                category_stats[article.category] = category_stats.get(article.category, 0) + 1
            
            # 分数收集
            if article.quality_score:
                quality_scores.append(article.quality_score)
            if article.relevance_score:
                relevance_scores.append(article.relevance_score)
        
        # 计算平均分
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        
        # 生成报告
        report = f"""
最近 {days} 天筛选报告 (Langchain架构)
{'='*50}

总体统计:
- 筛选通过文章: {len(articles)} 篇
- 平均质量评分: {avg_quality:.1f}/10
- 平均相关性评分: {avg_relevance:.1f}/10

来源分布:
"""
        
        # 添加来源统计
        for source, count in sorted(source_stats.items(), key=lambda x: x[1], reverse=True):
            report += f"- {source}: {count} 篇\n"
        
        # 添加类别统计
        if category_stats:
            report += "\n类别分布:\n"
            for category, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True):
                report += f"- {category}: {count} 篇\n"
        
        # 添加高质量文章推荐
        top_articles = sorted(articles, 
                            key=lambda x: (x.quality_score or 0) + (x.relevance_score or 0), 
                            reverse=True)[:5]
        
        if top_articles:
            report += "\n推荐阅读 (Top 5):\n"
            for i, article in enumerate(top_articles, 1):
                report += f"{i}. {article.title}\n"
                report += f"   来源: {article.source} | 质量: {article.quality_score:.1f} | 相关性: {article.relevance_score:.1f}\n"
                report += f"   链接: {article.url}\n\n"
        
        return report
    
    def run_full_workflow(self, days: int = 1, filter_limit: int = None, auto_export_excel: bool = True) -> Dict[str, Any]:
        """运行完整的Langchain工作流程"""
        print(f"🚀 启动Langchain新闻处理工作流")
        print(f"📅 处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        try:
            # 步骤1: 邮件获取链
            email_result = self.fetch_emails_chain(days=days)
            
            # 步骤2: 文章筛选链
            filter_result = self.filter_articles_chain(limit=filter_limit)
            
            # 步骤3: 报告生成链
            report = self.generate_report_chain(days=days)
            
            # 步骤4: 自动导出Excel (如果启用)
            excel_file = ""
            if auto_export_excel:
                excel_file = self._auto_export_excel()
            
            # 组合结果
            result = {
                'emails_processed': len(email_result["emails"]),
                'articles_added': email_result["articles_count"],
                'filter_stats': filter_result,
                'report': report,
                'excel_file': excel_file,
                'workflow_status': 'completed',
                'architecture': 'langchain'
            }
            
            # 输出最终结果
            print(f"\n{'='*50}")
            print(f"🎉 Langchain工作流程完成")
            print(f"{'='*50}")
            
            if report:
                print(report)
            
            if excel_file:
                print(f"\n📊 已自动导出当日Excel文件: {excel_file}")
            
            return result
            
        except Exception as e:
            print(f"❌ 工作流程执行失败: {e}")
            return {
                'emails_processed': 0,
                'articles_added': 0,
                'filter_stats': {},
                'report': "",
                'excel_file': "",
                'workflow_status': 'failed',
                'error': str(e),
                'architecture': 'langchain'
            }
    
    def _auto_export_excel(self) -> str:
        """自动导出当天的Excel文件"""
        try:
            print(f"\n📊 自动导出当日Excel文件...")
            
            # 导入excel_exporter
            from excel_exporter import excel_exporter
            
            # 导出今天的数据 (1天)
            excel_file = excel_exporter.export_selected_articles(days=1)
            
            if excel_file:
                print(f"✅ Excel文件已生成: {excel_file}")
                return excel_file
            else:
                print("⚠️ 今天没有筛选通过的文章，未生成Excel文件")
                return ""
                
        except Exception as e:
            print(f"❌ Excel导出失败: {e}")
            return ""


if __name__ == "__main__":
    # 测试简化Langchain处理器
    if not DEEPSEEK_API_KEY:
        print("请设置 DEEPSEEK_API_KEY 环境变量")
        exit(1)
    
    try:
        print("🧪 测试简化Langchain架构...")
        
        processor = LangchainProcessor()
        
        # 测试完整工作流
        result = processor.run_full_workflow(days=1, filter_limit=3)
        
        print(f"\n✅ 测试完成！")
        print(f"架构: {result.get('architecture', 'unknown')}")
        print(f"状态: {result.get('workflow_status', 'unknown')}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
