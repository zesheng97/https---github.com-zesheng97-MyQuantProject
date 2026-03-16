# 📋 GitHub 发布快速参考卡 | Quick Reference Card

## 🚀 5 分钟快速版（如果你有 Git 经验）

```powershell
# 1. 配置（仅一次）
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# 2. 在 GitHub 创建仓库：https://github.com/new
#    名称: personal-quant-lab
#    描述: A Python-based quantitative backtesting platform

# 3. 在本地推送代码
git init
git add .
git commit -m "feat: Initial commit - Personal Quant Lab v2026.0.0"
git remote add origin https://github.com/yourusername/personal-quant-lab.git
git branch -M main
git push -u origin main

# 4. 创建发布标签
git tag -a v2026.0.0 -m "Release version 2026.0.0"
git push origin v2026.0.0

# 5. 在 GitHub 网站上：
#    https://github.com/yourusername/personal-quant-lab/releases/new
#    选择标签 v2026.0.0，填写发布说明，点击 Publish release
```

---

## ⏱️ 15 分钟详细版（初学者）

### A. 准备阶段（2 分钟）

```powershell
# 验证 Git 已安装
git --version

# 配置用户信息
git config --global user.name "Your Real Name"    # 替换为你的名字
git config --global user.email "your@gmail.com"   # 替换为你的邮箱
```

### B. 创建 GitHub 仓库（3 分钟）

访问：https://github.com/new

| 设置项 | 值 |
|--------|-----|
| Repository name | `personal-quant-lab` |
| Description | `A Python-based mid-to-low frequency quantitative backtesting platform with Streamlit GUI` |
| Public/Private | **Public** ✅ |
| Initialize | 都**不勾选** |
| License | MIT |

点击 "Create repository" → **完成！**

### C. 推送代码（5 分钟）

打开 PowerShell，进入项目目录：

```powershell
cd D:\MyQuantProject

# 初始化 Git（如果还没有的话）
git init

# 查看状态
git status

# 添加所有文件
git add .

# 创建首次提交
git commit -m "feat: Initial commit - Personal Quant Lab v2026.0.0"

# 添加远程仓库（复制你的仓库 URL）
git remote add origin https://github.com/YOUR_USERNAME/personal-quant-lab.git

# 重命名主分支
git branch -M main

# 推送代码
git push -u origin main
```

**如果要求输入密码**：使用 GitHub Personal Access Token（不是真实密码）

### D. 创建发布（5 分钟）

```powershell
# 创建版本标签
git tag -a v2026.0.0 -m "Release version 2026.0.0 - First official release"

# 推送标签到 GitHub
git push origin v2026.0.0
```

在 GitHub 网页上：
1. 访问：https://github.com/YOUR_USERNAME/personal-quant-lab/releases
2. 点击 "Create a new release"
3. 选择标签：v2026.0.0
4. 发布标题：`Personal Quant Lab v2026.0.0`
5. 发布说明：复制 [RELEASE_v2026.0.0.md](RELEASE_v2026.0.0.md) 的内容
6. 点击 "Publish release"

---

## 🔑 关键命令速记

| 任务 | 命令 |
|------|------|
| 检查 Git 版本 | `git --version` |
| 配置用户名 | `git config --global user.name "Name"` |
| 配置邮箱 | `git config --global user.email "email"` |
| 初始化仓库 | `git init` |
| 查看状态 | `git status` |
| 添加所有文件 | `git add .` |
| 创建提交 | `git commit -m "message"` |
| 添加远程仓库 | `git remote add origin URL` |
| 列出远程仓库 | `git remote -v` |
| 推送代码 | `git push -u origin main` |
| 创建标签 | `git tag -a v2026.0.0 -m "message"` |
| 推送标签 | `git push origin v2026.0.0` |
| 查看提交历史 | `git log --oneline` |

---

## ✅ 检查清单

发布成功前，检查以下项目：

```
前置条件
☐ Git 已安装
☐ GitHub 账户已创建
☐ Git 全局配置已完成

文件准备
☐ README.md 已完成
☐ setup.py 已配置
☐ pyproject.toml 已配置
☐ requirements.txt 已列出依赖
☐ LICENSE 文件已添加
☐ CHANGELOG.md 已完成
☐ CONTRIBUTING.md 已完成
☐ .gitignore 已配置
☐ .github/ISSUE_TEMPLATE/ 已创建
☐ .github/workflows/tests.yml 已创建

GitHub 操作
☐ GitHub 仓库已创建（Public）
☐ 本地代码已推送到 main 分支
☐ 版本标签已创建并推送
☐ Release 页面已创建
☐ 仓库描述已填写
☐ Topics 已添加
☐ License 已设置为 MIT

验证
☐ 网页可以访问仓库
☐ 所有文件都在 GitHub 上
☐ Release 页面显示正确
☐ README.md 内容在主页显示
```

