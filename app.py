import os
from flask import Flask, render_template, redirect, request
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func, extract
from datetime import datetime
from flask_login import UserMixin, LoginManager, login_user, login_required, current_user, logout_user

app = Flask(__name__)
app.secret_key = os.urandom(24)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

Scss(app)

# --- DATABASE CONFIG ---
BASE_DB = os.getenv("BASE_DATABASE_URI", "sqlite:///database.db")
TASKS_DB = os.getenv("TASKS_DATABASE_URI", "sqlite:///tasks.db")
CHARTS_DB = os.getenv("CHARTS_DATABASE_URI", "sqlite:///charts.db")
USERS_DB = os.getenv("USERS_DATABASE_URI", "sqlite:///users.db")

app.config["SQLALCHEMY_DATABASE_URI"] = BASE_DB
app.config["SQLALCHEMY_BINDS"] = {
    'tasks': TASKS_DB,
    'charts': CHARTS_DB,
    'users': USERS_DB
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- MODELS ---
class MyTask(db.Model):
    __bind_key__ = 'tasks'
    __tablename__ = 'my_task'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(100), nullable=False)
    complete = db.Column(db.Integer, default=0)
    updated = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f"<Task {self.id}>"

class Spending(db.Model):
    __bind_key__ = 'charts'
    __tablename__ = 'spending'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, nullable = False)
    

    def __repr__(self):
        return f"<Spending {self.id} {self.category}>"

class User(db.Model, UserMixin):
    __bind_key__ = 'users'  
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(50), unique = True, nullable = False)
    password = db.Column(db.String(200), nullable = False)

# --- CREATE TABLES ---
with app.app_context():
    db.create_all()  # default DB
    # for bind in app.config["SQLALCHEMY_BINDS"]:
    #     engine = db.get_engine(app, bind=bind)
    #     db.metadata.create_all(bind=engine)

# --- ROUTES ---
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.route('/register', methods = ['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            return render_template('register.html', error="Username already taken")
        
        user = User(username = username, password = password)
        db.session.add(user)
        db.session.commit()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods = ['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
    
        user = User.query.filter_by(username = username).first()
        if user and user.password == password:
            login_user(user)
            return redirect('/')
    return render_template('login.html')

@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    selected_month = int(request.args.get('filter_month', datetime.utcnow().month))
    selected_year = int(request.args.get('filter_year', datetime.utcnow().year))

    if request.method == 'POST':
        form_type = request.form.get('form_type')

        if form_type == 'task':
            content = request.form['content'].strip()
            if content:
                db.session.add(MyTask(content=content, user_id=current_user.id))
                db.session.commit()
            # redirect to keep current month/year filter
            return redirect(f"/?filter_month={selected_month}&filter_year={selected_year}")

        elif form_type == 'spending':
            category = request.form['category'].strip()
            amount = float(request.form['amount'])
            month = int(request.form['month'])
            year = int(request.form['year'])
            date = datetime(year, month, 1)

            if category and amount:
                db.session.add(Spending(category=category, amount=amount, date=date, user_id=current_user.id))
                db.session.commit()

            # redirect to the same month/year after adding
            return redirect(f"/?filter_month={month}&filter_year={year}")


    # ----- TASKS GET -----
    tasks = MyTask.query.filter_by(user_id=current_user.id).order_by(MyTask.updated).all()

    # ----- SPENDING DATA -----
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

@app.route('/delete/<string:type>/', methods=['POST'])
@login_required
def delete(type):
    if type == 'task':
        id = request.form.get('id')
        item = MyTask.query.get_or_404(id)
        if item.user_id != current_user.id:
            return "Unauthorized", 403
        db.session.delete(item)

    elif type == 'spending':
        category = request.form.get('category')
        # delete all spendings in that category for current user
        Spending.query.filter_by(user_id=current_user.id, category=category).delete()

    else:
        return "Invalid type", 400

    db.session.commit()
    return redirect('/')

@app.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit(id):
    task = MyTask.query.get_or_404(id)
    if request.method == 'POST':
        task.content = request.form['content']
        task.updated = datetime.utcnow()
        db.session.commit()
        return redirect('/')
    return render_template('edit.html', task=task)

@app.route('/health')
def healthcheck():
    return {"status": "ok"}

@app.route('/add_spending', methods=['POST'])
@login_required
def add_spending():
    category = request.form['category']
    amount = float(request.form['amount'])
    month = int(request.form['month'])
    year = int(request.form['year'])

    date = datetime(year, month, 1)  # store as first day of month
    db.session.add(Spending(category=category, amount=amount, date=date, user_id=current_user.id))
    db.session.commit()
    return redirect('/')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/login')

# --- RUN APP ---
if __name__ == "__main__":
    app.run(debug=True)
