import os
from flask import Flask, render_template, redirect, request
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, extract
from datetime import datetime
from flask_login import UserMixin, LoginManager, login_user, login_required, current_user, logout_user
import tzlocal

# ======================================================
# APP SETUP
# ======================================================

app = Flask(__name__)

# Secret key for sessions & Flask-Login
app.secret_key = os.urandom(24)

# Flask-Login manager
login_manager = LoginManager()
login_manager.init_app(app)

# Route to redirect unauthenticated users to
login_manager.login_view = 'login'

# Detect local timezone
Local_TZ = tzlocal.get_localzone()

# Enable SCSS support
Scss(app)

# ======================================================
# DATABASE CONFIGURATION
# ======================================================

# Database URIs (environment-based with SQLite fallback)
BASE_DB = os.getenv("BASE_DATABASE_URI", "sqlite:///database.db")
TASKS_DB = os.getenv("TASKS_DATABASE_URI", "sqlite:///tasks.db")
CHARTS_DB = os.getenv("CHARTS_DATABASE_URI", "sqlite:///charts.db")
USERS_DB = os.getenv("USERS_DATABASE_URI", "sqlite:///users.db")

# Default database
app.config["SQLALCHEMY_DATABASE_URI"] = BASE_DB

# Bound databases for separation of concerns
app.config["SQLALCHEMY_BINDS"] = {
    'tasks': TASKS_DB,
    'charts': CHARTS_DB,
    'users': USERS_DB
}

# Disable SQLAlchemy event system (performance)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ======================================================
# MODELS
# ======================================================

class MyTask(db.Model):
    # Stored in the "tasks" bind
    __bind_key__ = 'tasks'
    __tablename__ = 'my_task'

    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(100), nullable=False)
    complete = db.Column(db.Integer, default=0)
    updated = db.Column(db.DateTime, default=datetime.now(Local_TZ))
    user_id = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Task {self.id}>"

class Spending(db.Model):
    # Stored in the "charts" bind
    __bind_key__ = 'charts'
    __tablename__ = 'spending'

    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.now(Local_TZ))
    user_id = db.Column(db.Integer, nullable = False)

    def __repr__(self):
        return f"<Spending {self.id} {self.category}>"

class User(db.Model, UserMixin):
    # Stored in the "users" bind
    __bind_key__ = 'users'

    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(50), unique = True, nullable = False)
    password = db.Column(db.String(200), nullable = False)

# ======================================================
# CREATE TABLES
# ======================================================

with app.app_context():
    # Creates tables for default DB and all binds
    db.create_all()

# ======================================================
# FLASK-LOGIN USER LOADER
# ======================================================

@login_manager.user_loader
def load_user(user_id):
    # Used by Flask-Login to reload user from session
    return User.query.get(int(user_id))

# ======================================================
# AUTH ROUTES
# ======================================================

