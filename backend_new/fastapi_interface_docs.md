# FastAPI 接口总览文档

本文档对应当前运行入口 [`backend/fastapi_app.py`](backend/fastapi_app.py:1)。

- OpenAPI 导入地址：[`/openapi.json`](backend/fastapi_app.py:54)
- 文档地址：[`/docs`](backend/fastapi_app.py:53)
- 本地服务地址：`http://127.0.0.1:5001`

> Apipost 推荐直接导入：`http://127.0.0.1:5001/openapi.json`

---

## 1. 统一约定

### 1.1 鉴权

除少数登录/注册/健康检查接口外，均使用：

```http
Authorization: Bearer {{token}}
```

图片访问接口额外支持：

```text
?token={{token}}
```

### 1.2 统一响应格式

成功：

```json
{
  "code": 0,
  "message": "success",
  "data": {}
}
```

失败：

```json
{
  "code": 400,
  "message": "错误说明",
  "data": null,
  "error_code": "INVALID_PARAMS"
}
```

### 1.3 常见状态码

| 状态码 | 含义 |
|---|---|
| `200` | 请求成功 |
| `201` | 创建成功 |
| `400` | 参数错误 |
| `401` | 未登录 / token 无效 |
| `403` | 无权限 |
| `404` | 资源不存在 |
| `422` | FastAPI 参数校验失败 |
| `500` | 服务端异常 |
| `503` | 依赖模型不可用 |

---

## 2. 接口分组总览

| 分组 | 代表接口 |
|---|---|
| 认证 | `/api/auth/send-code`、`/api/auth/register`、`/api/auth/login`、`/api/auth/logout` |
| 用户 | `/api/user/info`、`/api/user/avatar/upload`、`/api/user/images`、`/api/user/preferences` |
| 分析 | `/api/pca/analyze` |
| 推荐 | `/api/recommend/products`、`/api/recommend/bundles`、`/api/pca/personalized_recommendations` |
| 试妆 | `/api/makeup/session`、`/api/makeup/apply`、`/api/makeup/undo`、`/api/makeup/schemes` |
| 购物车 | `/api/cart`、`/api/cart/items`、`/api/cart/bundles` |
| 管理端 | `/api/admin/products` |
| 媒体 | `/api/media/process-upload`、`/api/media/images/output/{filename}` |

---

## 3. 关键接口明细

## 3.1 认证接口

### 3.1.1 发送验证码

- 方法：`POST`
- 路径：`/api/auth/send-code`
- 鉴权：否

请求体：

