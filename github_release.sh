#!/bin/bash
# Personal Quant Lab - GitHub Release Helper Script
# 个人量化实验室 - GitHub 发布辅助脚本

# 配置变量 (Configure these)
GITHUB_USERNAME="yourusername"
GITHUB_REPO="personal-quant-lab"
VERSION="2026.0.0"
RELEASE_DATE="$(date '+%Y-%m-%d')"

echo "=========================================="
echo "Personal Quant Lab - GitHub Release Helper"
echo "=========================================="
echo ""
echo "Configuration | 配置:"
echo "- GitHub Username: $GITHUB_USERNAME"
echo "- Repository: $GITHUB_REPO"
echo "- Version: $VERSION"
echo "- Release Date: $RELEASE_DATE"
echo ""

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查 Git 是否已安装
if ! command -v git &> /dev/null; then
    echo -e "${RED}❌ Git not found. Please install Git first.${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: 检查项目文件${NC}"
echo "Checking required files..."

files_to_check=(
    "README.md"
    "setup.py"
    "pyproject.toml"
    "requirements.txt"
    "LICENSE"
    "CHANGELOG.md"
    "CONTRIBUTING.md"
    ".gitignore"
)

for file in "${files_to_check[@]}"; do
    if [ -f "$file" ]; then
        echo -e "${GREEN}✅ $file${NC}"
    else
        echo -e "${RED}❌ $file (missing)${NC}"
    fi
done

echo ""
echo -e "${YELLOW}Step 2: Git 初始化${NC}"

if [ -d ".git" ]; then
    echo -e "${GREEN}✅ Git repository already initialized${NC}"
else
    echo "Initializing git repository..."
    git init
fi

echo ""
echo -e "${YELLOW}Step 3: 添加所有文件${NC}"
git add .
echo -e "${GREEN}✅ Files staged${NC}"

echo ""
echo -e "${YELLOW}Step 4: 首次 Commit${NC}"
git config --global user.email "your@email.com" 2>/dev/null
git config --global user.name "Your Name" 2>/dev/null

# 检查是否已有 commit
if git rev-parse --git-dir > /dev/null 2>&1; then
    if [ -z "$(git log --oneline -1 2>/dev/null)" ]; then
        git commit -m "feat: Initial commit - Personal Quant Lab v${VERSION}"
        echo -e "${GREEN}✅ Initial commit created${NC}"
    else
        echo -e "${GREEN}✅ Repository already has commits${NC}"
    fi
fi

echo ""
echo -e "${YELLOW}Step 5: 添加远程仓库${NC}"
echo "Please create a repository on GitHub first:"
echo "https://github.com/new"
echo ""
echo "Repository name: $GITHUB_REPO"
echo "Make sure it's PUBLIC"
echo ""
echo "Then run:"
echo "git remote add origin https://github.com/$GITHUB_USERNAME/$GITHUB_REPO.git"
echo "git branch -M main"
echo "git push -u origin main"
echo ""

echo -e "${YELLOW}Step 6: 创建发布标签${NC}"
echo "Running: git tag -a v${VERSION} -m \"Release version ${VERSION}\""
git tag -a v${VERSION} -m "Release version ${VERSION}" 2>/dev/null || echo "Tag already exists"
echo -e "${GREEN}✅ Tag created: v${VERSION}${NC}"

echo ""
echo -e "${YELLOW}Step 7: 生成摘要${NC}"
echo "Release Summary Created:"
echo "- Version: v${VERSION}"
echo "- Release Date: ${RELEASE_DATE}"
echo "- GitHub Repo: https://github.com/$GITHUB_USERNAME/$GITHUB_REPO"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ Pre-release Steps Complete!${NC}"
echo "=========================================="
echo ""
echo "Next steps (手动操作):"
echo "1. Push to GitHub:"
echo "   git remote add origin https://github.com/$GITHUB_USERNAME/$GITHUB_REPO.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo "   git push origin v${VERSION}"
echo ""
echo "2. Create Release on GitHub:"
echo "   - Go to: https://github.com/$GITHUB_USERNAME/$GITHUB_REPO/releases/new"
echo "   - Tag version: v${VERSION}"
echo "   - Title: Personal Quant Lab v${VERSION}"
echo "   - Description: Copy from RELEASE_v${VERSION}.md"
echo "   - Click: Publish release"
echo ""
echo "3. (Optional) Publish to PyPI:"
echo "   pip install twine build"
echo "   python -m build"
echo "   twine upload dist/*"
echo ""
echo -e "${GREEN}Congratulations! 🎉${NC}"
echo ""
