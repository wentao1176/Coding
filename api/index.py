from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import bcrypt
import jwt
import psycopg2
from psycopg2 import sql
import os
from datetime import datetime, timedelta

app = FastAPI()

def get_db_connection():
    try:
        conn = psycopg2.connect(os.environ["DATABASE_URL"])
        return conn
    except Exception as e:
        print(f"数据库连接失败: {e}")
        raise HTTPException(status_code=500, detail="数据库连接失败")

def init_database():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        create_table_query = """
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(255) NOT NULL UNIQUE,
            password VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT NOW()
        )
        """
        cursor.execute(create_table_query)
        conn.commit()
        cursor.close()
        conn.close()
        print("数据库表初始化成功")
    except Exception as e:
        print(f"初始化数据库失败: {e}")

init_database()

class User(BaseModel):
    username: str
    password: str

@app.post("/api/register")
def register(user: User):
    print(f"收到注册请求: {user.username}")
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT username FROM users WHERE username = %s", (user.username,))
        if cursor.fetchone():
            print(f"用户名已存在: {user.username}")
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        hashed_pw = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
        cursor.execute("INSERT INTO users (username, password) VALUES (%s, %s)", 
                      (user.username, hashed_pw))
        conn.commit()
        
        print(f"用户注册成功: {user.username}")
        return {"status": "ok", "msg": "注册成功"}
    except Exception as e:
        print(f"数据库操作失败: {e}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    finally:
        cursor.close()
        conn.close()

@app.post("/api/login")
def login(user: User):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT * FROM users WHERE username = %s", (user.username,))
        db_user = cursor.fetchone()
        
        if not db_user:
            raise HTTPException(status_code=401, detail="用户名不存在")
        
        if not bcrypt.checkpw(user.password.encode(), db_user['password'].encode()):
            raise HTTPException(status_code=401, detail="密码错误")
        
        token = jwt.encode(
            {"username": user.username, "exp": datetime.utcnow() + timedelta(days=7)},
            "my-secret-key",
            algorithm="HS256"
        )
        return {"status": "ok", "token": token}
    except Exception as e:
        print(f"数据库操作失败: {e}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    finally:
        cursor.close()
        conn.close()

@app.get("/api/check")
def check(token: str):
    try:
        data = jwt.decode(token, "my-secret-key", algorithms=["HS256"])
        return {"status": "ok", "username": data["username"]}
    except:
        raise HTTPException(status_code=401, detail="未登录")

@app.get("/api/users")
def get_users():
    """获取所有用户列表"""
    print(f"获取用户列表请求")
    
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT username FROM users")
        users = cursor.fetchall()
        user_list = [user['username'] for user in users]
        return {"status": "ok", "users": user_list, "count": len(user_list)}
    except Exception as e:
        print(f"数据库操作失败: {e}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    finally:
        cursor.close()
        conn.close()
