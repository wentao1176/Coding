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
        
        # 检查表是否存在，如果不存在则创建
        cursor.execute("SELECT EXISTS(SELECT FROM information_schema.tables WHERE table_name = 'user_files')")
        table_exists = cursor.fetchone()[0]
        
        if not table_exists:
            create_table_query = """
            CREATE TABLE user_files (
                id SERIAL PRIMARY KEY,
                filename VARCHAR(255),
                filetype VARCHAR(100),
                filedata TEXT,
                uploadtime TIMESTAMP DEFAULT NOW()
            )
            """
            cursor.execute(create_table_query)
            conn.commit()
            print("数据库表创建成功")
        else:
            print("数据库表已存在")
            
        cursor.close()
        conn.close()
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
    cursor = conn.cursor()
    
    try:
        # 检查用户名是否已存在
        cursor.execute("SELECT id FROM user_files WHERE filename = %s AND filetype = 'user'", (user.username,))
        if cursor.fetchone():
            print(f"用户名已存在: {user.username}")
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        # 密码加密
        hashed_pw = bcrypt.hashpw(user.password.encode(), bcrypt.gensalt()).decode()
        
        # 插入用户数据（使用 filename 存储用户名，filedata 存储密码，filetype 标记为 'user'）
        cursor.execute(
            "INSERT INTO user_files (filename, filetype, filedata) VALUES (%s, %s, %s)", 
            (user.username, 'user', hashed_pw)
        )
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
    cursor = conn.cursor()
    
    try:
        # 查询用户信息（filename=用户名，filetype=user）
        cursor.execute("SELECT filedata FROM user_files WHERE filename = %s AND filetype = 'user'", (user.username,))
        result = cursor.fetchone()
        
        if not result:
            raise HTTPException(status_code=401, detail="用户名不存在")
        
        hashed_password = result[0]
        
        # 验证密码
        if not bcrypt.checkpw(user.password.encode(), hashed_password.encode()):
            raise HTTPException(status_code=401, detail="密码错误")
        
        # 生成 token
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
    cursor = conn.cursor()
    
    try:
        # 查询所有用户（filetype='user'）
        cursor.execute("SELECT filename FROM user_files WHERE filetype = 'user'")
        users = cursor.fetchall()
        user_list = [user[0] for user in users]
        return {"status": "ok", "users": user_list, "count": len(user_list)}
    except Exception as e:
        print(f"数据库操作失败: {e}")
        raise HTTPException(status_code=500, detail="数据库操作失败")
    finally:
        cursor.close()
        conn.close()
