from flask import Flask, request, jsonify
from flask_socketio import SocketIO, join_room, leave_room, emit
import json
import uuid

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# 游戏房间管理
rooms = {}

class GameRoom:
    def __init__(self, room_id):
        self.room_id = room_id
        self.players = {}  # {username: sid}
        self.board = [[0 for _ in range(15)] for _ in range(15)]  # 15x15棋盘
        self.current_player = 1  # 1: 黑棋, 2: 白棋
        self.game_status = "waiting"  # waiting, playing, finished
        self.winner = None
        self.move_history = []
    
    def add_player(self, username, sid):
        if len(self.players)< 2:
            self.players[username] = sid
            return True
        return False
    
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

# 获取房间列表
@app.route('/api/go/rooms', methods=['GET'])
def get_rooms():
    room_list = []
    for room_id, room in rooms.items():
        room_list.append(room.to_dict())
    return jsonify({"status": "ok", "rooms": room_list})

# SocketIO事件处理
@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    # 查找并移除断开连接的玩家
    for room_id, room in list(rooms.items()):
        for username, sid in list(room.players.items()):
            if sid == request.sid:
                room.remove_player(username)
                emit('player_left', {'username': username}, room=room_id)
                # 如果房间为空，删除房间
                if len(room.players) == 0:
                    del rooms[room_id]
                break

@socketio.on('join')
def handle_join(data):
    room_id = data.get('room_id')
    username = data.get('username')
    
    if not room_id or not username:
        emit('error', {'message': '房间ID和用户名不能为空'})
        return
    
    # 创建房间（如果不存在）
    if room_id not in rooms:
        rooms[room_id] = GameRoom(room_id)
    
    room = rooms[room_id]
    
    # 添加玩家
    if room.add_player(username, request.sid):
        join_room(room_id)
        
        # 确定玩家身份（黑棋或白棋）
        player = 1 if len(room.players) == 1 else 2
        
        # 发送加入成功消息
        emit('joined', {
            'player': player,
            'game_state': room.to_dict()
        }, room=request.sid)
        
        # 通知其他玩家
        emit('player_joined', {'username': username}, room=room_id)
        
        # 如果房间满了，开始游戏
        if len(room.players) == 2:
            room.game_status = "playing"
            emit('game_started', {'game_state': room.to_dict()}, room=room_id)
    else:
        emit('error', {'message': '房间已满'})

@socketio.on('move')
def handle_move(data):
    room_id = data.get('room_id')
    row = data.get('row')
    col = data.get('col')
    
    if room_id not in rooms:
        emit('error', {'message': '房间不存在'})
        return
    
    room = rooms[room_id]
    username = None
    
    # 查找当前玩家
    for user, sid in room.players.items():
        if sid == request.sid:
            username = user
            break
    
    if not username:
        emit('error', {'message': '玩家未加入房间'})
        return
    
    # 确定玩家身份
    player = 1 if list(room.players.keys())[0] == username else 2
    
    # 执行落子
    success, message = room.make_move(row, col, player)
    
    emit('move_result', {
        'success': success,
        'message': message,
        'game_state': room.to_dict()
    }, room=room_id)

@socketio.on('chat')
def handle_chat(data):
    room_id = data.get('room_id')
    content = data.get('content')
    
    if room_id not in rooms:
        emit('error', {'message': '房间不存在'})
        return
    
    # 查找当前玩家
    username = None
    for user, sid in rooms[room_id].players.items():
        if sid == request.sid:
            username = user
            break
    
    if not username:
        emit('error', {'message': '玩家未加入房间'})
        return
    
    emit('chat', {
        'username': username,
        'content': content
    }, room=room_id)

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)