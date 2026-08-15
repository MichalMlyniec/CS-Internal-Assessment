from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from datetime import date
from Login_Signup import DB_PATH, register_teacher, login_teacher, register_student, login_student
from Year import current_school_year, make_year_string, parse_start_year
from Class import create_class, get_classes, get_class, delete_class
from Lesson import (
    create_lesson, get_lessons, get_lesson, get_lesson_public, delete_lesson, generate_qr_code, get_lan_ip,
    get_class_students, get_lesson_student_breakdown, get_student_history, get_student_engagement_summary
)
from Answer_Form import (
    QUESTION_TYPES, MAX_QUESTIONS, get_default_form, get_lesson_form, get_effective_form,
    get_questions, save_form,
    get_response_count, get_form_statistics, submit_response
)
import sqlite3

app = Flask(__name__)
app.secret_key = 'f3a9b2c7e1d4f6a8b0c2e5d7f9a1b3c5'

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            class_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT    NOT NULL,
            year_id    TEXT    NOT NULL,
            teacher_id INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lessons (
            lesson_id   INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson_name TEXT    NOT NULL,
            lesson_date TEXT    NOT NULL,
            class_id    INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS answer_forms (
            form_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id   INTEGER NOT NULL,
            lesson_id  INTEGER,
            is_default INTEGER NOT NULL DEFAULT 0
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            question_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            form_id        INTEGER NOT NULL,
            question_text  TEXT    NOT NULL,
            question_type  TEXT    NOT NULL,
            question_order INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS question_options (
            option_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id  INTEGER NOT NULL,
            option_text  TEXT    NOT NULL,
            option_order INTEGER NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS students (
            student_id    INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT    UNIQUE NOT NULL,
            password_hash TEXT    NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            response_id INTEGER PRIMARY KEY AUTOINCREMENT,
            form_id     INTEGER NOT NULL,
            lesson_id   INTEGER NOT NULL,
            question_id INTEGER NOT NULL,
            student_id  INTEGER NOT NULL,
            answer_text TEXT    NOT NULL
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS class_student_labels (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id     INTEGER NOT NULL,
            student_id   INTEGER NOT NULL,
            label_number INTEGER NOT NULL,
            UNIQUE(class_id, student_id)
        )
    ''')

    cursor.execute('PRAGMA table_info(responses)')
    response_columns = {row[1] for row in cursor.fetchall()}
    if 'lesson_id' not in response_columns:
        cursor.execute('ALTER TABLE responses ADD COLUMN lesson_id INTEGER')

    conn.commit()
    conn.close()

init_db()


def build_respond_url(lesson_id):
    respond_path = url_for('lesson_respond', lesson_id=lesson_id)
    host = request.host.split(':')[0]
    if host.endswith('.pythonanywhere.com'):
        return request.url_root.rstrip('/') + respond_path
    return f'http://{get_lan_ip()}:5000{respond_path}'


class Student:
    def __init__(self, student_id, username, class_id):
        self.student_id = student_id
        self.username   = username
        self.class_id   = class_id

    def submit_feedback(self, _lesson_id, _answers):
        pass

    def get_answers(self, _lesson_id):
        pass

    def get_all_answers(self):
        pass


@app.route('/')
def home():
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username         = request.form['username'].strip()
        password         = request.form['password']
        confirm_password = request.form['confirm_password']

        if not username or not password:
            flash('Username and password cannot be empty.', 'error')
            return render_template('signup.html')

        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'error')
            return render_template('signup.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters long.', 'error')
            return render_template('signup.html')

        success, message = register_teacher(username, password)
        if success:
            flash(message, 'success')
            return redirect(url_for('login'))
        else:
            flash(message, 'error')

    return render_template('signup.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']

        success, teacher_id = login_teacher(username, password)
        if success:
            session['teacher_id'] = teacher_id
            session['username']   = username
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect username or password.', 'error')

    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'teacher_id' not in session:
        flash('Please log in to access the dashboard.', 'error')
        return redirect(url_for('login'))
    year      = request.args.get('year', current_school_year())
    start     = parse_start_year(year)
    prev_year = make_year_string(start - 1)
    next_year = make_year_string(start + 1)
    classes   = get_classes(session['teacher_id'], year)
    return render_template('dashboard.html',
        username=session['username'],
        classes=classes,
        year=year,
        prev_year=prev_year,
        next_year=next_year
    )


@app.route('/create_class', methods=['GET', 'POST'])
def create_class_route():
    if 'teacher_id' not in session:
        return redirect(url_for('login'))

    current = current_school_year()
    start   = parse_start_year(current)
    years   = [make_year_string(start + i) for i in range(-2, 2)]

    if request.method == 'POST':
        class_name = request.form['class_name'].strip()
        year_id    = request.form['year_id']

        if not class_name:
            flash('Class name cannot be empty.', 'error')
            return render_template('create_class.html', years=years, current=current)

        create_class(session['teacher_id'], class_name, year_id)
        flash('Class created successfully.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('create_class.html', years=years, current=current)


@app.route('/class/<int:class_id>')
def class_view(class_id):
    if 'teacher_id' not in session:
        return redirect(url_for('login'))

    class_info = get_class(class_id, session['teacher_id'])
    if class_info is None:
        flash('Class not found.', 'error')
        return redirect(url_for('dashboard'))

    lessons  = get_lessons(class_id)
    students = get_class_students(class_id)
    return render_template('class.html', class_info=class_info, lessons=lessons, students=students)


@app.route('/class/<int:class_id>/delete', methods=['POST'])
def delete_class_route(class_id):
    if 'teacher_id' not in session:
        return redirect(url_for('login'))

    class_info = get_class(class_id, session['teacher_id'])
    if class_info is None:
        flash('Class not found.', 'error')
        return redirect(url_for('dashboard'))

    delete_class(class_id)
    flash('Class deleted.', 'success')
    return redirect(url_for('dashboard'))


@app.route('/class/<int:class_id>/create_lesson', methods=['GET', 'POST'])
def create_lesson_route(class_id):
    if 'teacher_id' not in session:
        return redirect(url_for('login'))

    class_info = get_class(class_id, session['teacher_id'])
    if class_info is None:
        flash('Class not found.', 'error')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        lesson_name = request.form['lesson_name'].strip()
        lesson_date = request.form['lesson_date']

        if not lesson_name or not lesson_date:
            flash('Lesson name and date cannot be empty.', 'error')
            return render_template('create_lesson.html', class_info=class_info)

        create_lesson(class_id, lesson_name, lesson_date)
        flash('Lesson created successfully.', 'success')
        return redirect(url_for('class_view', class_id=class_id))

    return render_template('create_lesson.html', class_info=class_info)


@app.route('/class/<int:class_id>/student/<int:student_id>')
def class_student_view(class_id, student_id):
    if 'teacher_id' not in session:
        return redirect(url_for('login'))

    class_info = get_class(class_id, session['teacher_id'])
    if class_info is None:
        flash('Class not found.', 'error')
        return redirect(url_for('dashboard'))

    student_entry = next(
        (s for s in get_class_students(class_id) if s['student_id'] == student_id),
        None
    )
    if student_entry is None:
        flash('That student has no submitted answers in this class.', 'error')
        return redirect(url_for('class_view', class_id=class_id))

    history     = get_student_history(class_id, student_id)
    engagement  = get_student_engagement_summary(class_id, student_id)

    return render_template('class_student.html',
        class_info=class_info,
        label=student_entry['label'],
        history=history,
        engagement=engagement
    )


@app.route('/lesson/<int:lesson_id>')
def lesson_view(lesson_id):
    if 'teacher_id' not in session:
        return redirect(url_for('login'))

    lesson_info = get_lesson(lesson_id, session['teacher_id'])
    if lesson_info is None:
        flash('Lesson not found.', 'error')
        return redirect(url_for('dashboard'))

    effective_form     = get_effective_form(lesson_info['class_id'], lesson_id)
    questions          = get_questions(effective_form['form_id']) if effective_form else []
    is_custom          = bool(effective_form) and not effective_form['is_default']
    response_count     = get_response_count(lesson_id)
    statistics         = get_form_statistics(effective_form['form_id'], lesson_id) if effective_form and response_count else []
    student_breakdown  = (
        get_lesson_student_breakdown(lesson_id, effective_form['form_id'], lesson_info['class_id'])
        if effective_form and response_count else []
    )
    is_upcoming        = date.fromisoformat(lesson_info['lesson_date']) >= date.today()

    return render_template('lesson.html',
        lesson_info=lesson_info,
        questions=questions,
        is_custom=is_custom,
        response_count=response_count,
        statistics=statistics,
        student_breakdown=student_breakdown,
        is_upcoming=is_upcoming
    )


@app.route('/lesson/<int:lesson_id>/delete', methods=['POST'])
def delete_lesson_route(lesson_id):
    if 'teacher_id' not in session:
        return redirect(url_for('login'))

    lesson_info = get_lesson(lesson_id, session['teacher_id'])
    if lesson_info is None:
        flash('Lesson not found.', 'error')
        return redirect(url_for('dashboard'))

    class_id = lesson_info['class_id']
    delete_lesson(lesson_id)
    flash('Lesson deleted.', 'success')
    return redirect(url_for('class_view', class_id=class_id))


@app.route('/lesson/<int:lesson_id>/qr_code')
def lesson_qr_code(lesson_id):
    if 'teacher_id' not in session:
        return redirect(url_for('login'))

    lesson_info = get_lesson(lesson_id, session['teacher_id'])
    if lesson_info is None:
        flash('Lesson not found.', 'error')
        return redirect(url_for('dashboard'))

    effective_form = get_effective_form(lesson_info['class_id'], lesson_id)
    if effective_form is None:
        flash('This lesson has no answer form yet (no default or custom form exists), so a QR code cannot be generated.', 'error')
        return redirect(url_for('lesson_view', lesson_id=lesson_id))

    respond_url = build_respond_url(lesson_id)
    buffer = generate_qr_code(respond_url, image_format='PDF', resolution=180.0)

    safe_name = ''.join(char if char.isalnum() else '_' for char in lesson_info['lesson_name'])
    return send_file(
        buffer,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'{safe_name}_qr_code.pdf'
    )


@app.route('/lesson/<int:lesson_id>/qr_code_image')
def lesson_qr_code_image(lesson_id):
    if 'teacher_id' not in session:
        return redirect(url_for('login'))

    lesson_info = get_lesson(lesson_id, session['teacher_id'])
    if lesson_info is None:
        flash('Lesson not found.', 'error')
        return redirect(url_for('dashboard'))

    effective_form = get_effective_form(lesson_info['class_id'], lesson_id)
    if effective_form is None:
        flash('This lesson has no answer form yet (no default or custom form exists), so a QR code cannot be generated.', 'error')
        return redirect(url_for('lesson_view', lesson_id=lesson_id))

    respond_url = build_respond_url(lesson_id)
    buffer = generate_qr_code(respond_url, image_format='PNG')

    return send_file(buffer, mimetype='image/png')


@app.route('/lesson/<int:lesson_id>/respond', methods=['GET', 'POST'])
def lesson_respond(lesson_id):
    lesson_info = get_lesson_public(lesson_id)
    if lesson_info is None:
        return render_template('student_message.html',
            title='Not Found',
            message='This lesson does not exist.'
        )

    if 'student_id' not in session:
        return render_template('student_auth.html', lesson_info=lesson_info)

    effective_form = get_effective_form(lesson_info['class_id'], lesson_id)
    if effective_form is None:
        return render_template('student_message.html',
            title='No Answer Form',
            message='No answer form is available for this lesson yet.'
        )

    questions = get_questions(effective_form['form_id'])

    if request.method == 'POST':
        answers = {}
        for question in questions:
            question_id = question['question_id']
            if question['question_type'] == 'multiple_choice':
                values = request.form.getlist(f'question_{question_id}[]')
                if values:
                    answers[question_id] = '|'.join(values)
            else:
                value = request.form.get(f'question_{question_id}', '').strip()
                if value:
                    answers[question_id] = value

        if not answers:
            flash('Please answer at least one question.', 'error')
            return render_template('student_answer_form.html', lesson_info=lesson_info, questions=questions)

        submit_response(lesson_id, effective_form['form_id'], session['student_id'], answers)
        return render_template('student_message.html',
            title='Thank You',
            message='Your answers have been submitted. Thank you for your feedback!'
        )

    return render_template('student_answer_form.html', lesson_info=lesson_info, questions=questions)


@app.route('/lesson/<int:lesson_id>/student_signup', methods=['POST'])
def student_signup_route(lesson_id):
    username         = request.form['username'].strip()
    password         = request.form['password']
    confirm_password = request.form['confirm_password']

    if not username or not password:
        flash('Username and password cannot be empty.', 'error')
        return redirect(url_for('lesson_respond', lesson_id=lesson_id))

    if password != confirm_password:
        flash('Passwords do not match. Please try again.', 'error')
        return redirect(url_for('lesson_respond', lesson_id=lesson_id))

    if len(password) < 6:
        flash('Password must be at least 6 characters long.', 'error')
        return redirect(url_for('lesson_respond', lesson_id=lesson_id))

    success, message = register_student(username, password)
    if not success:
        flash(message, 'error')
        return redirect(url_for('lesson_respond', lesson_id=lesson_id))

    _, student_id = login_student(username, password)
    session['student_id']       = student_id
    session['student_username'] = username
    return redirect(url_for('lesson_respond', lesson_id=lesson_id))


@app.route('/lesson/<int:lesson_id>/student_login', methods=['POST'])
def student_login_route(lesson_id):
    username = request.form['username'].strip()
    password = request.form['password']

    success, student_id = login_student(username, password)
    if success:
        session['student_id']       = student_id
        session['student_username'] = username
    else:
        flash('Incorrect username or password.', 'error')

    return redirect(url_for('lesson_respond', lesson_id=lesson_id))


@app.route('/student_logout')
def student_logout():
    session.pop('student_id', None)
    session.pop('student_username', None)
    return render_template('student_message.html',
        title='Logged Out',
        message='You have been logged out.'
    )


def _parse_questions_from_form(form):
    indices = sorted({
        int(key.rsplit('_', 1)[-1])
        for key in form.keys()
        if key.startswith('question_text_')
    })

    questions = []
    for i in indices:
        text  = form.get(f'question_text_{i}', '').strip()
        qtype = form.get(f'question_type_{i}', '')
        if not text or qtype not in QUESTION_TYPES:
            continue
        options = [opt.strip() for opt in form.getlist(f'options_{i}[]') if opt.strip()]
        questions.append({'question_text': text, 'question_type': qtype, 'options': options})
    return questions


def _validate_questions(questions):
    if not questions:
        return 'Add at least one question.'
    if len(questions) > MAX_QUESTIONS:
        return f'A form can have at most {MAX_QUESTIONS} questions.'
    for question in questions:
        if question['question_type'] in ('one_answer', 'multiple_choice') and len(question['options']) < 2:
            return f'"{question["question_text"]}" needs at least 2 answer options.'
    return None


@app.route('/class/<int:class_id>/answer_form', methods=['GET', 'POST'])
def class_answer_form_route(class_id):
    if 'teacher_id' not in session:
        return redirect(url_for('login'))

    class_info = get_class(class_id, session['teacher_id'])
    if class_info is None:
        flash('Class not found.', 'error')
        return redirect(url_for('dashboard'))

    template_args = {
        'title': 'Default Answer Form',
        'context_label': f"Class: {class_info['class_name']} ({class_info['year_id']})",
        'back_url': url_for('class_view', class_id=class_id),
        'action_url': url_for('class_answer_form_route', class_id=class_id),
        'max_questions': MAX_QUESTIONS
    }

    if request.method == 'POST':
        questions = _parse_questions_from_form(request.form)
        error = _validate_questions(questions)
        if error:
            flash(error, 'error')
            return render_template('answer_form.html', questions=questions, **template_args)

        save_form(class_id, None, is_default=True, questions=questions)
        flash('Default answer form saved. New lessons in this class will start with it.', 'success')
        return redirect(url_for('class_view', class_id=class_id))

    existing_form = get_default_form(class_id)
    questions = get_questions(existing_form['form_id']) if existing_form else []
    return render_template('answer_form.html', questions=questions, **template_args)


@app.route('/lesson/<int:lesson_id>/answer_form', methods=['GET', 'POST'])
def lesson_answer_form_route(lesson_id):
    if 'teacher_id' not in session:
        return redirect(url_for('login'))

    lesson_info = get_lesson(lesson_id, session['teacher_id'])
    if lesson_info is None:
        flash('Lesson not found.', 'error')
        return redirect(url_for('dashboard'))

    if date.fromisoformat(lesson_info['lesson_date']) < date.today():
        flash('This lesson has already passed, its answer form can no longer be customized.', 'error')
        return redirect(url_for('lesson_view', lesson_id=lesson_id))

    template_args = {
        'title': 'Custom Answer Form',
        'context_label': f"Lesson: {lesson_info['lesson_name']} ({lesson_info['lesson_date']})",
        'back_url': url_for('lesson_view', lesson_id=lesson_id),
        'action_url': url_for('lesson_answer_form_route', lesson_id=lesson_id),
        'max_questions': MAX_QUESTIONS
    }

    if request.method == 'POST':
        questions = _parse_questions_from_form(request.form)
        error = _validate_questions(questions)
        if error:
            flash(error, 'error')
            return render_template('answer_form.html', questions=questions, **template_args)

        save_form(lesson_info['class_id'], lesson_id, is_default=False, questions=questions)
        flash('Custom answer form saved for this lesson.', 'success')
        return redirect(url_for('lesson_view', lesson_id=lesson_id))

    existing_custom_form = get_lesson_form(lesson_id)
    if existing_custom_form:
        questions = get_questions(existing_custom_form['form_id'])
    else:
        default_form = get_default_form(lesson_info['class_id'])
        questions = get_questions(default_form['form_id']) if default_form else []
    return render_template('answer_form.html', questions=questions, **template_args)


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'success')
    return redirect(url_for('login'))


if __name__ == '__main__':
    lan_ip = get_lan_ip()
    print('=' * 60)
    print(f'Server starting. On other devices (same Wi-Fi), open:')
    print(f'  http://{lan_ip}:5000')
    print('If that address does not match your Wi-Fi adapter\'s IPv4')
    print('address (check with "ipconfig"), the wrong network interface')
    print('was detected.')
    print('=' * 60)
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
