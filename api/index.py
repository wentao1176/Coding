from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
import bcrypt
import jwt
import psycopg2
from psycopg2 import sql
import os
import json
import random
import string
from datetime import datetime, timedelta

app = FastAPI()

def get_db_connection():
    try:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            print("错误：环境变量 DATABASE_URL 未设置")
            raise HTTPException(status_code=500, detail="环境变量 DATABASE_URL 未设置")
        
        print(f"尝试连接数据库，URL: {db_url[:20]}...")
        
        # 添加连接参数，增加稳定性
        conn = psycopg2.connect(
            db_url,
            connect_timeout=10,
            options='-c statement_timeout=30000'
        )
        
        print("数据库连接成功")
        return conn
    except Exception as e:
        print(f"数据库连接失败: {type(e).__name__}: {e}")
        
        # 尝试使用备用连接方式（如果是 Supabase）
        if "supabase" in db_url:
            print("尝试使用备用连接方式...")
            try:
                # 尝试使用 IPv4 连接
                import socket
                socket.setdefaulttimeout(10)
                conn = psycopg2.connect(db_url)
                print("备用连接方式成功")
                return conn
            except Exception as e2:
                print(f"备用连接方式也失败: {type(e2).__name__}: {e2}")
        
        raise HTTPException(status_code=500, detail=f"数据库连接失败: {type(e).__name__}: {str(e)}")

def init_database():
    """初始化数据库表（仅在需要时执行）"""
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
        return True
    except Exception as e:
        print(f"初始化数据库失败: {type(e).__name__}: {e}")
        return False

class User(BaseModel):
    username: str
    password: str

class AdminLogin(BaseModel):
    username: str
    password: str

