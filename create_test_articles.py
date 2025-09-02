"""
创建测试文章用于验证批量筛选功能
"""
from data_storage import db_manager
from datetime import datetime

def create_test_articles():
    """创建测试文章"""
    
    test_articles = [
        {
            'title': '特斯拉上海超级工厂部署AI质检系统',
            'summary': '特斯拉在其上海超级工厂部署了基于机器视觉的AI质检系统，可自动检测车身缺陷，检测精度达到99.5%，大幅提升了生产质量控制效率。',
            'url': 'https://example.com/tesla-ai-quality-control',
            'source': '汽车制造技术',
            'publish_time': '2025-01-15 10:00:00',
            'email_message_id': 'test_batch_1'
        },
        {
            'title': '比亚迪西安工厂引入数字孪生技术',
            'summary': '比亚迪在西安新工厂采用数字孪生技术，通过虚拟仿真优化生产布局和流程，预计可提升20%的生产效率并降低15%的运营成本。',
            'url': 'https://example.com/byd-digital-twin',
            'source': '智能制造周刊',
            'publish_time': '2025-01-15 11:30:00',
            'email_message_id': 'test_batch_2'
        },
        {
            'title': '大众汽车采用3D打印技术生产复杂零部件',
            'summary': '大众汽车集团在德国工厂引入大型3D打印设备，用于生产传统工艺难以制造的复杂汽车零部件，缩短了产品开发周期。',
            'url': 'https://example.com/vw-3d-printing',
            'source': '增材制造资讯',
            'publish_time': '2025-01-15 14:20:00',
            'email_message_id': 'test_batch_3'
        },
        {
            'title': '新款iPhone发布会引发关注',
            'summary': '苹果公司在秋季发布会上推出了新款iPhone，配备了更先进的芯片和摄像头系统，预计将推动消费电子市场增长。',
            'url': 'https://example.com/iphone-launch',
            'source': '科技新闻',
            'publish_time': '2025-01-15 16:00:00',
            'email_message_id': 'test_batch_4'
        },
        {
            'title': '工业机器人在汽车装配线的智能化应用',
            'summary': '新一代协作机器人在汽车装配线上实现了人机协作，配备视觉传感器和力反馈系统，可精确完成复杂装配任务。',
            'url': 'https://example.com/collaborative-robots',
            'source': '工业自动化',
            'publish_time': '2025-01-15 17:45:00',
            'email_message_id': 'test_batch_5'
        },
        {
            'title': '股市大涨创历史新高',
            'summary': '今日股市表现强劲，主要指数均创历史新高，投资者信心大增，交易量较昨日增长30%。',
            'url': 'https://example.com/stock-market-high',
            'source': '财经日报',
            'publish_time': '2025-01-15 18:30:00',
            'email_message_id': 'test_batch_6'
        }
    ]
    
    print(f"创建 {len(test_articles)} 篇测试文章...")
    
    # 保存测试文章
    saved_articles = db_manager.save_articles(test_articles)
    
    print(f"成功保存 {len(saved_articles)} 篇测试文章到数据库")
    
    return saved_articles

if __name__ == "__main__":
    try:
        create_test_articles()
        print("测试文章创建完成!")
    except Exception as e:
        print(f"创建测试文章失败: {e}")
        import traceback
        traceback.print_exc()