---

## 🆘 快速故障排除

### 问题：`fatal: not a git repository`
```powershell
# 确保在正确目录
cd D:\MyQuantProject

# 初始化 Git
git init
```

### 问题：推送失败（401 Unauthorized）
```powershell
# 使用 Personal Access Token 而不是密码
# 1. GitHub → Settings → Developer settings → Personal access tokens
# 2. 生成新 Token
# 3. 下次推送时使用 Token 作为密码
```

### 问题：`fatal: unable to access 'xxx': Could not resolve host`
```powershell
# 检查网络连接
ping github.com

# 如果没有 GitHub 密钥认证，尝试 HTTPS
git remote set-url origin https://github.com/yourusername/personal-quant-lab.git
```

### 问题：`error: pathspec 'main' did not match any files`
```powershell
# 检查当前分支
git branch -a

# 重命名分支
git branch -M master main  # 如果当前分支是 master
```

### 问题：标签已存在
```powershell
# 删除本地标签
git tag -d v2026.0.0

# 删除远程标签
git push origin --delete v2026.0.0

# 重新创建标签
git tag -a v2026.0.0 -m "Release version 2026.0.0"
git push origin v2026.0.0
```

---

## 📱 Windows PowerShell 特定技巧

### 打开 PowerShell
- 按 `Win + R`，输入 `powershell`，按 Enter
- 或右键点击文件夹，选择 "Open in Windows Terminal"

### 复制粘贴
- 右键点击选择内容后 Shift + Insert 粘贴
- 或启用 Ctrl+C/V（新版 Windows Terminal）

### 查看文件夹内容
```powershell
# 列出当前目录
ls

# 列出包含隐藏文件
ls -Force

# 查看特定文件
type README.md
```

### 环境变量查询
```powershell
# 查看用户主目录
$env:USERPROFILE

# 查看所有环境变量
Get-ChildItem env:
```

---

## 📈 发布后的常见操作

### 推送新的更新
```powershell
# 编辑文件...

# 查看改动
git status

# 添加改动
git add .

# 创建新提交
git commit -m "fix: Fix backtest calculation bug"

# 推送更新
git push origin main
```

### 创建新版本
```powershell
# 创建新标签（版本递增）
git tag -a v2026.1.0 -m "Release version 2026.1.0 - Add RSI strategy"

# 推送标签
git push origin v2026.1.0

# 在 GitHub Releases 页面创建新 Release
```

### 创建功能分支
```powershell
# 为新功能创建分支
git checkout -b feature/add-bollinger-bands

# 推送分支
git push -u origin feature/add-bollinger-bands

# 完成后可以在 GitHub 上创建 Pull Request
```

---

## 🎓 推荐学习资源

如果你想深入了解 Git 和 GitHub：

- **GitHub 官方教程**：https://docs.github.com/
- **Git 官方文档**：https://git-scm.com/doc
- **Interactive Git Tutorial**：https://learngitbranching.js.org/
- **GitHub CLI 参考**：https://cli.github.com/

---

## 💡 专业提示

1. **定期推送**：不要等到完成所有工作才提交。每完成一个功能就提交一次。

2. **清晰的提交信息**：
   ```
   ✅ Good: "feat: Add RSI indicator to strategy library"
   ❌ Bad: "updated files" 或 "fix bug"
   ```

3. **使用 .gitignore**：确保不提交 `__pycache__`、`.env`、`*.pyc` 等

4. **保护 main 分支**：
   - GitHub → Settings → Branches → Add protection rule
   - 要求 PR 审查再合并

5. **Star 很重要**：250+ Stars 通常表示项目很受欢迎

---

## 🎉 成功标志

你的项目已成功发布，如果：

```
✅ GitHub 仓库页面显示所有文件
✅ README.md 内容在主页显示
✅ Releases 页面显示 v2026.0.0
✅ 可以从网页 Clone 代码：
   git clone https://github.com/yourusername/personal-quant-lab.git
✅ 项目描述、Topics、License 都已设置
✅ 可以看到你的 commit 历史
```

**恭喜！你现在是一个开源项目的维护者了！** 🚀

---

## 📞 需要帮助？

- 查看详细教程：[DETAILED_GITHUB_TUTORIAL.md](DETAILED_GITHUB_TUTORIAL.md)
- 检查发布清单：[GITHUB_RELEASE_CHECKLIST.md](GITHUB_RELEASE_CHECKLIST.md)
- GitHub 官方文档：https://docs.github.com/
- 提交 Issue 寻求帮助：https://github.com/yourusername/personal-quant-lab/issues

---

**祝你发布顺利！** 🎊
