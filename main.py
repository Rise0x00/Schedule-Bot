import asyncio
from telebot.async_telebot import AsyncTeleBot
from telebot import types
from telebot.types import InputMediaPhoto
import keyboards as kb
import aiosqlite
import excel_parser_solnechnaya as epsl
import excel_parser_shabulina as epsh

BOT_API_TOKEN = '7882275526:AAHkP5YZyt-RjXe8qVPqoCl3i3CFO3TaNVU'
admins = [1611784096, 1996378796, 6379037676]
authorized_users = [1611784096, 1996378796, 6379037676]

DB_NAME = "Database.db" # Имя базы данных

db_lock = asyncio.Lock() # Блокировка для работы с базой данных
bot = AsyncTeleBot(BOT_API_TOKEN) # Инициализация бота

# Словарь для хранения состояний пользователей и константы состояний
user_states = {}

STATE_WAITING_FOR_GROUP = "waiting_for_group"
STATE_WAITING_FEEDBACK = "waiting_for_feedback"

async def init_db(): # Инициализация базы данных
    async with aiosqlite.connect(DB_NAME) as db:
        # Создаем таблицу Users, если она не существует
        await db.execute('''
        CREATE TABLE IF NOT EXISTS Users (
            user_id INTEGER PRIMARY KEY,
            group_id INTEGER DEFAULT 0,
            corpus_id INTEGER DEFAULT 0)''')
        await db.commit()

async def db_execute_select(query, fetchall=False): # Выполнение выборки из БД и получение результата
    # Используем блокировку для предотвращения конкурентного доступа к БД
    async with db_lock:
        async with aiosqlite.connect(DB_NAME) as db:
            cursor = await db.execute(query)
            if fetchall:
                result = await cursor.fetchall()
            else:
                result = await cursor.fetchone()
    return result

async def get_user_settings_text(user_id):
    # Получает текущие настройки пользователя и возвращает форматированный текст
    user_data = await db_execute_select(f"SELECT group_id, corpus_id FROM Users WHERE user_id = {user_id}")
    if not user_data: return "Настройки не найдены"
    group_id, corpus_id = user_data
    group_text = f"Группа: {group_id}" if group_id != 0 else "Группа: не указана"
    corpus_name = "Солнечная" if corpus_id == 1 else "Шабулина" if corpus_id == 2 else ""
    corpus_text = f"Корпус: {corpus_id} ({corpus_name})" if corpus_id != 0 else "Корпус: не указан"
    return f"Ваши текущие настройки:\n{group_text}\n{corpus_text}"

@bot.message_handler(commands=['feedback']) # Обработчик /feedback
async def feedback_message(message):
    global user_states
    user_id = message.from_user.id
    await bot.send_message(user_id, "Опишите вашу проблему")
    user_states[user_id] = STATE_WAITING_FEEDBACK

@bot.message_handler(commands=['start']) # Обработчик /start
async def start_message(message):
    user_id = message.from_user.id
    if user_id not in authorized_users:
        await bot.send_message(user_id, "Извините, но у вас нет доступа к этому боту.")
        return
    
    # Проверяем, существует ли пользователь в БД
    user_data = await db_execute_select(f"SELECT group_id, corpus_id FROM Users WHERE user_id = {user_id}")
    
    if not user_data: # Если пользователя нет в БД, добавляем его
        async with db_lock:
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("INSERT INTO Users (user_id) VALUES (?)", (user_id,))
                await db.commit()
    
    settings_text = await get_user_settings_text(user_id)
    await bot.send_message(
        user_id, 
        f"<b>Добро пожаловать!</b>\n\n{settings_text}\n\nВыберите действие:", 
        reply_markup=kb.main_menu(),
        parse_mode='HTML')

