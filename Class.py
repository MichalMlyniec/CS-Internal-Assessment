import sqlite3
from Login_Signup import DB_PATH

def create_class(teacher_id, class_name, year_id, origin_class_id=None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO classes (class_name, year_id, teacher_id, origin_class_id) VALUES (?, ?, ?, ?)',
        (class_name, year_id, teacher_id, origin_class_id)
    )
    class_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return class_id


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
        'SELECT class_id, class_name, year_id, origin_class_id FROM classes WHERE class_id = ? AND teacher_id = ?',
        (class_id, teacher_id)
    )
    class_row = cursor.fetchone()
    conn.close()
    return class_row


def get_continuable_classes(teacher_id, prev_year_id, year_id):
    """Classes from prev_year_id that haven't already been continued into year_id."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        '''SELECT class_id, class_name, year_id FROM classes
           WHERE teacher_id = ? AND year_id = ?
           AND class_id NOT IN (
               SELECT origin_class_id FROM classes
               WHERE teacher_id = ? AND year_id = ? AND origin_class_id IS NOT NULL
           )
           ORDER BY class_name''',
        (teacher_id, prev_year_id, teacher_id, year_id)
    )
    classes = cursor.fetchall()
    conn.close()
    return classes


def continue_classes(teacher_id, class_ids, year_id):
    """Create a class in year_id for each selected class, linked back to its origin and carrying over its default answer form."""
    from Answer_Form import get_default_form, get_questions, save_form

    new_class_ids = []
    for class_id in class_ids:
        origin = get_class(class_id, teacher_id)
        if origin is None:
            continue

        new_class_id = create_class(teacher_id, origin['class_name'], year_id, origin_class_id=class_id)
        new_class_ids.append(new_class_id)

        default_form = get_default_form(class_id)
        if default_form:
            questions = get_questions(default_form['form_id'])
            if questions:
                save_form(new_class_id, None, is_default=True, questions=questions)

    return new_class_ids


def delete_class(class_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'DELETE FROM responses WHERE lesson_id IN (SELECT lesson_id FROM lessons WHERE class_id = ?)',
        (class_id,)
    )
    cursor.execute(
        'DELETE FROM question_options WHERE question_id IN '
        '(SELECT question_id FROM questions WHERE form_id IN '
        '(SELECT form_id FROM answer_forms WHERE class_id = ?))',
        (class_id,)
    )
    cursor.execute(
        'DELETE FROM questions WHERE form_id IN (SELECT form_id FROM answer_forms WHERE class_id = ?)',
        (class_id,)
    )
    cursor.execute('DELETE FROM answer_forms WHERE class_id = ?', (class_id,))
    cursor.execute('DELETE FROM lessons WHERE class_id = ?', (class_id,))
    cursor.execute('DELETE FROM class_student_labels WHERE class_id = ?', (class_id,))
    cursor.execute('DELETE FROM classes WHERE class_id = ?', (class_id,))
    conn.commit()
    conn.close()