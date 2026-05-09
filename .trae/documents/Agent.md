# 颜选MenX——男士个性化试妆与美妆智选平台 - AI Agent 项目规范

> 基于 Harness Engineering 框架的 AI 驱动开发规范
> 版本: 1.0.0
> 日期: 2026-05-09

---

## 1. 项目概述

### 1.1 产品定位
**颜选MenX——男士个性化试妆与美妆智选平台** 是一款专为 18-35 岁男性设计的智能图像矫正与风格男妆生成系统，解决男性化妆入门难题，提供：
- 智能人脸矫正与模糊检测
- PCA 季型色彩分析
- 虚拟试妆（风格/局部）
- 个性化产品推荐
- 妆容方案保存与分享

### 1.2 目标用户
- **核心用户**: 18-35 岁男性，对形象管理有需求但缺乏化妆经验
- **使用场景**: 职场面试、约会社交、日常通勤、重要场合

### 1.3 核心价值主张
> "让每位男性都能轻松拥有得体妆容，展现最佳形象"

---

## 2. Harness Engineering 框架

### 2.1 框架理念
Harness Engineering 是一种 AI 原生开发方法论，强调：
- **Human-in-the-loop**: 人类决策 + AI 执行
- **Explicit Context**: 明确的上下文管理
- **Measurable Output**: 可衡量的输出质量
- **Continuous Verification**: 持续验证与迭代

### 2.2 核心原则

```
┌─────────────────────────────────────────────────────────────┐
│                    Harness Engineering                      │
├─────────────────────────────────────────────────────────────┤
│  1. CONTEXT FIRST    →  完整上下文传递，避免信息丢失        │
│  2. EXPLICIT SPEC    →  明确规格，消除歧义                  │
│  3. VERIFIABLE OUT   →  可验证的输出，确保质量              │
│  4. ITERATIVE REFINE →  迭代优化，持续改进                  │
│  5. KNOWLEDGE REUSE  →  知识复用，避免重复                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 3. 项目结构规范

### 3.1 目录结构

```
颜选MenX——男士个性化试妆与美妆智选平台—智能图像矫正与风格男妆生成系统/
├── .trae/                          # AI 工作区
│   ├── documents/                  # 项目文档
│   │   ├── Agent.md               # 本文件：项目规范
│   │   ├── Plan.md                # 项目计划
│   │   └── Tasks.md               # 任务追踪
│   └── prompts/                    # 复用 Prompt 模板
│
├── src/                            # 前端源码 (Vue 3 + TypeScript)
│   ├── api/                        # API 接口定义
│   ├── assets/                     # 静态资源
│   ├── components/                 # 通用组件
│   ├── router/                     # 路由配置
│   ├── store/                      # 状态管理
│   ├── utils/                      # 工具函数
│   ├── views/                      # 页面视图
│   ├── App.vue
│   └── main.ts
│
├── backend_new/                    # 后端源码 (FastAPI + Python)
│   ├── database/                   # 数据库文件
│   │   ├── schema.sql             # 数据库结构
│   │   └── app_data.db            # SQLite 数据库
│   ├── fastapi_app.py             # FastAPI 主应用
│   ├── db_manager.py              # 数据库管理
│   ├── makeup_gan.py              # 妆容生成算法
│   ├── face_detection.py          # 人脸检测
│   ├── face_correction.py         # 人脸矫正
│   ├── blur_detection.py          # 模糊检测
│   └── ...
│
├── data/                           # 数据资源
│   ├── products/                   # 商品数据
│   ├── tutorials/                  # 化妆教程
│   └── color_palettes/            # 色号数据
│
├── memory/                         # 项目记忆
│   └── *.md                        # 需求文档、修改记录
│
├── dist/                           # 构建输出
├── index.html
├── package.json
└── README.md
```

### 3.2 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件/目录 | kebab-case | `fastapi-app.py`, `user-profile.ts` |
| 组件名 | PascalCase | `ImageUpload.vue`, `MakeupEngine.ts` |
| 函数/变量 | camelCase | `applyMakeup()`, `userId` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRY_COUNT`, `API_BASE_URL` |
| 数据库表 | snake_case | `product_sku`, `makeup_sessions` |
| API 端点 | kebab-case | `/api/makeup/apply`, `/api/user/profile` |

---

## 4. 开发工作流

### 4.1 任务生命周期

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  需求分析 │ → │  方案设计 │ → │  代码实现 │ → │  测试验证 │ → │  部署上线 │
│  (Plan)  │    │  (Spec)  │    │  (Code)  │    │  (Test)  │    │ (Deploy) │
└──────────┘    └──────────┘    └──────────┘    └──────────┘    └──────────┘
      ↑                                                            │
      └──────────────────────── 迭代优化 ←──────────────────────────┘
