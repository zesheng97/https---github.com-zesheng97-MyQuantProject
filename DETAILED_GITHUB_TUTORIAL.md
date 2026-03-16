# 🚀 GitHub 发布完整教程 | GitHub Release Complete Guide

[中文详细版本](#中文详细版本) | [English Quick Guide](#english-quick-guide)

---

<a name="中文详细版本"></a>

# 📘 中文详细版本

## 📋 前置条件检查

在开始之前，请确保你已经准备好以下内容：

### 1. 安装 Git
```bash
# 检查是否已安装 Git
git --version

# 如果未安装，请从以下地址下载：
# Windows: https://git-scm.com/download/win
# macOS: https://git-scm.com/download/mac
# Linux (Ubuntu): sudo apt-get install git
```

### 2. 创建 GitHub 账户
- 访问 https://github.com
- 点击 "Sign up"（注册）
- 填写用户名、邮箱、密码
- 按照邮件验证步骤完成注册

### 3. 配置 Git 全局用户
这很重要！这样 Git 才知道你的身份。

```bash
# 配置用户名（替换为你的真实名字）
git config --global user.name "Your Name"

# 配置邮箱（使用你 GitHub 账户的邮箱）
git config --global user.email "your.email@example.com"

# 验证配置是否成功
git config --global --list
```

### 4. 设置 GitHub 认证（重要！）

在 Windows 上，有两种认证方式：

#### 方式 A：使用 Personal Access Token（推荐）✅

1. **在 GitHub 上生成 Token**
   - 登录 GitHub → 点击右上角头像 → Settings
   - 左侧菜单 → Developer settings → Personal access tokens → Fine-grained tokens
   - 点击 "Generate new token"
   - Token name: `personal-quant-lab-release`
   - Expiration: 90 days（或更长）
   - Resource owner: 选择你的账户
   - Repository access: "All repositories"
   - Permissions:
     - ✅ Contents: Read and Write
     - ✅ Metadata: Read-only
   - 点击 "Generate token"
   - **复制 Token 并保存到安全的地方**（只会显示一次！）

2. **在 Windows Credential Manager 中保存**
   ```powershell
   # 打开 PowerShell（以管理员身份）
   # 或者手动打开：Windows 设置 → 凭据管理器
   
   # 使用 Token 替代密码进行 git push
   # 当询问密码时，粘贴你的 Token
   ```

#### 方式 B：使用 SSH Key（更安全）

```bash
# 1. 生成 SSH Key（如果还没有的话）
ssh-keygen -t ed25519 -C "your.email@example.com"
# 或者对于旧系统：
ssh-keygen -t rsa -b 4096 -C "your.email@example.com"

# 2. 按 Enter 三次接受默认设置

# 3. 查看公钥内容（Windows PowerShell）
Get-Content $env:USERPROFILE\.ssh\id_ed25519.pub

# 4. 复制公钥内容

# 5. 在 GitHub 添加 SSH Key
#    - GitHub → Settings → SSH and GPG keys → New SSH key
#    - Title: Personal Quant Lab
#    - Keys: 粘贴公钥内容
#    - Add SSH key

# 6. 测试连接
ssh -T git@github.com
# 应该看到: "Hi username! You've successfully authenticated..."
```

---

## 🎯 第一步：在 GitHub 创建新仓库

### 1. 登录 GitHub 并创建仓库

```
访问: https://github.com/new
```

### 2. 填写仓库信息

| 字段 | 填写内容 | 说明 |
|------|---------|------|
| **Repository name** | `personal-quant-lab` | 仓库名称（会显示在 URL 中） |
| **Description** | `A Python-based mid-to-low frequency quantitative backtesting platform with Streamlit GUI` | 项目描述 |
| **Public / Private** | **Public** ✅ | 选择公开（这样其他人可以看到） |
| **Initialize with README** | ⚪ 不勾选 | 我们已经有 README.md 了 |
| **.gitignore template** | ⚪ 不选择 | 我们已经有 .gitignore 了 |
| **License** | MIT | 选择 MIT License |

### 3. 点击 "Create repository"

✅ **完成！** 你将看到仓库页面，显示如下信息：
```
Quick setup — if you've done this kind of thing before
or
…or create a new repository on the command line
…or push an existing repository from the command line
```

---

## 🎯 第二步：在本地初始化 Git 仓库

打开 PowerShell 或 Command Prompt，进入你的项目目录：

```powershell
# 进入项目目录
cd D:\MyQuantProject

# 初始化 Git 仓库（如果还没有的话）
git init

# 查看仓库状态
git status
```

你会看到所有文件都是红色的（Untracked files），这是正常的。

---

## 🎯 第三步：添加文件到暂存区

```powershell
# 添加所有文件到暂存区
git add .

# 查看哪些文件已被添加
git status
```

你会看到所有文件变成绿色（Changes to be committed）。

### 🔍 验证重要文件

确保这些文件已被添加：
```
✅ README.md
✅ setup.py
✅ pyproject.toml
✅ requirements.txt
✅ LICENSE
✅ CHANGELOG.md
✅ CONTRIBUTING.md
✅ .gitignore
✅ 所有 Python 源代码文件
✅ .github/ 目录（含工作流）
```

---

## 🎯 第四步：创建首次提交

```powershell
# 创建提交（commit）
git commit -m "feat: Initial commit - Personal Quant Lab v2026.0.0"

# 查看提交日志
git log --oneline
```

你应该看到输出类似：
```
abc1234 feat: Initial commit - Personal Quant Lab v2026.0.0
```

---

## 🎯 第五步：连接到 GitHub 仓库

这一步连接你的本地仓库到 GitHub 上的远程仓库。

```powershell
# 添加远程仓库
# 替换 yourusername 为你的 GitHub 用户名
git remote add origin https://github.com/yourusername/personal-quant-lab.git

# 验证是否添加成功
git remote -v
```

你会看到：
```
origin  https://github.com/yourusername/personal-quant-lab.git (fetch)
origin  https://github.com/yourusername/personal-quant-lab.git (push)
```

---

## 🎯 第六步：重命名主分支为 "main"（可选但推荐）

GitHub 现在的默认分支是 `main`，而不是 `master`：

```powershell
# 重命名分支
git branch -M main

# 验证分支名称
git branch -a
```

你会看到 `main` 分支。

---

## 🎯 第七步：推送代码到 GitHub（重要！）

这是将你的本地代码上传到 GitHub 的关键步骤。

```powershell
# 推送代码到 GitHub 的 main 分支
git push -u origin main
```

### 如果这是第一次推送

你可能会看到登录提示：
- **方法 1**：粘贴你的 Personal Access Token（当要求密码时）
- **方法 2**：使用 SSH（如果你已经设置了）
- **方法 3**：使用 GitHub CLI

### 成功标志

如果看到以下输出，说明推送成功：
```
Enumerating objects: 150, done.
Counting objects: 100% (150/150), done.
Delta compression using up to 12 threads
Compressing objects: 100% (120/120), done.
Writing objects: 100% (150/150), 45.32 KiB | 2.26 MiB/s, done.
Total 150 (delta 30), reused 0 (delta 0), pack-reused 0
remote: Resolving deltas: 100% (30/30), done.
To https://github.com/yourusername/personal-quant-lab.git
 * [new branch]      main -> main
Branch 'main' set to track remote branch 'main' from 'origin'.
```

✅ **恭喜！你的代码已成功推送到 GitHub！**

---

## 🎯 第八步：验证 GitHub 上的代码

访问你的 GitHub 仓库：
```
https://github.com/yourusername/personal-quant-lab
```

你应该看到：
- ✅ 所有文件已显示
- ✅ README.md 内容自动显示在仓库页面下方
- ✅ 文件树完整
- ✅ commit 计数正确

---

## 🎯 第九步：创建发布标签 (Release Tag)

标签用于标记特定的版本。

```powershell
# 创建带注释的标签
git tag -a v2026.0.0 -m "Release version 2026.0.0 - First official release"

# 验证标签是否创建
git tag -l

# 推送标签到 GitHub
git push origin v2026.0.0

# 如果要推送所有标签：
git push origin --tags
```

---

## 🎯 第十步：在 GitHub 上创建 Release

### 方法 1：通过网页界面（最简单）✅ 推荐

1. **访问你的仓库**
   ```
   https://github.com/yourusername/personal-quant-lab
   ```

2. **进入 Releases 页面**
   - 点击右侧 "Releases"
   - 或访问：`https://github.com/yourusername/personal-quant-lab/releases`

3. **点击 "Create a new release"**

4. **填写发布信息**

   | 字段 | 内容 |
   |------|------|
   | **Choose a tag** | v2026.0.0（下拉菜单选择） |
   | **Release title** | `Personal Quant Lab v2026.0.0` |
   | **Describe this release** | 复制以下内容... |

5. **发布说明内容**（复制粘贴）

打开 [RELEASE_v2026.0.0.md](RELEASE_v2026.0.0.md) 的内容，复制到 "Describe this release" 字段。

或者简单版本：
```markdown
# Personal Quant Lab v2026.0.0

## ✨ Features
- ✅ Parameterized backtesting engine
- ✅ Interactive Streamlit GUI
- ✅ Company information management
- ✅ Integer share trading logic
- ✅ Benchmark comparison (NASDAQ & S&P 500)
- ✅ Daily trading data display
- ✅ Bilingual documentation (English & Chinese)

## 🚀 Installation
```bash
git clone https://github.com/yourusername/personal-quant-lab.git
cd personal-quant-lab
pip install -r requirements.txt
python run_gui.py
```

## 📚 Documentation
- [README.md](README.md) - Complete documentation
- [QUICKSTART.md](QUICKSTART.md) - Quick start guide
- [CHANGELOG.md](CHANGELOG.md) - Version history

## License
MIT License
```

6. **设置选项**
   - ☑️ "This is a pre-release" - 如果这是beta版本，勾选；否则不勾选
   - ☐ "Set as the latest release" - 保持默认（勾选）

7. **点击 "Publish release"**

✅ **完成！你的 Release 已发布！**

---

## 🎯 第十一步：配置仓库设置

### 1. 添加仓库描述

1. 进入 Settings（仓库右侧的 ⚙️ 图标）
2. 在 "About" 部分（右侧边栏）：
   - 点击 ⚙️ 按钮
   - **Description**: `A Python-based mid-to-low frequency quantitative backtesting platform`
   - **Website**: （可选，如有个人网站）
   - **Topics**: 添加以下标签：
     - `quantitative-trading`
     - `backtesting`
     - `fintech`
     - `streamlit`
     - `python`

### 2. 设置 License

1. 在 Settings → General → License
2. 如果还没有被自动识别，点击 "Choose a license" → 选择 MIT

### 3. 启用 Discussions（可选）

1. Settings → Features
2. ☑️ 勾选 "Discussions"
3. 这样用户可以在 Discussions 中提问而不是在 Issues 中

---

## 📊 验证清单

发布成功的标志：

- [ ] ✅ GitHub 仓库页面显示你的项目
- [ ] ✅ 所有文件都已上传
- [ ] ✅ README.md 在仓库主页显示内容
- [ ] ✅ Releases 页面显示 v2026.0.0
- [ ] ✅ 可以 clone 仓库：`git clone https://github.com/yourusername/personal-quant-lab.git`
- [ ] ✅ 项目描述和 Topics 已设置
- [ ] ✅ MIT License 已显示
- [ ] ✅ Contributors 显示你的名字

---

## 🆘 常见问题与解决方案

### ❓ 问题 1：推送时要求输入用户名和密码

**解决方案**：
```powershell
# 如果要求用户名，输入你的 GitHub 用户名
# 如果要求密码，粘贴你的 Personal Access Token（不是真实密码！）
```

### ❓ 问题 2：`fatal: not a git repository`

**解决方案**：
```powershell
# 确保你在项目根目录
cd D:\MyQuantProject

# 检查是否有 .git 目录
dir /a | findstr .git

# 如果没有，运行：
git init
```

### ❓ 问题 3：远程仓库 URL 错误

**解决方案**：
```powershell
# 查看当前的 remote
git remote -v

# 如果 URL 错误，通过以下命令修改
git remote set-url origin https://github.com/yourusername/personal-quant-lab.git

# 验证修改
git remote -v
```

### ❓ 问题 4：忘记 Personal Access Token

**解决方案**：
```powershell
# 重新生成 Token：
# 1. GitHub → Settings → Developer settings → Personal access tokens
# 2. Delete 旧的 Token
# 3. 创建新的 Token
# 4. 下次推送时使用新的 Token
```

### ❓ 问题 5：提交了敏感信息（如密码）

**解决方案**：
```powershell
# 如果敏感信息已推送到 GitHub，立即：
# 1. 修改密码/重新生成 Token
# 2. 联系 GitHub 支持或使用 git-filter-repo 工具清理历史

# 简单方式（对于小项目）：
git reset --soft HEAD~1  # 撤销最后一次提交
# 编辑文件，移除敏感信息
git add .
git commit -m "Remove sensitive information"
git push -f origin main
```

---

## 📈 发布后的下一步

### 1. 分享你的项目
- Twitter/X：分享 GitHub 链接和简介
- Reddit：在 r/algotrading, r/learnprogramming 等社区分享
- LinkedIn：发布你的项目文章
- 量化交易论坛：分享给相关社区

### 2. 吸引 Star ⭐
- 项目好用的话，宣传朋友点 Star
- Star 数量代表项目受欢迎程度
- 150+ Star 通常被当成好项目的指标

### 3. 回应用户反馈
- 定期检查 Issues（GitHub 上的 Issues 标签）
- 回复用户的问题
- 及时修复报告的 Bug

### 4. 组织代码
```powershell
# 创建分支用于新功能开发
git checkout -b feature/new-strategy

# 开发完成后，创建 Pull Request
# GitHub 会提示创建 PR 的选项
```

### 5. 定期发布更新
```powershell
# 每次有重要更新时：
git add .
git commit -m "feat: Add RSI strategy"
git push origin main

# 创建新标签
git tag -a v2026.1.0 -m "Version 2026.1.0 - Add RSI strategy"
git push origin v2026.1.0

# 在 GitHub Releases 页面创建新的 Release
```

---

## 🎯 完整命令速查表

```powershell
# === 首次设置 ===
git init                                          # 初始化
git config --global user.name "Your Name"         # 配置用户名
git config --global user.email "your@email.com"   # 配置邮箱

# === 首次推送 ===
git add .                                          # 添加所有文件
git commit -m "feat: Initial commit - v2026.0.0"  # 创建提交
git remote add origin https://github.com/yourusername/personal-quant-lab.git  # 添加远程
git branch -M main                                 # 重命名分支
git push -u origin main                            # 推送代码

# === 创建发布 ===
git tag -a v2026.0.0 -m "Release version 2026.0.0"  # 创建标签
git push origin v2026.0.0                           # 推送标签

# === 后续更新 ===
git add .                                          # 修改后添加
git commit -m "fix: Fix backtest bug"              # 创建新提交
git push origin main                               # 推送更新
```

---

## 🎉 恭喜！

你已经成功发布了 **Personal Quant Lab v2026.0.0** 到 GitHub！

**现在你有：**
- ✅ 公开的 GitHub 仓库
- ✅ 完整的项目文档
- ✅ 官方 Release 版本
- ✅ 版本控制和历史追踪
- ✅ 社区协作的基础设施

**建议继续：**
- 🌟 在 Twitter 等社交媒体分享
- 📖 撰写使用教程
- 🐛 积极修复用户报告的 Bug
- 🚀 规划下一个版本（v2026.1.0）

---

<a name="english-quick-guide"></a>

# 📗 English Quick Guide

## Prerequisites

```bash
# 1. Install Git: https://git-scm.com/
# 2. Create GitHub account: https://github.com

# 3. Configure Git
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# 4. Generate Personal Access Token at:
#    GitHub → Settings → Developer settings → Personal access tokens
```

## Step-by-Step

### Step 1: Create Repository on GitHub
- Go to https://github.com/new
- Repository name: `personal-quant-lab`
- Create repository

### Step 2: Push Code

```bash
cd D:\MyQuantProject

# Initialize Git
git init

# Add all files
git add .

# Create commit
git commit -m "feat: Initial commit - Personal Quant Lab v2026.0.0"

# Add remote repository (replace yourusername)
git remote add origin https://github.com/yourusername/personal-quant-lab.git

# Rename main branch
git branch -M main

# Push to GitHub
git push -u origin main
```

### Step 3: Create Release Tag

```bash
# Create tag
git tag -a v2026.0.0 -m "Release version 2026.0.0"

# Push tag
git push origin v2026.0.0
```

### Step 4: Create Release on GitHub

1. Go to: https://github.com/yourusername/personal-quant-lab/releases
2. Click "Create a new release"
3. Select tag: v2026.0.0
4. Release title: `Personal Quant Lab v2026.0.0`
5. Description: Copy from RELEASE_v2026.0.0.md
6. Click "Publish release"

### Step 5: Configure Repository

1. Go to Settings
2. Add description and topics
3. Verify MIT License is set

**Done! Your project is now on GitHub! 🎉**

---

**需要帮助？查看完整的中文版本上面的部分！**  
**Need help? Check the complete Chinese version above!**
