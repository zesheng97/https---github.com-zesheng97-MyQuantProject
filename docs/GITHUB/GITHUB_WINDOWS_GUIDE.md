# 🪟 Windows 上 GitHub 发布完整指南（傻瓜版）

## 📝 一句话总结

你要做的就是：把本地文件夹的代码 **上传到 GitHub**，这样其他人可以在网页上看到你的代码。

---

## 🎯 分 5 步完成（每步都有图示说明）

### **第 1 步：安装 Git（如果还没装）**

1. 访问：https://git-scm.com/download/win
2. 点击绿色的 "Download" 按钮
3. 双击已下载的 `.exe` 文件
4. 一直点 "Next" 到安装完成
5. 重启电脑

#### 验证是否安装成功：
- 按 `Win + R`（Windows开始菜单右下角的"运行"）
- 输入 `powershell`
- 输入 `git --version`
- 如果显示版本号（如 `git version 2.40.0`），说明安装成功 ✅

---

### **第 2 步：配置你的身份（一次性）**

打开 PowerShell（按 `Win + R` → 输入 `powershell`）：

```powershell
# 第一行：配置你的名字（用你的真名替换）
git config --global user.name "Zhang San"

# 第二行：配置你的邮箱（用你的真实邮箱替换）
git config --global user.email "zhangsan@gmail.com"
```

每行输入后按 Enter。两行都输入完成后，PowerShell 不会显示任何反馈（这是正常的）。

---

### **第 3 步：在 GitHub 网站上创建空仓库**

1. 用浏览器访问：https://github.com（如果未登录，先登录）
2. 点击右上角的 **+** 按钮 → 选择 **New repository**
3. 在 "Repository name" 输入：`personal-quant-lab`
4. 在 "Description" 输入：`A Python-based quantitative backtesting platform`
5. 选择 **Public**（这样所有人都能看到）
6. **不要勾选** "Initialize this repository with a README"（我们已经有了）
7. 点击 **Create repository**

**完成！你会看到一个新的空仓库页面。**

页面上会显示这样的内容：
```
…or push an existing repository from the command line

git remote add origin https://github.com/yourname/personal-quant-lab.git
git branch -M main
git push -u origin main
```

**复制这个网址**（你的 GitHub 用户名会自动代替 `yourname`）：
```
https://github.com/yourname/personal-quant-lab.git
```

---

### **第 4 步：上传代码（关键步骤！）**

打开 PowerShell，进入项目文件夹：

```powershell
# 进入项目目录（根据你的实际路径调整）
cd D:\MyQuantProject
```

然后依次执行以下命令（每行后按 Enter）：

```powershell
# 1. 初始化 Git 仓库
git init

# 2. 查看文件状态（可选，用来验证）
git status

# 3. 添加所有文件
git add .

# 4. 创建"快照"（提交）
git commit -m "feat: Initial commit - Personal Quant Lab v2026.0.0"

# 5. 告诉 Git 远程仓库地址（从第 3 步复制，替换 YOUR_NAME）
git remote add origin https://github.com/YOUR_NAME/personal-quant-lab.git

# 6. 重命名主分支为 main
git branch -M main

# 7. 上传代码到 GitHub（这是最重要的！）
git push -u origin main
```

#### 可能会发生什么：

**情况 1：弹出登录窗口** ✅
- 输入你的 GitHub 用户名
- 输入你的 GitHub 密码（或 Personal Access Token）
- 点击确定

**情况 2：PowerShell 要求输入密码**
- 粘贴你的 Personal Access Token（见下面的"获取认证"）
- 按 Enter

**情况 3：看到绿色的成功消息** ✅
- 代码已成功上传！

---

### **获取 Personal Access Token（如果需要）**

如果上传时要求输入密码，用 Token 代替真实密码：

1. 登录 GitHub → 点击右上角头像
2. 选择 **Settings**
3. 左侧菜单 → **Developer settings**
4. **Personal access tokens** → **Tokens (classic)**
5. **Generate new token**
6. 在 "Note" 输入：`personal-quant-lab-release`
7. 在 "Expiration" 选择：**90 days** 或更长
8. 在 "Select scopes" 勾选：**repo**（完整的仓库访问权限）
9. 点击 **Generate token**
10. **复制显示的 Token**（只会显示一次！）

以后上传代码时：
- 用户名：你的 GitHub 用户名
- 密码：粘贴这个 Token

---

### **第 5 步：创建发布版本**

#### 5A. 创建标签（在 PowerShell 中）

```powershell
# 仍在 D:\MyQuantProject 目录下

# 创建版本标签
git tag -a v2026.0.0 -m "Release version 2026.0.0"

# 上传标签到 GitHub
git push origin v2026.0.0
```

#### 5B. 在 GitHub 网页上创建 Release

