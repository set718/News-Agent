"""
简单测试批量筛选功能
"""
from simple_langchain import LangchainProcessor
from data_storage import db_manager
from config import DEEPSEEK_API_KEY

def test_simple_batch():
    """测试简化Langchain的批量筛选"""
    
    if not DEEPSEEK_API_KEY:
        print("未设置DEEPSEEK_API_KEY，无法进行测试")
        return
    
    print("测试简化Langchain批量筛选功能")
    print("="*50)
    
    # 检查是否有未筛选的文章
    unfiltered = db_manager.get_unfiltered_articles(limit=10)
    
    if not unfiltered:
        print("没有未筛选的文章可以测试")
        print("请先运行 create_test_articles.py 创建测试文章")
        return
    
    print(f"找到 {len(unfiltered)} 篇未筛选文章")
    
    # 初始化处理器（使用批量大小3进行测试）
    processor = LangchainProcessor(batch_size=3)
    
    # 执行批量筛选
    print("\n开始批量筛选测试...")
    result = processor.filter_articles_chain(limit=6)
    
    print(f"\n测试结果:")
    print(f"总计: {result['total']}")
    print(f"成功处理: {result['processed']}")
    print(f"筛选通过: {result['selected']}")
    print(f"筛选未通过: {result['rejected']}")
    print(f"处理失败: {result['failed']}")
    
    if result['processed'] > 0:
        print(f"\n批量筛选功能正常工作!")
        print(f"成功率: {result['processed'] / result['total'] * 100:.1f}%")
    else:
        print(f"\n批量筛选可能存在问题，请检查配置")

if __name__ == "__main__":
    try:
        test_simple_batch()
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()