"""
基于Langchain的工作流链
重构原有功能为标准的Langchain Chain架构
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from langchain.chains.base import Chain
from langchain.memory import SimpleMemory
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from pydantic import BaseModel, Field

from email_fetcher import EmailFetcher
from data_storage import db_manager
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, CONTENT_FILTER_PROMPT


class FilterResult(BaseModel):
    """筛选结果的Pydantic模型"""
    is_selected: bool = Field(description="是否通过筛选")
    quality_score: float = Field(description="质量评分(1-10)", ge=1, le=10)
    relevance_score: float = Field(description="相关性评分(1-10)", ge=1, le=10)
    reason: str = Field(description="筛选理由")
    key_points: List[str] = Field(description="关键要点", default=[])
    category: str = Field(description="文章分类")


class EmailFetchChain(Chain):
    """邮件获取链 - 负责获取和解析Google Alert邮件"""
    
    input_key: str = "days"
    output_key: str = "emails"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.email_fetcher = EmailFetcher()
    
    @property
    def input_keys(self) -> List[str]:
        return [self.input_key]
    
    @property
    def output_keys(self) -> List[str]:
        return [self.output_key]
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行邮件获取"""
        days = inputs.get(self.input_key, 1)
        
        print(f"\n{'='*50}")
        print(f"🔄 Chain 1: 获取最近 {days} 天的 Google Alert 邮件")
        print(f"{'='*50}")
        
        try:
            # 获取邮件
            alert_emails = self.email_fetcher.fetch_google_alerts(days=days)
            
            if not alert_emails:
                print("没有找到新的Google Alert邮件")
                return {self.output_key: []}
            
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
                    # 为文章添加邮件ID
                    for article in email.articles:
                        article['email_message_id'] = email.message_id
                    
                    # 保存文章
                    saved_articles = db_manager.save_articles(email.articles)
                    total_new_articles += len(saved_articles)
                    stored_emails.append(email)
            
            print(f"✅ 邮件获取完成: {len(stored_emails)} 封邮件, {total_new_articles} 篇新文章")
            return {self.output_key: stored_emails}
            
        except Exception as e:
            print(f"❌ 邮件获取失败: {e}")
            return {self.output_key: []}


