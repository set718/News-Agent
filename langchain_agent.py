"""
基于Langchain Agent的新闻处理系统
使用Agent框架来协调不同的工具和任务
"""
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.memory import ConversationBufferMemory
from langchain_openai import ChatOpenAI
from langchain_core.tools import BaseTool
from langchain.hub import pull
from pydantic import BaseModel, Field

from email_fetcher import EmailFetcher
from data_storage import db_manager
from langchain_chains import ArticleFilterChain, ReportGenerationChain
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, LANGCHAIN_VERBOSE


class EmailFetchInput(BaseModel):
    """邮件获取工具的输入"""
    days: int = Field(description="获取最近几天的邮件", default=1)


class EmailFetchTool(BaseTool):
    """邮件获取工具"""
    name = "email_fetcher"
    description = "获取和存储Google Alert邮件。输入天数，返回获取到的邮件数量。"
    args_schema = EmailFetchInput
    
    def __init__(self):
        super().__init__()
        self.email_fetcher = EmailFetcher()
    
    def _run(self, days: int = 1) -> str:
        """执行邮件获取"""
        try:
            alert_emails = self.email_fetcher.fetch_google_alerts(days=days)
            
            if not alert_emails:
                return f"没有找到最近{days}天的新邮件"
            
            # 存储邮件和文章
            total_new_articles = 0
            stored_emails = 0
            
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
                    stored_emails += 1
            
            return f"成功获取并存储了{stored_emails}封邮件，包含{total_new_articles}篇新文章"
            
        except Exception as e:
            return f"邮件获取失败: {str(e)}"


class ArticleFilterInput(BaseModel):
    """文章筛选工具的输入"""
    limit: int = Field(description="要筛选的文章数量限制", default=50)


class ArticleFilterTool(BaseTool):
    """文章筛选工具"""
    name = "article_filter"
    description = "使用AI筛选文章内容。输入文章数量限制，返回筛选结果统计。"
    args_schema = ArticleFilterInput
    
    def __init__(self):
        super().__init__()
        self.filter_chain = ArticleFilterChain()
    
    def _run(self, limit: int = 50) -> str:
        """执行文章筛选"""
        try:
            result = self.filter_chain({"limit": limit})
            stats = result["filter_stats"]
            
            if stats["total"] == 0:
                return "没有找到需要筛选的文章"
            
            return (f"筛选完成：处理了{stats['processed']}/{stats['total']}篇文章，"
                   f"通过{stats['selected']}篇，未通过{stats['rejected']}篇，"
                   f"失败{stats['failed']}篇")
            
        except Exception as e:
            return f"文章筛选失败: {str(e)}"


class ReportGenerationInput(BaseModel):
    """报告生成工具的输入"""
    days: int = Field(description="报告覆盖的天数", default=1)


class ReportGenerationTool(BaseTool):
    """报告生成工具"""
    name = "report_generator"
    description = "生成筛选结果的详细报告。输入天数，返回格式化的报告内容。"
    args_schema = ReportGenerationInput
    
    def __init__(self):
        super().__init__()
        self.report_chain = ReportGenerationChain()
    
    def _run(self, days: int = 1) -> str:
        """生成报告"""
        try:
            result = self.report_chain({"days": days})
            report = result["report"]
            
            if not report:
                return f"最近{days}天没有数据可生成报告"
            
            return report
            
        except Exception as e:
            return f"报告生成失败: {str(e)}"


class DatabaseStatsInput(BaseModel):
    """数据库统计工具的输入"""
    pass


class DatabaseStatsTool(BaseTool):
    """数据库统计工具"""
    name = "database_stats"
    description = "获取数据库统计信息，包括邮件和文章的数量统计。"
    args_schema = DatabaseStatsInput
    
    def _run(self) -> str:
        """获取数据库统计"""
        try:
            stats = db_manager.get_statistics()
            
            return (f"数据库统计：\n"
                   f"- 总邮件数: {stats['total_emails']}\n"
                   f"- 总文章数: {stats['total_articles']}\n"
                   f"- 已筛选文章: {stats['filtered_articles']}\n"
                   f"- 筛选通过: {stats['selected_articles']}\n"
                   f"- 筛选率: {stats['filter_rate']:.2%}\n"
                   f"- 通过率: {stats['selection_rate']:.2%}")
            
        except Exception as e:
            return f"获取统计信息失败: {str(e)}"