```

### 4.2 AI 协作模式

#### 模式 A: 自主执行 (Autonomous)
适用于: 明确的编码任务、数据迁移、文档生成
```
用户: "实现购物车接口的批量删除功能"
AI:  直接编写代码 → 运行测试 → 提交结果
```

#### 模式 B: 协作设计 (Collaborative)
适用于: 架构决策、复杂功能设计、方案评审
```
用户: "如何优化试妆渲染的性能？"
AI:  分析现状 → 提出方案 → 讨论决策 → 执行实现
```

#### 模式 C: 辅助咨询 (Advisory)
适用于: 技术选型、问题排查、最佳实践
```
用户: "应该选择哪种图像压缩算法？"
AI:  提供对比分析 → 给出建议 → 等待用户决策
```

### 4.3 代码审查清单

- [ ] 功能完整性：是否满足需求规格
- [ ] 代码质量：可读性、可维护性
- [ ] 性能影响：时间/空间复杂度
- [ ] 安全考虑：输入验证、权限控制
- [ ] 测试覆盖：单元测试、集成测试
- [ ] 文档更新：API 文档、注释

---

## 5. 数据规范

### 5.1 商品数据结构

```typescript
// SKU (Stock Keeping Unit) - 最小库存单元
interface ProductSKU {
  sku_id: string;              // 唯一标识: "lip_001_rose"
  spu_id: string;              // 所属系列: "lip_001"
  shade_name: string;          // 色号名: "玫瑰豆沙"
  hex_color: string;           // 原始色值: "#B14A5A"
  render_hex: string;          // 渲染色值: "#A84558"
  render_mode: number;         // 渲染模式: 0=叠加, 1=混合
  finish_type: string;         // 妆效: "matte" | "glossy" | "natural"
  opacity: number;             // 透明度: 0.0 - 1.0
  feather: number;             // 羽化程度: 0 - 100
  apply_area: string;          // 上妆区域: "lips" | "eyes" | "brow" | "skin" | "cheeks"
  category: string;            // 品类: "lip" | "eye" | "brow" | "base" | "contour"
  price: number;               // 价格
  season_match: string;        // 适配季型: "Warm Autumn"
  brand: string;               // 品牌
}

// SPU (Standard Product Unit) - 标准化产品单元
interface ProductSPU {
  spu_id: string;              // 唯一标识
  brand: string;               // 品牌
  product_name: string;        // 产品名
  category: string;            // 品类
  apply_area: string;          // 上妆区域
  image_url: string;           // 商品图
}
```

### 5.2 色号标准库

```typescript
// 男士专用色号定义
const MEN_MAKEUP_PALETTE = {
  // 唇部
  lip: {
    natural: ["#C98B7B", "#B87A6A", "#A86959"],      // 自然裸色
    rose: ["#B14A5A", "#A84558", "#9F3F52"],         // 玫瑰豆沙
    coral: ["#E07A5F", "#D06A50", "#C05A40"],        // 珊瑚橘
  },
  // 眉部
  brow: {
    black: ["#2C2C2C", "#1A1A1A", "#0D0D0D"],        // 自然黑
    brown: ["#4A3728", "#5C4033", "#6B4423"],        // 深棕
    gray: ["#5A5A5A", "#696969", "#787878"],         // 灰棕
  },
  // 底妆
  base: {
    ivory: "#F5E6D3",        // 象牙白
    natural: "#E8D4C4",      // 自然色
    wheat: "#D4B896",        // 小麦色
  }
};
```

### 5.3 季型色彩映射

```typescript
const SEASON_COLOR_MAP = {
  "Warm Spring": {
    recommended: ["#F2A65A", "#E27D60", "#E8B04F"],
    avoid: ["#9BA7C0", "#8FA1BF", "#6C7A89"]
  },
  "Warm Autumn": {
    recommended: ["#C68642", "#8B4513", "#A0522D"],
    avoid: ["#E6E6FA", "#87CEEB", "#B0C4DE"]
  },
  "Cool Summer": {
    recommended: ["#7D8FB3", "#A58AB5", "#6D9DC5"],
    avoid: ["#D8A47F", "#C97A63", "#B76E5D"]
  },
  "Cool Winter": {
    recommended: ["#6A5ACD", "#8A2BE2", "#5F9EA0"],
    avoid: ["#FFDAB9", "#F4A460", "#D2B48C"]
  }
};
```

---

## 6. API 设计规范

### 6.1 统一响应格式

```typescript
// 成功响应
interface SuccessResponse<T> {
  code: 0;
  message: "success";
  data: T;
}

