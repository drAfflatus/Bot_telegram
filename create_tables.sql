create table if not exists STUDENT(
ID_STUDENT BIGINT primary key
);

create table if not exists DICT(
ID_WORD INTEGER primary key,
ENGLISH VARCHAR(60) not null,
RUSSIAN VARCHAR(100) not null,
TRANSCRIPT VARCHAR(60)
);

create table if not exists LESSON(
ID_STUDENT BIGINT references STUDENT(ID_STUDENT),
ID_WORD INTEGER references DICT(ID_WORD),
LEVEL INTEGER not null,
DEL BOOLEAN not null
);
create table if not exists MY_DICT(
ID_STUDENT BIGINT references STUDENT(ID_STUDENT),
ID_WORD int generated always as identity (start 1000000) primary key,
ENGLISH VARCHAR(60) not null,
RUSSIAN VARCHAR(100) not null,
LEVEL INTEGER not null,
DEL BOOLEAN not null
);