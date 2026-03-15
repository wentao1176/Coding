from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import bcrypt
import jwt
from datetime import datetime, timedelta

app = FastAPI()

# 内存存储用户数据（重启后丢失）
users_db = {}

class User(BaseModel):
    username: str
    password: str

@app.post("/api/register")
def register(user: User):
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="用户名已存在")
    hashed_pw = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
    users_db[user.username] = hashed_pw
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