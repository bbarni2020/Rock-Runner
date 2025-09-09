from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import secrets
import hashlib
import datetime
import json
import os
import re
import jwt
from functools import wraps

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.getenv('JWT_SECRET', 'rock-runner-secret-key-' + secrets.token_hex(16))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

DB_NAME = "game_users.db"

def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_verified BOOLEAN DEFAULT TRUE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            high_score INTEGER DEFAULT 0,
            total_games INTEGER DEFAULT 0,
            total_playtime INTEGER DEFAULT 0,
            average_score REAL DEFAULT 0,
            last_played TIMESTAMP,
            difficulty_stats TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            score INTEGER NOT NULL,
            playtime INTEGER NOT NULL,
            difficulty INTEGER DEFAULT 2,
            session_start TIMESTAMP,
            session_end TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_completed BOOLEAN DEFAULT TRUE,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    conn.close()

def validate_email_format(email):
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def hash_password(password):
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256((password + salt).encode()).hexdigest()
    return f"{salt}:{password_hash}"

def verify_password(password, stored_hash):
    try:
        salt, password_hash = stored_hash.split(':')
        return hashlib.sha256((password + salt).encode()).hexdigest() == password_hash
    except:
        return False

def generate_jwt_token(user_id, email, username):
    now = datetime.datetime.utcnow()
    payload = {
        'user_id': user_id,
        'email': email,
        'username': username,
        'iat': now,
        'exp': now + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_jwt_token(token):
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def jwt_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        auth_header = request.headers.get('Authorization')
        
        if auth_header:
            try:
                token = auth_header.split(" ")[1]
            except IndexError:
                return jsonify({'success': False, 'message': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'success': False, 'message': 'Token is missing'}), 401
        
        payload = verify_jwt_token(token)
        if payload is None:
            return jsonify({'success': False, 'message': 'Token is invalid or expired'}), 401
        
        request.user_id = payload['user_id']
        request.user_email = payload['email']
        request.username = payload['username']
        
        return f(*args, **kwargs)
    return decorated_function

@app.route('/api/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not email or not username or not password:
            return jsonify({'success': False, 'message': 'Email, username, and password are required'}), 400
        
        if not validate_email_format(email):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'message': 'Password must be at least 6 characters long'}), 400
        
        if len(username) < 3:
            return jsonify({'success': False, 'message': 'Username must be at least 3 characters long'}), 400
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id FROM users WHERE email = ? OR username = ?', (email, username))
        existing_user = cursor.fetchone()
        
        if existing_user:
            conn.close()
            return jsonify({'success': False, 'message': 'Email or username already exists'}), 400
        
        password_hash = hash_password(password)
        
        current_time = datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO users (email, username, password_hash, last_login)
            VALUES (?, ?, ?, ?)
        ''', (email, username, password_hash, current_time))
        
        user_id = cursor.lastrowid
        
        cursor.execute('''
            INSERT INTO game_stats (user_id, difficulty_stats)
            VALUES (?, ?)
        ''', (user_id, json.dumps({'easy': 0, 'normal': 0, 'hard': 0})))
        
        conn.commit()
        conn.close()
        
        token = generate_jwt_token(user_id, email, username)
        
        user_data = {
            'id': user_id,
            'email': email,
            'username': username,
            'stats': {
                'highScore': 0,
                'totalGames': 0,
                'totalPlaytime': 0,
                'averageScore': 0,
                'difficultyStats': {'easy': 0, 'normal': 0, 'hard': 0}
            }
        }
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! Welcome to Rock Runner!',
            'token': token,
            'user': user_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '').strip()
        
        if not email or not password:
            return jsonify({'success': False, 'message': 'Email and password are required'}), 400
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('SELECT id, username, password_hash FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if not user:
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
        
        user_id, username, stored_password_hash = user
        
        if not verify_password(password, stored_password_hash):
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid email or password'}), 401
        
        current_time = datetime.datetime.now().isoformat()
        cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', (current_time, user_id))
        
        cursor.execute('''
            SELECT high_score, total_games, total_playtime, average_score, difficulty_stats
            FROM game_stats WHERE user_id = ?
        ''', (user_id,))
        
        stats = cursor.fetchone()
        if stats:
            stats_data = {
                'highScore': stats[0] or 0,
                'totalGames': stats[1] or 0,
                'totalPlaytime': stats[2] or 0,
                'averageScore': stats[3] or 0,
                'difficultyStats': json.loads(stats[4]) if stats[4] else {'easy': 0, 'normal': 0, 'hard': 0}
            }
        else:
            stats_data = {
                'highScore': 0,
                'totalGames': 0,
                'totalPlaytime': 0,
                'averageScore': 0,
                'difficultyStats': {'easy': 0, 'normal': 0, 'hard': 0}
            }
        
        conn.commit()
        conn.close()
        
        token = generate_jwt_token(user_id, email, username)
        
        user_data = {
            'id': user_id,
            'email': email,
            'username': username,
            'stats': stats_data
        }
        
        return jsonify({
            'success': True,
            'message': 'Login successful!',
            'token': token,
            'user': user_data
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/update-stats', methods=['POST'])
def update_stats():
    try:
        data = request.get_json()
        user_id = data.get('userId')
        score = data.get('score', 0)
        playtime = data.get('playtime', 0)
        difficulty = data.get('difficulty', 'normal')
        
        if not user_id:
            return jsonify({'success': False, 'message': 'User ID required'}), 400
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT high_score, total_games, total_playtime, average_score, difficulty_stats
            FROM game_stats WHERE user_id = ?
        ''', (user_id,))
        
        current_stats = cursor.fetchone()
        
        if current_stats:
            new_high_score = max(current_stats[0] or 0, score)
            new_total_games = (current_stats[1] or 0) + 1
            new_total_playtime = (current_stats[2] or 0) + playtime
            new_average_score = ((current_stats[3] or 0) * (new_total_games - 1) + score) / new_total_games
            
            difficulty_stats = json.loads(current_stats[4]) if current_stats[4] else {}
            difficulty_map = {1: 'easy', 2: 'normal', 3: 'hard'}
            diff_key = difficulty_map.get(difficulty, 'normal')
            difficulty_stats[diff_key] = difficulty_stats.get(diff_key, 0) + 1
            
            current_time = datetime.datetime.now().isoformat()
            cursor.execute('''
                UPDATE game_stats 
                SET high_score = ?, total_games = ?, total_playtime = ?, 
                    average_score = ?, last_played = ?, difficulty_stats = ?
                WHERE user_id = ?
            ''', (new_high_score, new_total_games, new_total_playtime, 
                  new_average_score, current_time, 
                  json.dumps(difficulty_stats), user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Stats updated successfully'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/get-stats/<int:user_id>', methods=['GET'])
def get_stats(user_id):
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT high_score, total_games, total_playtime, average_score, difficulty_stats
            FROM game_stats WHERE user_id = ?
        ''', (user_id,))
        
        stats = cursor.fetchone()
        conn.close()
        
        if stats:
            return jsonify({
                'success': True,
                'stats': {
                    'highScore': stats[0] or 0,
                    'totalGames': stats[1] or 0,
                    'totalPlaytime': stats[2] or 0,
                    'averageScore': stats[3] or 0,
                    'difficultyStats': json.loads(stats[4]) if stats[4] else {'easy': 0, 'normal': 0, 'hard': 0}
                }
            })
        else:
            return jsonify({'success': False, 'message': 'User stats not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/user/stats', methods=['GET'])
@jwt_required
def get_user_stats():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT high_score, total_games, total_playtime, average_score, difficulty_stats
            FROM game_stats WHERE user_id = ?
        ''', (request.user_id,))
        
        stats = cursor.fetchone()
        conn.close()
        
        if stats:
            return jsonify({
                'success': True,
                'stats': {
                    'highScore': stats[0] or 0,
                    'totalGames': stats[1] or 0,
                    'totalPlaytime': stats[2] or 0,
                    'averageScore': round(stats[3] or 0, 2),
                    'difficultyStats': json.loads(stats[4]) if stats[4] else {'easy': 0, 'normal': 0, 'hard': 0}
                }
            })
        else:
            return jsonify({
                'success': True,
                'stats': {
                    'highScore': 0,
                    'totalGames': 0,
                    'totalPlaytime': 0,
                    'averageScore': 0,
                    'difficultyStats': {'easy': 0, 'normal': 0, 'hard': 0}
                }
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/user/add-score', methods=['POST'])
@jwt_required
def add_user_score():
    try:
        data = request.get_json()
        score = data.get('score', 0)
        playtime = data.get('playtime', 0)
        difficulty = data.get('difficulty', 2)
        session_start = data.get('sessionStart')
        
        if score < 0 or playtime < 0:
            return jsonify({'success': False, 'message': 'Invalid score or playtime'}), 400

        if playtime > 0:
            max_possible_score = playtime * 10
            if score > max_possible_score:
                return jsonify({'success': False, 'message': 'Score too high for playtime'}), 400

        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()

        recent_time = (datetime.datetime.now() - datetime.timedelta(seconds=10)).isoformat()
        cursor.execute('''
            SELECT COUNT(*) FROM game_sessions 
            WHERE user_id = ? AND session_end > ?
        ''', (request.user_id, recent_time))
        
        recent_count = cursor.fetchone()[0]
        if recent_count > 0:
            conn.close()
            return jsonify({'success': False, 'message': 'Too many score submissions. Please wait.'}), 429

        session_start_time = session_start if session_start else datetime.datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO game_sessions (user_id, score, playtime, difficulty, session_start, session_end)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (request.user_id, score, playtime, difficulty, session_start_time, datetime.datetime.now().isoformat()))

        cursor.execute('''
            SELECT high_score, total_games, total_playtime, average_score, difficulty_stats
            FROM game_stats WHERE user_id = ?
        ''', (request.user_id,))
        
        current_stats = cursor.fetchone()
        
        if current_stats:
            current_high_score = current_stats[0] or 0
            new_high_score = max(current_high_score, score)
            new_total_games = (current_stats[1] or 0) + 1
            new_total_playtime = (current_stats[2] or 0) + playtime
            new_average_score = ((current_stats[3] or 0) * (new_total_games - 1) + score) / new_total_games
            
            difficulty_stats = json.loads(current_stats[4]) if current_stats[4] else {}
            difficulty_map = {1: 'easy', 2: 'normal', 3: 'hard'}
            diff_key = difficulty_map.get(difficulty, 'normal')
            difficulty_stats[diff_key] = difficulty_stats.get(diff_key, 0) + 1
            
            cursor.execute('''
                UPDATE game_stats 
                SET high_score = ?, total_games = ?, total_playtime = ?, 
                    average_score = ?, last_played = ?, difficulty_stats = ?
                WHERE user_id = ?
            ''', (new_high_score, new_total_games, new_total_playtime, 
                  new_average_score, datetime.datetime.now().isoformat(), 
                  json.dumps(difficulty_stats), request.user_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Score added successfully',
                'newHighScore': new_high_score > current_high_score,
                'stats': {
                    'highScore': new_high_score,
                    'totalGames': new_total_games,
                    'totalPlaytime': new_total_playtime,
                    'averageScore': round(new_average_score, 2),
                    'difficultyStats': difficulty_stats
                }
            })
        else:
            return jsonify({'success': False, 'message': 'User stats not found'}), 404
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/user/game-sessions', methods=['GET'])
@jwt_required
def get_user_game_sessions():
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(max(limit, 1), 50)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT score, playtime, difficulty, session_start, session_end, is_completed
            FROM game_sessions 
            WHERE user_id = ?
            ORDER BY session_end DESC
            LIMIT ?
        ''', (request.user_id, limit))
        
        sessions = cursor.fetchall()
        conn.close()
        
        session_list = []
        difficulty_map = {1: 'Easy', 2: 'Normal', 3: 'Hard'}
        
        for session in sessions:
            session_list.append({
                'score': session[0],
                'playtime': session[1],
                'difficulty': difficulty_map.get(session[2], 'Normal'),
                'sessionStart': session[3],
                'sessionEnd': session[4],
                'isCompleted': bool(session[5])
            })
        
        return jsonify({
            'success': True,
            'sessions': session_list
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/leaderboard/high-scores', methods=['GET'])
def get_high_scores():
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(max(limit, 1), 50)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.username, gs.high_score, gs.last_played
            FROM game_stats gs
            JOIN users u ON gs.user_id = u.id
            WHERE gs.high_score > 0
            ORDER BY gs.high_score DESC
            LIMIT ?
        ''', (limit,))
        
        scores = cursor.fetchall()
        conn.close()
        
        leaderboard = []
        for i, (username, high_score, last_played) in enumerate(scores, 1):
            leaderboard.append({
                'rank': i,
                'username': username,
                'highScore': high_score,
                'lastPlayed': last_played
            })
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/user/rank', methods=['GET'])
@jwt_required
def get_user_rank():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT high_score FROM game_stats WHERE user_id = ?
        ''', (request.user_id,))
        
        user_score_result = cursor.fetchone()
        if not user_score_result:
            conn.close()
            return jsonify({'success': False, 'message': 'User stats not found'}), 404
        
        user_high_score = user_score_result[0] or 0
        
        cursor.execute('''
            SELECT COUNT(*) + 1 as rank
            FROM game_stats 
            WHERE high_score > ?
        ''', (user_high_score,))
        
        rank_result = cursor.fetchone()
        user_rank = rank_result[0] if rank_result else 1
        
        cursor.execute('SELECT COUNT(*) FROM game_stats WHERE high_score > 0')
        total_players_result = cursor.fetchone()
        total_players = total_players_result[0] if total_players_result else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'rank': user_rank,
            'highScore': user_high_score,
            'totalPlayers': total_players,
            'percentile': round((total_players - user_rank + 1) / max(total_players, 1) * 100, 1) if total_players > 0 else 0
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/user/profile', methods=['GET'])
@jwt_required
def get_user_profile():
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT u.email, u.username, u.created_at, u.last_login,
                   gs.high_score, gs.total_games, gs.total_playtime, gs.average_score
            FROM users u
            LEFT JOIN game_stats gs ON u.id = gs.user_id
            WHERE u.id = ?
        ''', (request.user_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return jsonify({
                'success': True,
                'profile': {
                    'email': result[0],
                    'username': result[1],
                    'createdAt': result[2],
                    'lastLogin': result[3],
                    'highScore': result[4] or 0,
                    'totalGames': result[5] or 0,
                    'totalPlaytime': result[6] or 0,
                    'averageScore': round(result[7] or 0, 2)
                }
            })
        else:
            return jsonify({'success': False, 'message': 'User not found'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.datetime.now().isoformat()})

if __name__ == '__main__':
    init_database()
    
    app.run(debug=True, host='0.0.0.0', port=8371)