```json
{
  "phone": "13800138000",
  "type": "register"
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `phone` | string | 是 | 手机号 |
| `type` | string | 是 | `register/login/reset_password` |

预期返回：

```json
{
  "code": 0,
  "message": "验证码发送成功",
  "data": {
    "code_id": "code_xxx",
    "phone": "13800138000",
    "type": "register"
  }
}
```

### 3.1.2 注册

- 方法：`POST`
- 路径：`/api/auth/register`
- 鉴权：否

请求体：

```json
{
  "phone": "13800138000",
  "password": "123456",
  "confirmPassword": "123456",
  "code": "123456"
}
```

### 3.1.3 登录

- 方法：`POST`
- 路径：`/api/auth/login`
- 鉴权：否

密码登录示例：

```json
{
  "phone": "13800138000",
  "password": "123456",
  "loginType": "password"
}
```

验证码登录示例：

```json
{
  "phone": "13800138000",
  "code": "123456",
  "loginType": "code"
}
```

成功返回通常包含：

- `token`
- `user_id`
- `phone`
- `avatar`
- `nickname`

---

## 3.2 用户与个人中心接口

### 3.2.1 获取当前用户信息

- 方法：`GET`
- 路径：`/api/user/info`
- 鉴权：是

请求头：

```http
Authorization: Bearer {{token}}
```

成功返回：

```json
{
  "code": 0,
  "message": "获取用户信息成功",
  "data": {
    "user_id": "user_xxx",
    "phone": "13800138000",
    "nickname": "智颜体验官",
    "avatar": "http://127.0.0.1:5001/api/media/images/avatar/defaults/avatar-default.png?token={{token}}",
    "season_type": "Warm Autumn",
    "last_login_at": "2026-03-18 20:00:00",
    "last_history": {}
  }
}
```

### 3.2.2 上传用户头像

- 方法：`POST`
- 路径：`/api/user/avatar/upload`
- 鉴权：是
- Content-Type：`multipart/form-data`

表单字段：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | file | 是 | 头像图片 |

成功返回：

```json
{
  "code": 0,
  "message": "头像上传成功",
  "data": {
    "user_id": "user_xxx",
    "avatar": "http://127.0.0.1:5001/api/media/images/avatar/avatar/user_xxx/2026/03/18/avatar_user_xxx_xxx.jpg?token={{token}}",
    "biz_type": "avatar",
    "relative_path": "avatar/user_xxx/2026/03/18/avatar_user_xxx_xxx.jpg"
  }
}
```

### 3.2.3 获取用户图片列表

- 方法：`GET`
- 路径：`/api/user/images`
- 鉴权：是

Query 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `limit` | integer | 否 | 返回条数，默认 50 |

返回：

```json
{
  "code": 0,
  "message": "获取图片列表成功",
  "data": {
    "items": [
      {
        "image_id": "img_xxx",
        "image_type": "corrected",
        "file_path": "database/images/outputs/corrected/user_xxx/2026/03/18/demo.jpg",
        "url": "http://127.0.0.1:5001/api/media/images/output/corrected/user_xxx/2026/03/18/demo.jpg?token={{token}}"
      }
    ],
    "count": 1
  }
}
```

### 3.2.4 删除用户图片

- 方法：`DELETE`
- 路径：`/api/user/images/{image_id}`
- 鉴权：是

Path 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `image_id` | string | 是 | 图片主键 |

成功返回：

```json
{
  "code": 0,
  "message": "删除图片成功",
  "data": {
    "image_id": "img_92ff7f4de8024662"
  }
}
```

### 3.2.5 获取用户偏好

- `GET /api/user/preferences`

### 3.2.6 更新用户偏好

- `PUT /api/user/preferences`

请求体示例：

```json
{
  "preferred_scenes": ["日常通勤", "约会氛围"],
  "preferred_categories": ["lip", "brow"],
  "preferred_finishes": ["natural", "matte"],
  "budget_min": 99,
  "budget_max": 299
}
```

---

## 3.3 PCA / 分析接口

### 3.3.1 上传并分析季型

- 方法：`POST`
- 路径：`/api/pca/analyze`
- 鉴权：是
- Content-Type：`multipart/form-data`

表单参数：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `image` | file | 是 | 待分析人脸图片 |
| `user_id` | string | 否 | 可选；若传需与当前 token 一致 |

成功返回会包含：

- `season_type`
- `tone`
- `recommended_colors`
- `avoid_colors`
- `corrected_image`
- `image_id`

### 3.3.2 个性化推荐

- 方法：`GET`
- 路径：`/api/pca/personalized_recommendations`
- 鉴权：是

Query：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `limit` | integer | 否 | 推荐数，默认 10 |

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}` |

预期返回：

```json
{
  "code": 0,
  "message": "获取个性化推荐成功",
  "data": {
    "products": [
      {
        "product_id": "brow_001_brown",
        "name": "深棕立体眉笔",
        "category": "brow",
        "price": 89.0
      }
    ],
    "behavior_snapshot": []
  }
}
```

---

## 3.4 推荐接口

### 3.4.1 推荐商品

- 方法：`GET`
- 路径：`/api/recommend/products`
- 鉴权：是

Query 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `season` | string | 否 | 季型，如 `Warm Autumn` |
| `category` | string | 否 | `base/brow/eye/contour/lip` |
| `limit` | integer | 否 | 条数 |
| `user_id` | string | 否 | 若传入需与当前登录用户一致 |

### 3.4.2 套装推荐

- 方法：`GET`
- 路径：`/api/recommend/bundles`

- 鉴权：是

Query 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `season` | string | 否 | 季型，如 `Warm Autumn` |
| `current_product` | string | 否 | 当前商品 SKU，用于做关联推荐 |
| `user_id` | string | 否 | 若传入需与当前登录用户一致 |

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}` |

预期返回：

```json
{
  "code": 0,
  "message": "获取套装推荐成功",
  "data": {
    "bundle_name": "全套型男方案",
    "products": [],
    "total_price": 0,
    "discount_price": 0,
    "season": "Warm Autumn"
  }
}
```

### 3.4.3 搭配推荐

- 方法：`GET`
- 路径：`/api/recommend/pairs`

- 鉴权：是

Query 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `source_sku_id` | string | 是 | 源商品 SKU |
| `limit` | integer | 否 | 返回条数，默认 6 |

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}` |

---

## 3.5 试妆接口

### 3.5.1 创建试妆会话