@app.post("/api/register")
def register(user: User):
    print(f"收到注册请求: {user.username}")
    
    # 先初始化数据库
    if not init_database():
        raise HTTPException(status_code=500, detail="数据库初始化失败")
    
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
        print(f"数据库操作失败: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"数据库操作失败: {type(e).__name__}: {str(e)}")
    finally:
        cursor.close()
        conn.close()

@app.post("/api/login")
def login(user: User):
    # 先初始化数据库
    if not init_database():
        raise HTTPException(status_code=500, detail="数据库初始化失败")
    
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
        print(f"数据库操作失败: {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=f"数据库操作失败: {type(e).__name__}: {str(e)}")
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
    """获取所有用户列表（不带密码）"""
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


@app.post("/api/admin/login")
def admin_login(admin: AdminLogin):
    """管理员登录"""
    # 简单的管理员验证（实际生产环境应该更复杂）
    if admin.username == "admin" and admin.password == "admin123":
        token = jwt.encode(
            {"role": "admin", "exp": datetime.utcnow() + timedelta(days=1)},
            "admin-secret-key",
            algorithm="HS256"
        )
        return {"status": "ok", "token": token}
    else:
        raise HTTPException(status_code=401, detail="管理员账号或密码错误")


@app.get("/api/admin/check")
def admin_check(token: str):
    """验证管理员 token"""
    try:
        data = jwt.decode(token, "admin-secret-key", algorithms=["HS256"])
        if data.get("role") != "admin":
            raise HTTPException(status_code=401, detail="权限不足")
        return {"status": "ok"}
    except:
        raise HTTPException(status_code=401, detail="管理员 token 无效")


@app.get("/api/admin/users")
def admin_get_users(token: str):
    """管理员获取所有用户信息（包含密码哈希）"""
    try:
        # 验证管理员权限
        data = jwt.decode(token, "admin-secret-key", algorithms=["HS256"])
        if data.get("role") != "admin":
            raise HTTPException(status_code=401, detail="权限不足")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            cursor.execute("SELECT filename, filedata, uploadtime FROM user_files WHERE filetype = 'user'")
            users = cursor.fetchall()
            
            user_list = []
            for user in users:
                user_list.append({
                    "username": user[0],
                    "password_hash": user[1],
                    "created_at": user[2].strftime("%Y-%m-%d %H:%M:%S") if user[2] else None
                })
            
            return {"status": "ok", "users": user_list, "count": len(user_list)}
        finally:
            cursor.close()
            conn.close()
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="管理员 token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="管理员 token 无效")
    except Exception as e:
        print(f"管理员查询用户失败: {e}")
        raise HTTPException(status_code=500, detail="查询失败")


@app.post("/api/admin/reset-password")
def admin_reset_password(token: str, username: str, new_password: str):
    """管理员重置用户密码"""
    try:
        # 验证管理员权限
        data = jwt.decode(token, "admin-secret-key", algorithms=["HS256"])
        if data.get("role") != "admin":
            raise HTTPException(status_code=401, detail="权限不足")
        
        if not new_password or len(new_password) < 6:
            raise HTTPException(status_code=400, detail="密码长度至少6位")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 检查用户是否存在
            cursor.execute("SELECT id FROM user_files WHERE filename = %s AND filetype = 'user'", (username,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 密码加密
            hashed_pw = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
            
            # 更新密码
            cursor.execute(
                "UPDATE user_files SET filedata = %s WHERE filename = %s AND filetype = 'user'",
                (hashed_pw, username)
            )
            conn.commit()
            
            return {"status": "ok", "msg": "密码重置成功"}
        finally:
            cursor.close()
            conn.close()
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="管理员 token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="管理员 token 无效")
    except Exception as e:
        print(f"管理员重置密码失败: {e}")
        raise HTTPException(status_code=500, detail="重置失败")


@app.post("/api/admin/delete-user")
def admin_delete_user(token: str, username: str):
    """管理员删除用户账号"""
    try:
        # 验证管理员权限
        data = jwt.decode(token, "admin-secret-key", algorithms=["HS256"])
        if data.get("role") != "admin":
            raise HTTPException(status_code=401, detail="权限不足")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # 检查用户是否存在
            cursor.execute("SELECT id FROM user_files WHERE filename = %s AND filetype = 'user'", (username,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="用户不存在")
            
            # 删除用户
            cursor.execute(
                "DELETE FROM user_files WHERE filename = %s AND filetype = 'user'",
                (username,)
            )
            conn.commit()
            
            return {"status": "ok", "msg": "用户删除成功"}
        finally:
            cursor.close()
            conn.close()
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="管理员 token 已过期")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="管理员 token 无效")
    except Exception as e:
        print(f"管理员删除用户失败: {e}")
        raise HTTPException(status_code=500, detail="删除失败")


# 五子棋游戏相关代码
class GameRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = {}  # {username: websocket}
        self.board = [[0 for _ in range(15)] for _ in range(15)]  # 15x15棋盘
        self.current_player = 1  # 1: 黑棋, 2: 白棋
        self.game_status = "waiting"  # waiting, playing, finished
        self.winner = None
        self.move_history = []
    
    def add_player(self, username, websocket):
        if len(self.players) >= 2:
            return False
        self.players[username] = websocket
        return True
    
    def remove_player(self, username):
        if username in self.players:
            del self.players[username]
            return True
        return False
    
    def make_move(self, row, col, player):
        if self.game_status != "playing":
            return False, "游戏未开始"
        
        if player != self.current_player:
            return False, "不是你的回合"
        
        if row< 0 or row >= 15 or col< 0 or col >= 15:
            return False, "位置超出范围"
        
        if self.board[row][col] != 0:
            return False, "该位置已有棋子"
        
        self.board[row][col] = player
        self.move_history.append({"row": row, "col": col, "player": player})
        
        if self.check_win(row, col, player):
            self.game_status = "finished"
            self.winner = player
            return True, "游戏结束，玩家获胜"
        
        self.current_player = 2 if player == 1 else 1
        return True, "落子成功"
    
    def check_win(self, row, col, player):
        # 检查横向
        count = 1
        # 向左
        c = col - 1
        while c >= 0 and self.board[row][c] == player:
            count += 1
            c -= 1
        # 向右
        c = col + 1
        while c< 15 and self.board[row][c] == player:
            count += 1
            c += 1
        if count >= 5:
            return True
        
        # 检查纵向
        count = 1
        # 向上
        r = row - 1
        while r >= 0 and self.board[r][col] == player:
            count += 1
            r -= 1
        # 向下
        r = row + 1
        while r< 15 and self.board[r][col] == player:
            count += 1
            r += 1
        if count >= 5:
            return True
        
        # 检查对角线（左上到右下）
        count = 1
        # 左上
        r, c = row - 1, col - 1
        while r >= 0 and c >= 0 and self.board[r][c] == player:
            count += 1
            r -= 1
            c -= 1
        # 右下
        r, c = row + 1, col + 1
        while r< 15 and c < 15 and self.board[r][c] == player:
            count += 1
            r += 1
            c += 1
        if count >= 5:
            return True
        
        # 检查对角线（右上到左下）
        count = 1
        # 右上
        r, c = row - 1, col + 1
        while r >= 0 and c< 15 and self.board[r][c] == player:
            count += 1
            r -= 1
            c += 1
        # 左下
        r, c = row + 1, col - 1
        while r< 15 and c >= 0 and self.board[r][c] == player:
            count += 1
            r += 1
            c -= 1
        if count >= 5:
            return True
        
        return False
    
    def get_game_state(self):
        return {
            "room_id": self.room_id,
            "players": list(self.players.keys()),
            "board": self.board,
            "current_player": self.current_player,
            "game_status": self.game_status,
            "winner": self.winner,
            "move_history": self.move_history
        }


# 全局房间管理
game_rooms = {}


def generate_room_id():
    """生成随机房间ID"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


@app.websocket("/ws/go/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    await websocket.accept()
    
    try:
        # 接收用户信息
        user_data = await websocket.receive_json()
        username = user_data.get("username")
        
        if not username:
            await websocket.send_json({"type": "error", "message": "用户名不能为空"})
            await websocket.close()
            return
        
        # 创建或加入房间
        if room_id not in game_rooms:
            game_rooms[room_id] = GameRoom(room_id)
        
        room = game_rooms[room_id]
        
        # 添加玩家
        if not room.add_player(username, websocket):
            await websocket.send_json({"type": "error", "message": "房间已满"})
            await websocket.close()
            return
        
        # 发送房间信息
        await websocket.send_json({
            "type": "joined",
            "room_id": room_id,
            "player": 1 if len(room.players) == 1 else 2,
            "game_state": room.get_game_state()
        })
        
        # 广播玩家加入
        for player_name, player_ws in room.players.items():
            if player_ws != websocket:
                await player_ws.send_json({
                    "type": "player_joined",
                    "username": username
                })
        
        # 如果房间满2人，开始游戏
        if len(room.players) == 2:
            room.game_status = "playing"
            for player_ws in room.players.values():
                await player_ws.send_json({
                    "type": "game_started",
                    "game_state": room.get_game_state()
                })
        
        # 游戏主循环
        while True:
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            if message_type == "move":
                row = data.get("row")
                col = data.get("col")
                
                # 确定当前玩家
                player = 1 if list(room.players.keys())[0] == username else 2
                
                success, message = room.make_move(row, col, player)
                
                response = {
                    "type": "move_result",
                    "success": success,
                    "message": message,
                    "game_state": room.get_game_state()
                }
                
                # 广播给所有玩家
                for player_ws in room.players.values():
                    await player_ws.send_json(response)
            
            elif message_type == "chat":
                content = data.get("content")
                # 广播聊天消息
                for player_ws in room.players.values():
                    await player_ws.send_json({
                        "type": "chat",
                        "username": username,
                        "content": content
                    })
    
    except WebSocketDisconnect:
        # 处理玩家断开连接
        if room_id in game_rooms:
            room = game_rooms[room_id]
            if username in room.players:
                room.remove_player(username)
                
                # 广播玩家离开
                for player_name, player_ws in room.players.items():
                    await player_ws.send_json({
                        "type": "player_left",
                        "username": username
                    })
                
                # 如果房间为空，删除房间
                if len(room.players) == 0:
                    del game_rooms[room_id]
    
    except Exception as e:
        print(f"WebSocket错误: {e}")


@app.get("/api/go/rooms")
def get_rooms():
    """获取所有游戏房间"""
    rooms_info = []
    for room_id, room in game_rooms.items():
        rooms_info.append({
            "room_id": room_id,
            "players": list(room.players.keys()),
            "game_status": room.game_status
        })
    return {"status": "ok", "rooms": rooms_info}
