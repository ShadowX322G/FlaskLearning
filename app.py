# imports
import os
from flask import Flask, render_template, redirect, request
from flask_scss import Scss
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# my app
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

# Data Class ~ Row of Data
class MyTask(db.Model):
    __bind_key__ = 'tasks'
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(100), nullable=False)
    complete = db.Column(db.Integer, default=0)
    updated = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<Task {self.id}>"
    
def init_db():
    with app.app_context():
        db.create_all()

# Routes to Webpages
# Home Page
@app.route('/', methods=['GET', 'POST'])
def index():

    #Add a Task
    if request.method == 'POST': 
        if not request.form['content'].strip():
            return redirect('/')
        else:
            current_task = request.form['content']
        new_task = MyTask(content = current_task)
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect('/')
        except Exception as e:
            print(f"ERROR:{e}")
            return(f"ERROR:{e}")
        
    # See all current Tasks
    else:
        tasks = MyTask.query.order_by(MyTask.updated).all()
        return render_template('index.html', tasks=tasks)

# Delete an Item
@app.route("/delete/<int:id>")
def delete(id:int):
    delete_task = MyTask.query.get_or_404(id)
    try:
        db.session.delete(delete_task)
        db.session.commit()
        return redirect("/")
    except Exception as e:
        return(f"ERROR:{e}")

# Edit an Item
@app.route("/edit/<int:id>", methods=['GET', 'POST'])
def edit(id:int):
    edit_task = MyTask.query.get_or_404(id)
    if request.method == 'POST':
        edit_task.content = request.form['content']
        edit_task.updated = datetime.utcnow()
        try:
            db.session.commit()
            return redirect("/")
        except Exception as e:
            return(f"ERROR:{e}")
    else:
        return render_template('edit.html', task=edit_task)


@app.route("/health")
def healthcheck():
    return {"status": "ok"}

# Runner and Debugger
if __name__ == '__main__':
    init_db()
    app.run(debug=True)