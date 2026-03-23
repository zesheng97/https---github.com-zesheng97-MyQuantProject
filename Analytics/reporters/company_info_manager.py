"""
文件位置: Analytics/reporters/company_info_manager.py
描述: 企业信息管理器（阶段 1：基于 yfinance 的快速实现）
功能: 从 yfinance 获取企业信息，本地缓存支持
"""

import json
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict
import yfinance as yf
from utils.safe_access import safe_get_first, safe_get

# 尝试导入翻译库
HAS_TRANSLATOR = False  # 暂时禁用翻译功能（googletrans 4.0+ 需要异步支持）
TRANSLATOR = None


class CompanyInfoManager:
    """
    企业信息管理器
    - 优先级 1：本地缓存 (Company_KnowledgeBase/)
    - 优先级 2：yfinance 获取信息
    - 优先级 3：AI 深度总结（未来）
    """
    
    def __init__(self, cache_dir: str = "Company_KnowledgeBase"):
        """
        初始化信息管理器
        
        Args:
            cache_dir: 本地缓存目录
        """
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
    
    def get_company_info(self, symbol: str, force_refresh: bool = False) -> Dict:
        """
        获取企业信息（优先从缓存，否则从 yfinance）
        
        Args:
            symbol: 股票代码 (INTC, AAPL, 等)
            force_refresh: 是否强制刷新（重新从 yfinance 获取）
            
        Returns:
            企业信息字典
        """
        
        # 1. 尝试从本地缓存读取
        if not force_refresh:
            cached_info = self._read_cache(symbol)
            if cached_info:
                return cached_info
        
        # 2. 从 yfinance 获取信息
        try:
            company_info = self._fetch_from_yfinance(symbol)
            
            # 3. 保存到本地缓存
            self._save_cache(symbol, company_info)
            
            return company_info
            
        except Exception as e:
            # 如果获取失败，返回默认信息
            print(f"⚠️ 获取 {symbol} 信息失败: {e}")
            return self._get_default_info(symbol)
    
    def _read_cache(self, symbol: str) -> Optional[Dict]:
        """
        从本地缓存读取企业信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            缓存的信息字典，或 None 如果不存在
        """
        cache_file = self.cache_dir / f"{symbol}.json"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"⚠️ 读取缓存失败 {symbol}: {e}")
        
        return None
    
    def _save_cache(self, symbol: str, info: Dict):
        """
        保存企业信息到本地缓存
        
        Args:
            symbol: 股票代码
            info: 企业信息字典
        """
        cache_file = self.cache_dir / f"{symbol}.json"
        
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"⚠️ 保存缓存失败 {symbol}: {e}")
    
    def _fetch_from_yfinance(self, symbol: str) -> Dict:
        """
        从 yfinance 获取企业基础信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            企业信息字典
        """
        
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # 获取企业英文简介
        business_summary_en = info.get('longBusinessSummary', '')
        
        # 尝试翻译为中文
        business_summary_cn = self._translate_to_chinese(business_summary_en) if business_summary_en else ''
        
        # 提取关键字段
        # ✅ 使用安全访问函数避免 IndexError
        officers = info.get('companyOfficers', [])
        first_officer = safe_get_first(officers, {})
        ceo_name = first_officer.get('name', 'N/A') if first_officer else 'N/A'
        
        company_data = {
            'symbol': symbol,
            'name': info.get('longName', info.get('shortName', symbol)),
            'sector': info.get('sector', 'N/A'),
            'industry': info.get('industry', 'N/A'),
            'website': info.get('website', 'N/A'),
            'employees': info.get('fullTimeEmployees', 'N/A'),
            'founded': self._extract_founded(info),
            'ceo': ceo_name,
            
            # 企业简介（中英双语）
            'business_summary_cn': business_summary_cn,
            'business_summary_en': business_summary_en,
            
            # 股票基础信息
            'current_price': info.get('currentPrice', 'N/A'),
            'open_price': info.get('regularMarketOpen', info.get('open', 'N/A')),  # 开盘价
            'day_change': info.get('regularMarketChange', 'N/A'),  # 当日涨跌（数字）
            'day_change_percent': info.get('regularMarketChangePercent', 'N/A'),  # 当日涨跌幅（%）
            'market_cap': info.get('marketCap', 'N/A'),
            'pe_ratio': info.get('trailingPE', 'N/A'),
            
            # 财务指标
            'fcf': info.get('freeCashflow', 'N/A'),  # 自由现金流
            'roe': info.get('returnOnEquity', 'N/A'),  # 股东权益回报率
            
            # IPO日期
            'ipo_date': self._extract_ipo_date(info),
            
            'last_updated': datetime.now().isoformat(),
            'source': 'yfinance',
        }
        
        return company_data
    
    def _extract_ipo_date(self, info: Dict) -> str:
        """
        从info字典中提取IPO日期
        
        Args:
            info: 从yfinance获取的info字典
            
        Returns:
            IPO日期字符串 (YYYY-MM-DD) 或 'N/A'
        """
        try:
            ipo_date = info.get('ipoDate', None)
            if ipo_date:
                # 如果是时间戳
                if isinstance(ipo_date, (int, float)):
                    ipo_datetime = datetime.fromtimestamp(ipo_date)
                    return ipo_datetime.strftime('%Y-%m-%d')
                # 如果已是字符串
                elif isinstance(ipo_date, str):
                    return ipo_date[:10]  # 截取YYYY-MM-DD部分
        except:
            pass
        return 'N/A'
    
    def _translate_to_chinese(self, text: str) -> str:
        """
        将文本翻译为中文
        
        Args:
            text: 要翻译的英文文本
            
        Returns:
            中文翻译，如果不可用则返回空字符串
        """
        if not text or len(text) < 20:  # 文本过短，不翻译
            return ''
        
        if not HAS_TRANSLATOR:
            return ''
        
        try:
            # 使用正确的 googletrans API 参数名
            translation = TRANSLATOR.translate(text, lang_src='en', lang_tgt='zh-CN')
            return translation.get('text', '')
        except Exception as e:
            print(f"⚠️ 翻译失败 {str(e)}: {text[:50]}")
            return ''
    
    def _extract_founded(self, info: Dict) -> str:
        """
        提取公司成立年份
        """
        if 'founded' in info:
            return str(info['founded'])
        
        # yfinance 通常不提供成立年份，返回 N/A
        return 'N/A'
    
    def _get_default_info(self, symbol: str) -> Dict:
        """
        返回默认企业信息（当获取失败时）
        """
        return {
            'symbol': symbol,
            'name': symbol,
            'sector': 'N/A',
            'industry': 'N/A',
            'website': 'N/A',
            'employees': 'N/A',
            'founded': 'N/A',
            'ceo': 'N/A',
            'business_summary_en': '企业信息加载失败，请稍后重试。',
            'business_summary_cn': '',
            'current_price': 'N/A',
            'open_price': 'N/A',
            'day_change': 'N/A',
            'day_change_percent': 'N/A',
            'market_cap': 'N/A',
            'pe_ratio': 'N/A',
            'fcf': 'N/A',
            'roe': 'N/A',
            'last_updated': datetime.now().isoformat(),
            'source': 'default',
        }
    
    def get_all_cached_symbols(self) -> list:
        """
        获取所有已缓存的标的列表
        
        Returns:
            标的代码列表
        """
        cached_files = self.cache_dir.glob('*.json')
        return sorted([f.stem for f in cached_files])