@bot.callback_query_handler(func=lambda call: True) # Обработчик всех callback-запросов
async def process_callback(call):
    chat_id = call.message.chat.id
    user_id = call.from_user.id
    # Проверяем тип callback и выполняем соответствующие действия
    if call.data == 'setup_profile':  # Обработка запроса на настройку профиля
        await bot.edit_message_text("Выберите действие:", chat_id, call.message.id, reply_markup=kb.setup_profile())

    elif call.data == 'change_group':  # Обработка запроса на изменение группы
        # Устанавливаем состояние ожидания ввода группы
        user_states[user_id] = STATE_WAITING_FOR_GROUP
        await bot.edit_message_text("Введите номер группы:", chat_id, call.message.id, reply_markup=kb.back_to_set())

    elif call.data == 'change_corpus':  # Обработка запроса на изменение корпуса
        await bot.edit_message_text("Выберите свой корпус:", chat_id, call.message.id, reply_markup=kb.corpus_list())
    
    elif call.data == 'rasp_call': # Накостыленный костыль для изменения расписания звонков
        file_ids = [
            "AgACAgIAAxkDAAIBmGgNTkSqmJVCxjOG6AiFhPaHsW_yAAJE7jEbRnloSF1OBBA5uExIAQADAgADeAADNgQ",
            "AgACAgIAAxkDAAIBmWgNTnGiZx_k6hIEjt_uZXLOy8gYAAJF7jEbRnloSOTqxfrBPg4YAQADAgADeAADNgQ"
            ]
        try: await bot.delete_message(call.message.chat.id, call.message.id)
        except: pass
        media = [InputMediaPhoto(media=file_id, caption=f"Фото {i+1}") for i, file_id in enumerate(file_ids)]
        await bot.send_media_group(chat_id=call.message.chat.id, media=media)
        await bot.send_message(call.message.chat.id, "Расписание звонков", reply_markup=kb.back_to_mm())

    elif call.data == 'changes_today': # Накостыленный костыль для изменения расписания на сегодня
        await bot.edit_message_text("Пожалуйста, подождите...", chat_id, call.message.id, reply_markup=kb.back_to_mm()) 
        group_number = await db_execute_select(f"SELECT group_id FROM Users WHERE user_id = {user_id}")
        data = epsl.parse_data(group_number[0], "wednesday")
        string_rasp = f"<b>Изменения на cегодня для группы {group_number[0]}:</b>\n\n"
        if data[0] != False:
            for row in data[1]:
                string_rasp += f"{row[0]}\n\n "
        else:
            string_rasp += data[1]
        await bot.edit_message_text(string_rasp, chat_id, call.message.id, reply_markup=kb.back_to_mm(), parse_mode='HTML')
        
    elif call.data == 'changes_tomorrow': # Накостыленный костыль для изменения расписания на завтра
        await bot.edit_message_text("Пожалуйста, подождите...", chat_id, call.message.id, reply_markup=kb.back_to_mm())
        group_number = await db_execute_select(f"SELECT group_id FROM Users WHERE user_id = {user_id}")
        data = epsl.parse_data(group_number[0], "wednesday")
        string_rasp = f"<b>Изменения на завтра для группы {group_number[0]}:</b>\n\n"
        if data[0] != False:
            for row in data[1]:
                string_rasp += f"{row[0]}\n\n "
        else:
            string_rasp += data[1]
        await bot.edit_message_text(string_rasp, chat_id, call.message.id, reply_markup=kb.back_to_mm(), parse_mode='HTML')

    elif call.data in ["mn", "tu", "wen", "th", "fr"]: # Расписание на день недели
        await bot.edit_message_text("Пожалуйста, подождите...", chat_id, call.message.id, reply_markup=kb.back_to_mm()) 
        week = {"mn": "monday", "tu": "tuesday", "wen": "wednesday", "th": "thursday", "fr": "friday"}
        week_rus = {"mn": "понедельник", "tu": "вторник", "wen": "среда", "th": "четверг", "fr": "пятница"}
        group_number = await db_execute_select(f"SELECT group_id FROM Users WHERE user_id = {user_id}")
        corpus_id = await db_execute_select(f"SELECT corpus_id FROM Users WHERE user_id = {user_id}")
        if corpus_id[0] == 1:
            data = epsl.parse_data(group_number[0], week[call.data])
        elif corpus_id[0] == 2:
            data = epsh.parse_data(group_number[0], week[call.data])
        string_rasp = f"<b>Расписание на {week_rus[call.data]} для группы {group_number[0]}:</b>\n\n"
        if data[0] != False:
            for row in data[1]:
                string_rasp += f"{row[0]}\n\n "
        else:
            string_rasp += data[1]
        await bot.edit_message_text(string_rasp, chat_id, call.message.id, reply_markup=kb.back_to_mm(), parse_mode='HTML')

    elif call.data.startswith('set_corpus_'):  # Обработка выбора корпуса
        corpus_number = int(call.data.split('_')[-1])
        # Обновляем корпус в БД
        async with db_lock:
            async with aiosqlite.connect(DB_NAME) as db:
                await db.execute("UPDATE Users SET corpus_id = ? WHERE user_id = ?", (corpus_number, user_id))
                await db.commit()
        settings_text = await get_user_settings_text(user_id)
        # Отправляем сообщение с обновленными данными
        await bot.edit_message_text(
            f"<b>Корпус успешно обновлен!</b>\n\n{settings_text}\n\nВыберите действие:", 
            chat_id, call.message.id, reply_markup=kb.main_menu(),
            parse_mode='HTML')
        
    elif call.data == 'back_to_main':  # Обработка запроса на возврат в главное меню
        # Сбрасываем состояние пользователя, если оно существует
        if user_id in user_states:
            del user_states[user_id]
        # Получаем данные пользователя из базы
        settings_text = await get_user_settings_text(user_id)
        await bot.edit_message_text(f"<b>Добро пожаловать!</b>\n\n{settings_text}\n\nВыберите действие:", chat_id, call.message.id, reply_markup=kb.main_menu(), parse_mode='HTML')
    
    elif call.data == 'back_to_setup':  # Обработка запроса на возврат в настройку профиля
        if user_id in user_states:
            del user_states[user_id]
        await bot.edit_message_text("Выберите действие:", chat_id, call.message.id, reply_markup=kb.setup_profile())

