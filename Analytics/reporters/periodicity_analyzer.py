"""
文件位置: Analytics/reporters/periodicity_analyzer.py
描述: 股票周期性分析工具
功能: FFT + 小波分析 + 统计周期性测试 = 综合周期性评分
"""

import numpy as np
import pandas as pd
from scipy import signal, fft
from scipy.signal import morlet2, cwt
from scipy.stats import kurtosis, skew
import warnings
warnings.filterwarnings('ignore')

class PeriodicityAnalyzer:
    """
    周期性分析器 - 综合使用多种方法
    阈值: 0.7（0-1范围，更高表示周期性更强）
    """
    
    def __init__(self, threshold: float = 0.7):
        """
        初始化周期性分析器
        
        Args:
            threshold: 周期性强度阈值（0-1），>= threshold 视为强周期性
        """
        self.threshold = threshold
    
    def analyze(self, data: pd.Series, name: str = "Data") -> dict:
        """
        综合分析周期性特征
        
        Args:
            data: 时间序列（通常是收盘价）
            name: 数据标识
            
        Returns:
            {
                'symbol': 标识,
                'is_periodic': 是否强周期性,
                'periodicity_score': 综合周期性分数 (0-1),
                'fft_score': FFT周期性分数,
                'wavelet_score': 小波周期性分数,
                'kpss_score': KPSS统计周期性分数,
                'dominant_period_fft': 主周期(FFT),
                'dominant_period_wavelet': 主周期(小波),
                'details': 详细信息
            }
        """
        
        if data is None or len(data) < 50:
            return self._empty_result(name, "数据不足")
        
        # 清理数据
        data_clean = data.dropna()
        if len(data_clean) < 50:
            return self._empty_result(name, "有效数据不足")
        
        # 归一化
        data_norm = (data_clean - data_clean.mean()) / data_clean.std()
        
        # 1. FFT分析
        fft_score, dominant_period_fft = self._fft_analysis(data_norm)
        
        # 2. 小波分析
        wavelet_score, dominant_period_wavelet = self._wavelet_analysis(data_norm)
        
        # 3. KPSS周期性测试
        kpss_score = self._kpss_periodicity_score(data_norm)
        
        # 4. 综合评分 (加权平均)
        weights = {'fft': 0.4, 'wavelet': 0.4, 'kpss': 0.2}
        periodicity_score = (
            fft_score * weights['fft'] + 
            wavelet_score * weights['wavelet'] + 
            kpss_score * weights['kpss']
        )
        periodicity_score = np.clip(periodicity_score, 0, 1)
        
        # 5. 判定是否强周期性
        is_periodic = periodicity_score >= self.threshold
        
        return {
            'symbol': name,
            'is_periodic': is_periodic,
            'periodicity_score': round(periodicity_score, 4),
            'fft_score': round(fft_score, 4),
            'wavelet_score': round(wavelet_score, 4),
            'kpss_score': round(kpss_score, 4),
            'dominant_period_fft': int(dominant_period_fft) if dominant_period_fft else None,
            'dominant_period_wavelet': int(dominant_period_wavelet) if dominant_period_wavelet else None,
            'threshold': self.threshold,
            'details': {
                'data_length': len(data_clean),
                'mean': float(data_clean.mean()),
                'std': float(data_clean.std()),
                'trend_strength': self._trend_strength(data_norm)
            }
        }
    
    def _fft_analysis(self, data: pd.Series) -> tuple:
        """
        FFT快速傅里叶变换分析
        获取主周期及周期性强度
        
        Returns: (周期性分数, 主周期天数)
        """
        try:
            n = len(data)
            if n < 4:
                return 0.0, None
            
            # 计算FFT
            fft_vals = np.abs(fft.fft(data.values))
            
            # 只看一半（因为FFT对称）
            fft_vals = fft_vals[:n // 2]
            freqs = np.arange(len(fft_vals))
            
            # 忽略趋势项（频率0）
            if len(fft_vals) > 1:
                fft_vals[0] = 0  # DC分量置0
            
            # 找主周期
            if len(fft_vals) > 0:
                peak_freq_idx = np.argmax(fft_vals[1:]) + 1
                dominant_period = n / (peak_freq_idx + 1)
                
                # 周期性强度：主峰与平均值的比值
                peak_power = fft_vals[peak_freq_idx]
                avg_power = np.mean(fft_vals[1:])
                
                if avg_power > 0:
                    periodicity_score = min(peak_power / (avg_power * 3), 1.0)
                else:
                    periodicity_score = 0.0
                
                return periodicity_score, dominant_period
            
            return 0.0, None
            
        except Exception as e:
            print(f"⚠️ FFT分析异常: {e}")
            return 0.0, None
    
    def _wavelet_analysis(self, data: pd.Series) -> tuple:
        """
        连续小波变换（CWT）分析
        使用Morlet小波捕捉时间-频率信息
        
        Returns: (周期性分数, 主周期天数)
        """
        try:
            n = len(data)
            if n < 10:
                return 0.0, None
            
            # 设置小波尺度范围（对应周期）
            # 周期 ≈ 4π * scale / f_center
            min_period = 5  # 最小5天
            max_period = min(n // 2, 252)  # 最大一年左右
            scales = np.arange(min_period, max_period)
            
            # 执行CWT
            coefficients = cwt(data.values, morlet2, scales)
            
            # 计算每个尺度的能量（平均绝对值）
            energies = np.mean(np.abs(coefficients), axis=1)
            
            # 平滑能量曲线
            if len(energies) > 5:
                energies_smooth = self._smooth(energies, window_len=5)
            else:
                energies_smooth = energies
            
            # 找主周期
            if len(energies_smooth) > 0:
                peak_scale_idx = np.argmax(energies_smooth)
                dominant_scale = scales[peak_scale_idx]
                dominant_period = 4 * np.pi * dominant_scale / 5.336  # Morlet中心频率
                
                # 周期性强度
                peak_energy = energies_smooth[peak_scale_idx]
                avg_energy = np.mean(energies_smooth)
                
                if avg_energy > 0:
                    periodicity_score = min(peak_energy / (avg_energy * 2), 1.0)
                else:
                    periodicity_score = 0.0
                
                return periodicity_score, dominant_period
            
            return 0.0, None
            
        except Exception as e:
            print(f"⚠️ 小波分析异常: {e}")
            return 0.0, None
    
    def _kpss_periodicity_score(self, data: pd.Series) -> float:
        """
        基于KPSS测试的周期性评分
        思想：强周期性数据应该有较强的自相关性
        
        Returns: 周期性分数 (0-1)
        """
        try:
            # 计算自相关函数（ACF）
            acf_vals = [data.autocorr(lag=i) for i in range(1, min(len(data) // 4, 100))]
            
            if not acf_vals:
                return 0.0
            
            # 周期性指标：
            # 1. 多个显著自相关峰
            # 2. 自相关衰减缓慢（周期长）
            significant_peaks = sum(1 for acf in acf_vals if abs(acf) > 0.3)
            decay_rate = (acf_vals[0] - acf_vals[-1]) / len(acf_vals) if len(acf_vals) > 1 else 0
            
            # 周期性分数 = 显著峰数 * 缓慢衰减系数
            if len(acf_vals) > 0:
                score = min(significant_peaks / 10 * (1 - decay_rate * 0.5), 1.0)
            else:
                score = 0.0
            
            return max(score, 0.0)
            
        except Exception as e:
            print(f"⚠️ KPSS评分异常: {e}")
            return 0.0
    
    def _trend_strength(self, data: pd.Series) -> float:
        """
        计算趋势强度（用于区分趋势与周期）
        高趋势强度说明数据主要受趋势驱动，周期性弱
        """
        try:
            if len(data) < 2:
                return 0.0
            
            # 线性回归的R²
            x = np.arange(len(data))
            z = np.polyfit(x, data.values, 1)
            p = np.poly1d(z)
            y_fit = p(x)
            
            ss_res = np.sum((data.values - y_fit) ** 2)
            ss_tot = np.sum((data.values - np.mean(data)) ** 2)
            
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
            
            return max(r_squared, 0.0)
            
        except:
            return 0.0
    
    def _smooth(self, data: np.ndarray, window_len: int = 11) -> np.ndarray:
        """简单的移动平均平滑"""
        if len(data) < window_len:
            return data
        
        kernel = np.ones(window_len) / window_len
        smoothed = np.convolve(data, kernel, mode='same')
        return smoothed
    
    def _empty_result(self, name: str, reason: str) -> dict:
        """返回空结果"""
        return {
            'symbol': name,
            'is_periodic': False,
            'periodicity_score': 0.0,
            'fft_score': 0.0,
            'wavelet_score': 0.0,
            'kpss_score': 0.0,
            'dominant_period_fft': None,
            'dominant_period_wavelet': None,
            'threshold': self.threshold,
            'error': reason
        }
    
    @staticmethod
    def batch_analyze(symbols_data: dict, threshold: float = 0.7) -> pd.DataFrame:
        """
        批量分析多个标的的周期性
        
        Args:
            symbols_data: {symbol: pd.Series}
            threshold: 周期性阈值
            
        Returns:
            分析结果DataFrame
        """
        analyzer = PeriodicityAnalyzer(threshold=threshold)
        results = []
        
        for symbol, data in symbols_data.items():
            result = analyzer.analyze(data, name=symbol)
            results.append(result)
        
        return pd.DataFrame(results)
