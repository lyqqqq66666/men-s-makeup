# Git备份与项目上传计划

> 目标：修复 .gitignore，将完整前后端代码上传到 GitHub
> 仓库：https://github.com/lyqqqq66666/men-s-makeup

---

## 1. 问题分析

### 当前 .gitignore 问题

```gitignore
# 问题行（导致后端代码无法上传）：
backend/      ← 忽略了整个后端目录
*.py          ← 忽略了所有Python文件
```

### 需要保留的忽略项

| 忽略项 | 原因 |
|--------|------|
| `node_modules/` | 前端依赖，体积大，可重新安装 |
| `.venv/` | Python虚拟环境，可重建 |
| `__pycache__/` | Python缓存，自动生成 |
| `*.pyc` | Python编译缓存 |
| `dist/` | 前端构建产物，可重新构建 |
| `.env` | 环境变量，可能含敏感信息 |
| `*.db` | 数据库文件，用户数据 |
| `database/images/outputs/` | 生成的图片，运行时产生 |
| `database/debug_rois/` | 调试图片，运行时产生 |

### 需要上传的后端代码

| 目录/文件 | 说明 |
|-----------|------|
| `backend_new/` | 新版后端代码（FastAPI） |
| `backend/*.py` | 旧版后端Python文件 |
| `backend/database/schema.sql` | 数据库结构 |
| `requirements.txt` | Python依赖（如存在） |

---

## 2. 修改方案

### 新的 .gitignore 内容

```gitignore
# ===== 前端 =====
node_modules/
dist/
dist-ssr/
*.local

# ===== Python =====
.venv/
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
*.egg-info/
.eggs/
*.egg

# ===== 数据库与运行时文件 =====
*.db
*.db-journal
backend/database/images/
backend_new/database/images/

# ===== 环境变量与敏感信息 =====
.env
.env.local
.env.*.local
*.pem
*.key

# ===== 日志 =====
logs/
*.log
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# ===== 编辑器与系统 =====
.vscode/
.idea/
.DS_Store
Thumbs.db
*.suo
*.ntvs*
*.njsproj
*.sln
*.sw?

# ===== 临时文件 =====
*.tmp
*.temp
.cache/

# ===== 测试与覆盖率 =====
coverage/
.coverage
htmlcov/

# ===== 文档（可选保留）=====
# *.docx
# *.pdf
```

---

## 3. 执行步骤

### 步骤 1：修改 .gitignore
- 删除 `backend/` 和 `*.py` 忽略规则
- 添加正确的忽略规则

### 步骤 2：初始化 Git（如未初始化）
```bash
cd /Users/LYQ/Desktop/大三资料/我的vibe-coding项目/Trae挑战赛/MenX/智颜方正—智能图像矫正与风格男妆生成系统
git init
```

### 步骤 3：添加远程仓库
```bash
git remote add origin https://github.com/lyqqqq66666/men-s-makeup.git
git fetch origin
```

### 步骤 4：添加所有文件
```bash
git add .
```

### 步骤 5：提交
```bash
git commit -m "feat: 添加完整前后端代码

- 前端: Vue 3 + TypeScript
- 后端: FastAPI + Python
- 数据库: SQLite (23张表)
- 商品数据: 184 SKU
- 文档: PRD + Agent规范 + 计划"
```

### 步骤 6：推送（强制覆盖或合并）
```bash
# 方案A：强制覆盖（如果旧仓库可以丢弃）
git push -f origin main

# 方案B：合并（如果保留旧提交历史）
git pull origin main --allow-unrelated-histories
git push origin main
```

---

## 4. 验证清单

- [ ] `.gitignore` 修改完成
- [ ] `backend_new/` 目录被 git 追踪
- [ ] `*.py` 文件被 git 追踪
- [ ] `node_modules/` 未被追踪
- [ ] `.venv/` 未被追踪
- [ ] `*.db` 未被追踪
- [ ] GitHub 仓库显示完整代码

---

## 5. 注意事项

1. **数据库文件**：`*.db` 被忽略，不会上传用户数据
2. **环境变量**：`.env` 被忽略，敏感信息不会泄露
3. **依赖目录**：`node_modules/` 和 `.venv/` 不上传，需用户自行安装

---

## 6. 后续操作

完成 Git 备份后，我可以开始：
1. 运行种子数据脚本，导入商品数据
2. 检查并修复后端代码
3. 完善项目文档

**您确认后，我将执行上述步骤。**