class ArticleFilterChain(Chain):
    """文章筛选链 - 使用LLM进行内容筛选"""
    
    input_key: str = "limit"
    output_key: str = "filter_stats"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        # 初始化LLM
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base=DEEPSEEK_BASE_URL,
            temperature=0.3,
            max_tokens=1000
        )
        
        # 创建输出解析器
        self.output_parser = PydanticOutputParser(pydantic_object=FilterResult)
        
        # 创建提示模板
        self.prompt = PromptTemplate(
            template=CONTENT_FILTER_PROMPT + "\n{format_instructions}",
            input_variables=["title", "source", "summary", "publish_time", "url"],
            partial_variables={"format_instructions": self.output_parser.get_format_instructions()}
        )
        
        # 构建链
        self.filter_chain = (
            self.prompt 
            | self.llm 
            | self.output_parser
        )
    
    @property
    def input_keys(self) -> List[str]:
        return [self.input_key]
    
    @property
    def output_keys(self) -> List[str]:
        return [self.output_key]
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行文章筛选"""
        limit = inputs.get(self.input_key, 50)
        
        print(f"\n{'='*50}")
        print(f"🤖 Chain 2: 使用 LLM 筛选文章内容")
        print(f"{'='*50}")
        
        # 获取未筛选的文章
        unfiltered_articles = db_manager.get_unfiltered_articles(limit=limit)
        
        if not unfiltered_articles:
            print("没有找到需要筛选的文章")
            return {self.output_key: {'total': 0, 'processed': 0, 'selected': 0, 'rejected': 0, 'failed': 0}}
        
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
                # 使用Langchain链进行筛选
                filter_input = {
                    "title": article.title,
                    "source": article.source or "未知来源",
                    "summary": article.summary or "无摘要",
                    "publish_time": article.publish_time or "未知时间",
                    "url": article.url[:100] + "..." if len(article.url) > 100 else article.url
                }
                
                result = self.filter_chain.invoke(filter_input)
                
                # 转换为字典格式
                filter_result = {
                    'is_selected': result.is_selected,
                    'quality_score': result.quality_score,
                    'relevance_score': result.relevance_score,
                    'reason': result.reason,
                    'key_points': result.key_points,
                    'category': result.category
                }
                
                # 更新数据库
                success = db_manager.update_article_filter_result(article.id, filter_result)
                if success:
                    stats['processed'] += 1
                    if result.is_selected:
                        stats['selected'] += 1
                        print(f"  ✅ 通过筛选")
                    else:
                        stats['rejected'] += 1
                        print(f"  ❌ 未通过筛选")
                else:
                    stats['failed'] += 1
                    print(f"  ⚠️ 数据库更新失败")
                
            except Exception as e:
                print(f"  ❌ 筛选失败: {e}")
                stats['failed'] += 1
        
        print(f"\n✅ 筛选完成:")
        print(f"  - 总计: {stats['total']}")
        print(f"  - 成功处理: {stats['processed']}")
        print(f"  - 筛选通过: {stats['selected']}")
        print(f"  - 筛选未通过: {stats['rejected']}")
        print(f"  - 处理失败: {stats['failed']}")
        
        return {self.output_key: stats}


class ReportGenerationChain(Chain):
    """报告生成链 - 生成分析报告"""
    
    input_key: str = "days"
    output_key: str = "report"
    
    @property
    def input_keys(self) -> List[str]:
        return [self.input_key]
    
    @property
    def output_keys(self) -> List[str]:
        return [self.output_key]
    
    def _call(self, inputs: Dict[str, Any]) -> Dict[str, Any]:
        """生成报告"""
        days = inputs.get(self.input_key, 1)
        
        print(f"\n{'='*50}")
        print(f"📊 Chain 3: 生成筛选报告")
        print(f"{'='*50}")
        
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
                return {self.output_key: report}
            
            # 生成详细报告
            report = self._generate_detailed_report(selected_articles, days)
            
            print("✅ 报告生成完成")
            return {self.output_key: report}
            
        except Exception as e:
            print(f"❌ 报告生成失败: {e}")
            return {self.output_key: ""}
    
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
最近 {days} 天筛选报告
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


class NewsProcessingWorkflow:
    """新闻处理工作流 - 组合多个Chain"""
    
    def __init__(self):
        # 初始化各个链
        self.email_chain = EmailFetchChain()
        self.filter_chain = ArticleFilterChain()
        self.report_chain = ReportGenerationChain()
        
        # 初始化内存
        self.memory = SimpleMemory()
    
    def run_full_workflow(self, days: int = 1, filter_limit: int = 50) -> Dict[str, Any]:
        """运行完整的工作流程"""
        print(f"🚀 Google Alert 处理工作流程启动 (Langchain架构)")
        print(f"📅 处理时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 创建工作流输入
        workflow_input = {
            "days": days,
            "limit": filter_limit,
            "timestamp": datetime.now()
        }
        
        # 存储到内存
        self.memory.save_context(
            {"input": workflow_input},
            {"status": "started"}
        )
        
        try:
            # 步骤1: 获取邮件
            email_result = self.email_chain({"days": days})
            emails = email_result["emails"]
            
            # 步骤2: 筛选文章
            filter_result = self.filter_chain({"limit": filter_limit})
            filter_stats = filter_result["filter_stats"]
            
            # 步骤3: 生成报告
            report_result = self.report_chain({"days": days})
            report = report_result["report"]
            
            # 最终结果
            result = {
                'emails_processed': len(emails),
                'filter_stats': filter_stats,
                'report': report,
                'workflow_status': 'completed'
            }
            
            # 存储结果到内存
            self.memory.save_context(
                {"workflow_input": workflow_input},
                {"workflow_result": result}
            )
            
            # 输出最终结果
            print(f"\n{'='*50}")
            print(f"🎉 工作流程完成")
            print(f"{'='*50}")
            
            if report:
                print(report)
            
            return result
            
        except Exception as e:
            print(f"❌ 工作流程执行失败: {e}")
            self.memory.save_context(
                {"workflow_input": workflow_input},
                {"error": str(e), "workflow_status": "failed"}
            )
            return {
                'emails_processed': 0,
                'filter_stats': {},
                'report': "",
                'workflow_status': 'failed',
                'error': str(e)
            }
    
    def run_email_only(self, days: int = 1) -> Dict[str, Any]:
        """仅运行邮件获取"""
        return self.email_chain({"days": days})
    
    def run_filter_only(self, limit: int = 50) -> Dict[str, Any]:
        """仅运行文章筛选"""
        return self.filter_chain({"limit": limit})
    
    def run_report_only(self, days: int = 1) -> Dict[str, Any]:
        """仅运行报告生成"""
        return self.report_chain({"days": days})
    
    def get_memory_variables(self) -> Dict[str, Any]:
        """获取内存中的变量"""
        return self.memory.load_memory_variables({})
