from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import smtplib
import secrets
import hashlib
import datetime
import json
import os
import re
import jwt
from functools import wraps
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
CORS(app)

JWT_SECRET = os.getenv('JWT_SECRET', 'rock-runner-secret-key-' + secrets.token_hex(16))
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

SMTP_SERVER = "smtp.dreamhost.com"
SMTP_PORT = 587
EMAIL_ADDRESS = ""
EMAIL_PASSWORD = ""

DB_NAME = "game_users.db"

def init_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP,
            is_verified BOOLEAN DEFAULT FALSE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS otp_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL,
            code TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NOT NULL,
            used BOOLEAN DEFAULT FALSE
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
    
    conn.commit()
    conn.close()

def validate_email_format(email):
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None

def send_otp_email(email, otp_code):
    try:
        msg = MIMEMultipart('alternative')
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = email
        msg['Subject'] = "🚀 Rock Runner - Your Space Access Code"
        
        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Rock Runner - Access Code</title>
            <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap" rel="stylesheet">
        </head>
        <body style="
            margin: 0;
            padding: 0;
            background: linear-gradient(135deg, #0f0f23 0%, #16213e 50%, #0f3460 100%);
            font-family: 'Orbitron', monospace;
            color: #ffd700;
            min-height: 100vh;
        ">
            <div style="
                max-width: 600px;
                margin: 0 auto;
                padding: 40px 20px;
            ">
                <!-- Header -->
                <div style="
                    text-align: center;
                    margin-bottom: 40px;
                ">
                    <h1 style="
                        color: #ffd700;
                        font-size: 2.5em;
                        font-weight: 900;
                        margin: 0;
                        text-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
                        letter-spacing: 3px;
                    ">🚀 ROCK RUNNER</h1>
                    <p style="
                        color: #00ffff;
                        font-size: 1.1em;
                        margin: 10px 0 0 0;
                        letter-spacing: 1px;
                    ">SPACE ADVENTURE GAME</p>
                </div>
                
                <!-- Main Content -->
                <div style="
                    background: rgba(26, 26, 46, 0.8);
                    border: 2px solid #ffd700;
                    border-radius: 15px;
                    padding: 30px;
                    text-align: center;
                    box-shadow: 0 0 30px rgba(255, 215, 0, 0.3);
                ">
                    <h2 style="
                        color: #ffd700;
                        font-size: 1.8em;
                        margin: 0 0 20px 0;
                        font-weight: 700;
                    ">🔐 SECURE ACCESS CODE</h2>
                    
                    <p style="
                        color: #ffffff;
                        font-size: 1.1em;
                        line-height: 1.6;
                        margin: 20px 0;
                    ">Your space mission access code is ready, Commander!</p>
                    
                    <!-- OTP Code Box -->
                    <div style="
                        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
                        border: 3px solid #00ffff;
                        border-radius: 12px;
                        padding: 25px;
                        margin: 30px 0;
                        box-shadow: 0 0 25px rgba(0, 255, 255, 0.4);
                    ">
                        <p style="
                            color: #00ffff;
                            font-size: 0.9em;
                            margin: 0 0 10px 0;
                            letter-spacing: 1px;
                        ">ACCESS CODE</p>
                        <div style="
                            color: #ffd700;
                            font-size: 3em;
                            font-weight: 900;
                            letter-spacing: 8px;
                            text-shadow: 0 0 15px rgba(255, 215, 0, 0.6);
                            margin: 0;
                        ">{otp_code}</div>
                    </div>
                    
                    <!-- Instructions -->
                    <div style="
                        background: rgba(255, 215, 0, 0.1);
                        border-left: 4px solid #ffd700;
                        padding: 20px;
                        margin: 25px 0;
                        text-align: left;
                    ">
                        <p style="
                            color: #ffffff;
                            margin: 0 0 10px 0;
                            font-size: 1em;
                            line-height: 1.5;
                        "><strong style="color: #ffd700;">⏱️ Mission Time:</strong> This code expires in 10 minutes</p>
                        <p style="
                            color: #ffffff;
                            margin: 0 0 10px 0;
                            font-size: 1em;
                            line-height: 1.5;
                        "><strong style="color: #ffd700;">🎯 Mission Objective:</strong> Enter this code in your game login</p>
                        <p style="
                            color: #ffffff;
                            margin: 0;
                            font-size: 1em;
                            line-height: 1.5;
                        "><strong style="color: #ffd700;">🔒 Security Note:</strong> Use this code only once</p>
                    </div>
                    
                    <p style="
                        color: #888;
                        font-size: 0.9em;
                        margin: 25px 0 0 0;
                        line-height: 1.4;
                    ">If you didn't request this code, please ignore this transmission. Your account remains secure.</p>
                </div>
                
                <!-- Footer -->
                <div style="
                    text-align: center;
                    margin-top: 40px;
                    padding-top: 20px;
                    border-top: 1px solid rgba(255, 215, 0, 0.3);
                ">
                    <p style="
                        color: #00ffff;
                        font-size: 1.1em;
                        margin: 0 0 10px 0;
                        font-weight: 700;
                    ">🌟 READY FOR ADVENTURE? 🌟</p>
                    <p style="
                        color: #888;
                        font-size: 0.8em;
                        margin: 0;
                    ">Rock Runner Space Command Center<br>
                    Automated Mission Control System</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_body = f"""
        ROCK RUNNER - Space Access Code
        
        Your mission access code: {otp_code}
        
        This code expires in 10 minutes.
        Enter it in your game login to continue your space adventure!
        
        If you didn't request this code, please ignore this message.
        
        Happy gaming, Commander!
        - Rock Runner Space Command
        """
        
        part1 = MIMEText(text_body, 'plain')
        part2 = MIMEText(html_body, 'html')
        
        msg.attach(part1)
        msg.attach(part2)
        
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        text = msg.as_string()
        server.sendmail(EMAIL_ADDRESS, email, text)
        server.quit()
        
        return True
    except Exception as e:
        print(f"Email sending failed: {e}")
        return False

def generate_otp():
    return f"{secrets.randbelow(900000) + 100000}"

def hash_code(code):
    return hashlib.sha256(code.encode()).hexdigest()

def generate_jwt_token(user_id, email, username):
    payload = {
        'user_id': user_id,
        'email': email,
        'username': username,
        'iat': datetime.datetime.utcnow(),
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=JWT_EXPIRATION_HOURS)
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
                token = auth_header.split(" ")[1]  # Bearer <token>
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

@app.route('/api/request-otp', methods=['POST'])
def request_otp():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        username = data.get('username', '').strip()
        
        if not email or not username:
            return jsonify({'success': False, 'message': 'Email and username are required'}), 400
        
        if not validate_email_format(email):
            return jsonify({'success': False, 'message': 'Invalid email format'}), 400
        
        if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
            return jsonify({'success': False, 'message': 'Email service not configured'}), 500
        
        otp_code = generate_otp()
        hashed_code = hash_code(otp_code)
        
        expires_at = datetime.datetime.now() + datetime.timedelta(minutes=10)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('DELETE FROM otp_codes WHERE email = ? AND expires_at < ?', 
                      (email, datetime.datetime.now()))
        
        cursor.execute('''
            INSERT INTO otp_codes (email, code, expires_at)
            VALUES (?, ?, ?)
        ''', (email, hashed_code, expires_at))
        
        conn.commit()
        conn.close()
        
        if send_otp_email(email, otp_code):
            return jsonify({
                'success': True,
                'message': 'OTP sent to your email. Check your inbox!'
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Failed to send email. Please try again.'
            }), 500
            
    except Exception as e:
        print(f"Error requesting OTP: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/verify-otp', methods=['POST'])
def verify_otp():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        username = data.get('username', '').strip()
        otp_code = data.get('otp', '').strip()
        
        if not email or not username or not otp_code:
            return jsonify({'success': False, 'message': 'All fields are required'}), 400
        
        hashed_code = hash_code(otp_code)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id FROM otp_codes 
            WHERE email = ? AND code = ? AND expires_at > ? AND used = FALSE
        ''', (email, hashed_code, datetime.datetime.now()))
        
        otp_record = cursor.fetchone()
        
        if not otp_record:
            conn.close()
            return jsonify({'success': False, 'message': 'Invalid or expired OTP'}), 400
        
        cursor.execute('UPDATE otp_codes SET used = TRUE WHERE id = ?', (otp_record[0],))
        
        cursor.execute('SELECT id, username FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        
        if user:
            user_id = user[0]
            cursor.execute('UPDATE users SET last_login = ? WHERE id = ?', 
                          (datetime.datetime.now(), user_id))
        else:
            cursor.execute('''
                INSERT INTO users (email, username, last_login, is_verified)
                VALUES (?, ?, ?, TRUE)
            ''', (email, username, datetime.datetime.now()))
            user_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO game_stats (user_id, difficulty_stats)
                VALUES (?, ?)
            ''', (user_id, json.dumps({'easy': 0, 'normal': 0, 'hard': 0})))
        
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
        
        return jsonify({
            'success': True,
            'message': 'Login successful!',
            'token': token,
            'user': {
                'id': user_id,
                'email': email,
                'username': username,
                'stats': stats_data
            }
        })
        
    except Exception as e:
        print(f"Error verifying OTP: {e}")
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
            
            cursor.execute('''
                UPDATE game_stats 
                SET high_score = ?, total_games = ?, total_playtime = ?, 
                    average_score = ?, last_played = ?, difficulty_stats = ?
                WHERE user_id = ?
            ''', (new_high_score, new_total_games, new_total_playtime, 
                  new_average_score, datetime.datetime.now(), 
                  json.dumps(difficulty_stats), user_id))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Stats updated successfully'})
        
    except Exception as e:
        print(f"Error updating stats: {e}")
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
        print(f"Error getting stats: {e}")
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
        print(f"Error getting user stats: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/user/update-score', methods=['POST'])
@jwt_required
def update_user_score():
    try:
        data = request.get_json()
        score = data.get('score', 0)
        playtime = data.get('playtime', 0)
        difficulty = data.get('difficulty', 2)  # Default to normal
        
        if score < 0 or playtime < 0:
            return jsonify({'success': False, 'message': 'Invalid score or playtime'}), 400
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT high_score, total_games, total_playtime, average_score, difficulty_stats
            FROM game_stats WHERE user_id = ?
        ''', (request.user_id,))
        
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
            
            cursor.execute('''
                UPDATE game_stats 
                SET high_score = ?, total_games = ?, total_playtime = ?, 
                    average_score = ?, last_played = ?, difficulty_stats = ?
                WHERE user_id = ?
            ''', (new_high_score, new_total_games, new_total_playtime, 
                  new_average_score, datetime.datetime.now(), 
                  json.dumps(difficulty_stats), request.user_id))
            
            conn.commit()
            conn.close()
            
            return jsonify({
                'success': True,
                'message': 'Score updated successfully',
                'newHighScore': new_high_score > (current_stats[0] or 0),
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
        print(f"Error updating user score: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/leaderboard/high-scores', methods=['GET'])
def get_high_scores():
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(max(limit, 1), 50)  # Limit between 1 and 50
        
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
        print(f"Error getting high scores: {e}")
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
        print(f"Error getting user rank: {e}")
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
        print(f"Error getting user profile: {e}")
        return jsonify({'success': False, 'message': 'Server error'}), 500

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.datetime.now().isoformat()})

if __name__ == '__main__':
    init_database()
    
    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS', '')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
    
    if not EMAIL_ADDRESS or not EMAIL_PASSWORD:
        print("WARNING: Email credentials not set. Set EMAIL_ADDRESS and EMAIL_PASSWORD environment variables.")
        print("Example: export EMAIL_ADDRESS='your-email@domain.com'")
        print("Example: export EMAIL_PASSWORD='your-password'")
    
    print("Starting Rock Runner API Server...")
    print(f"Database: {DB_NAME}")
    print(f"SMTP Server: {SMTP_SERVER}:{SMTP_PORT}")
    
    app.run(debug=True, host='0.0.0.0', port=8371)