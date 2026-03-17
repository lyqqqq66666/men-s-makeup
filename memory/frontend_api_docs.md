# 智颜方正 - 前端功能与后端接口规格说明书 v1.0

本档旨在总结“智颜方正”系统当前前端已实现的功能，并定义后端需配合的接口。文档按功能模块划分，包含接口路径、请求方法、输入参数及响应说明。

---

## 1. 用户与个人中心模块 (User & Profile)

### 1.1 用户登录 / 注册 / 找回密码
- **登录**: `POST /auth/login`
- **注册**: `POST /auth/register`
- **找回密码 (重置)**: `POST /auth/reset-password`
    - **输入**:
      ```json
      {
        "phone": "string",
        "code": "string",
        "newPassword": "string"
      }
      ```
- **发送验证码**: `POST /auth/send-code`
    - **参数**: `{ "phone": "string", "type": "register | login | resetPwd" }`
- **退出登录**: `POST /auth/logout`

### 1.2 个人档案与诊断记录
- **获取当前用户信息 (GET)**: `GET /auth/userInfo`
    - **核心逻辑**: 用于在用户进入“个人中心”或重新进入页面时，获取最新的头像、昵称、手机号以及**最近一次 PCA 季型结论**。
    - **响应示例**:
      ```json
      {
        "nickname": "智颜体验师",
        "avatar": "url",
        "phone": "138****",
        "season_type": "warm_autumn",
        "last_diagnostic_date": "2024-03-13"
      }
      ```
- **修改个人资料**: `PUT /user/profile`
    - **参数**: `{ "nickname": "string", "avatar": "string" }`
- **最近诊断历史**: `GET /user/history`
    - **功能**: 获取用户上传的照片记录及对应的诊断状态（如：已诊断-暖秋型/待诊断）。

### 1.3 方案归档库 (Makeup Plans)
- **主要功能**: 用户可保存满意的妆容效果为“方案”，支持按场景（面试、约会等）分类。
- **接口路径**:
    - `POST /api/makeup/plan/save`: 保存方案。
    - `GET /api/makeup/plans`: 获取方案列表。
- **方案字段需求**:
    - `name`: 方案名称
    - `scene_tag`: 场景标签 (如: 商务稳重, 日常通勤)
    - `image_id`: 封面图 ID
    - `configuration`: 包含所选的所有 SKU/产品 ID 及其渲染参数
    - `recommend_reason`: 系统或用户记录的推荐理由

---

## 2. 核心图像处理与 PCA 诊断 (Image & PCA)

### 2.1 图像预处理
- **接口路径**: 
    - `/api/image/detect-face`: 人脸识别与关键点检测。
    - `/api/image/detect-blur`: 图片模糊度检测。
    - `/api/image/smart-correct`: 智能图像矫正（光影、角度）。
- **方法**: `POST (multipart/form-data)`
- **核心逻辑**: 后端需对原始照片进行质量评估，确保后续 PCA 和试妆的准确度。

### 2.2 色彩诊断 (Color PCA)
- **主要功能**: 基于用户上传的矫正后图片，分析其肤色、瞳孔色等，给出季型结论。
- **接口路径**: `POST /api/pca/analyze_color_type`
- **响应数据建议**:
    ```json
    {
      "season_type": "warm_autumn", 
      "color_palette": ["hex1", "hex2", ...],
      "analysis_report": "分析文案",
      "recommended_styles": ["轻熟职场", "面试清爽"]
    }
    ```

---

## 3. 试妆渲染引擎 (Makeup Engine)

### 3.1 渲染执行
- **接口路径**:
    - `/api/makeup/apply-style`: **一键渲染**。根据模板 ID/名称应用整套妆效。
    - `/api/makeup/apply-step`: **分步试妆**。按部位（底妆、眉笔、唇色）叠加效果。
- **分步请求参数**:
    ```json
    {
      "image_id": "string",
      "step": "base | eyebrow | eye | contour | lip",
      "product_id": "number/string"
    }
    ```

### 3.2 操作管理
- **功能点**: 支持撤销上一步、重置为初始状态、一键卸妆。
- **接口需求**: 需后端支持 Session 机制或记录渲染链路，以便快速返回上一阶段的图片 URL。

---

## 4. 个性化商城与推荐系统 (Shop & Recommendation)

### 4.1 个性化商品列表
- **主要功能**: 基于 PCA 诊断结果的商品展示。
- **接口路径**: `GET /api/pca/recommend_products`
- **核心逻辑**: 前端传入 `season` 分类，后端返回符合该季型的 SKU 列表。
- **卡片数据扩展**: SKU 需包含 `tags`（如: PCA推荐, 新手友好）、`color_hex`（色号预览）。

### 4.2 购物车与推荐组合
- **主要功能**: 普通单品加入购物车，以及推荐引擎的“一键购齐”功能。
- **接口需求**:
    - `POST /api/cart/add-set`: 支持一次性将某个方案/套装内的所有商品加入购物车。
    - `GET /api/makeup/sets`: 获取系统预置的节气/节日推荐套装。

---
> [!NOTE]
> 以上接口中，`/api/image/*` 和 `/api/pca/*` 对算法精度要求较高，请后端优先保证处理速度并在超时时提供合理的 Pending 状态。
