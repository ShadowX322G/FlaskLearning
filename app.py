import os
from flask import Flask, render_template, redirect, request
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
Scss(app)

# --- DATABASE CONFIG ---
BASE_DB = os.getenv("BASE_DATABASE_URI", "sqlite:///database.db")
TASKS_DB = os.getenv("TASKS_DATABASE_URI", "sqlite:///tasks.db")
CHARTS_DB = os.getenv("CHARTS_DATABASE_URI", "sqlite:///charts.db")

app.config["SQLALCHEMY_DATABASE_URI"] = BASE_DB
app.config["SQLALCHEMY_BINDS"] = {
    'tasks': TASKS_DB,
    'charts': CHARTS_DB
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# --- MODELS ---
class MyTask(db.Model):
    __bind_key__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(100), nullable=False)
    complete = db.Column(db.Integer, default=0)
    updated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Task {self.id}>"

class Spending(db.Model):
    __bind_key__ = 'charts'
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Spending {self.id} {self.category}>"

# --- CREATE TABLES ---
with app.app_context():
    db.create_all()  # default DB
    for bind in app.config["SQLALCHEMY_BINDS"]:
        engine = db.get_engine(app, bind=bind)
        db.metadata.create_all(bind=engine)

# --- ROUTES ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        form_type = request.form.get('form_type')

        if form_type == 'task':
            content = request.form['content'].strip()
            if content:
                db.session.add(MyTask(content=content))
                db.session.commit()

        elif form_type == 'spending':
            category = request.form['category'].strip()
            amount = float(request.form['amount'])
            if category and amount:
                db.session.add(Spending(category=category, amount=amount))
                db.session.commit()

        return redirect('/')

    # ----- TASKS GET -----
    tasks = MyTask.query.order_by(MyTask.updated).all()

    # ----- SPENDING DATA -----
    data = db.session.query(Spending.category, db.func.sum(Spending.amount))\
                     .group_by(Spending.category).all()
    categories = [row[0] for row in data]
    amounts = [row[1] for row in data]

    return render_template('dashboard.html', tasks=tasks, categories=categories, amounts=amounts)

@app.route('/delete/<int:id>')
def delete(id):
    task = MyTask.query.get_or_404(id)
    db.session.delete(task)
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
def add_spending():
    category = request.form['category']
    amount = float(request.form['amount'])
    db.session.add(Spending(category=category, amount=amount))
    db.session.commit()
    return redirect('/')

# --- RUN APP ---
if __name__ == "__main__":
    app.run(debug=True)