- 方法：`POST`
- 路径：`/api/makeup/session`
- 鉴权：是

支持两种请求：

#### A. JSON 模式

```json
{
  "original_image": "http://127.0.0.1:5001/api/media/images/output/corrected/user_xxx/2026/03/18/demo.jpg?token={{token}}"
}
```

#### B. multipart 模式

- `original_image`: 文件
- `user_id_form`: 可选

参数说明：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `original_image` | string / file | 是 | 原图 URL 或文件 |
| `user_id_form` | string | 否 | multipart 模式下的用户 ID，若传需与当前登录用户一致 |

预期返回：

```json
{
  "code": 0,
  "message": "创建试妆会话成功",
  "data": {
    "session_id": "session_abcd1234ef56",
    "original_image": "http://127.0.0.1:5001/api/media/images/output/corrected/user_xxx/...jpg?token={{token}}",
    "current_image": "http://127.0.0.1:5001/api/media/images/output/corrected/user_xxx/...jpg?token={{token}}",
    "applied_products": [],
    "step": 0,
    "status": "active"
  }
}
```

### 3.5.2 应用试妆

- 方法：`POST`
- 路径：`/api/makeup/apply`
- 鉴权：是

#### 风格试妆示例

```json
{
  "session_id": "session_abcd1234ef56",
  "style": "clean"
}
```

#### 局部试妆示例

```json
{
  "session_id": "session_abcd1234ef56",
  "product_id": "lip_002_rose",
  "category": "lip"
}
```

### 3.5.3 撤销 / 重置 / 局部重置

- `POST /api/makeup/undo`
- `POST /api/makeup/reset`
- `POST /api/makeup/reset-part`

共同请求体核心字段：

```json
{
  "session_id": "session_abcd1234ef56"
}
```

补充说明：

- `/api/makeup/reset-part` 额外需要：

```json
{
  "session_id": "session_abcd1234ef56",
  "category": "lip"
}
```

其中 `category` 必须是：`base/brow/eye/contour/lip`

### 3.5.4 保存方案

- 方法：`POST`
- 路径：`/api/makeup/schemes`

```json
{
  "session_id": "session_abcd1234ef56",
  "scheme_name": "通勤妆方案"
}
```

### 3.5.5 获取方案列表

- 方法：`GET`
- 路径：`/api/makeup/schemes`

- 鉴权：是

Query 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `limit` | integer | 否 | 返回条数，默认 50 |
| `user_id` | string | 否 | 若传入需与当前登录用户一致 |

### 3.5.6 获取方案详情

- 方法：`GET`
- 路径：`/api/makeup/schemes/{scheme_id}`

Path 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `scheme_id` | string | 是 | 方案主键 |

### 3.5.7 删除方案

- 方法：`DELETE`
- 路径：`/api/makeup/schemes/{scheme_id}`

Path 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `scheme_id` | string | 是 | 方案主键 |

### 3.5.8 获取试妆会话

- 方法：`GET`
- 路径：`/api/makeup/session/{session_id}`

Path 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `session_id` | string | 是 | 试妆会话 ID |

### 3.5.9 妆容评分

- 方法：`POST`
- 路径：`/api/makeup/score`

请求体：

```json
{
  "session_id": "session_abcd1234ef56"
}
```

---

## 3.6 购物车接口

### 3.6.1 获取购物车

- 方法：`GET`
- 路径：`/api/cart`

- 鉴权：是

返回结构：

```json
{
  "code": 0,
  "message": "获取购物车成功",
  "data": {
    "user_id": "user_xxx",
    "items": [
      {
        "product_id": "brow_001_brown",
        "name": "深棕立体眉笔",
        "quantity": 2,
        "price": 89.0
      }
    ],
    "summary": {
      "item_count": 1,
      "total_quantity": 2,
      "total_amount": 178.0
    }
  }
}
```

### 3.6.2 加入购物车

- `POST /api/cart/items`

- 鉴权：是

```json
{
  "product_id": "brow_001_brown",
  "quantity": 2
}
```

### 3.6.3 更新数量

- `PUT /api/cart/items`

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}` |
| `Content-Type` | 是 | `application/json` |

请求体：

```json
{
  "product_id": "brow_001_brown",
  "quantity": 3
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `product_id` | string | 是 | SKU / 商品 ID |
| `quantity` | integer | 是 | 目标数量，大于 0 |

### 3.6.4 删除购物车商品

- `DELETE /api/cart/items/{product_id}`

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}` |

Path 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `product_id` | string | 是 | 要删除的商品 SKU |

### 3.6.5 清空购物车

- `POST /api/cart/clear`

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}` |

