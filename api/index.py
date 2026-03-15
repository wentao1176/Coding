from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import bcrypt
import jwt
import os
from datetime import timedelta

app = FastAPI()

# 用户数据模型
class User(BaseModel):
    username: str
    password: str

# 数据文件路径
USER_FILE = "users.txt"

# 确保文件存在
if not os.path.exists(USER_FILE):
    with open(USER_FILE, "w", encoding="utf-8") as f:
        f.write("")

# 注册（保存到 TXT）
@app.post("/register")
def register(user: User):
    # 读取所有用户
    with open(USER_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # 检查用户名是否已存在
    for line in lines:
        if line.strip():
            u, _ = line.split("||")
            if u == user.username:
                raise HTTPException(status_code=400, detail="用户名已存在")

    # 密码加密
    hashed_pw = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()

    # 写入文件
    with open(USER_FILE, "a", encoding="utf-8") as f:
        f.write(f"{user.username}||{hashed_pw}\n")

    return {"status": "ok", "msg": "注册成功"}

# 登录（从 TXT 读取验证）
@app.post("/login")
def login(user: User):
    with open(USER_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue

        u, p = line.split("||")
        if u == user.username:
            # 验证密码
            if bcrypt.checkpw(user.password.encode(), p.encode()):
                token = jwt.encode(
                    {"username": user.username, "exp": timedelta(days=7)},
                    "my-secret-key",
                    algorithm="HS256"
                )
                return {"status": "ok", "token": token}
            else:
                raise HTTPException(status_code=401, detail="密码错误")

    raise HTTPException(status_code=401, detail="用户名不存在")

# 检查登录状态
@app.get("/check")
def check(token: str):
    try:
        data = jwt.decode(token, "my-secret-key", algorithms=["HS256"])
        return {"status": "ok", "username": data["username"]}
    except:
        raise HTTPException(status_code=401, detail="未登录")