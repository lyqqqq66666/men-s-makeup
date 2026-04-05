# `backend_new` 部署手册（GitHub -> 服务器）

本文按你的当前情况写：前端已在服务器可访问，现在把后端通过 GitHub 同步到服务器并上线。

仓库地址（你当前本地 `origin`）：
`git@github.com:lyqqqq66666/men-s-makeup.git`

---

## 0. 先看这个高风险提示（很重要）

当前 `backend_new` 代码在启动时会调用 `db_manager.init_db()`，而 `schema.sql` 是“全量重建”风格（包含很多 `DROP TABLE`）。

这意味着：
- 每次服务重启，存在清空业务表数据的风险。

建议：
- 演示环境可以先跑。
- 正式环境请先改 `init_db` 逻辑（改成只初始化、不重建），再上线。
- 至少每次重启前备份数据库文件：`backend_new/database/app_data.db`。

---

## 1. 本地：把 `backend_new` 推到 GitHub

在项目根目录执行：

```bash
cd "/Users/LYQ/Desktop/大三资料/大三上/数字图像处理/智颜方正—智能图像矫正与风格男妆生成系统"
git status
```

把后端新目录和文档提交：

```bash
git add backend_new
git add backend_new_部署手册_GitHub到服务器.md
git commit -m "feat: add backend_new and deployment guide"
git push origin main
```

如果你的主分支不是 `main`，把上面最后一行改成对应分支名（比如 `master`）。

---

## 2. 服务器：拉代码（clone 或 pull）

### 2.1 首次部署（服务器还没有该仓库）

```bash
cd /opt
sudo git clone git@github.com:lyqqqq66666/men-s-makeup.git
sudo chown -R $USER:$USER /opt/men-s-makeup
cd /opt/men-s-makeup
```

### 2.2 非首次部署（服务器已有仓库）

```bash
cd /opt/men-s-makeup
git pull origin main
```

---

## 3. 服务器：创建 Python 环境并安装依赖

> 以下按 Ubuntu/Debian 示例。

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip

cd /opt/men-s-makeup/backend_new
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
```

安装运行 `fastapi_app.py` 需要的核心依赖：

```bash
pip install fastapi "uvicorn[standard]" pydantic python-multipart
pip install opencv-python numpy pillow mediapipe
pip install torch diffusers transformers accelerate safetensors
```

如果服务器拉取 HuggingFace 模型慢，可配置：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

---

## 4. 服务器：先手工启动验证

在 `backend_new` 目录：

```bash
source .venv/bin/activate
uvicorn fastapi_app:app --host 0.0.0.0 --port 5001
```

另开终端测试：

```bash
curl http://127.0.0.1:5001/health
```

看到健康检查返回即说明后端服务可用。

---

## 5. 用 systemd 托管 FastAPI（推荐）

创建服务文件：

```bash
sudo nano /etc/systemd/system/men-makeup-backend.service
```

写入以下内容：

```ini
[Unit]
Description=Men Makeup FastAPI Backend
After=network.target

[Service]
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/men-s-makeup/backend_new
Environment=MODEL_PREFLIGHT_ON_BOOT=0
Environment=MODEL_PREFLIGHT_STRICT=0
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/men-s-makeup/backend_new/.venv/bin/uvicorn fastapi_app:app --host 127.0.0.1 --port 5001 --workers 1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

注意把 `User`/`Group` 改成你的服务器登录用户（常见是 `ubuntu` 或 `root`）。

启动并设为开机自启：

```bash
sudo systemctl daemon-reload
sudo systemctl enable men-makeup-backend
sudo systemctl restart men-makeup-backend
sudo systemctl status men-makeup-backend
```

看日志：

```bash
sudo journalctl -u men-makeup-backend -f
```

---

## 6. Nginx 反向代理（前端已可访问）

你前端已上线，只需要在现有站点配置里加后端代理（同域名最省心）：

```nginx
location /api/ {
    proxy_pass http://127.0.0.1:5001/api/;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

location /docs {
    proxy_pass http://127.0.0.1:5001/docs;
    proxy_set_header Host $host;
}

location /openapi.json {
    proxy_pass http://127.0.0.1:5001/openapi.json;
    proxy_set_header Host $host;
}
```

保存后检查并重载：

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 7. 数据库与图片存储目录

`backend_new` 使用本地 SQLite 与本地文件：
- 数据库：`/opt/men-s-makeup/backend_new/database/app_data.db`
- 上传图：`/opt/men-s-makeup/backend_new/database/images/uploads`
- 输出图：`/opt/men-s-makeup/backend_new/database/images/outputs`
- 头像图：`/opt/men-s-makeup/backend_new/database/images/avatar`

备份命令示例：

```bash
cd /opt/men-s-makeup/backend_new
cp database/app_data.db "database/app_data.db.bak.$(date +%F_%H-%M-%S)"
```

---

## 8. 后续更新（标准流程）

每次本地改完后端：

```bash
# 本地
git add .
git commit -m "feat/fix: xxx"
git push origin main
```

服务器更新：

```bash
cd /opt/men-s-makeup
git pull origin main
cd backend_new
source .venv/bin/activate
pip install -U fastapi "uvicorn[standard]" pydantic python-multipart opencv-python numpy pillow mediapipe torch diffusers transformers accelerate safetensors
sudo systemctl restart men-makeup-backend
sudo systemctl status men-makeup-backend
```

---

## 9. 联调检查清单

1. 前端请求地址是否走同域 `/api/...`。  
2. `curl http://127.0.0.1:5001/health` 是否正常。  
3. `sudo systemctl status men-makeup-backend` 是否 `active (running)`。  
4. `sudo journalctl -u men-makeup-backend -f` 是否无报错。  
5. 浏览器打开 `https://你的域名/docs` 是否可访问。  

---

## 10. 推荐你下一步马上做的事

1. 先按本文完成“演示环境”部署并验证联调。  
2. 在正式上线前，修改 `db_manager.init_db`，避免重启清库。  
3. 把 Python 依赖固化到 `requirements.txt`，后续部署会更稳定。  

