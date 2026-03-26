from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import json
import uuid
import asyncio

app = FastAPI()

# 游戏房间管理（内存存储）
rooms = {}

class GameRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = {}  # {username: player_id}
        self.board = [[0 for _ in range(15)] for _ in range(15)]  # 15x15棋盘
        self.current_player = 1  # 1: 黑棋, 2: 白棋
        self.game_status = "waiting"  # waiting, playing, finished
        self.winner = None
        self.move_history = []
    
    def add_player(self, username):
        if len(self.players)< 2:
            player_id = 1 if len(self.players) == 0 else 2
            self.players[username] = player_id
            return player_id
        return None
    
    def remove_player(self, username):
        if username in self.players:
            del self.players[username]
            return True
        return False
    
    def make_move(self, row, col, player):
        if self.game_status != "playing":
            return False, "游戏尚未开始"
        
        if self.current_player != player:
            return False, "不是你的回合"
        
        if row< 0 or row >= 15 or col< 0 or col >= 15:
            return False, "位置超出棋盘范围"
        
        if self.board[row][col] != 0:
            return False, "该位置已有棋子"
        
        self.board[row][col] = player
        self.move_history.append((row, col, player))
        
        # 检查胜负
        if self.check_win(row, col, player):
            self.game_status = "finished"
            self.winner = player
            return True, f"玩家 {player} 获胜！"
        
        # 切换玩家
        self.current_player = 2 if player == 1 else 1
        return True, "落子成功"
    
    def check_win(self, row, col, player):
        # 检查横向
        count = 1
        for c in range(col + 1, 15):
            if self.board[row][c] == player:
                count += 1
            else:
                break
        for c in range(col - 1, -1, -1):
            if self.board[row][c] == player:
                count += 1
            else:
                break
        if count >= 5:
            return True
        
        # 检查纵向
        count = 1
        for r in range(row + 1, 15):
            if self.board[r][col] == player:
                count += 1
            else:
                break
        for r in range(row - 1, -1, -1):
            if self.board[r][col] == player:
                count += 1
            else:
                break
        if count >= 5:
            return True
        
        # 检查斜向
        count = 1
        r, c = row + 1, col + 1
        while r< 15 and c < 15:
            if self.board[r][c] == player:
                count += 1
                r += 1
                c += 1
            else:
                break
        r, c = row - 1, col - 1
        while r >= 0 and c >= 0:
            if self.board[r][c] == player:
                count += 1
                r -= 1
                c -= 1
            else:
                break
        if count >= 5:
            return True
        
        # 检查反斜向
        count = 1
        r, c = row + 1, col - 1
        while r< 15 and c >= 0:
            if self.board[r][c] == player:
                count += 1
                r += 1
                c -= 1
            else:
                break
        r, c = row - 1, col + 1
        while r >= 0 and c < 15:
            if self.board[r][c] == player:
                count += 1
                r -= 1
                c += 1
            else:
                break
        if count >= 5:
            return True
        
        return False
    
    def to_dict(self):
        return {
            "room_id": self.room_id,
            "players": list(self.players.keys()),
            "board": self.board,
            "current_player": self.current_player,
            "game_status": self.game_status,
            "winner": self.winner
        }

class JoinRoomRequest(BaseModel):
    room_id: str
    username: str

class MoveRequest(BaseModel):
    room_id: str
    username: str
    row: int
    col: int

class ChatRequest(BaseModel):
    room_id: str
    username: str
    content: str

# 获取房间列表
@app.get("/api/go/rooms")
async def get_rooms():
    room_list = []
    for room_id, room in rooms.items():
        room_list.append(room.to_dict())
    return {"status": "ok", "rooms": room_list}

# 加入房间
@app.post("/api/go/join")
async def join_room(request: JoinRoomRequest):
    room_id = request.room_id
    username = request.username
    
    if not room_id or not username:
        raise HTTPException(status_code=400, detail="房间ID和用户名不能为空")
    
    # 创建房间（如果不存在）
    if room_id not in rooms:
        rooms[room_id] = GameRoom(room_id)
    
    room = rooms[room_id]
    
    # 添加玩家
    player_id = room.add_player(username)
    if player_id:
        # 如果房间满了，开始游戏
        if len(room.players) == 2:
            room.game_status = "playing"
        
        return {
            "status": "ok",
            "player": player_id,
            "game_state": room.to_dict()
        }
    else:
        raise HTTPException(status_code=400, detail="房间已满")

# 执行落子
@app.post("/api/go/move")
async def make_move(request: MoveRequest):
    room_id = request.room_id
    username = request.username
    row = request.row
    col = request.col
    
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    room = rooms[room_id]
    
    if username not in room.players:
        raise HTTPException(status_code=400, detail="玩家未加入房间")
    
    player_id = room.players[username]
    
    success, message = room.make_move(row, col, player_id)
    
    return {
        "status": "ok",
        "success": success,
        "message": message,
        "game_state": room.to_dict()
    }

# 发送聊天
@app.post("/api/go/chat")
async def send_chat(request: ChatRequest):
    room_id = request.room_id
    username = request.username
    content = request.content
    
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    room = rooms[room_id]
    
    if username not in room.players:
        raise HTTPException(status_code=400, detail="玩家未加入房间")
    
    return {
        "status": "ok",
        "username": username,
        "content": content
    }

# 获取游戏状态
@app.get("/api/go/state/{room_id}")
async def get_game_state(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="房间不存在")
    
    return {
        "status": "ok",
        "game_state": rooms[room_id].to_dict()
    }