from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

def main_menu():
    markup_main = types.InlineKeyboardMarkup()
    markup_main.add(types.InlineKeyboardButton('🔧 Настроить профиль', callback_data='setup_profile'))
    markup_main.add(types.InlineKeyboardButton('📅 Изменения на сегодня', callback_data='changes_today'))
    markup_main.add(types.InlineKeyboardButton('📅 Изменения на завтра', callback_data='changes_tomorrow'))
    
    markup_main.row(
    types.InlineKeyboardButton('Пн', callback_data='mn'),
    types.InlineKeyboardButton('Вт', callback_data='tu'),
    types.InlineKeyboardButton('Ср', callback_data='wen'),
    types.InlineKeyboardButton('Чт', callback_data='th'),
    types.InlineKeyboardButton('Пт', callback_data='fr')
    )
    markup_main.add(types.InlineKeyboardButton('⏰Рассписание звонков', callback_data='rasp_call'))

    return markup_main

def setup_profile():
    markup_setup = types.InlineKeyboardMarkup()
    markup_setup.add(types.InlineKeyboardButton('👥 Изменить группу', callback_data='change_group'))
    markup_setup.add(types.InlineKeyboardButton('🗺 Изменить корпус', callback_data='change_corpus'))
    markup_setup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
    return markup_setup

def back_to_set():
    markup_change_group = types.InlineKeyboardMarkup()
    markup_change_group.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_setup'))
    return markup_change_group

def back_to_mm():
    btm = types.InlineKeyboardMarkup()
    btm.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_main'))
    return btm

def corpus_list():
    markup_corpus_list = types.InlineKeyboardMarkup()
    markup_corpus_list.add(types.InlineKeyboardButton('Корпус 1 (Солнечная)', callback_data='set_corpus_1'))
    markup_corpus_list.add(types.InlineKeyboardButton('Корпус 2 (Шабулина)', callback_data='set_corpus_2'))
    markup_corpus_list.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_setup'))
    return markup_corpus_list