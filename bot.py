import threading
import time
import random
import telebot
import pymysql
from datetime import datetime

# Конфигурация базы данных
db_config = {
    'host': 'mysql.j1007852.myjino.ru',
    'port': 3306,
    'user': 'j1007852',
    'password': 'el|N#2}-F8',
    'database': 'j1007852_lr1_bg'
}

# Инициализация Телеграм-бота
bot = telebot.TeleBot("8140304603:AAEtbvL4ZEtrEYBeou1YJape5dSJkAII_zY")

# Подключение к базе данных
connection = pymysql.connect(**db_config)
cursor = connection.cursor()

# Создание таблиц, если они не существуют
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    join_date DATETIME DEFAULT CURRENT_TIMESTAMP
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS command_usage (
    id INT AUTO_INCREMENT PRIMARY KEY,
    command VARCHAR(255) NOT NULL,
    usage_count INT DEFAULT 0,
    last_used DATETIME DEFAULT CURRENT_TIMESTAMP
);
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS messages (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    text TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
''')

connection.commit()

# Словарь для случайного сообщения при запуске
messages_dict = {
    1: "Привет!",
    2: "Добро пожаловать!",
    3: "Хорошего дня!",
    4: "Давайте начнем!",
    5: "Удачи!"
}

# Файл для случайных сообщений по таймеру
file_path = 'йоу.txt'

# Функция для сохранения сообщения в базу данных
def save_message_to_db(user_id, username, text):
    cursor.execute("SELECT id FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if not user:
        cursor.execute("INSERT INTO users (id, username) VALUES (%s, %s)", (user_id, username))
        connection.commit()

    cursor.execute("INSERT INTO messages (user_id, text, timestamp) VALUES (%s, %s, %s)",
                   (user_id, text, datetime.now()))
    connection.commit()

def increment_command_usage(command):
    """Увеличивает счетчик использования команды."""
    cursor.execute("SELECT id FROM command_usage WHERE command = %s", (command,))
    if cursor.fetchone():
        cursor.execute(
            """
            UPDATE command_usage
            SET usage_count = usage_count + 1, last_used = %s
            WHERE command = %s
            """,
            (datetime.now(), command)
        )
    else:
        cursor.execute(
            "INSERT INTO command_usage (command, usage_count, last_used) VALUES (%s, %s, %s)",
            (command, 1, datetime.now())
        )
    connection.commit()

# Обработчики Телеграм-бота
@bot.message_handler(commands=['start'])
def start_message(message):
    increment_command_usage('/start')
    random_message = random.choice(list(messages_dict.values()))
    bot.reply_to(message, random_message)
    save_message_to_db(message.from_user.id, message.from_user.username or "Unknown", "Добро пожаловать в бота!")

@bot.message_handler(commands=['help'])
def help_message(message):
    increment_command_usage('/help')
    help_text = (
        "/start - Запуск бота, отправка случайного приветственного сообщения.\n"
        "/start_timer - Запуск периодической отправки случайного сообщения из файла.\n"
        "/game - Начать простую игру со стоп-словом 'стоп'.\n"
        "/help - Вывод списка команд и их описание."
    )
    bot.reply_to(message, help_text)
    save_message_to_db(message.from_user.id, message.from_user.username or "Unknown", help_text)

# Функция для периодической отправки случайных сообщений
def send_random_message_periodically(chat_id, interval=10):
    while True:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()
            if lines:
                random_line = random.choice(lines).strip()
                bot.send_message(chat_id, random_line)
                # Сохраняем сообщение в файл
                save_message_to_db(chat_id, "Bot", random_line)
        time.sleep(interval)

@bot.message_handler(commands=['start_timer'])
def start_timer_message(message):
    increment_command_usage('/start_timer')
    chat_id = message.chat.id
    interval = 10  # секунды, можно изменить
    for i in range(5):
        threading.Thread(target=send_random_message_periodically, args=(chat_id, interval), daemon=True).start()


@bot.message_handler(commands=['game'])
def start_game(message):
    increment_command_usage('/game')
    chat_id = message.chat.id
    bot.send_message(chat_id, "Игра началась! Напишите любое сообщение, а я повторю его. Напишите 'стоп', чтобы завершить игру.")

    # Определяем функцию для обработки сообщений в процессе игры
    def game_handler(msg):
        if msg.text.lower() == 'стоп':
            bot.send_message(chat_id, "Игра завершена. Спасибо за игру!")
            bot.clear_step_handler_by_chat_id(chat_id)  # Убираем обработчик, чтобы завершить игру
        else:
            bot.send_message(chat_id, f"Вы сказали: {msg.text}")
            bot.register_next_step_handler(msg, game_handler)  # Повторная регистрация обработчика

    # Запускаем обработчик для первого сообщения
    bot.register_next_step_handler(message, game_handler)


@bot.message_handler(func=lambda message: True)
def handle_message(message):
    bot.reply_to(message, f"Вы сказали: {message.text}")
    save_message_to_db(message.from_user.id, message.from_user.username or "Unknown", message.text)

# Функция запуска бота
def start_bot():
    bot.polling()