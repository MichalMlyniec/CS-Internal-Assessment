#Here is the code for class: lesson and its functionalities.
import sqlite3
import io
import socket
import qrcode
from Login_Signup import DB_PATH


def create_lesson(class_id, lesson_name, lesson_date):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(
        'INSERT INTO lessons (lesson_name, lesson_date, class_id) VALUES (?, ?, ?)',
        (lesson_name, lesson_date, class_id)
    )
    lesson_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return lesson_id


def get_lessons(class_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        'SELECT lesson_id, lesson_name, lesson_date, class_id FROM lessons WHERE class_id = ? ORDER BY lesson_date',
        (class_id,)
    )
    lessons = cursor.fetchall()
    conn.close()
    return lessons


def get_lesson(lesson_id, teacher_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT lessons.lesson_id, lessons.lesson_name, lessons.lesson_date, lessons.class_id,
               classes.class_name, classes.year_id
        FROM lessons
        JOIN classes ON classes.class_id = lessons.class_id
        WHERE lessons.lesson_id = ? AND classes.teacher_id = ?
        ''',
        (lesson_id, teacher_id)
    )
    lesson = cursor.fetchone()
    conn.close()
    return lesson


def delete_lesson(lesson_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM responses WHERE lesson_id = ?', (lesson_id,))
    cursor.execute(
        'DELETE FROM question_options WHERE question_id IN '
        '(SELECT question_id FROM questions WHERE form_id IN '
        '(SELECT form_id FROM answer_forms WHERE lesson_id = ?))',
        (lesson_id,)
    )
    cursor.execute(
        'DELETE FROM questions WHERE form_id IN (SELECT form_id FROM answer_forms WHERE lesson_id = ?)',
        (lesson_id,)
    )
    cursor.execute('DELETE FROM answer_forms WHERE lesson_id = ?', (lesson_id,))
    cursor.execute('DELETE FROM lessons WHERE lesson_id = ?', (lesson_id,))
    conn.commit()
    conn.close()


def get_lesson_public(lesson_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute(
        '''
        SELECT lessons.lesson_id, lessons.lesson_name, lessons.lesson_date, lessons.class_id,
               classes.class_name
        FROM lessons
        JOIN classes ON classes.class_id = lessons.class_id
        WHERE lessons.lesson_id = ?
        ''',
        (lesson_id,)
    )
    lesson = cursor.fetchone()
    conn.close()
    return lesson


def _is_lan_address(ip):
    parts = ip.split('.')
    if len(parts) != 4 or ip.startswith('169.254.'):
        return False
    first, second = int(parts[0]), int(parts[1])
    return first == 10 or (first == 192 and second == 168) or (first == 172 and 16 <= second <= 31)


def get_lan_ip():
    candidates = []

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(('8.8.8.8', 80))
        candidates.append(sock.getsockname()[0])
    except OSError:
        pass
    finally:
        sock.close()

    try:
        _, _, ip_list = socket.gethostbyname_ex(socket.gethostname())
        candidates.extend(ip_list)
    except OSError:
        pass

    for ip in candidates:
        if _is_lan_address(ip):
            return ip

    return candidates[0] if candidates else '127.0.0.1'


def generate_qr_code(data, image_format='PNG', resolution=None):
    qr = qrcode.QRCode(
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4
    )
    qr.add_data(data)
    qr.make(fit=True)
    image = qr.make_image(fill_color='black', back_color='white')

    buffer = io.BytesIO()
    if resolution:
        image.save(buffer, format=image_format, resolution=resolution)
    else:
        image.save(buffer, format=image_format)
    buffer.seek(0)
    return buffer


def get_class_students(class_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        'SELECT student_id, label_number FROM class_student_labels WHERE class_id = ?',
        (class_id,)
    )
    labels = {row['student_id']: row['label_number'] for row in cursor.fetchall()}
    next_number = max(labels.values(), default=0) + 1

    cursor.execute(
        '''
        SELECT student_id, MIN(response_id) AS first_response
        FROM responses
        JOIN lessons ON lessons.lesson_id = responses.lesson_id
        WHERE lessons.class_id = ?
        GROUP BY student_id
        ORDER BY first_response
        ''',
        (class_id,)
    )
    responders = cursor.fetchall()

    for row in responders:
        student_id = row['student_id']
        if student_id not in labels:
            labels[student_id] = next_number
            cursor.execute(
                'INSERT INTO class_student_labels (class_id, student_id, label_number) VALUES (?, ?, ?)',
                (class_id, student_id, next_number)
            )
            next_number += 1

    conn.commit()
    conn.close()

    responder_ids = {row['student_id'] for row in responders}
    students = [
        {'student_id': student_id, 'label_number': label_number, 'label': f'Student{label_number}'}
        for student_id, label_number in labels.items()
        if student_id in responder_ids
    ]
    return sorted(students, key=lambda s: s['label_number'])


def get_lesson_student_breakdown(lesson_id, form_id, class_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        'SELECT question_id, question_text, question_type FROM questions '
        'WHERE form_id = ? ORDER BY question_order',
        (form_id,)
    )
    questions = cursor.fetchall()

    cursor.execute(
        'SELECT student_id, question_id, answer_text FROM responses WHERE lesson_id = ?',
        (lesson_id,)
    )
    response_rows = cursor.fetchall()
    conn.close()

    answers_by_student = {}
    for row in response_rows:
        answers_by_student.setdefault(row['student_id'], {})[row['question_id']] = row['answer_text']

    labels = {s['student_id']: s for s in get_class_students(class_id)}

    breakdown = []
    for student_id, answers in answers_by_student.items():
        student_label = labels.get(student_id)
        breakdown.append({
            'label_number': student_label['label_number'] if student_label else 0,
            'label': student_label['label'] if student_label else 'Student?',
            'answers': [
                {
                    'question_text': question['question_text'],
                    'question_type': question['question_type'],
                    'answer_text': answers.get(question['question_id'], '—')
                }
                for question in questions
            ]
        })

    return sorted(breakdown, key=lambda item: item['label_number'])


def get_student_history(class_id, student_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute(
        '''
        SELECT lessons.lesson_id, lessons.lesson_name, lessons.lesson_date,
               questions.question_text, questions.question_type, responses.answer_text
        FROM responses
        JOIN lessons ON lessons.lesson_id = responses.lesson_id
        JOIN questions ON questions.question_id = responses.question_id
        WHERE lessons.class_id = ? AND responses.student_id = ?
        ORDER BY lessons.lesson_date, questions.question_order
        ''',
        (class_id, student_id)
    )
    rows = cursor.fetchall()
    conn.close()

    history = {}
    order = []
    for row in rows:
        lesson_id = row['lesson_id']
        if lesson_id not in history:
            history[lesson_id] = {
                'lesson_id': lesson_id,
                'lesson_name': row['lesson_name'],
                'lesson_date': row['lesson_date'],
                'answers': []
            }
            order.append(lesson_id)
        history[lesson_id]['answers'].append({
            'question_text': row['question_text'],
            'question_type': row['question_type'],
            'answer_text': row['answer_text']
        })

    return [history[lesson_id] for lesson_id in order]


def get_student_engagement_summary(class_id, student_id):
    history = get_student_history(class_id, student_id)

    points = []
    for entry in history:
        values = []
        for answer in entry['answers']:
            if answer['question_type'] == 'yes_no':
                values.append(1.0 if answer['answer_text'] == 'Yes' else 0.0)
            elif answer['question_type'] == 'one_answer' and answer['answer_text'].replace('.', '', 1).isdigit():
                values.append(float(answer['answer_text']))
        if values:
            points.append({
                'lesson_name': entry['lesson_name'],
                'lesson_date': entry['lesson_date'],
                'score': sum(values) / len(values)
            })

    if len(points) < 2:
        trend = 'Not enough data yet to show a trend.'
    else:
        midpoint = len(points) // 2 or 1
        first_half = points[:midpoint]
        second_half = points[midpoint:] or points[-1:]
        first_avg = sum(p['score'] for p in first_half) / len(first_half)
        second_avg = sum(p['score'] for p in second_half) / len(second_half)
        if second_avg > first_avg + 0.05:
            trend = 'This student appears to be responding more positively over time.'
        elif second_avg < first_avg - 0.05:
            trend = 'This student appears to be responding less positively over time.'
        else:
            trend = "This student's responses have stayed fairly steady over time."

    max_score = max((p['score'] for p in points), default=0) or 1
    return {'points': points, 'trend': trend, 'max_score': max_score}