class NewsProcessingAgent:
    """新闻处理Agent"""
    
    def __init__(self):
        # 初始化LLM
        self.llm = ChatOpenAI(
            model="deepseek-chat",
            openai_api_key=DEEPSEEK_API_KEY,
            openai_api_base=DEEPSEEK_BASE_URL,
            temperature=0.1,
            max_tokens=2000
        )
        
        # 初始化工具
        self.tools = [
            EmailFetchTool(),
            ArticleFilterTool(),
            ReportGenerationTool(),
            DatabaseStatsTool()
        ]
        
        # 初始化内存
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        # 初始化Agent
        try:
            prompt = pull("hwchase17/openai-functions-agent")
        except:
            # 如果无法从hub获取，使用默认提示
            from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
            prompt = ChatPromptTemplate.from_messages([
                ("system", "You are a helpful assistant. Use the tools available to you to complete tasks."),
                MessagesPlaceholder(variable_name="chat_history"),
                ("human", "{input}"),
                MessagesPlaceholder(variable_name="agent_scratchpad")
            ])
        
        agent = create_openai_functions_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        self.agent = AgentExecutor(
            agent=agent,
            tools=self.tools,
            memory=self.memory,
            verbose=LANGCHAIN_VERBOSE,
            handle_parsing_errors=True,
            max_iterations=10
        )
    
    def execute_task(self, task_description: str) -> str:
        """执行任务"""
        try:
            # 添加系统提示
            system_prompt = """
你是一个专业的新闻处理助手，负责协调Google Alert邮件的获取、筛选和报告生成。

可用的工具：
1. email_fetcher - 获取邮件
2. article_filter - 筛选文章
3. report_generator - 生成报告
4. database_stats - 查看统计

请根据用户的需求，合理使用这些工具完成任务。
"""
            
            full_prompt = f"{system_prompt}\n\n用户任务: {task_description}"
            
            result = self.agent.invoke({"input": full_prompt})
            return result
            
        except Exception as e:
            return f"任务执行失败: {str(e)}"
    
    def run_full_workflow(self, days: int = 1, filter_limit: int = 50) -> str:
        """运行完整工作流"""
        task = (f"请执行完整的新闻处理工作流：\n"
               f"1. 获取最近{days}天的Google Alert邮件\n"
               f"2. 筛选最多{filter_limit}篇文章\n"
               f"3. 生成最近{days}天的详细报告\n"
               f"4. 提供最终的统计信息\n"
               f"请按顺序执行这些步骤，并在每步后报告进度。")
        
        return self.execute_task(task)
    
    def get_statistics(self) -> str:
        """获取统计信息"""
        return self.execute_task("请查看并报告当前数据库的统计信息")
    
    def fetch_emails_only(self, days: int = 1) -> str:
        """仅获取邮件"""
        return self.execute_task(f"请获取最近{days}天的Google Alert邮件")
    
    def filter_articles_only(self, limit: int = 50) -> str:
        """仅筛选文章"""
        return self.execute_task(f"请筛选最多{limit}篇未处理的文章")
    
    def generate_report_only(self, days: int = 1) -> str:
        """仅生成报告"""
        return self.execute_task(f"请生成最近{days}天的筛选报告")
    
    def clear_memory(self):
        """清空对话内存"""
        self.memory.clear()
    
    def get_memory_summary(self) -> str:
        """获取内存摘要"""
        try:
            memory_vars = self.memory.load_memory_variables({})
            chat_history = memory_vars.get("chat_history", [])
            
            if not chat_history:
                return "对话内存为空"
            
            summary = f"对话历史（共{len(chat_history)}条记录）：\n"
            for i, message in enumerate(chat_history[-5:], 1):  # 只显示最近5条
                role = "用户" if message.type == "human" else "助手"
                content = message.content[:100] + "..." if len(message.content) > 100 else message.content
                summary += f"{i}. {role}: {content}\n"
            
            return summary
            
        except Exception as e:
            return f"获取内存摘要失败: {str(e)}"


# 创建全局Agent实例
news_agent = None

def get_news_agent() -> NewsProcessingAgent:
    """获取新闻处理Agent实例"""
    global news_agent
    if news_agent is None:
        news_agent = NewsProcessingAgent()
    return news_agent


if __name__ == "__main__":
    # 测试Agent功能
    if not DEEPSEEK_API_KEY:
        print("请设置 DEEPSEEK_API_KEY 环境变量")
        exit(1)
    
    try:
        print("🤖 初始化新闻处理Agent...")
        agent = NewsProcessingAgent()
        
        print("\n📊 获取当前统计信息...")
        stats_result = agent.get_statistics()
        print(stats_result)
        
        print("\n🔄 测试完整工作流...")
        workflow_result = agent.run_full_workflow(days=1, filter_limit=5)
        print(workflow_result)
        
        print("\n🧠 内存摘要:")
        memory_summary = agent.get_memory_summary()
        print(memory_summary)
        
    except Exception as e:
        print(f"Agent测试失败: {e}")
        import traceback
        traceback.print_exc()
