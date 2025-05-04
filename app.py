from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime
from contextlib import closing
import os

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates'))
app.secret_key = 'your_secret_key_here'
DATABASE = 'attendance.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with closing(get_db_connection()) as conn:
        cursor = conn.cursor()

        cursor.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        );
        
        CREATE TABLE IF NOT EXISTS students (
            student_id TEXT PRIMARY KEY,
            name TEXT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_name TEXT UNIQUE NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS timetable (
            timetable_id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
        );
        
        CREATE TABLE IF NOT EXISTS attendance (
            attendance_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            subject_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Present', 'Absent', 'Late')),
            FOREIGN KEY (student_id) REFERENCES students(student_id),
            FOREIGN KEY (subject_id) REFERENCES subjects(subject_id)
        );
        ''')
        
        # Insert sample data
        cursor.execute("INSERT OR IGNORE INTO users VALUES (1, 'teacher', 'pass123', 'teacher')")
        cursor.execute("INSERT OR IGNORE INTO students VALUES ('23IT101', 'John Doe')")
        cursor.execute("INSERT OR IGNORE INTO subjects (subject_name) VALUES ('Mathematics')")
        conn.commit()

@app.route('/')
def login():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def handle_login():
    username = request.form.get('username')
    password = request.form.get('password')
    role = request.form.get('role')

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ? AND role = ?', 
                       (username, password, role)).fetchone()
    conn.close()

    if user:
        if role == 'student':
            return redirect(url_for('student_dashboard', student_id=username))
        elif role == 'teacher':
            return redirect(url_for('teacher_dashboard'))
    else:
        flash('Invalid credentials. Please try again.', 'error')
        return redirect(url_for('login'))

@app.route('/student-dashboard')
def student_dashboard():
    student_id = request.args.get('student_id')
    conn = get_db_connection()
    
    student = conn.execute('SELECT * FROM students WHERE student_id = ?', (student_id,)).fetchone()
    
    attendance = conn.execute('''
        SELECT a.date, s.subject_name, a.status 
        FROM attendance a
        JOIN subjects s ON a.subject_id = s.subject_id
        WHERE a.student_id = ?
        ORDER BY a.date DESC
    ''', (student_id,)).fetchall()
    
    timetable = conn.execute('''
        SELECT s.subject_name, t.day, t.start_time, t.end_time
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.subject_id
        ORDER BY 
            CASE t.day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END,
            t.start_time
    ''').fetchall()
    
    conn.close()

    if student:
        return render_template('student-dashboard.html', 
                             student_id=student['student_id'], 
                             student_name=student['name'],
                             attendance=attendance,
                             timetable=timetable)
    else:
        flash('Student not found', 'error')
        return redirect(url_for('login'))

@app.route('/teacher-dashboard')
def teacher_dashboard():
    return render_template('teacher-dashboard.html')

@app.route('/manage-students', methods=['GET', 'POST'])
def manage_students():
    conn = get_db_connection()
    
    if request.method == 'POST':
        student_id = request.form.get('student_id')
        student_name = request.form.get('student_name')
        
        try:
            conn.execute('INSERT INTO students (student_id, name) VALUES (?, ?)', 
                         (student_id, student_name))
            conn.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', 
                         (student_id, 'pass123', 'student'))
            conn.commit()
            flash('Student added successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Student ID already exists!', 'error')
        finally:
            conn.close()
            return redirect(url_for('manage_students'))
    
    students = conn.execute('SELECT * FROM students ORDER BY student_id').fetchall()
    conn.close()
    return render_template('manage-students.html', students=students)

@app.route('/delete-student/<student_id>')
def delete_student(student_id):
    conn = get_db_connection()
    
    try:
        conn.execute('DELETE FROM students WHERE student_id = ?', (student_id,))
        conn.execute('DELETE FROM users WHERE username = ? AND role = "student"', (student_id,))
        conn.execute('DELETE FROM attendance WHERE student_id = ?', (student_id,))
        conn.commit()
        flash('Student deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting student: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('manage_students'))

@app.route('/manage-subjects', methods=['GET', 'POST'])
def manage_subjects():
    conn = get_db_connection()
    
    if request.method == 'POST':
        subject_name = request.form.get('subject_name')
        
        try:
            conn.execute('INSERT INTO subjects (subject_name) VALUES (?)', (subject_name,))
            conn.commit()
            flash('Subject added successfully!', 'success')
        except sqlite3.IntegrityError:
            flash('Subject already exists!', 'error')
        finally:
            conn.close()
            return redirect(url_for('manage_subjects'))
    
    subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_name').fetchall()
    conn.close()
    return render_template('manage-subjects.html', subjects=subjects)

@app.route('/delete-subject/<int:subject_id>')
def delete_subject(subject_id):
    conn = get_db_connection()
    
    try:
        conn.execute('DELETE FROM subjects WHERE subject_id = ?', (subject_id,))
        conn.commit()
        flash('Subject deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting subject: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('manage_subjects'))

@app.route('/manage-timetable', methods=['GET', 'POST'])
def manage_timetable():
    conn = get_db_connection()
    
    if request.method == 'POST':
        subject_id = request.form.get('subject_id')
        day = request.form.get('day')
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        
        try:
            conn.execute('''
                INSERT INTO timetable (subject_id, day, start_time, end_time) 
                VALUES (?, ?, ?, ?)
            ''', (subject_id, day, start_time, end_time))
            conn.commit()
            flash('Timetable entry added successfully!', 'success')
        except Exception as e:
            flash(f'Error adding timetable entry: {str(e)}', 'error')
        finally:
            conn.close()
            return redirect(url_for('manage_timetable'))
    
    timetable = conn.execute('''
        SELECT t.timetable_id, s.subject_name, t.day, t.start_time, t.end_time
        FROM timetable t
        JOIN subjects s ON t.subject_id = s.subject_id
        ORDER BY 
            CASE t.day
                WHEN 'Monday' THEN 1
                WHEN 'Tuesday' THEN 2
                WHEN 'Wednesday' THEN 3
                WHEN 'Thursday' THEN 4
                WHEN 'Friday' THEN 5
                WHEN 'Saturday' THEN 6
                WHEN 'Sunday' THEN 7
            END,
            t.start_time
    ''').fetchall()
    
    subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_name').fetchall()
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    conn.close()
    
    return render_template('manage-timetable.html', 
                         timetable=timetable, 
                         subjects=subjects, 
                         days=days)

@app.route('/delete-timetable-entry/<int:timetable_id>')
def delete_timetable_entry(timetable_id):
    conn = get_db_connection()
    
    try:
        conn.execute('DELETE FROM timetable WHERE timetable_id = ?', (timetable_id,))
        conn.commit()
        flash('Timetable entry deleted successfully!', 'success')
    except Exception as e:
        flash(f'Error deleting timetable entry: {str(e)}', 'error')
    finally:
        conn.close()
    
    return redirect(url_for('manage_timetable'))

@app.route('/mark-attendance', methods=['GET', 'POST'])
def mark_attendance():
    if request.method == 'POST':
        date = request.form.get('date', datetime.today().strftime('%Y-%m-%d'))
        subject_id = request.form.get('subject_id')

        if not subject_id:
            flash('Please select a subject', 'error')
            return redirect(url_for('mark_attendance'))

        conn = get_db_connection()
        try:
            students = conn.execute('SELECT * FROM students').fetchall()
            for student in students:
                status = request.form.get(f"status_{student['student_id']}", 'Absent')
                # Check if attendance already exists for this student, subject, and date
                existing = conn.execute('''
                    SELECT * FROM attendance 
                    WHERE student_id = ? AND subject_id = ? AND date = ?
                ''', (student['student_id'], subject_id, date)).fetchone()
                
                if existing:
                    # Update existing record
                    conn.execute('''
                        UPDATE attendance SET status = ?
                        WHERE student_id = ? AND subject_id = ? AND date = ?
                    ''', (status, student['student_id'], subject_id, date))
                else:
                    # Insert new record
                    conn.execute('''
                        INSERT INTO attendance (student_id, subject_id, date, status)
                        VALUES (?, ?, ?, ?)
                    ''', (student['student_id'], subject_id, date, status))
            
            conn.commit()
            flash('Attendance saved successfully!', 'success')
        except Exception as e:
            conn.rollback()
            flash(f'Error saving attendance: {str(e)}', 'error')
        finally:
            conn.close()
        
        return redirect(url_for('mark_attendance'))
    
    # GET request handling
    conn = get_db_connection()
    try:
        students = conn.execute('SELECT * FROM students ORDER BY name').fetchall()
        subjects = conn.execute('SELECT * FROM subjects ORDER BY subject_name').fetchall()
        timetable = conn.execute('''
            SELECT s.subject_name, t.day, t.start_time, t.end_time
            FROM timetable t 
            JOIN subjects s ON t.subject_id = s.subject_id
            ORDER BY t.day, t.start_time
        ''').fetchall()
        
        # Get recent attendance records for display
        recent_attendance = conn.execute('''
            SELECT a.date, s.subject_name, st.name as student_name, a.status
            FROM attendance a
            JOIN subjects s ON a.subject_id = s.subject_id
            JOIN students st ON a.student_id = st.student_id
            ORDER BY a.date DESC
            LIMIT 10
        ''').fetchall()
        
        return render_template('mark-attendance.html',
                            students=students,
                            subjects=subjects,
                            timetable=timetable,
                            recent_attendance=recent_attendance,
                            today=datetime.today().strftime('%Y-%m-%d'))
    except Exception as e:
        flash(f'Error loading attendance page: {str(e)}', 'error')
        return redirect(url_for('teacher_dashboard'))
    finally:
        conn.close()

if __name__ == '__main__':
    init_db()
    app.run(debug=True)