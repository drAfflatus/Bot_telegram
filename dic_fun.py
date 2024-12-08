"""
Файл модуля содержащий функции программы
"""
import random
import re
import os
from telebot import types, TeleBot, custom_filters
from telebot.storage import StateMemoryStorage
from telebot.handler_backends import State, StatesGroup
from psycopg2 import sql
import dotenv
import random
import json

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


def load_dotenv():
    """Функция, обеспечивающая получение данных из файла окружения."""
    dotenv.load_dotenv()
    dotenv.load_dotenv(dotenv.find_dotenv(filename='config.env', usecwd=True))


def read_from_json(file_path, cur, conn):
    """
    Функция для чтения файла json.
    """
    cur.execute("""
         SELECT * 
         FROM
         dict;
         """)
    res = cur.fetchone()
    if not (res):
        print("------------- json loading----------------")
        print("Заполнение таблицы словаря...")
        with open(file_path, encoding='UTF-8') as f:
            json_data = json.load(f)
            for lst in json_data:
                lvl_1 = lst.get('id')
                lvl_2 = lst.get('en')
                lvl_3 = lst.get('ru')
                lvl_4 = lst.get('tr')
                print(lvl_1, lvl_2, lvl_3, lvl_4)
                cur.execute("""
                    INSERT INTO dict
                    (id_word,english,russian,transcript)
                    VALUES (%s,%s,%s,%s);
                    """, (lvl_1, lvl_2, lvl_3, lvl_4))
                conn.commit()


# def drop_tables(cur, conn):
#     """Функция для удаления таблиц """
#
#     cur.execute("""
#                 DROP TABLE  IF EXISTS LESSON CASCADE;
#                 DROP TABLE  IF EXISTS MY_DICT CASCADE;
#                 DROP TABLE  IF EXISTS WORD CASCADE;
#                 DROP TABLE  IF EXISTS STUDENT CASCADE;
#                 """)
#     conn.commit()
#
#
# def create_tables(cur, conn):
#     """Функция для создания таблиц в БД """
#     cur.execute("""
#                 create table if not exists STUDENT(
#                 ID_STUDENT BIGINT primary key
#                 );
#
#                 create table if not exists DICT(
#                 ID_WORD INTEGER primary key,
#                 ENGLISH VARCHAR(60) not null,
#                 RUSSIAN VARCHAR(100) not null,
#                 TRANSCRIPT VARCHAR(60)
#                 );
#
#                 create table if not exists LESSON(
#                 ID_STUDENT BIGINT references STUDENT(ID_STUDENT),
#                 ID_WORD INTEGER references DICT(ID_WORD),
#                 LEVEL INTEGER not null,
#                 DEL BOOLEAN not null
#                 );
#
#                 create table if not exists MY_DICT(
#                 ID_STUDENT BIGINT references STUDENT(ID_STUDENT),
#                 ID_WORD int generated always as identity (start 1000000) primary key,
#                 ENGLISH VARCHAR(60) not null,
#                 RUSSIAN VARCHAR(100) not null,
#                 LEVEL INTEGER not null,
#                 DEL BOOLEAN not null
#                 );
#                 """)
#
#     conn.commit()


def ghost_english_words(cur, conn):
    """Метод возвращает английские слова для
       подстановки вариантов ответов (списком).
       Запускается единожды в сессию программы.
        """
    cur.execute("""
                SELECT english
                FROM dict;
                """)
    # lst = self.cur.fetchmany(1000)
    # r = random.sample(list(lst), 4)
    return list(cur.fetchmany(1000))


def get_target_word_from_base(id_member, cur, conn):
    sql_templ = sql.SQL("""
            select d.id_word,english,russian,l.level
            from dict d
            join lesson l
            on  d.id_word = l.id_word
            where l.id_student = {t} and l.del = false and l.level<5
            /*order by level asc*/
            limit 20;
            """.format(t=id_member))
    cur.execute(sql_templ)
    res = cur.fetchall()
    if res == None:
        res = [""]
    res = list(res)
    if not (len(res)):
        res = [""]

    sql_templ = sql.SQL("""
                select id_word,english,russian,level
                from my_dict 
                where id_student = {t} and del = false and level<5
                limit 20;
                """.format(t=id_member))
    cur.execute(sql_templ)
    res_my_d = cur.fetchall()
    if res_my_d == None:
        pass
    res = list(res)
    if not (len(res)):
        res_my_d = [""]
    res.extend(res_my_d)

    return random.sample(res, 1)


