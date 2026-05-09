## 步骤 1：从 GitHub 克隆源代码

```bash
cd /home/ubuntu/project
git clone https://github.com/lyqqqq66666/men-s-makeup.git frontend
```

## 步骤 2：安装依赖并构建

```bash
cd /home/ubuntu/project/frontend
npm install
npm run build
```

## 步骤 3：修改 Nginx 配置

```bash
编辑 Nginx 配置文件：


sudo nano /etc/nginx/sites-available/default
找到这一行：


root /home/ubuntu/project/frontend;
改为：


root /home/ubuntu/project/frontend/dist;
保存退出（Ctrl+O，Enter，Ctrl+X）
```

## 步骤 4：重启 Nginx

```bash
sudo nginx -t
sudo systemctl restart nginx
```

## 步骤 5：测试

在浏览器访问 http://106.54.194.110

## 以后更新代码的流程：

```bash
cd /home/ubuntu/project/frontend
git pull origin main
npm install  # 如果有新依赖
npm run build
```

## 以后更新代码的流程：

```bash
cd /home/ubuntu/project/frontend
git pull origin main
npm install  # 如果有新依赖
npm run build
```
