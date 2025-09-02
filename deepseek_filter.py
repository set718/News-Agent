"""
DeepSeek 内容筛选模块
使用 DeepSeek API 对新闻内容进行智能筛选
"""
import json
import time
from typing import Dict, List, Optional
from openai import OpenAI

from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, CONTENT_FILTER_PROMPT
from data_storage import NewsArticle, db_manager


class DeepSeekFilter:
    """DeepSeek 内容筛选器"""
    
    def __init__(self, api_key: str = DEEPSEEK_API_KEY):
        if not api_key:
            raise ValueError("DEEPSEEK_API_KEY 未设置，请在 .env 文件中配置")
        
        self.client = OpenAI(
            api_key=api_key,
            base_url=DEEPSEEK_BASE_URL
        )
        
        self.model = "deepseek-chat"
        self.max_retries = 3
        self.retry_delay = 1  # 秒
    
    def filter_article(self, article: NewsArticle) -> Optional[Dict]:
        """
        筛选单篇文章
        
        Args:
            article: 新闻文章对象
            
        Returns:
            筛选结果字典，失败时返回None
        """
        try:
            # 构建提示词
            prompt = CONTENT_FILTER_PROMPT.format(
                title=article.title,
                source=article.source or "未知来源",
                summary=article.summary or "无摘要",
                publish_time=article.publish_time or "未知时间",
                url=article.url[:100] + "..." if len(article.url) > 100 else article.url
            )
            
            # 调用 DeepSeek API
            response = self._call_api_with_retry(prompt)
            if not response:
                return None
            
            # 解析响应
            filter_result = self._parse_response(response)
            if filter_result:
                print(f"筛选完成: {article.title[:50]}... -> {'通过' if filter_result.get('is_selected') else '未通过'}")
                return filter_result
            else:
                print(f"解析响应失败: {article.title[:50]}...")
                return None
                
        except Exception as e:
            print(f"筛选文章失败 {article.title[:50]}...: {e}")
            return None
    
    def _call_api_with_retry(self, prompt: str) -> Optional[str]:
        """带重试机制的API调用"""
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
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
                    temperature=0.3,  # 较低温度确保一致性
                    max_tokens=1000
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                print(f"API调用失败 (尝试 {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (attempt + 1))  # 指数退避
                else:
                    print("API调用最终失败")
                    return None
    
    def _parse_response(self, response: str) -> Optional[Dict]:
        """解析API响应"""
        try:
            # 尝试提取JSON部分
            response = response.strip()
            
            # 查找JSON开始和结束位置
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
                    
                    return result
                else:
                    print(f"响应缺少必需字段: {result}")
                    return None
            else:
                print(f"无法找到有效JSON: {response}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"原始响应: {response}")
            return None
        except Exception as e:
            print(f"解析响应时出错: {e}")
            return None
    
    def batch_filter_articles_optimized(self, articles: List[NewsArticle], 
                                       batch_size: int = 5) -> Dict[str, int]:
        """
        优化的批量筛选文章 - 一次API调用处理多篇文章
        
        Args:
            articles: 文章列表
            batch_size: 每次API调用处理的文章数量
            
        Returns:
            筛选统计信息
        """
        print(f"开始批量筛选 {len(articles)} 篇文章 (批处理大小: {batch_size})...")
        
        stats = {
            'total': len(articles),
            'processed': 0,
            'selected': 0,
            'rejected': 0,
            'failed': 0
        }
        
        # 按批次处理文章
        for batch_start in range(0, len(articles), batch_size):
            batch_end = min(batch_start + batch_size, len(articles))
            batch_articles = articles[batch_start:batch_end]
            
            print(f"处理批次 {batch_start//batch_size + 1}: 文章 {batch_start+1}-{batch_end}")
            
            # 批量筛选这组文章
            batch_results = self._batch_filter_articles_api(batch_articles)
            
            # 处理结果
            for i, (article, result) in enumerate(zip(batch_articles, batch_results)):
                if result:
                    # 更新数据库
                    success = db_manager.update_article_filter_result(article.id, result)
                    if success:
                        stats['processed'] += 1
                        if result.get('is_selected'):
                            stats['selected'] += 1
                            print(f"  ✓ 文章 {batch_start+i+1}: 通过")
                        else:
                            stats['rejected'] += 1
                            print(f"  ✗ 文章 {batch_start+i+1}: 未通过")
                    else:
                        stats['failed'] += 1
                        print(f"  ⚠ 文章 {batch_start+i+1}: 数据库更新失败")
                else:
                    stats['failed'] += 1
                    print(f"  ⚠ 文章 {batch_start+i+1}: 筛选失败")
            
            # 批次间短暂延迟
            if batch_end < len(articles):
                time.sleep(0.5)
        
        print(f"\n批量筛选完成:")
        print(f"总计: {stats['total']}")
        print(f"成功处理: {stats['processed']}")
        print(f"筛选通过: {stats['selected']}")
        print(f"筛选未通过: {stats['rejected']}")
        print(f"处理失败: {stats['failed']}")
        
        return stats

    def _batch_filter_articles_api(self, articles: List[NewsArticle]) -> List[Optional[Dict]]:
        """
        单次API调用批量筛选多篇文章
        
        Args:
            articles: 文章列表
            
        Returns:
            筛选结果列表
        """
        try:
            # 构建批量提示词
            batch_prompt = self._build_batch_prompt(articles)
            
            # 调用 DeepSeek API
            response = self._call_api_with_retry(batch_prompt)
            if not response:
                return [None] * len(articles)
            
            # 解析批量响应
            return self._parse_batch_response(response, len(articles))
            
        except Exception as e:
            print(f"批量筛选API调用失败: {e}")
            return [None] * len(articles)

    def _build_batch_prompt(self, articles: List[NewsArticle]) -> str:
        """构建批量筛选的提示词"""
        prompt = """你是一个专业的新闻内容分析师，负责评估和筛选新闻文章的质量和相关性。

目标用户：汽车行业制造工程师
关注领域：汽车工厂建设、AI技术、先进制造技术

筛选标准：
1. 优先保留：
   - 汽车工厂建设、扩建、技术升级相关
   - 汽车制造流程、生产线、质量控制
   - 可应用于汽车工厂的AI技术（工业机器人、机器视觉、数字孪生、预测性维护等）
   - 先进制造技术（增材制造/3D打印、自动化、智能制造、工业4.0等）
   - 汽车供应链、材料技术、新能源汽车制造

2. 保留但降低优先级：
   - 通用制造技术（如果可应用于汽车工厂）
   - 其他行业的先进制造案例（如果技术可借鉴）

3. 明确剔除：
   - 政治、社会、娱乐新闻
   - 仅涉及非汽车行业制造的内容
   - 汽车销售、市场营销、金融投资类新闻
   - 与制造工程无关的汽车新闻（如车型发布、测评等）

请分析以下 {num_articles} 篇新闻，并对每篇文章返回筛选结果。请严格按照JSON数组格式返回，数组中每个元素对应一篇文章的筛选结果：

{articles_content}

请返回一个JSON数组，包含 {num_articles} 个筛选结果，格式如下：
[
    {{
        "is_selected": true/false,
        "quality_score": 1-10的评分（内容深度和价值）,
        "relevance_score": 1-10的评分（与汽车制造工程的相关性）,
        "reason": "详细的筛选理由，说明为什么选择或拒绝",
        "key_points": ["提取的关键技术要点或制造信息"],
        "category": "分类：汽车工厂建设/AI制造技术/先进制造/供应链技术/其他"
    }},
    ...
]"""
        
        # 构建文章内容
        articles_content = ""
        for i, article in enumerate(articles, 1):
            articles_content += f"""
文章 {i}:
标题：{article.title}
来源：{article.source or "未知来源"}
内容摘要：{article.summary or "无摘要"}
发布时间：{article.publish_time or "未知时间"}
原文链接：{article.url[:100] + "..." if len(article.url) > 100 else article.url}

"""
        
        return prompt.format(
            num_articles=len(articles),
            articles_content=articles_content.strip()
        )

    def _parse_batch_response(self, response: str, expected_count: int) -> List[Optional[Dict]]:
        """解析批量API响应"""
        try:
            # 尝试提取JSON数组
            response = response.strip()
            
            # 查找JSON数组开始和结束位置
            start_idx = response.find('[')
            end_idx = response.rfind(']') + 1
            
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                results = json.loads(json_str)
                
                if not isinstance(results, list):
                    print(f"响应不是JSON数组格式")
                    return [None] * expected_count
                
                # 验证结果数量
                if len(results) != expected_count:
                    print(f"响应数量不匹配：期望 {expected_count}，实际 {len(results)}")
                    # 调整结果数量
                    if len(results) < expected_count:
                        results.extend([None] * (expected_count - len(results)))
                    else:
                        results = results[:expected_count]
                
                # 验证和清理每个结果
                cleaned_results = []
                for i, result in enumerate(results):
                    if result and isinstance(result, dict):
                        # 验证必需字段
                        required_fields = ['is_selected', 'quality_score', 'relevance_score', 'reason']
                        if all(field in result for field in required_fields):
                            # 确保分数在有效范围内
                            result['quality_score'] = max(1, min(10, float(result.get('quality_score', 5))))
                            result['relevance_score'] = max(1, min(10, float(result.get('relevance_score', 5))))
                            # 确保key_points是列表
                            if 'key_points' not in result:
                                result['key_points'] = []
                            elif not isinstance(result['key_points'], list):
                                result['key_points'] = [str(result['key_points'])]
                            # 确保category存在
                            if 'category' not in result:
                                result['category'] = '其他'
                            
                            cleaned_results.append(result)
                        else:
                            print(f"文章 {i+1} 响应缺少必需字段: {result}")
                            cleaned_results.append(None)
                    else:
                        print(f"文章 {i+1} 响应格式错误")
                        cleaned_results.append(None)
                
                return cleaned_results
            else:
                print(f"无法找到有效JSON数组: {response[:200]}...")
                return [None] * expected_count
                
        except json.JSONDecodeError as e:
            print(f"JSON解析失败: {e}")
            print(f"原始响应: {response[:500]}...")
            return [None] * expected_count
        except Exception as e:
            print(f"解析批量响应时出错: {e}")
            return [None] * expected_count

    def batch_filter_articles(self, articles: List[NewsArticle], 
                            delay_between_calls: float = 0.5) -> Dict[str, int]:
        """
        批量筛选文章（兼容原接口，内部使用优化版本）
        
        Args:
            articles: 文章列表
            delay_between_calls: API调用之间的延迟（秒）
            
        Returns:
            筛选统计信息
        """
        # 使用优化的批量处理，批次大小设为5篇
        return self.batch_filter_articles_optimized(articles, batch_size=5)
    
    def filter_unprocessed_articles(self, limit: int = 50) -> Dict[str, int]:
        """
        筛选数据库中未处理的文章
        
        Args:
            limit: 每次处理的文章数量上限
            
        Returns:
            筛选统计信息
        """
        # 获取未筛选的文章
        unfiltered_articles = db_manager.get_unfiltered_articles(limit=limit)
        
        if not unfiltered_articles:
            print("没有找到未筛选的文章")
            return {'total': 0, 'processed': 0, 'selected': 0, 'rejected': 0, 'failed': 0}
        
        return self.batch_filter_articles(unfiltered_articles)


class ContentAnalyzer:
    """内容分析器 - 提供额外的分析功能"""
    
    def __init__(self, filter_instance: DeepSeekFilter):
        self.filter = filter_instance
    
    def analyze_article_trends(self, articles: List[NewsArticle]) -> Dict:
        """分析文章趋势"""
        if not articles:
            return {}
        
        # 按来源统计
        source_stats = {}
        for article in articles:
            source = article.source or "未知来源"
            source_stats[source] = source_stats.get(source, 0) + 1
        
        # 按类别统计（如果有筛选结果）
        category_stats = {}
        quality_scores = []
        relevance_scores = []
        
        for article in articles:
            if article.category:
                category_stats[article.category] = category_stats.get(article.category, 0) + 1
            if article.quality_score:
                quality_scores.append(article.quality_score)
            if article.relevance_score:
                relevance_scores.append(article.relevance_score)
        
        # 计算平均分
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        avg_relevance = sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0
        
        return {
            'total_articles': len(articles),
            'source_distribution': source_stats,
            'category_distribution': category_stats,
            'average_quality_score': avg_quality,
            'average_relevance_score': avg_relevance,
            'score_ranges': {
                'quality_min': min(quality_scores) if quality_scores else 0,
                'quality_max': max(quality_scores) if quality_scores else 0,
                'relevance_min': min(relevance_scores) if relevance_scores else 0,
                'relevance_max': max(relevance_scores) if relevance_scores else 0
            }
        }
    
    def generate_summary_report(self, days: int = 1) -> str:
        """生成筛选摘要报告"""
        # 获取筛选通过的文章
        selected_articles = db_manager.get_selected_articles(days=days)
        
        if not selected_articles:
            return f"最近 {days} 天没有筛选通过的文章。"
        
        # 分析趋势
        analysis = self.analyze_article_trends(selected_articles)
        
        # 生成报告
        report = f"""
最近 {days} 天筛选报告
{'='*50}

总体统计:
- 筛选通过文章: {analysis['total_articles']} 篇
- 平均质量评分: {analysis['average_quality_score']:.1f}/10
- 平均相关性评分: {analysis['average_relevance_score']:.1f}/10

来源分布:
"""
        
        # 添加来源统计
        for source, count in sorted(analysis['source_distribution'].items(), 
                                   key=lambda x: x[1], reverse=True):
            report += f"- {source}: {count} 篇\n"
        
        # 添加类别统计
        if analysis['category_distribution']:
            report += "\n类别分布:\n"
            for category, count in sorted(analysis['category_distribution'].items(), 
                                        key=lambda x: x[1], reverse=True):
                report += f"- {category}: {count} 篇\n"
        
        # 添加高质量文章推荐
        top_articles = sorted(selected_articles, 
                            key=lambda x: (x.quality_score or 0) + (x.relevance_score or 0), 
                            reverse=True)[:5]
        
        if top_articles:
            report += "\n推荐阅读 (Top 5):\n"
            for i, article in enumerate(top_articles, 1):
                report += f"{i}. {article.title}\n"
                report += f"   来源: {article.source} | 质量: {article.quality_score:.1f} | 相关性: {article.relevance_score:.1f}\n"
                report += f"   链接: {article.url}\n\n"
        
        return report


# 全局筛选器实例
content_filter = DeepSeekFilter() if DEEPSEEK_API_KEY else None


if __name__ == "__main__":
    # 测试筛选功能
    if not DEEPSEEK_API_KEY:
        print("请设置 DEEPSEEK_API_KEY 环境变量")
        exit(1)
    
    try:
        filter_instance = DeepSeekFilter()
        
        # 获取未筛选的文章进行测试
        print("开始测试筛选功能...")
        
        # 筛选未处理的文章
        stats = filter_instance.filter_unprocessed_articles(limit=5)  # 只处理5篇作为测试
        
        if stats['total'] > 0:
            print(f"\n测试完成，处理了 {stats['processed']} 篇文章")
            
            # 生成报告
            analyzer = ContentAnalyzer(filter_instance)
            report = analyzer.generate_summary_report(days=1)
            print("\n" + report)
        else:
            print("没有找到未处理的文章，请先运行邮件获取程序")
    
    except Exception as e:
        print(f"测试失败: {e}")