// 错误响应
interface ErrorResponse {
  code: number;           // HTTP 状态码或业务码
  message: string;        // 错误描述
  data: null;
  error_code: string;     // 错误类型标识
}
```

### 6.2 接口命名规范

| 操作 | HTTP 方法 | URL 模式 | 示例 |
|------|-----------|----------|------|
| 查询列表 | GET | `/api/{resource}` | `GET /api/products` |
| 查询详情 | GET | `/api/{resource}/{id}` | `GET /api/products/lip_001` |
| 创建 | POST | `/api/{resource}` | `POST /api/products` |
| 更新 | PUT | `/api/{resource}/{id}` | `PUT /api/products/lip_001` |
| 删除 | DELETE | `/api/{resource}/{id}` | `DELETE /api/products/lip_001` |
| 动作 | POST | `/api/{resource}/{action}` | `POST /api/makeup/apply` |

### 6.3 分页规范

```typescript
interface PaginationParams {
  page: number;        // 页码，从 1 开始
  page_size: number;   // 每页数量，默认 20
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}
```

---

## 7. 算法模块规范

### 7.1 妆容渲染流程

```
输入图片
    ↓
人脸检测 (MediaPipe Face Mesh - 468 关键点)
    ↓
区域提取 (唇部/眼部/眉部/面部轮廓)
    ↓
色彩映射 (根据 SKU 的 hex_color + render_mode)
    ↓
羽化融合 (feather 参数控制边缘过渡)
    ↓
透明度调整 (opacity 参数控制强度)
    ↓
输出渲染图
```

### 7.2 渲染参数说明

| 参数 | 范围 | 说明 |
|------|------|------|
| `opacity` | 0.0 - 1.0 | 妆容透明度，值越大颜色越明显 |
| `feather` | 0 - 100 | 羽化半径，值越大边缘越柔和 |
| `render_mode` | 0 / 1 | 0=颜色叠加，1=柔光混合 |
| `transparency_max` | 0.0 - 1.0 | 最大透明度限制 |

### 7.3 PCA 季型分析

```python
# 特征向量定义
PCA_FEATURES = [
    "skin_r", "skin_g", "skin_b",      # 肤色 RGB
    "hair_r", "hair_g", "hair_b",      # 发色 RGB
]

# 季型分类
SEASON_TYPES = [
    "Warm Spring",   # 暖春
    "Warm Autumn",   # 暖秋
    "Cool Summer",   # 冷夏
    "Cool Winter",   # 冷冬
]
```

---

## 8. 前端开发规范

### 8.1 组件设计原则

- **单一职责**: 每个组件只做一件事
- **Props 向下传递**: 数据通过 props 向下流动
- **事件向上抛出**: 通过 emit 向上通知
- **Composition API**: 优先使用 `<script setup>` 语法

### 8.2 状态管理

```typescript
// Pinia Store 结构
import { defineStore } from 'pinia'

export const useUserStore = defineStore('user', {
  state: () => ({
    userInfo: null,
    token: null,
    isLoggedIn: false
  }),
  
  getters: {
    hasSeasonType: (state) => !!state.userInfo?.season_type
  },
  
  actions: {
    async login(credentials) {
      // 登录逻辑
    },
    logout() {
      // 登出逻辑
    }
  }
})
```

### 8.3 样式规范

- 使用 Tailwind CSS 进行原子化样式
- 组件级样式使用 scoped
- 主题色通过 CSS 变量定义

```css
:root {
  --color-primary: #3B82F6;
  --color-secondary: #10B981;
  --color-accent: #F59E0B;
  --color-background: #F9FAFB;
  --color-text: #1F2937;
}
```

---

## 9. 后端开发规范

### 9.1 FastAPI 项目结构

```python
# 路由分组
from fastapi import APIRouter

auth_router = APIRouter(prefix="/api/auth", tags=["认证"])
user_router = APIRouter(prefix="/api/user", tags=["用户"])
makeup_router = APIRouter(prefix="/api/makeup", tags=["试妆"])
product_router = APIRouter(prefix="/api/products", tags=["商品"])

# 依赖注入
async def get_current_user(token: str = Depends(oauth2_scheme)):
    # 验证 token 并返回用户信息
    pass

# 接口定义
@makeup_router.post("/apply")
async def apply_makeup(
    data: MakeupApplyRequest,
    user: User = Depends(get_current_user)
):
    """应用妆容"""
    pass
```

### 9.2 数据库操作规范

```python
# 使用参数化查询防止 SQL 注入
query = """
    SELECT * FROM product_sku 
    WHERE category = ? AND season_match = ?
"""
results = db.execute(query, (category, season_type))

# 事务处理
with db.transaction():
    db.execute("INSERT INTO ...", params)
    db.execute("UPDATE ...", params)
```

### 9.3 错误处理

```python
from fastapi import HTTPException

class BusinessError(HTTPException):
    def __init__(self, code: int, message: str, error_code: str):
        super().__init__(
            status_code=code,
            detail={
                "code": code,
                "message": message,
                "error_code": error_code,
                "data": None
            }
        )