@app.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        # If login button clicked on register page
        form_type = request.form.get('form_type')
        if form_type == 'login':
            return redirect('/login')

        # Get credentials
        username = request.form['username']
        password = request.form['password']

        # Prevent duplicate usernames
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error="Username already taken")

        # Create new user
        user = User(username = username, password = password)
        db.session.add(user)
        db.session.commit()

        return redirect('/login')

    return render_template('register.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':

        # Get credentials
        username = request.form['username']
        password = request.form['password']

        # Find user
        user = User.query.filter_by(username = username).first()

        # User not found
        if user is None:
            return render_template('register.html', error="User does not exist. Please register.")

        # Password mismatch
        if user is not None:
            if user.password != password:
                return render_template('login.html', error="Invalid password")

        # Successful login
        if user and user.password == password:
            login_user(user)
            return redirect('/')

    return render_template('login.html')

# ======================================================
# DASHBOARD
# ======================================================

@app.route('/', methods=['GET', 'POST'])
def index():
    # Redirect unauthenticated users
    if not current_user.is_authenticated:
        return redirect('/register')

    # Read selected month/year from query params
    selected_month = int(request.args.get('filter_month', datetime.now(Local_TZ).month))
    selected_year = int(request.args.get('filter_year', datetime.now(Local_TZ).year))

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        # ---------------- TASK FORM ----------------
        if form_type == 'task':
            content = request.form['content'].strip()
            if content:
                db.session.add(MyTask(content=content, user_id=current_user.id))
                db.session.commit()

            # Preserve month/year filter
            return redirect(f"/?filter_month={selected_month}&filter_year={selected_year}")

        # ---------------- SPENDING FORM ----------------
        elif form_type == 'spending':
            category = request.form['category'].strip()
            amount = float(request.form['amount'])

            # Month/year pulled from form
            selected_month = int(request.form.get['month'])
            selected_year = int(request.form['year'])

            # Stored as first day of the month
            date = datetime(selected_year, selected_month, 1)

            if category and amount:
                db.session.add(
                    Spending(
                        category=category,
                        amount=amount,
                        date=date,
                        user_id=current_user.id
                    )
                )
                db.session.commit()

            return redirect(f"/?filter_month={selected_month}&filter_year={selected_year}")

    # ==================================================
    # TASK DATA
    # ==================================================

    tasks = (
        MyTask.query
        .filter_by(user_id=current_user.id)
        .order_by(MyTask.updated)
        .all()
    )

    # ==================================================
    # SPENDING AGGREGATION
    # ==================================================

    data = (
        db.session.query(
            Spending.category,
            db.func.sum(Spending.amount)
        )
        .filter_by(user_id=current_user.id)
        .filter(extract('month', Spending.date) == selected_month)
        .filter(extract('year', Spending.date) == selected_year)
        .group_by(Spending.category)
        .order_by(func.min(Spending.id))
        .all()
    )

    categories = [row[0] for row in data]
    amounts = [row[1] for row in data]

    # Raw spending list (used for deletion/display)
    spendings = Spending.query.filter_by(user_id=current_user.id).all()
    spending_list = [(s.category, s.amount, s.id) for s in spendings]

    return render_template(
        'dashboard.html',
        tasks=tasks,
        data=data,
        categories=categories,
        amounts=amounts,
        spending_list=spending_list,
        selected_month=selected_month,
        selected_year=selected_year
    )

# ======================================================
# DELETE ROUTES
# ======================================================

@app.route('/delete/<string:type>/', methods=['POST'])
@login_required
def delete(type):
    # Preserve filter after deletion
    filter_month = request.form.get('filter_month', datetime.now(Local_TZ).month)
    filter_year = request.form.get('filter_year', datetime.now(Local_TZ).year)

    if type == 'task':
        id = request.form.get('id')
        item = MyTask.query.get_or_404(id)

        # Ownership check
        if item.user_id != current_user.id:
            return "Unauthorized", 403

        db.session.delete(item)

    elif type == 'spending':
        category = request.form.get('category')

        # Delete all spending entries for this category
        Spending.query.filter_by(
            user_id=current_user.id,
            category=category
        ).delete()

    else:
        return "Invalid type", 400

    db.session.commit()
    return redirect(f"/?filter_month={filter_month}&filter_year={filter_year}")

# ======================================================
# EDIT TASK
# ======================================================

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    task = MyTask.query.get_or_404(id)

    if request.method == 'POST':
        task.content = request.form['content']
        task.updated = datetime.now(Local_TZ)
        db.session.commit()
        return redirect('/')

    return render_template('edit.html', task=task)

# ======================================================
# MISC ROUTES
# ======================================================

@app.route('/health')
def healthcheck():
    # Simple uptime check
    return {"status": "ok"}

@app.route('/add_spending', methods=['POST'])
@login_required
def add_spending():
    category = request.form['category']
    amount = float(request.form['amount'])
    month = int(request.form['month'])
    year = int(request.form['year'])

    date = datetime(year, month, 1)
    db.session.add(
        Spending(
            category=category,
            amount=amount,
            date=date,
            user_id=current_user.id
        )
    )
    db.session.commit()

    return redirect(f"/?filter_month={month}&filter_year={year}")

@app.route('/logout')
@login_required
def logout():
    # Clear user session
    logout_user()
    return redirect('/login')

# ======================================================
# RUN APP
# ======================================================

if __name__ == "__main__":
    app.run(debug=True)
