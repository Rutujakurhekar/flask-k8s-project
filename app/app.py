from flask import Flask, jsonify
import psycopg2
import os

app = Flask(__name__)

def get_db_connection():
    conn = psycopg2.connect(
        host=os.environ.get('DB_HOST', 'localhost'),
        database=os.environ.get('DB_NAME', 'appdb'),
        user=os.environ.get('DB_USER', 'postgres'),
        password=os.environ.get('DB_PASSWORD', 'password')
    )
    return conn

@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

@app.route('/ready')
def ready():
    try:
        conn = get_db_connection()
        conn.close()
        return jsonify({"status": "ready", "db": "connected"}), 200
    except Exception as e:
        return jsonify({"status": "not ready", "error": str(e)}), 503

@app.route('/users')
def get_users():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('SELECT id, name, email FROM users;')
        users = cur.fetchall()
        cur.close()
        conn.close()
        return jsonify({"users": [
            {"id": u[0], "name": u[1], "email": u[2]} 
            for u in users
        ]}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/init')
def init_db():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100),
                email VARCHAR(100)
            );
        ''')
        cur.execute('''
            INSERT INTO users (name, email) 
            VALUES ('Rutuja Kurhekar', 'rutuja@example.com')
            ON CONFLICT DO NOTHING;
        ''')
        conn.commit()
        cur.close()
        conn.close()
        return jsonify({"status": "database initialized"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
