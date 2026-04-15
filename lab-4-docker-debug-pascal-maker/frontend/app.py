from flask import Flask, render_template, request, redirect, url_for
import requests
from datetime import datetime, date
import os

app = Flask(__name__, static_url_path='/static')

backend_url = os.environ.get("BACKEND_URL", "http://backend:8000")

def get_todos():
    response = requests.get(f"{backend_url}/todos")
    todos_data = response.json()

    todos = []
    for todo_item in todos_data:
        todo = {
            "id": todo_item[0],
            "todo_text": todo_item[1],
            "due_date": datetime.strptime(todo_item[2], "%Y-%m-%d").date() if todo_item[2] else None,
            "completed": todo_item[3]
        }
        todos.append(todo)

    return todos

def add_todo(todo_text, due_date=None):
    response = requests.post(
        f"{backend_url}/add-todo",
        data={"todo_text": todo_text, "due_date": due_date}
    )
    return response.json()

@app.route("/")
@app.route("/todos", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        new_todo = request.form.get("todo_text")
        add_todo(new_todo)
        return redirect(url_for("index"))

    todos = get_todos()
    return render_template("app.html", todos=todos)

@app.route("/add-todo", methods=["POST"])
def add_todos():
    todo_text = request.form.get("todo_text")
    due_date = request.form.get("due_date")
    add_todo(todo_text, due_date)
    return redirect(url_for("index"))

@app.route("/complete-todo/<int:todo_id>", methods=["POST"])
def complete_todo(todo_id):
    mark_todo_completed(todo_id)
    return redirect(url_for("index"))

def mark_todo_completed(todo_id):
    response = requests.post(f"{backend_url}/complete-todo/{todo_id}")
    return response.json()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