# 使用示例
if not product:
    raise BusinessError(
        code=404,
        message="商品不存在",
        error_code="PRODUCT_NOT_FOUND"
    )
```

---

## 10. 数据爬取规范

### 10.1 爬虫开发原则

1. **遵守 robots.txt**: 尊重网站的爬虫协议
2. **控制请求频率**: 避免对目标网站造成压力
3. **数据清洗**: 爬取后进行数据验证和清洗
4. **增量更新**: 支持增量爬取，避免重复数据

### 10.2 目标数据源

| 数据类型 | 目标网站 | 数据内容 |
|----------|----------|----------|
| 产品信息 | 天猫、京东 | 男士化妆品 SKU、价格、色号 |
| 色号数据 | 品牌官网 | 官方色号名称、HEX 值 |
| 教程内容 | B站、小红书 | 男士化妆教程步骤 |
| 用户评价 | 电商平台 | 产品评价、使用反馈 |

### 10.3 数据存储格式

```json
{
  "source": "tmall",
  "crawl_time": "2026-05-09T10:00:00Z",
  "data": {
    "sku_id": "lip_001",
    "name": "男士润色唇膏",
    "brand": "品牌名",
    "category": "lip",
    "price": 89.0,
    "shade_name": "自然裸色",
    "hex_color": "#C98B7B",
    "images": ["url1", "url2"],
    "description": "产品描述"
  }
}
```

---

## 11. 测试规范

### 11.1 测试金字塔

```
        /\
       /  \
      / E2E \          # 端到端测试 (少量)
     /--------\
    /  Integration \    # 集成测试 (中等)
   /----------------\
  /    Unit Tests     \ # 单元测试 (大量)
 /----------------------\
```

### 11.2 测试命名规范

```python
# 单元测试
def test_apply_makeup_with_valid_sku():
    """测试使用有效 SKU 应用妆容"""
    pass

def test_apply_makeup_with_invalid_sku_raises_error():
    """测试使用无效 SKU 时抛出异常"""
    pass

# 集成测试
def test_makeup_session_full_flow():
    """测试完整试妆流程"""
    pass
```

### 11.3 关键测试场景

- [ ] 人脸检测：不同角度、光线条件
- [ ] 妆容渲染：各部位、各风格
- [ ] 推荐算法：季型匹配准确性
- [ ] 性能测试：图片处理响应时间
- [ ] 并发测试：多用户同时试妆

---

## 12. 部署规范

### 12.1 环境定义

| 环境 | 用途 | 数据库 |
|------|------|--------|
| local | 本地开发 | SQLite |
| dev | 开发测试 | SQLite / PostgreSQL |
| staging | 预发布 | PostgreSQL |
| prod | 生产环境 | PostgreSQL |

### 12.2 环境变量

```bash
# 数据库
DATABASE_URL=sqlite:///./app_data.db

# 安全
SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# 功能开关
MODEL_PREFLIGHT_ON_BOOT=1
MAKEUP_SESSION_TTL_HOURS=24

# 外部服务
# SMS_API_KEY=xxx
# OSS_ENDPOINT=xxx
```

### 12.3 部署检查清单

- [ ] 环境变量配置正确
- [ ] 数据库迁移完成
- [ ] 静态资源构建成功
- [ ] API 文档可访问
- [ ] 健康检查接口正常
- [ ] 日志收集配置完成

---

## 13. 文档维护

### 13.1 文档更新触发条件

- 新增/修改 API 接口 → 更新 API 文档
- 数据库结构变更 → 更新数据库文档
- 算法逻辑调整 → 更新算法说明
- 项目结构变化 → 更新本规范

### 13.2 文档版本控制

```markdown
## 变更日志

### v1.0.0 (2026-05-09)
- 初始版本
- 定义项目结构和开发规范

### v1.1.0 (待定)
- 新增推荐算法规范
- 完善数据爬取规范
```

---

## 14. 附录

### 14.1 常用命令

```bash
# 前端开发
npm install
npm run dev
npm run build

# 后端开发
python backend_new/fastapi_app.py

# 数据库
sqlite3 backend_new/database/app_data.db < backend_new/database/schema.sql

# 测试
pytest tests/
```

### 14.2 参考资源

- [Vue 3 文档](https://vuejs.org/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [MediaPipe Face Mesh](https://developers.google.com/mediapipe/solutions/vision/face_landmarker)
- [Tailwind CSS](https://tailwindcss.com/)

### 14.3 联系方式

- 项目负责人: [待填写]
- 技术负责人: [待填写]
- 产品负责人: [待填写]

---

> **注意**: 本文档是活文档，会根据项目发展持续更新。任何变更请通过 PR 流程提交。