# Обработчик текстовых сообщений для обратной связи
@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == STATE_WAITING_FEEDBACK)
async def process_feedback(message):
    global user_states
    user_id = message.from_user.id
    for i in admins:
        await bot.send_message(i, f'Получена обратная связь от пользователя <b>{user_id}</b>:\n\n{message.text}', parse_mode='HTML')
    settings_text = await get_user_settings_text(user_id)

    await bot.send_message(user_id,
        f"<b>Сообщение отправлено!</b>\n\n{settings_text}\n\nВыберите действие:", 
        reply_markup=kb.main_menu(),
        parse_mode='HTML')
    if user_id in user_states:
        del user_states[user_id]

# Обработчик текстовых сообщений для ввода группы
@bot.message_handler(func=lambda message: message.from_user.id in user_states and user_states[message.from_user.id] == STATE_WAITING_FOR_GROUP)
async def process_group_input(message):
    user_id = message.from_user.id
    group_number = message.text.strip()

    # Проверяем, что введено число
    if not group_number.isdigit():
        await bot.send_message(user_id, "Пожалуйста, введите корректный номер группы (только цифры):")
        return
    
    find1 = epsl.find_cells(f"new_data.xlsx", group_number)
    find2 = epsh.find_cells(f"data_2.xlsx", group_number)

    if (find1 == []) and (find2 == []):
        await bot.send_message(user_id, "Пожалуйста, введите номер существующей группы (только цифры):")
        return
    
    # Сбрасываем состояние пользователя
    del user_states[user_id]

    # Обновляем группу в базе данных
    async with db_lock:
        async with aiosqlite.connect(DB_NAME) as db:
            await db.execute("UPDATE Users SET group_id = ? WHERE user_id = ?", (int(group_number), user_id))
            await db.commit()
    
    # Получаем обновленные данные пользователя
    settings_text = await get_user_settings_text(user_id)
    await bot.send_message(
        user_id, 
        f"<b>Номер группы успешно обновлен!</b>\n\n{settings_text}\n\nВыберите действие:", 
        reply_markup=kb.main_menu(),
        parse_mode='HTML')

async def main():
    # Запуск бесконечного опроса сервера Telegram
    await bot.infinity_polling(timeout=30, skip_pending=True)

async def startup():
    await init_db() # Инициализация БД перед запуском бота
    await main() # Запуск бота

if __name__ == '__main__':
    asyncio.run(startup()) # Точка входа в программу