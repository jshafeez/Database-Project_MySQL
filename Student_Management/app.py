from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from datetime import datetime, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False)

class Routine(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    routine = db.Column(db.Text, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.now().date() + timedelta(days=1))
    teacher = db.relationship('User', foreign_keys=[teacher_id], backref=db.backref('teacher_routines', lazy=True))


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/')
def index():
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            if user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
            elif user.role == 'hod':
                return redirect(url_for('hod_dashboard'))
            elif user.role == 'teacher':
                return redirect(url_for('teacher_dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student_dashboard'))
        else:
            return render_template('login.html', error='Invalid username or password')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        new_user = User(username=username, password=password, role=role)
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    teachers = User.query.filter_by(role='teacher').all()
    students = User.query.filter_by(role='student').all()
    hods = User.query.filter_by(role='hod').all()
    return render_template('admin_dashboard.html', teachers=teachers, students=students, hods=hods)

@app.route('/hod/dashboard')
@login_required
def hod_dashboard():
    if current_user.role != 'hod':
        return redirect(url_for('login'))
    students = User.query.filter_by(role='student').all()
    teachers = User.query.filter_by(role='teacher').all()
    return render_template('hod_dashboard.html', students=students, teachers=teachers)

@app.route('/teacher/dashboard')
@login_required
def teacher_dashboard():
    if current_user.role != 'teacher':
        return redirect(url_for('login'))
    
    teacher_routine = get_teacher_routine(current_user.id)  # Get teacher's routine from the database
    students = User.query.filter_by(role='student').all()
    
    return render_template('teacher_dashboard.html', routine=teacher_routine, students=students)

def get_teacher_routine(teacher_id):
    routine = Routine.query.filter_by(teacher_id=teacher_id).first()
    if routine:
        return routine.routine
    else:
        return None


# Add routine for teacher
@app.route('/create_routine', methods=['POST'])
@login_required
def create_routine():
    if current_user.role == 'teacher':
        routine_text = request.form['routine']
        cleaned_routine_text = routine_text.replace('\r\n', '')  # Remove \r\n
        # Get all students
        students = User.query.filter_by(role='student').all()
        for student in students:
            new_routine = Routine(teacher_id=current_user.id, routine=cleaned_routine_text)
            db.session.add(new_routine)
        db.session.commit()
    return redirect(url_for('teacher_dashboard'))

# Fetch routine for student
def get_student_routine(student_id):
    routines = Routine.query.all()
    if routines:
        cleaned_routines = [routine.routine.replace('\r\n', ' ') for routine in routines]
        return cleaned_routines
    else:
        return None
    
@app.route('/delete_routine', methods=['POST'])
@login_required
def delete_routine():
    if current_user.role != 'teacher':
        return redirect(url_for('login'))
    
    # Get the teacher's routine
    teacher_id = current_user.id
    routine = Routine.query.filter_by(teacher_id=teacher_id).first()
    
    # If routine exists, delete it
    if routine:
        db.session.delete(routine)
        db.session.commit()
        flash('Routine deleted successfully', 'success')
    else:
        flash('No routine to delete', 'info')
    
    return redirect(url_for('teacher_dashboard'))

@app.route('/student_dashboard')
@login_required
def student_dashboard():
    if current_user.role != 'student':
        return redirect(url_for('login'))
    
    student_routine = get_student_routine(current_user.id)  # Fetch student's routine from the database
    
    return render_template('student_dashboard.html', routine=student_routine)


@app.route('/add_user', methods=['POST'])
@login_required
def add_user():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    username = request.form['username']
    password = request.form['password']
    role = request.form['role']
    new_user = User(username=username, password=password, role=role)
    db.session.add(new_user)
    db.session.commit()
    return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard after adding user

@app.route('/delete_user/<int:user_id>', methods=['GET', 'POST'])
@login_required
def delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    user = User.query.get(user_id)
    if user:
        db.session.delete(user)
        db.session.commit()
    return redirect(url_for('admin_dashboard'))  # Redirect to admin dashboard after deleting user

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
