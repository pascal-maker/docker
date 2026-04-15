from fastapi import FastAPI, HTTPException, Form
import psycopg2
import os

app = FastAPI()

db_url = os.environ.get("DATABASE_URL")

def init_db():
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id SERIAL PRIMARY KEY,
                todo_text TEXT,
                due_date DATE,
                completed BOOLEAN DEFAULT FALSE
            )
        """)

        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print("Error initializing database:", str(e))

init_db()

def get_todos():
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM todos ORDER BY due_date")
        todos = cursor.fetchall()
        cursor.close()
        conn.close()
        return todos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def add_todo(todo_text, due_date=None):
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO todos (todo_text, due_date) VALUES (%s, %s)", (todo_text, due_date))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def mark_todo_completed(todo_id):
    try:
        conn = psycopg2.connect(db_url)
        cursor = conn.cursor()
        cursor.execute("UPDATE todos SET completed = TRUE WHERE id = %s", (todo_id,))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def read_root():
    return {"message": "Welcome to the Todo App!"}

@app.get("/todos")
def read_todos():
    todos = get_todos()
    return todos

@app.post("/add-todo")
def add_todos(todo_text: str = Form(...), due_date: str = Form(None)):
    add_todo(todo_text, due_date)
    return {"message": "Todo added successfully"}

@app.post("/complete-todo/{todo_id}")
def complete_todo(todo_id: int):
    mark_todo_completed(todo_id)
    return {"message": f"Todo with ID {todo_id} marked as completed"}
