import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'school_feedback.db')



def register_teacher(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        password_hash = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO teachers (username, password_hash) VALUES (?, ?)',
            (username, password_hash)
        )
        conn.commit()
        return True, 'Account created successfully.'
    except sqlite3.IntegrityError:
        return False, 'Username already exists. Please choose a different one.'
    finally:
        conn.close()


def login_teacher(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT teacher_id, password_hash FROM teachers WHERE username = ?',
        (username,)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return False, None

    teacher_id, stored_hash = row

    if check_password_hash(stored_hash, password):
        return True, teacher_id

    return False, None


def register_student(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        password_hash = generate_password_hash(password)
        cursor.execute(
            'INSERT INTO students (username, password_hash) VALUES (?, ?)',
            (username, password_hash)
        )
        conn.commit()
        return True, 'Account created successfully.'
    except sqlite3.IntegrityError:
        return False, 'Username already exists. Please choose a different one.'
    finally:
        conn.close()


def login_student(username, password):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT student_id, password_hash FROM students WHERE username = ?',
        (username,)
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return False, None

    student_id, stored_hash = row

    if check_password_hash(stored_hash, password):
        return True, student_id

    return False, None
