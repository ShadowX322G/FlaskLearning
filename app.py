import os
from flask import Flask, render_template, redirect, request
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

app = Flask(__name__)
Scss(app)

BASE_DB = os.getenv("BASE_DATABASE_URI", "sqlite:///database.db")
TASKS_DB = os.getenv("TASKS_DATABASE_URI", "sqlite:///tasks.db")

app.config["SQLALCHEMY_DATABASE_URI"] = BASE_DB
app.config["SQLALCHEMY_BINDS"] = {
    'tasks': TASKS_DB
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# ----------------------------
# Models
# ----------------------------
class MyTask(db.Model):
    __bind_key__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(100), nullable=False)
    complete = db.Column(db.Integer, default=0)
    updated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Task {self.id}>"

# ----------------------------
# Initialize tables (after models!)
with app.app_context():
    # default DB
    db.create_all()

    # tasks DB
    engine = db.get_engine(app, bind='tasks')
    db.metadata.create_all(bind=engine)

# Routes
# ----------------------------
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST': 
        content = request.form['content'].strip()
        if not content:
            return redirect('/')
        new_task = MyTask(content=content)
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect('/')
        except Exception as e:
            print(f"ERROR: {e}")
            return f"ERROR: {e}"
    else:
        tasks = MyTask.query.order_by(MyTask.updated).all()
        return render_template('index.html', tasks=tasks)

@app.route("/delete/<int:id>")
def delete(id):
    task = MyTask.query.get_or_404(id)
    try:
        db.session.delete(task)
        db.session.commit()
        return redirect("/")
    except Exception as e:
        return f"ERROR: {e}"

@app.route("/edit/<int:id>", methods=['GET', 'POST'])
def edit(id):
    task = MyTask.query.get_or_404(id)
    if request.method == 'POST':
        task.content = request.form['content']
        task.updated = datetime.utcnow()
        try:
            db.session.commit()
            return redirect("/")
        except Exception as e:
            return f"ERROR: {e}"
    else:
        return render_template('edit.html', task=task)

@app.route("/health")
def healthcheck():
    return {"status": "ok"}

# ----------------------------
# Run
# ----------------------------
if __name__ == "__main__":
    app.run(debug=True)
