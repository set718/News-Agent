"""
测试批量筛选功能
"""
import time
from datetime import datetime
from deepseek_filter import DeepSeekFilter
from data_storage import db_manager
from config import DEEPSEEK_API_KEY

def test_batch_performance():
    """测试批量处理性能"""
    
    if not DEEPSEEK_API_KEY:
        print("未设置DEEPSEEK_API_KEY，无法进行测试")
        return
    
    print("开始批量筛选性能测试")
    print("="*60)
    
    # 获取测试文章
    test_articles = db_manager.get_unfiltered_articles(limit=10)
    
    if len(test_articles) < 5:
        print("测试文章数量不足（至少需要5篇），请先运行邮件获取程序")
        return
    
    print(f"获取到 {len(test_articles)} 篇测试文章")
    
    # 初始化筛选器
    filter_instance = DeepSeekFilter()
    
    # 测试批量筛选（5篇一批）
    print(f"\n测试批量筛选 (批量大小: 5)")
    start_time = time.time()
    
    # 取前5篇进行测试
    test_batch = test_articles[:5]
    batch_stats = filter_instance.batch_filter_articles_optimized(
        test_batch, 
        batch_size=5
    )
    
    batch_time = time.time() - start_time
    
    print(f"\n批量筛选结果:")
    print(f"总耗时: {batch_time:.2f} 秒")
    print(f"处理文章: {batch_stats['processed']}/{batch_stats['total']}")
    print(f"筛选通过: {batch_stats['selected']}")
    print(f"筛选未通过: {batch_stats['rejected']}")
    print(f"处理失败: {batch_stats['failed']}")
    print(f"平均每篇: {batch_time / batch_stats['total']:.2f} 秒")
    
    if batch_stats['processed'] > 0:
        print(f"\n优化效果:")
        estimated_single_time = batch_stats['total'] * 2.5  # 估算单篇处理时间（包含延迟）
        speedup = estimated_single_time / batch_time
        print(f"估算单篇处理时间: {estimated_single_time:.2f} 秒")
        print(f"实际批量处理时间: {batch_time:.2f} 秒")
        print(f"预估提速倍数: {speedup:.2f}x")
        print(f"时间节省: {((estimated_single_time - batch_time) / estimated_single_time * 100):.1f}%")


if __name__ == "__main__":
    print("批量筛选功能测试")
    print("="*60)
    
    try:
        test_batch_performance()
        print("\n测试完成!")
        
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试失败: {e}")
        import traceback
        traceback.print_exc()