1. 访问你的仓库：`https://github.com/YOUR_NAME/personal-quant-lab`
2. 点击右侧的 **Releases**
3. 点击 **Create a new release**
4. 在 "Choose a tag" 选择：**v2026.0.0**
5. 在 "Release title" 输入：`Personal Quant Lab v2026.0.0`
6. 在 "Describe this release" 输入（简单版）：

```markdown
# Personal Quant Lab v2026.0.0

## ✨ Features
- Parameterized backtesting engine
- Interactive Streamlit GUI
- Company information management
- Integer share trading logic
- Benchmark comparison (NASDAQ & S&P 500)
- Bilingual documentation (English & Chinese)

## 🚀 Installation
```bash
git clone https://github.com/YOUR_NAME/personal-quant-lab.git
cd personal-quant-lab
pip install -r requirements.txt
python run_gui.py
```

## 📚 Documentation
See [README.md](README.md) for complete documentation.

## License
MIT License
```

7. 点击 **Publish release** ✅

**完成！你的项目已发布！**

---

## ✅ 验证发布是否成功

访问这个网址（替换 YOUR_NAME）：
```
https://github.com/YOUR_NAME/personal-quant-lab
```

你应该看到：
- ✅ 所有文件列表
- ✅ README.md 的内容显示在页面下方
- ✅ 右侧有 "Latest release" 显示 v2026.0.0

如果看到这些，说明发布成功了！🎉

---

## 🆘 常见问题速答

### Q1：Git 命令不工作
**A**：确保已安装 Git 且 PowerShell 已重启

### Q2：说找不到文件
**A**：确保 `cd D:\MyQuantProject` 正确（替换为你的实际路径）

### Q3：说仓库已存在
**A**：输入 `git remote remove origin` 然后重新 `git remote add origin https://...`

### Q4：密码/Token 错了
**A**：
- 如果多次失败，删除 Windows 凭证管理器中的 Git 凭证
- 创建新的 Personal Access Token 重试

### Q5：不小心提交了不想要的文件
**A**：
```powershell
# 撤销上一次提交（向后一步）
git reset --soft HEAD~1

# 编辑 .gitignore 忽略不想要的文件
# 然后重新提交
git add .
git commit -m "feat: Initial commit - Personal Quant Lab v2026.0.0"
git push -u origin main
```

---

## 💡 PowerShell 小技巧

### 查看当前目录
```powershell
pwd
```

### 列出文件夹内的文件
```powershell
ls
```

### 返回上一级目录
```powershell
cd ..
```

### 进入 D 盘
```powershell
cd D:\
```

---

## 📚 完整流程一览表

| 步骤 | 操作 | 完成标志 |
|------|------|---------|
| 1 | 安装 Git | `git --version` 显示版本号 |
| 2 | 配置身份 | PowerShell 无错误消息 |
| 3 | 创建 GitHub 仓库 | 看到空仓库页面 |
| 4 | 上传代码 | PowerShell 显示 "✓" 或绿色成功消息 |
| 5A | 创建标签 | 无错误消息 |
| 5B | 创建 Release | GitHub 页面显示 Release |
| ✅ | 验证 | 可以看到所有文件和 README |

---

## 🎯 每步的确切命令（复制粘贴即可）

### **一次性配置（仅第一次）**
```powershell
git config --global user.name "Zhang San"
git config --global user.email "zhangsan@gmail.com"
```

### **首次上传代码**
```powershell
cd D:\MyQuantProject
git init
git add .
git commit -m "feat: Initial commit - Personal Quant Lab v2026.0.0"
git remote add origin https://github.com/YOUR_NAME/personal-quant-lab.git
git branch -M main
git push -u origin main
```

### **创建发布版本**
```powershell
cd D:\MyQuantProject
git tag -a v2026.0.0 -m "Release version 2026.0.0"
git push origin v2026.0.0
```

### **后续推送更新**
```powershell
cd D:\MyQuantProject
git add .
git commit -m "fix: Fixed backtest bug"
git push origin main
```

---

## 🎊 恭喜你！

你现在拥有：
- ✅ GitHub 上的公开项目
- ✅ 版本控制和历史追踪
- ✅ 第一个官方 Release
- ✅ 漂亮的项目主页（README 展示）

**就这么简单！** 🚀

---

## 📖 想了解更多？

- **详细教程**：[DETAILED_GITHUB_TUTORIAL.md](DETAILED_GITHUB_TUTORIAL.md)
- **快速参考**：[GITHUB_QUICK_REFERENCE.md](GITHUB_QUICK_REFERENCE.md)
- **发布清单**：[GITHUB_RELEASE_CHECKLIST.md](GITHUB_RELEASE_CHECKLIST.md)

---

**需要帮助？重新读上面相关的部分，或者在项目 Issues 里提问！**
