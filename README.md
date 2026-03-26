# 宣文韬个人游戏项目

一个包含登录注册系统和多种游戏的Web应用项目。

## ✨ 功能特点

### 🔐 用户系统
- **用户注册与登录**：支持用户注册账号并登录
- **密码加密**：使用 bcrypt 加密存储密码
- **JWT 认证**：使用 JSON Web Token 进行身份验证
- **管理员后台**：支持管理员查看、重置密码和删除用户

### 🎮 游戏功能

#### 💣 扫雷游戏
- 三种难度模式：初级(9×9, 10雷)、中级(16×16, 40雷)、高级(16×30, 99雷)
- 计时功能
- 地雷计数
- 全屏游戏体验

#### 🐍 贪吃蛇游戏
- 三种难度模式：简单、中等、困难
- 键盘控制（方向键和 WASD）
- 虚拟摇杆控制（支持移动端）
- 分数计算
- 全屏游戏体验

## 🛠️ 技术栈

### 前端
- HTML5 + CSS3 + JavaScript
- 响应式设计，支持移动端

### 后端
- Python FastAPI
- JWT 身份认证
- bcrypt 密码加密

### 数据库
- PostgreSQL (Supabase)
- 环境变量配置数据库连接

## 📦 环境要求

### 运行环境
- Python 3.9+
- Node.js (可选，用于开发)

### 依赖包
```
fastapi
uvicorn
python-jose[cryptography]
passlib[bcrypt]
python-multipart
psycopg2-binary
python-dotenv
```

## 🚀 安装与运行

### 1. 克隆项目
```bash
git clone https://github.com/wentao1176/Coding.git
cd Coding
```

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境变量
创建 `.env` 文件：
```
DATABASE_URL="postgresql://username:password@host:port/database"
SECRET_KEY="your-secret-key"
```

### 4. 启动服务
```bash
uvicorn api.index:app --reload
```

### 5. 访问应用
- 前端页面：http://localhost:8000/
- API 文档：http://localhost:8000/docs

## 📁 项目结构

```
Coding/
├── api/
│   └── index.py          # FastAPI 后端入口
├── index.html            # 首页
├── register.html         # 注册页面
├── login.html            # 登录页面
├── admin.html            # 管理员页面
├── minesweeper.html      # 扫雷游戏选择页面
├── minesweeper-full.html # 扫雷游戏全屏页面
├── snake.html           # 贪吃蛇游戏选择页面
├── snake-full.html      # 贪吃蛇游戏全屏页面
├── vercel.json          # Vercel 部署配置
├── requirements.txt     # Python 依赖
└── README.md            # 项目说明
```

## 🌐 部署说明

### Vercel 部署
1. 将代码推送到 GitHub
2. 在 Vercel 上导入项目
3. 配置环境变量：
   - `DATABASE_URL`：PostgreSQL 数据库连接字符串
   - `SECRET_KEY`：用于 JWT 签名的密钥

## 📝 API 端点

### 用户相关
- `POST /api/register` - 用户注册
- `POST /api/login` - 用户登录
- `GET /api/users` - 获取用户列表（管理员）
- `PUT /api/users/{user_id}/reset-password` - 重置用户密码（管理员）
- `DELETE /api/users/{user_id}` - 删除用户（管理员）
- `POST /api/admin/login` - 管理员登录

## 🎯 主要功能流程

1. **用户注册** → 密码加密存储 → 返回 JWT Token
2. **用户登录** → 验证密码 → 返回 JWT Token
3. **游戏选择** → 选择难度 → 进入全屏游戏
4. **管理员管理** → 查看用户列表 → 重置密码/删除用户

## 📄 License

MIT License

## 👤 Author

宣文韬