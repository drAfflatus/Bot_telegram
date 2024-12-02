"""
Файл запуска программы
"""
import psycopg2
from dic_fun import *


print('Starting bot of telegram')
load_dotenv()
user_db = os.getenv("USER")
password_db = os.getenv("PASSWORD")
port_db = os.getenv("PORT")
base_db = os.getenv("BASENAME")
host_db = os.getenv("HOST")
token_bot = os.getenv("TOKEN_BOT")

conn = psycopg2.connect(
    database=base_db,
    user=user_db,
    password=password_db,
    host=host_db,
    port=port_db
)
cur = conn.cursor()
# ------------------------------------------
# drop_tables(cur, conn)
create_tables(cur, conn)
# ------------------------------------------
state_storage = StateMemoryStorage()

bot = TeleBot(token_bot, state_storage=state_storage)

read_from_json('words.json', cur, conn)

known_users = []
userStep = {}
buttons = []

"""
Функция соединения
"""


def show_hint(*lines):
    return '\n'.join(lines)


"""
Функция соединения пары слов: целевого и его перевода
"""


def show_target(data):
    return f"{data['target_word']} -> {data['translate_word']}"


class Command:
    DELETE_WORD = 'Удалить слово🔙'
    NEXT = 'Дальше ⏭'


class MyStates(StatesGroup):
    target_word = State()
    translate_word = State()
    another_words = State()


def get_user_step(uid):
    if uid in userStep:
        return userStep[uid]
    else:
        known_users.append(uid)
        userStep[uid] = 0
        print("New user detected, who hasn't used \"/start\" yet")
        return 0


@bot.message_handler(commands=['cards', 'start', 'go'])
def create_cards(message):
    cid = message.chat.id
    id_member = message.from_user.id
    if cid not in known_users:
        tuc_tuc_member(cur, conn, id_member)

        known_users.append(cid)
        userStep[cid] = 0
        bot.send_message(cid, f"Привет, {message.from_user.first_name},"
                              f" давай учить английский ...\n"
                              f" Я знаю 8000 слов \n Ты можешь добавить"
                              f" свои слова ... надо лишь\n"
                              f"ввести строку в формате: ///"
                              f" English word - русское слово\n "
                              f"Запомнил ?! Поехали !!!....")
    markup = types.ReplyKeyboardMarkup(row_width=2)

    global buttons
    buttons = []

    tw = get_target_word_from_base(cid, cur, conn)
    target_word = tw[0][1].upper()  # брать из БД
    translate = tw[0][2].upper()  # брать из БД
    level = tw[0][3]  # брать из БД
    id_word = tw[0][0]

    """ тащим из базы какоето кол-во английских слов- обманок. проверяем   
        чтобы в обмане не было нашего нужного слова и отбираем три для декорации
    """
    set_words_many = set(random.sample(ghost_english_words(cur, conn), 4))
    set_words_one = set(translate)
    res_list = list(set_words_many.difference(set_words_one))[:3]

    target_word_btn = types.KeyboardButton(target_word)
    buttons.append(target_word_btn)

    others = [res_list[0][0].upper(), res_list[1][0].upper(),
              res_list[2][0].upper()]  # из базы брать случайные англ слова
    other_words_btns = [types.KeyboardButton(word) for word in others]
    buttons.extend(other_words_btns)
    random.shuffle(buttons)
    next_btn = types.KeyboardButton(Command.NEXT)
    delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
    buttons.extend([next_btn, delete_word_btn])

    markup.add(*buttons)

    greeting = f"Выбери перевод слова:\n🇷🇺 {translate}"
    bot.send_message(message.chat.id, greeting, reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = target_word
        data['translate_word'] = translate
        data['other_words'] = others
        data['id_word'] = id_word
        data['level_word'] = level


@bot.message_handler(func=lambda message: message.text == Command.NEXT)
def next_cards(message):
    create_cards(message)


@bot.message_handler(func=lambda message: message.text == Command.DELETE_WORD)
def delete_word(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        delete_word_db(cur, conn, message.from_user.id, data['id_word'])  # удаляем слово
        add_some_word_to_dict(cur, conn, message.from_user.id)  # добавляем слово взамен
    bot.send_message(message.chat.id, f'Слово {data['translate_word'].upper()} удалено', )
    create_cards(message)


@bot.message_handler(func=lambda message: True, content_types=['text'])
def message_reply(message):
    text = message.text

    if text.find('///') != -1:
        new_words = text
        nw_list = re.split('[-]', new_words.replace('/', ''))
        print(nw_list)
        if len(nw_list) == 2:
            append_words_bd(cur, conn, message.from_user.id,
                            nw_list[0].strip(), nw_list[1].strip())
            bot.send_message(message.chat.id, f'Добавлено в словарь :'
                                              f'{nw_list[0]} - {nw_list[1]}')
        else:
            bot.send_message(message.chat.id,
                             'Неверный формат для словаря ! '
                             'Формат строки: // English word - Русское слово ')
        return

    markup = types.ReplyKeyboardMarkup(row_width=2)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        try:
            target_word = data['target_word']
        except KeyError:  # Exception:
            bot.send_message(message.chat.id, 'Что-то пошло не так. '
                                              'Запустите Бота еще раз командой: /go')
            return

        if text == target_word:
            hint = show_target(data)
            hint_text = ["Отлично!❤", hint]
            if data['level_word'] == 4:
                add_some_word_to_dict(cur, conn, message.from_user.id)
            level_word_up_down(cur, conn, message.from_user.id,
                               data['id_word'], data['level_word'], 1)

            # next_btn = types.KeyboardButton(Command.NEXT)
            # add_word_btn = types.KeyboardButton(Command.ADD_WORD)
            # delete_word_btn = types.KeyboardButton(Command.DELETE_WORD)
            # buttons.extend([next_btn, add_word_btn, delete_word_btn])
            hint = show_hint(*hint_text)
        else:
            for btn in buttons:
                if btn.text == text:
                    btn.text = text + '❌'
                    break
            hint = show_hint("Допущена ошибка!",
                             f"Попробуй ещё раз вспомнить"
                             f" слово 🇷🇺{data['translate_word']}")
            level_word_up_down(cur, conn, message.from_user.id,
                               data['id_word'], data['level_word'], -1)

    markup.add(*buttons)
    bot.send_message(message.chat.id, hint, reply_markup=markup)
    if text == target_word:
        next_cards(message)


bot.add_custom_filter(custom_filters.StateFilter(bot))

bot.infinity_polling(skip_pending=True)

cur.close()
conn.close()
