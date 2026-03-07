# 智颜方正 数据库与文件存储说明

为了更好地管理用户上传的大量图片及其处理结果，我们引入了 SQLite 数据库和结构化的文件存储系统。

## 1. 目录结构

所有的数据都存储在 `backend/database` 目录下：

```
backend/
  database/
    app_data.db             # SQLite 数据库文件 (存储元数据)
    images/
      uploads/              # 用户上传的原图 (命名: upload_{uuid}.jpg)
      outputs/              # 矫正处理后的结果图 (命名: corrected_{uuid}.jpg)
    debug_rois/             # 模糊检测过程中的特征区域截图 (命名: {uuid}_{feature}.jpg)
```

## 2. 数据库设计

数据库已拆分为三个独立的表，分别管理不同类型的图片记录。

### A. 表 `uploads` (上传原图)
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | INTEGER | 自增主键 |
| `group_id` | TEXT | **关联ID** (UUID) |
| `filename` | TEXT | 文件名 |
| `file_path` | TEXT | 文件路径 |
| `created_at` | TIMESTAMP | 创建时间 |

### B. 表 `debug_images` (调试用ROI)
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | INTEGER | 自增主键 |
| `group_id` | TEXT | **关联ID** (UUID) |
| `filename` | TEXT | 文件名 |
| `file_path` | TEXT | 文件路径 |
| `blur_score` | REAL | 模糊评分 |
| `created_at` | TIMESTAMP | 创建时间 |

### C. 表 `corrected_images` (矫正结果)
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | INTEGER | 自增主键 |
| `group_id` | TEXT | **关联ID** (UUID) |
| `filename` | TEXT | 文件名 |
| `file_path` | TEXT | 文件路径 |
| `correction_angle` | REAL | 矫正角度 |
| `created_at` | TIMESTAMP | 创建时间 |

### D. 表 `makeup_images` (风格美妆结果)
| 字段名 | 类型 | 说明 |
| :--- | :--- | :--- |
| `id` | INTEGER | 自增主键 |
| `group_id` | TEXT | **关联ID** (UUID) - 外键关联 `uploads` |
| `style` | TEXT | 美妆风格 (clean, business, idol) |
| `filename` | TEXT | 文件名 |
| `file_path` | TEXT | 文件路径 |
| `created_at` | TIMESTAMP | 创建时间 |

### SQL 查询示例

**1. 查询某次处理（group_id）对应的原图、矫正图和美妆结果：**
```sql
SELECT 
    u.filename AS original, 
    c.filename AS corrected,
    m.filename AS makeup_result,
    m.style AS makeup_style
FROM uploads u
LEFT JOIN corrected_images c ON u.group_id = c.group_id
LEFT JOIN makeup_images m ON u.group_id = m.group_id
WHERE u.group_id = 'YOUR_UUID_HERE';
```
