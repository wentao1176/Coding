from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import bcrypt
import jwt
import json
import os
from datetime import datetime, timedelta

app = FastAPI()

# 文件存储用户数据
# 使用绝对路径确保在任何环境下都能正确找到文件
USERS_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "users.json")

# 加载用户数据
users_db = {}
if os.path.exists(USERS_FILE):
    try:
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            users_db = json.load(f)
    except Exception as e:
        print(f"加载用户数据失败: {e}")
        users_db = {}

# 保存用户数据
def save_users():
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users_db, f, ensure_ascii=False, indent=2)
        print(f"用户数据已保存到: {USERS_FILE}")
    except Exception as e:
        print(f"保存用户数据失败: {e}")

class User(BaseModel):
    username: str
    password: str

@app.post("/api/register")
def register(user: User):
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="用户名已存在")
    hashed_pw = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    users_db[user.username] = hashed_pw
    save_users()  # 保存到文件
    return {"status": "ok", "msg": "注册成功"}

@app.post("/api/login")
def login(user: User):
    if user.username not in users_db:
        raise HTTPException(status_code=401, detail="用户名不存在")
    if not bcrypt.checkpw(user.password.encode(), users_db[user.username].encode()):
        raise HTTPException(status_code=401, detail="密码错误")
    token = jwt.encode(
        {"username": user.username, "exp": datetime.utcnow() + timedelta(days=7)},
        "my-secret-key",
        algorithm="HS256"
    )
    return {"status": "ok", "token": token}

@app.get("/api/check")
def check(token: str):
    try:
        data = jwt.decode(token, "my-secret-key", algorithms=["HS256"])
        return {"status": "ok", "username": data["username"]}
    except:
        raise HTTPException(status_code=401, detail="未登录")