def level_word_up_down(cur, conn, id_member, id_word, cur_level, incr=1):
    """

    :param id_member: id студента
    :param id_word: id  слова в базе
    :param cur_level: текущий уровень знания слова
    :param incr: шаг увеличения уровня знаний  угадал слово + 1 не угадал - 1
    :return: -
    """
    sql_templ = sql.SQL("""UPDATE lesson
            SET level = {t2}
            WHERE
            id_student = {t} and id_word = {t1};""".format(t=id_member, t1=id_word, t2=cur_level + incr))
    cur.execute(sql_templ)
    conn.commit()


def tuc_tuc_member(cur, conn, id_member):
    """
    Функция для заполнения первичными данными словаря из 20 слов для вновьподключающегося пользователя
    :param id_member:  айди пользователя. Из айди чата
    :return: -
    """
    cur.execute("""
                SELECT id_student 
                FROM 
                student
                WHERE
                id_student = %s;   
                """, (id_member,))

    member_res = cur.fetchone()

    if not (member_res):
        """если пользователь тут в первый раз, заносим
        его в базу с его IDтелегр , и даем двадцать слов
        к изучению в случайном порядке (для начала - хватит)
        """
        cur.execute("""
                SELECT id_word
                FROM dict 
        """)
        lst = cur.fetchmany(100)
        r = random.sample(list(lst), 20)
        ins = ''
        comma = ''
        """ Учащегося заносим в базу  """
        cur.execute("""
                            INSERT INTO student
                            (id_student)
                            VALUES (%s);
                            """, (id_member,))

        for i_r in r:
            ins = ins + comma + f'({id_member},{i_r[0]},0,False)'
            comma = ','

            # self.cur.execute("""
            #         INSERT INTO lesson
            #         (id_student,id_word)
            #         VALUES """+ins+";")
            # self.conn.commit()
            """ Добавляем новенькому в базу знаний его первые слова """
        sql_templ = sql.SQL("INSERT INTO lesson (id_student,id_word,level,del) VALUES {t}".format(t=ins))
        cur.execute(sql_templ)
        conn.commit()
        return True
    return False


def add_some_word_to_dict(cur, conn, id_member):
    """
    Функция добавляет в выборку, изучаемых учащимся слов, еще одно.
    При выборе нового слова исключаются слова уже присутствующие в базе знаний студента
    :return:
    """
    sql_templ = sql.SQL("""insert into lesson (id_student,id_word,level,del) values(
            {t},
            (select d.id_word 
            from dict d 
            left join lesson l
            on  d.id_word = l.id_word
            where l.id_word is null
            limit 1),0,false 
            );""".format(t=id_member))
    cur.execute(sql_templ)
    conn.commit()


def append_words_bd(cur, conn, id_member, en_word, ru_word):
    """
    Функция добавления в БД нового слова введенного пользователем
    :param id_member: айди пользователя
    :param en_word:  слово на англ языке
    :param ru_word: слово на русском языке
    :return: -
    """
    sql_templ = sql.SQL("""insert into my_dict (id_student,english,russian,level,del) values(
                {t},'{t1}','{t2}',0,false 
                );""".format(t=id_member, t1=en_word, t2=ru_word))

    cur.execute(sql_templ)
    conn.commit()


def delete_word_db(cur, conn, id_member, id_word):
    """
    Функция вносит в базу пометку - игнорировать слово при последующем изучении
    :param id_member:  передаем id студента
    :param id_word: - айди целевого слова
    :return: -
    """
    if id_word >= 1000000:
        name_table = 'my_dict'
    else:
        name_table = 'lesson'

    sql_templ = sql.SQL("""UPDATE {t3}
                SET del = True
                WHERE
                id_student = {t} and id_word = {t1};""".format(t=id_member, t1=id_word, t3=name_table))
    cur.execute(sql_templ)
    conn.commit()
