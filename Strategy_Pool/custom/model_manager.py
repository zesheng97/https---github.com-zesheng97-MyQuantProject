# Model Management Tools - XGBoost 模型管理工具
# 提供模型清理、备份、导出、导入等功能

import pandas as pd
import shutil
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime, timedelta
import warnings

class ModelManager:
    """模型管理器 - 清理、备份、导入导出"""
    
    def __init__(self, registry_path: str = "Data_Hub/model_registry"):
        self.registry_path = Path(registry_path)
        self.registry_csv = self.registry_path / "registry.csv"
        self.backup_dir = self.registry_path / "backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_registry(self) -> pd.DataFrame:
        """加载注册表"""
        if not self.registry_csv.exists():
            return pd.DataFrame()
        return pd.read_csv(self.registry_csv)
    
    def clean_low_performers(self, threshold: float = 0.5, dry_run: bool = True) -> List[str]:
        """
        清理表现不佳的模型
        
        参数：
            threshold: 性能分数阈值，低于此值的模型将被删除
            dry_run: 如果为 True，仅显示将删除的文件，不真正删除
        
        返回：
            deleted_models: 被删除的模型列表
        """
        df = self._load_registry()
        
        if df.empty:
            print("❌ 注册表为空")
            return []
        
        # 找到表现不佳的模型
        low_performers = df[df['performance_score'] < threshold]
        
        if low_performers.empty:
            print(f"✅ 无模型的性能分数低于 {threshold}")
            return []
        
        deleted_models = []
        
        print(f"\n {'🧹 [DRY RUN]' if dry_run else '🧹 [REAL]'} 即将清理 {len(low_performers)} 个低表现模型")
        print("-" * 60)
        
        for idx, row in low_performers.iterrows():
            model_id = row['model_id']
            print(f"  ❌ {model_id} (性能分数: {row['performance_score']:.4f})")
            
            if not dry_run:
                # 删除关联的模型文件
                model_files = [
                    self.registry_path / f"xgboost_{model_id.split('_')[-1]}.json",
                    self.registry_path / f"features_{model_id.split('_')[-1]}.pkl",
                    self.registry_path / f"metadata_{model_id.split('_')[-1]}.json"
                ]
                
                for file_path in model_files:
                    if file_path.exists():
                        file_path.unlink()
            
            deleted_models.append(model_id)
        
        if not dry_run:
            # 更新 CSV，删除这些行
            df_updated = df[~df['model_id'].isin(deleted_models)]
            df_updated.to_csv(self.registry_csv, index=False)
            print(f"\n✅ 已删除 {len(deleted_models)} 个模型和相关文件")
        else:
            print(f"\n💡 [DRY RUN] 以上文件将被删除，如要真正执行，请设置 dry_run=False")
        
        print("-" * 60 + "\n")
        
        return deleted_models
    
    def keep_top_n_models(self, top_n: int = 20, dry_run: bool = True) -> List[str]:
        """
        只保留表现最好的 N 个模型，删除其他模型
        
        参数：
            top_n: 保留的模型数量
            dry_run: 如果为 True，仅显示将删除的文件
        
        返回：
            deleted_models: 被删除的模型列表
        """
        df = self._load_registry()
        
        if df.empty or len(df) <= top_n:
            print("✅ 模型数量已经在限制范围内")
            return []
        
        # 按性能分数排序
        df_sorted = df.sort_values('performance_score', ascending=False)
        
        # 要删除的模型
        models_to_delete = df_sorted.iloc[top_n:]['model_id'].tolist()
        
        print(f"\n {'🧹 [DRY RUN]' if dry_run else '🧹 [REAL]'} 即将删除最后 {len(models_to_delete)} 个表现较差的模型 (保留 {top_n} 最佳)")
        print("-" * 60)
        
        for model_id in models_to_delete:
            perf_score = df[df['model_id'] == model_id]['performance_score'].values[0]
            print(f"  ❌ {model_id} (性能分数: {perf_score:.4f})")
            
            if not dry_run:
                # 删除文件
                timestamp = model_id.split('_')[-1]
                model_files = [
                    self.registry_path / f"xgboost_{timestamp}.json",
                    self.registry_path / f"features_{timestamp}.pkl",
                    self.registry_path / f"metadata_{timestamp}.json"
                ]
                
                for file_path in model_files:
                    if file_path.exists():
                        file_path.unlink()
        
        if not dry_run:
            # 更新 CSV
            df_updated = df[~df['model_id'].isin(models_to_delete)]
            df_updated.to_csv(self.registry_csv, index=False)
            print(f"\n✅ 已删除 {len(models_to_delete)} 个模型")
        else:
            print(f"\n💡 [DRY RUN] 以上文件将被删除，如要真正执行，请设置 dry_run=False")
        
        print("-" * 60 + "\n")
        
        return models_to_delete
    
    def clean_old_models(self, days: int = 30, dry_run: bool = True) -> List[str]:
        """
        删除超过指定天数的旧模型
        
        参数：
            days: 保留天数，超过此天数的模型将被删除
            dry_run: 如果为 True，仅显示将删除的文件
        
        返回：
            deleted_models: 被删除的模型列表
        """
        df = self._load_registry()
        
        if df.empty:
            print("❌ 注册表为空")
            return []
        
        # 转换时间戳列
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # 找到旧模型
        old_models_df = df[df['timestamp'] < cutoff_date]
        
        if old_models_df.empty:
            print(f"✅ 无超过 {days} 天的模型")
            return []
        
        deleted_models = []
        
        print(f"\n {'🧹 [DRY RUN]' if dry_run else '🧹 [REAL]'} 即将删除 {len(old_models_df)} 个超过 {days} 天的旧模型")
        print("-" * 60)
        
        for idx, row in old_models_df.iterrows():
            model_id = row['model_id']
            days_old = (datetime.now() - row['timestamp']).days
            print(f"  ❌ {model_id} (已有 {days_old} 天)")
            
            if not dry_run:
                timestamp = model_id.split('_')[-1]
                model_files = [
                    self.registry_path / f"xgboost_{timestamp}.json",
                    self.registry_path / f"features_{timestamp}.pkl",
                    self.registry_path / f"metadata_{timestamp}.json"
                ]
                
                for file_path in model_files:
                    if file_path.exists():
                        file_path.unlink()
            
            deleted_models.append(model_id)
        
        if not dry_run:
            # 更新 CSV
            df_updated = df[~df['model_id'].isin(deleted_models)]
            df_updated.to_csv(self.registry_csv, index=False)
            print(f"\n✅ 已删除 {len(deleted_models)} 个旧模型")
        else:
            print(f"\n💡 [DRY RUN] 以上文件将被删除，如要真正执行，请设置 dry_run=False")
        
        print("-" * 60 + "\n")
        
        return deleted_models
    
    def backup_registry(self, backup_name: Optional[str] = None) -> str:
        """
        备份整个模型注册中心
        
        参数：
            backup_name: 备份名称，默认使用时间戳
        
        返回：
            backup_path: 备份文件夹路径
        """
        if backup_name is None:
            backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        backup_path = self.backup_dir / backup_name
        
        # 复制整个注册目录（除了备份目录本身）
        if not backup_path.exists():
            # 复制所有模型文件
            for file_path in self.registry_path.glob("*"):
                if file_path.name != "backups" and file_path.is_file():
                    shutil.copy2(file_path, backup_path / file_path.name)
        
        # 主要是复制 CSV 和关键文件
        backup_path.mkdir(parents=True, exist_ok=True)
        
        for pattern in ["*.json", "*.pkl", "registry.csv"]:
            for file_path in self.registry_path.glob(pattern):
                shutil.copy2(file_path, backup_path / file_path.name)
        
        print(f"✅ 注册中心已备份到: {backup_path}")
        return str(backup_path)
    
    def list_backups(self) -> List[str]:
        """列出所有备份"""
        backups = [d.name for d in self.backup_dir.iterdir() if d.is_dir()]
        
        if not backups:
            print("❌ 无备份")
            return []
        
        print("\n📦 现有备份:")
        for backup in sorted(backups, reverse=True):
            backup_path = self.backup_dir / backup
            file_count = len(list(backup_path.glob("*")))
            print(f"  📁 {backup} ({file_count} 个文件)")
        print()
        
        return backups
    
    def restore_from_backup(self, backup_name: str, confirm: bool = False):
        """
        从备份恢复模型注册中心
        
        参数：
            backup_name: 备份名称
            confirm: 如果为 True，跳过确认提示
        """
        backup_path = self.backup_dir / backup_name
        
        if not backup_path.exists():
            print(f"❌ 备份不存在: {backup_name}")
            return
        
        if not confirm:
            response = input(f"⚠️  确认要从 {backup_name} 恢复？这将覆盖当前数据。(yes/no): ")
            if response.lower() != 'yes':
                print("❌ 已取消")
                return
        
        # 先备份当前状态
        current_backup = self.backup_registry(f"pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        print(f"💾 当前状态已备份到: {current_backup}")
        
        # 恢复
        for file_path in backup_path.glob("*"):
            shutil.copy2(file_path, self.registry_path / file_path.name)
        
        print(f"✅ 已从 {backup_name} 恢复")
    
    def export_to_excel(self, output_path: str = "models_export.xlsx") -> str:
        """
        导出注册表为 Excel 文件
        
        参数：
            output_path: 输出文件路径
        
        返回：
            output_path
        """
        df = self._load_registry()
        
        if df.empty:
            print("❌ 注册表为空")
            return ""
        
        try:
            # 创建 Excel Writer
            with pd.ExcelWriter(output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Models', index=False)
                
                # 添加统计信息表
                stats_data = {
                    '指标': ['总模型数', '平均性能分数', '平均验证准确率', 
                            '平均模拟收益率', '平均训练时间'],
                    '值': [
                        len(df),
                        df['performance_score'].mean(),
                        df['validation_accuracy'].mean(),
                        df['simulation_return'].mean(),
                        df['training_time'].mean()
                    ]
                }
                stats_df = pd.DataFrame(stats_data)
                stats_df.to_excel(writer, sheet_name='Statistics', index=False)
            
            print(f"✅ 已导出到: {output_path}")
            return output_path
        
        except ImportError:
            print("⚠️  需要安装 openpyxl: pip install openpyxl")
            # 降级为 CSV
            output_csv = output_path.replace('.xlsx', '.csv')
            df.to_csv(output_csv, index=False)
            print(f"✅ 已导出为 CSV: {output_csv}")
            return output_csv
    
    def print_disk_usage(self):
        """打印磁盘使用情况"""
        total_size = 0
        model_count = 0
        
        for file_path in self.registry_path.glob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
                model_count += 1
        
        size_mb = total_size / (1024 * 1024)
        
        print(f"\n💾 磁盘使用情况")
        print("-" * 40)
        print(f"文件数: {model_count}")
        print(f"总大小: {size_mb:.2f} MB")
        print("-" * 40 + "\n")


def interactive_cleanup():
    """交互式清理菜单"""
    manager = ModelManager()
    
    while True:
        print("\n🧹 模型清理工具")
        print("=" * 40)
        print("1. 清理低表现模型 (DRY RUN)")
        print("2. 清理低表现模型 (真实执行)")
        print("3. 仅保留 TOP N 模型 (DRY RUN)")
        print("4. 仅保留 TOP N 模型 (真实执行)")
        print("5. 删除旧模型 (DRY RUN)")
        print("6. 删除旧模型 (真实执行)")
        print("7. 备份注册中心")
        print("8. 列出备份")
        print("9. 从备份恢复")
        print("10. 导出为 Excel")
        print("11. 查看磁盘使用")
        print("0. 退出")
        print("=" * 40)
        
        choice = input("选择操作 (0-11): ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            threshold = float(input("输入性能分数阈值 (默认 0.5): ") or "0.5")
            manager.clean_low_performers(threshold=threshold, dry_run=True)
        elif choice == "2":
            threshold = float(input("输入性能分数阈值 (默认 0.5): ") or "0.5")
            manager.clean_low_performers(threshold=threshold, dry_run=False)
        elif choice == "3":
            top_n = int(input("输入保留模型数 (默认 20): ") or "20")
            manager.keep_top_n_models(top_n=top_n, dry_run=True)
        elif choice == "4":
            top_n = int(input("输入保留模型数 (默认 20): ") or "20")
            manager.keep_top_n_models(top_n=top_n, dry_run=False)
        elif choice == "5":
            days = int(input("输入保留天数 (默认 30): ") or "30")
            manager.clean_old_models(days=days, dry_run=True)
        elif choice == "6":
            days = int(input("输入保留天数 (默认 30): ") or "30")
            manager.clean_old_models(days=days, dry_run=False)
        elif choice == "7":
            name = input("输入备份名称 (默认使用时间戳): ").strip() or None
            manager.backup_registry(backup_name=name)
        elif choice == "8":
            manager.list_backups()
        elif choice == "9":
            manager.list_backups()
            name = input("输入备份名称: ").strip()
            manager.restore_from_backup(name)
        elif choice == "10":
            output = input("输入输出文件路径 (默认 models_export.xlsx): ").strip() or "models_export.xlsx"
            manager.export_to_excel(output)
        elif choice == "11":
            manager.print_disk_usage()
        else:
            print("❌ 无效选择")


if __name__ == "__main__":
    interactive_cleanup()
