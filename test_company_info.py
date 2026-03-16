"""
快速测试脚本：验证企业信息管理器
"""

import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from Analytics.reporters.company_info_manager import CompanyInfoManager

print("=" * 60)
print("测试 CompanyInfoManager")
print("=" * 60)

# 初始化管理器
manager = CompanyInfoManager()

# 测试几个标的
test_symbols = ['AAPL', 'INTC', 'MSFT']

for symbol in test_symbols:
    print(f"\n📥 获取 {symbol} 的企业信息...")
    
    try:
        info = manager.get_company_info(symbol)
        
        print(f"✅ 成功获取 {symbol}")
        print(f"   名称: {info.get('name')}")
        print(f"   行业: {info.get('industry')}")
        print(f"   领域: {info.get('sector')}")
        print(f"   当前价格: ${info.get('current_price')}")
        print(f"   P/E 比率: {info.get('pe_ratio')}")
        print(f"   简介长度: {len(info.get('business_summary', ''))} 字")
        print(f"   缓存标记: {info.get('source')}")
        
    except Exception as e:
        print(f"❌ 获取 {symbol} 失败: {e}")

print("\n" + "=" * 60)
print("✅ 企业信息管理器工作正常")
print("=" * 60)

# 列出已缓存的标的
cached = manager.get_all_cached_symbols()
print(f"\n📦 已缓存标的数: {len(cached)}")
if cached:
    print(f"   {', '.join(cached)}")
