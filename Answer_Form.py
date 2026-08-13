#For the answer form creation and connection to other objects
import sqlite3
from Login_Signup import DB_PATH

QUESTION_TYPES = ('one_answer', 'multiple_choice', 'yes_no', 'written')
MAX_QUESTIONS = 10


def get_default_form(class_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT form_id, class_id, lesson_id, is_default FROM answer_forms '
        'WHERE class_id = ? AND is_default = 1',
        (class_id,)
    )
    form = cursor.fetchone()
    conn.close()
    return form


def get_lesson_form(lesson_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT form_id, class_id, lesson_id, is_default FROM answer_forms WHERE lesson_id = ?',
        (lesson_id,)
    )
    form = cursor.fetchone()
    conn.close()
    return form


def get_effective_form(class_id, lesson_id):
    custom_form = get_lesson_form(lesson_id)
    if custom_form is not None:
        return custom_form
    return get_default_form(class_id)


def get_questions(form_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT question_id, question_text, question_type FROM questions '
        'WHERE form_id = ? ORDER BY question_order',
        (form_id,)
    )
    questions = cursor.fetchall()

    result = []
    for question in questions:
        cursor.execute(
            'SELECT option_text FROM question_options WHERE question_id = ? ORDER BY option_order',
            (question['question_id'],)
        )
        options = [row['option_text'] for row in cursor.fetchall()]
        result.append({
            'question_id': question['question_id'],
            'question_text': question['question_text'],
            'question_type': question['question_type'],
            'options': options
        })

    conn.close()
    return result


def save_form(class_id, lesson_id, is_default, questions):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    if is_default:
        cursor.execute(
            'SELECT form_id FROM answer_forms WHERE class_id = ? AND is_default = 1',
            (class_id,)
        )
    else:
        cursor.execute('SELECT form_id FROM answer_forms WHERE lesson_id = ?', (lesson_id,))
    existing = cursor.fetchone()

    if existing:
        form_id = existing[0]
        cursor.execute(
            'DELETE FROM question_options WHERE question_id IN '
            '(SELECT question_id FROM questions WHERE form_id = ?)',
            (form_id,)
        )
        cursor.execute('DELETE FROM questions WHERE form_id = ?', (form_id,))
    else:
        cursor.execute(
            'INSERT INTO answer_forms (class_id, lesson_id, is_default) VALUES (?, ?, ?)',
            (class_id, None if is_default else lesson_id, 1 if is_default else 0)
        )
        form_id = cursor.lastrowid

    for order, question in enumerate(questions, start=1):
        cursor.execute(
            'INSERT INTO questions (form_id, question_text, question_type, question_order) '
            'VALUES (?, ?, ?, ?)',
            (form_id, question['question_text'], question['question_type'], order)
        )
        question_id = cursor.lastrowid
        for opt_order, option_text in enumerate(question.get('options', []), start=1):
            cursor.execute(
                'INSERT INTO question_options (question_id, option_text, option_order) '
                'VALUES (?, ?, ?)',
                (question_id, option_text, opt_order)
            )

    conn.commit()
    conn.close()
    return form_id


def submit_response(lesson_id, form_id, student_id, answers):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    for question_id, answer_text in answers.items():
        cursor.execute(
            'INSERT INTO responses (form_id, lesson_id, question_id, student_id, answer_text) '
            'VALUES (?, ?, ?, ?, ?)',
            (form_id, lesson_id, question_id, student_id, answer_text)
        )
    conn.commit()
    conn.close()


def get_response_count(lesson_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'SELECT COUNT(DISTINCT response_id) FROM responses WHERE lesson_id = ?',
        (lesson_id,)
    )
    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_form_statistics(form_id, lesson_id):
    questions = get_questions(form_id)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    statistics = []
    for question in questions:
        cursor.execute(
            'SELECT answer_text FROM responses WHERE question_id = ? AND lesson_id = ?',
            (question['question_id'], lesson_id)
        )
        answers = [row['answer_text'] for row in cursor.fetchall()]

        if question['question_type'] == 'written':
            statistics.append({**question, 'answers': answers})
        else:
            option_labels = question['options'] if question['options'] else ['Yes', 'No']
            tally = {option: 0 for option in option_labels}
            for answer in answers:
                for value in answer.split('|'):
                    if value in tally:
                        tally[value] += 1
            max_count = max(tally.values(), default=0) or 1
            bars = [
                {'option': option, 'count': count, 'percentage': round(count / max_count * 100)}
                for option, count in tally.items()
            ]
            statistics.append({**question, 'tally': tally, 'bars': bars})

    conn.close()
    return statistics
