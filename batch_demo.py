"""
批量筛选功能演示
"""
from data_storage import db_manager, NewsArticle
from deepseek_filter import DeepSeekFilter
from config import DEEPSEEK_API_KEY
import time

def create_demo_articles():
    """创建演示文章"""
    demo_articles = [
        NewsArticle(
            id=None,
            title="特斯拉上海超级工厂采用全新AI制造系统提升生产效率",
            summary="特斯拉在其上海超级工厂部署了先进的人工智能制造系统，包括机器视觉质检、预测性维护和智能生产调度，预计将生产效率提升30%。",
            url="https://example.com/tesla-ai-manufacturing",
            source="汽车制造新闻",
            publish_time="2025-01-15 10:00:00"
        ),
        NewsArticle(
            id=None,
            title="比亚迪投资50亿建设新能源汽车智能工厂",
            summary="比亚迪宣布在西安投资50亿元建设新能源汽车智能制造基地，将采用工业4.0技术和数字孪生系统，年产能达30万辆。",
            url="https://example.com/byd-smart-factory",
            source="新能源汽车资讯",
            publish_time="2025-01-15 11:30:00"
        ),
        NewsArticle(
            id=None,
            title="宝马集团推出3D打印技术用于汽车零部件生产",
            summary="宝马集团在其德国工厂引入大型3D打印设备，用于生产复杂汽车零部件，这项增材制造技术将大幅缩短产品开发周期。",
            url="https://example.com/bmw-3d-printing",
            source="制造技术周刊",
            publish_time="2025-01-15 14:20:00"
        ),
        NewsArticle(
            id=None,
            title="明星结婚典礼盛况空前，众多娱乐明星出席",
            summary="知名影星在豪华酒店举办婚礼，现场布置奢华，众多娱乐圈好友到场祝贺，婚礼花费据传达千万元。",
            url="https://example.com/celebrity-wedding",
            source="娱乐八卦",
            publish_time="2025-01-15 16:00:00"
        ),
        NewsArticle(
            id=None,
            title="大众汽车集团采用数字孪生技术优化生产线",
            summary="大众汽车在其德国沃尔夫斯堡工厂实施数字孪生技术，通过虚拟仿真优化生产流程，预计可减少15%的生产成本。",
            url="https://example.com/vw-digital-twin",
            source="工业制造报",
            publish_time="2025-01-15 17:45:00"
        )
    ]
    return demo_articles

def demo_batch_filtering():
    """演示批量筛选功能"""
    
    if not DEEPSEEK_API_KEY:
        print("未设置DEEPSEEK_API_KEY，无法进行演示")
        return
    
    print("批量筛选功能演示")
    print("="*60)
    
    # 创建演示文章
    demo_articles = create_demo_articles()
    print(f"创建了 {len(demo_articles)} 篇演示文章")
    
    # 显示文章标题
    print("\n演示文章列表:")
    for i, article in enumerate(demo_articles, 1):
        print(f"{i}. {article.title}")
        print(f"   来源: {article.source}")
        print(f"   摘要: {article.summary[:50]}...")
        print()
    
    # 初始化筛选器
    print("初始化DeepSeek筛选器...")
    filter_instance = DeepSeekFilter()
    
    # 演示批量筛选
    print("\n开始批量筛选演示...")
    print("="*50)
    
    start_time = time.time()
    
    # 使用批量筛选API
    batch_results = filter_instance._batch_filter_articles_api(demo_articles)
    
    end_time = time.time()
    
    print(f"\n批量筛选完成! 耗时: {end_time - start_time:.2f} 秒")
    print(f"平均每篇: {(end_time - start_time) / len(demo_articles):.2f} 秒")
    
    # 显示筛选结果
    print("\n筛选结果:")
    print("="*50)
    
    selected_count = 0
    rejected_count = 0
    
    for i, (article, result) in enumerate(zip(demo_articles, batch_results), 1):
        print(f"\n文章 {i}: {article.title[:40]}...")
        if result:
            status = "通过" if result['is_selected'] else "未通过"
            print(f"结果: {status}")
            print(f"质量评分: {result['quality_score']}/10")
            print(f"相关性评分: {result['relevance_score']}/10")
            print(f"分类: {result['category']}")
            print(f"理由: {result['reason'][:80]}...")
            
            if result['is_selected']:
                selected_count += 1
            else:
                rejected_count += 1
        else:
            print("结果: 筛选失败")
    
    # 总结
    print(f"\n筛选总结:")
    print(f"="*30)
    print(f"总文章数: {len(demo_articles)}")
    print(f"筛选通过: {selected_count}")
    print(f"筛选未通过: {rejected_count}")
    print(f"筛选失败: {len(demo_articles) - selected_count - rejected_count}")
    
    # 性能对比
    estimated_single_time = len(demo_articles) * 2.0  # 估算单篇处理时间
    actual_batch_time = end_time - start_time
    speedup = estimated_single_time / actual_batch_time if actual_batch_time > 0 else 1
    
    print(f"\n性能对比:")
    print(f"估算单篇处理时间: {estimated_single_time:.2f} 秒")
    print(f"实际批量处理时间: {actual_batch_time:.2f} 秒")
    print(f"提速倍数: {speedup:.2f}x")
    print(f"时间节省: {((estimated_single_time - actual_batch_time) / estimated_single_time * 100):.1f}%")

if __name__ == "__main__":
    try:
        demo_batch_filtering()
    except Exception as e:
        print(f"演示失败: {e}")
        import traceback
        traceback.print_exc()