from flask import Flask, render_template, request, redirect, session, flash
import os
import threading
import pymysql
from bot import start_bot

# Конфигурация базы данных
db_config = {
    'host': 'mysql.j1007852.myjino.ru',
    'port': 3306,
    'user': 'j1007852',
    'password': 'el|N#2}-F8',
    'database': 'j1007852_lr1_bg'
}

# Flask-приложение
app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # Секретный ключ для сессий

# Функция для подключения к базе данных
def get_db_connection():
    return pymysql.connect(**db_config)

@app.route('/')
def index():
    if 'username' in session:
        return render_template('index.html')
    return "<h1>Добро пожаловать на сайт!</h1><a href='/login'>Войти</a> или <a href='/register'>Зарегистрироваться</a>"

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not password:
            flash('Имя пользователя и пароль обязательны!', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Пароли не совпадают!', 'error')
            return render_template('register.html')

        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Проверяем, существует ли пользователь
                cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cursor.fetchone():
                    flash('Пользователь уже существует!', 'error')
                    return render_template('register.html')

                # Добавляем пользователя
                cursor.execute(
                    "INSERT INTO users (username, password) VALUES (%s, %s)",
                    (username, password)
                )
                conn.commit()
                flash('Регистрация успешна! Теперь вы можете войти.', 'success')
                return redirect('/login')
        except Exception as e:
            flash(f'Ошибка регистрации: {e}', 'error')
            return render_template('register.html')
        finally:
            conn.close()

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        try:
            conn = get_db_connection()
            with conn.cursor() as cursor:
                # Проверяем пользователя
                cursor.execute(
                    "SELECT id FROM users WHERE username = %s AND password = %s",
                    (username, password)
                )
                user = cursor.fetchone()
                if user:
                    session['username'] = username
                    flash('Вы успешно вошли!', 'success')
                    return redirect('/')
                else:
                    flash('Неверное имя пользователя или пароль!', 'error')
        except Exception as e:
            flash(f'Ошибка входа: {e}', 'error')
        finally:
            conn.close()

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('Вы вышли из системы.', 'success')
    return redirect('/')

FILE_PATH = "йоу.txt"

@app.route('/view_commands')
def view_commands():
    commands = [
        "/start - Запуск бота",
        "/help - Список команд",
        "/start_timer - Запуск таймера"
    ]
    return render_template('index.html', commands=commands)

@app.route('/view_random_messages')
def view_random_messages():
    if not os.path.exists(FILE_PATH):
        random_messages = []
    else:
        with open(FILE_PATH, 'r', encoding='utf-8') as file:
            random_messages = file.readlines()
    return render_template('index.html', random_messages=[msg.strip() for msg in random_messages])

@app.route('/add_random_message', methods=['POST'])
def add_random_message():
    message = request.form['random_message']
    with open(FILE_PATH, 'a', encoding='utf-8') as file:
        file.write(f"{message}\n")
    return redirect('/view_random_messages')

@app.route('/statistics')
def command_statistics():
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT command, usage_count FROM command_usage ORDER BY usage_count DESC")
            stats = cursor.fetchall()

        # Формируем данные для графика
        commands = [row[0] for row in stats]
        usage_counts = [row[1] for row in stats]

        return render_template('statistics.html', stats=stats, commands=commands, usage_counts=usage_counts)
    except Exception as e:
        flash(f"Ошибка загрузки статистики: {e}", "error")
        return redirect('/')
    finally:
        conn.close()



def run_flask():
    app.run(debug=True, port=5000)

if __name__ == '__main__':
    # Запускаем Telegram-бота в отдельном потоке
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()

    # Запускаем Flask-приложение
    run_flask()