import telebot
from telebot import types
from datetime import datetime, timedelta
import threading
import time
import matplotlib.pyplot as plt
from io import BytesIO

import os
TOKEN = os.environ.get("TOKEN")
bot = telebot.TeleBot(TOKEN)


# ===== Пример данных =====
duty_list = [
    {"user_id": 123456789, "name": "Иван", "date": "2025-12-09", "time": "08:00"},
    {"user_id": 987654321, "name": "Мария", "date": "2025-12-09", "time": "10:00"}
]

events_list = [
    {"name": "Собрание", "date": "2025-12-10", "time": "14:00"},
    {"name": "Конференция", "date": "2025-12-11", "time": "16:00"}
]

polls = {}  # для хранения опросов: {poll_id: {"question": str, "options": [str], "votes": {user_id: option_index}}}


# ===== Функции напоминаний =====
def reminder_loop():
    while True:
        now = datetime.now()
        # Дежурства
        for duty in duty_list:
            duty_time = datetime.strptime(duty["date"] + " " + duty["time"], "%Y-%m-%d %H:%M")
            if 0 <= (duty_time - now).total_seconds() <= 60:
                bot.send_message(duty["user_id"],
                                 f"Напоминание: сегодня дежурство в {duty['time']}. Пожалуйста, пришлите доказательство (фото кружка).")

        # Мероприятия
        for event in events_list:
            event_time = datetime.strptime(event["date"] + " " + event["time"], "%Y-%m-%d %H:%M")
            for duty in duty_list:  # уведомляем всех дежурных, можно менять
                if 0 <= (event_time - now).total_seconds() <= 60:
                    bot.send_message(duty["user_id"],
                                     f"Напоминание: мероприятие '{event['name']}' начинается {event['time']}.")

        time.sleep(60)  # проверка каждую минуту


# ===== Меню =====
def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    btn1 = types.KeyboardButton("/start")
    btn2 = types.KeyboardButton("/about")
    btn3 = types.KeyboardButton("/events")
    btn4 = types.KeyboardButton("/news")
    btn5 = types.KeyboardButton("/duty")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup


# ===== Команды =====
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id,
                     "Добро пожаловать в Ассистент Парламента! Выберите команду в меню.",
                     reply_markup=main_menu())


@bot.message_handler(commands=['about'])
def about(message):
    bot.send_message(message.chat.id,
                     "Ассистент Парламента — цифровой помощник для управления дежурствами и мероприятиями. "
                     "Функции: напоминания, опросы, новости, мероприятия.", reply_markup=main_menu())


@bot.message_handler(commands=['events'])
def events(message):
    text = "Список ближайших мероприятий:\n"
    for event in events_list:
        text += f"{event['name']} — {event['date']} в {event['time']}\n"
    bot.send_message(message.chat.id, text, reply_markup=main_menu())


@bot.message_handler(commands=['news'])
def news(message):
    # пример новостей
    bot.send_message(message.chat.id, "Новости пока отсутствуют.", reply_markup=main_menu())


@bot.message_handler(commands=['duty'])
def duty(message):
    text = "Дежурства:\n"
    for duty in duty_list:
        text += f"{duty['name']} — {duty['date']} в {duty['time']}\n"
    bot.send_message(message.chat.id, text, reply_markup=main_menu())


# ===== Обработка фото-доказательств =====
@bot.message_handler(content_types=['photo'])
def photo_handler(message):
    bot.reply_to(message, "Спасибо, доказательство получено!")


# ===== Создание опроса =====
@bot.message_handler(commands=['create_poll'])
def create_poll(message):
    # Пример: /create_poll Вопрос;Вариант1;Вариант2;Вариант3
    try:
        content = message.text.split(' ', 1)[1]
        question, *options = content.split(';')
        poll_id = len(polls) + 1
        polls[poll_id] = {"question": question, "options": options, "votes": {}}
        text = f"Создан опрос #{poll_id}: {question}\n"
        for i, opt in enumerate(options, 1):
            text += f"{i}. {opt}\n"
        bot.send_message(message.chat.id, text)
        bot.send_message(message.chat.id, f"Голосуйте с помощью команды /vote {poll_id} <номер_варианта>")
    except:
        bot.send_message(message.chat.id, "Неправильный формат. Пример: /create_poll Вопрос;Вариант1;Вариант2;Вариант3")


# ===== Голосование =====
@bot.message_handler(commands=['vote'])
def vote_poll(message):
    try:
        parts = message.text.split()
        poll_id = int(parts[1])
        option = int(parts[2]) - 1
        user_id = message.from_user.id
        if poll_id in polls and 0 <= option < len(polls[poll_id]["options"]):
            polls[poll_id]["votes"][user_id] = option
            bot.send_message(message.chat.id, "Ваш голос учтён!")
        else:
            bot.send_message(message.chat.id, "Неверный ID опроса или номер варианта.")
    except:
        bot.send_message(message.chat.id, "Неправильный формат. Пример: /vote 1 2")


# ===== Показать результаты =====
@bot.message_handler(commands=['poll_results'])
def poll_results(message):
    try:
        poll_id = int(message.text.split()[1])
        if poll_id not in polls:
            bot.send_message(message.chat.id, "Такого опроса нет.")
            return

        poll = polls[poll_id]
        options = poll["options"]
        votes_count = [0]*len(options)
        for vote in poll["votes"].values():
            votes_count[vote] += 1

        # Построить график
        plt.figure(figsize=(6,4))
        plt.bar(options, votes_count, color='blue')
        plt.title(poll["question"])
        plt.ylabel("Количество голосов")
        plt.tight_layout()

        bio = BytesIO()
        plt.savefig(bio, format='png')
        bio.seek(0)
        bot.send_photo(message.chat.id, bio)
        plt.close()

    except:
        bot.send_message(message.chat.id, "Ошибка при показе результатов. Пример: /poll_results 1")


# ===== Запуск напоминаний в отдельном потоке =====
threading.Thread(target=reminder_loop, daemon=True).start()

# ===== Запуск бота =====
bot.polling(none_stop=True)