### 3.6.6 套装加入购物车

- `POST /api/cart/bundles`

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}` |
| `Content-Type` | 是 | `application/json` |

请求体示例（bundle_id 模式）：

```json
{
  "bundle_id": "bundle_autumn_001",
  "product_ids": []
}
```

请求体示例（直接产品模式）：

```json
{
  "product_ids": ["lip_001", "brow_001", "base_001"]
}
```

### 3.6.7 批量设置购物车

- `POST /api/cart/items/bulk`

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}` |
| `Content-Type` | 是 | `application/json` |

请求体示例：

```json
{
  "items": [
    {"product_id": "lip_001", "quantity": 2},
    {"product_id": "brow_001", "quantity": 1}
  ]
}
```

---

## 3.7 管理端商品接口

### 3.7.1 获取商品列表

- `GET /api/admin/products`

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}`，且用户必须是管理员 |

Query：

- `limit`
- `category`
- `keyword`

参数说明：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `limit` | integer | 否 | 返回条数，默认 200 |
| `category` | string | 否 | 品类过滤，如 `lip` |
| `keyword` | string | 否 | 商品名模糊搜索 |

### 3.7.2 创建商品

- `POST /api/admin/products`

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}`，且用户必须是管理员 |
| `Content-Type` | 是 | `application/json` |

```json
{
  "p_id": "lip_001",
  "name": "柔雾唇釉 01",
  "category": "lip",
  "apply_area": "lips",
  "render_hex": "#B14A5A"
}
```

字段说明：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `p_id` | string | 是 | SKU 主键 |
| `name` | string | 是 | 商品名称 |
| `category` | string | 是 | `base/brow/eye/contour/lip` |
| `apply_area` | string | 是 | `skin/brow/eyes/lips/cheeks` |
| `render_hex` | string | 是 | 渲染色值 |

### 3.7.3 获取 / 更新 / 删除单个商品

- `GET /api/admin/products/{product_id}`
- `PUT /api/admin/products/{product_id}`
- `DELETE /api/admin/products/{product_id}`

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}`，且用户必须是管理员 |

Path 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `product_id` | string | 是 | 商品 SKU |

更新商品请求体示例：

```json
{
  "name": "柔雾唇釉 01 升级版",
  "render_hex": "#A84558"
}
```

---

## 3.8 媒体接口

### 3.8.1 压缩图片

- `POST /api/media/compress`

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}` |
| `Content-Type` | 是 | `multipart/form-data` |

表单参数：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | file | 是 | 待压缩图片 |

### 3.8.2 上传并预处理图片

- `POST /api/media/process-upload`

请求头：

| Header | 必填 | 说明 |
|---|---|---|
| `Authorization` | 是 | `Bearer {{token}}` |
| `Content-Type` | 是 | `multipart/form-data` |

表单参数：

| 字段 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `file` | file | 是 | 原始待处理图片 |

### 3.8.3 访问输出图 / 上传图 / 头像图

- `GET /api/media/images/output/{filename}`
- `GET /api/media/images/upload/{filename}`
- `GET /api/media/images/avatar/{filename}`

Path 参数：

| 参数 | 类型 | 必填 | 说明 |
|---|---|---|---|
| `filename` | string | 是 | 路径型文件名，支持多级目录 |

图片接口支持：

- `Authorization: Bearer {{token}}`
- 或 `?token={{token}}`

---

## 4. 状态码总览

| 状态码 | 典型场景 |
|---|---|
| `200` | 查询、删除、更新成功 |
| `201` | 创建成功 |
| `400` | 缺少参数、参数非法、图片类型错误 |
| `401` | 未登录、token 缺失或失效 |
| `403` | 鉴权通过但无权限访问该资源 |
| `404` | 图片、方案、会话、商品不存在 |
| `422` | FastAPI 模型校验不通过 |
| `500` | 未处理异常 |
| `503` | GAN 模型未加载或不可用 |

---

## 5. Apipost 导入建议

1. 先启动服务 [`backend/fastapi_app.py`](backend/fastapi_app.py:2649)
2. 在 Apipost 中导入：`http://127.0.0.1:5001/openapi.json`
3. 在全局变量中设置：
   - `token`
4. 为受保护接口统一加：

```http
Authorization: Bearer {{token}}
```

如果是图片直链访问，也可以直接在 URL 后拼：

```text
?token={{token}}
```

