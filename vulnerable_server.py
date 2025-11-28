from flask import Flask, request, render_template_string, session, redirect, url_for, flash
import os
import hashlib
import mysql.connector

app = Flask(__name__)
app.secret_key = os.urandom(24)

def get_db_connection():
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'prueba'
    }
    # Conectamos con la opción dictionary=True para poder usar nombres en lugar de números
    conn = mysql.connector.connect(**db_config)
    return conn

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

@app.route('/')
def index():
    return 'Welcome to the Task Manager Application!'

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        # Usamos cursor con diccionario para toda la app
        cursor = conn.cursor(dictionary=True)

        print(f"Intento de login con: {password}")
        
        # --- CAMINO VULNERABLE (SQL INJECTION) ---
        if "' OR '" in password:
            query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
            print("Ejecutando Query Vulnerable:", query)
            cursor.execute(query)
            user = cursor.fetchone()
        
        # --- CAMINO SEGURO ---
        else:
            hashed_password = hash_password(password)
            query = "SELECT * FROM users WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashed_password))
            user = cursor.fetchone()

        cursor.close()
        conn.close()

        # Verificamos si user existe ANTES de intentar leerlo
        if user:
            print("Usuario encontrado:", user)
            session['user_id'] = user['id']     # Usamos nombres gracias al dictionary=True
            session['role'] = user['role']
            return redirect(url_for('dashboard'))
        else:
            print("Usuario no encontrado (user es None)")
            return 'Invalid credentials!'

    return '''
        <form method="post">
            Username: <input type="text" name="username"><br>
            Password: <input type="password" name="password"><br>
            <input type="submit" value="Login">
        </form>
    '''

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM tasks WHERE user_id = %s", (user_id,))
    tasks = cursor.fetchall()
    cursor.close()
    conn.close()

    return render_template_string('''
        <h1>Welcome, user {{ user_id }}!</h1>
        <form action="/add_task" method="post">
            <input type="text" name="task" placeholder="New task"><br>
            <input type="submit" value="Add Task">
        </form>
        <h2>Your Tasks</h2>
        <ul>
        {% for task in tasks %}
            <li>{{ task['tasks'] }} <a href="/delete_task/{{ task['id'] }}">Delete</a></li>
        {% endfor %}
        </ul>
    ''', user_id=user_id, tasks=tasks)

@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    task_content = request.form['task']
    user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor() # Aquí no necesitamos diccionario
    cursor.execute("INSERT INTO tasks (user_id, tasks) VALUES (%s, %s)", (user_id, task_content))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))

@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('dashboard'))

@app.route('/admin')
def admin():
    if 'user_id' not in session or session.get('role') != 'admin':
        return redirect(url_for('login'))
    return 'Welcome to the admin panel!'

if __name__ == '__main__':
    app.run(debug=True)