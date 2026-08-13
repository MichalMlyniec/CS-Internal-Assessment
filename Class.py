import sqlite3
from Login_Signup import DB_PATH

def create_class(teacher_id, class_name, year_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO classes (class_name, year_id, teacher_id) VALUES (?, ?, ?)',
        (class_name, year_id, teacher_id)
    )
    conn.commit()
    conn.close()


def get_classes(teacher_id, year_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT class_id, class_name, year_id FROM classes WHERE teacher_id = ? AND year_id = ?',
        (teacher_id, year_id)
    )
    classes = cursor.fetchall()
    conn.close()
    return classes


def get_class(class_id, teacher_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT class_id, class_name, year_id FROM classes WHERE class_id = ? AND teacher_id = ?',
        (class_id, teacher_id)
    )
    class_row = cursor.fetchone()
    conn.close()
    return class_row