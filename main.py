from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import sqlite3
from contextlib import contextmanager

app = FastAPI(title="Library Management API", description="API for managing books in a library")

# Pydantic models
class BookCreate(BaseModel):
    title: str
    author: str
    publication_year: int
    isbn: str

class Book(BookCreate):
    id: int

# Database connection
def get_db():
    conn = sqlite3.connect("library.db")
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Initialize database
def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                publication_year INTEGER NOT NULL,
                isbn TEXT NOT NULL UNIQUE
            )
        """)
        conn.commit()

init_db()

# CRUD Operations
@app.get("/items", response_model=List[Book])
async def get_books():
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM books")
        books = cursor.fetchall()
        return [Book(**dict(book)) for book in books]

@app.get("/items/{id}", response_model=Book)
async def get_book(id: int):
    with get_db() as conn:
        cursor = conn.execute("SELECT * FROM books WHERE id = ?", (id,))
        book = cursor.fetchone()
        if book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return Book(**dict(book))

@app.post("/items", response_model=Book)
async def create_book(book: BookCreate):
    try:
        with get_db() as conn:
            cursor = conn.execute(
                """
                INSERT INTO books (title, author, publication_year, isbn)
                VALUES (?, ?, ?, ?)
                RETURNING *
                """,
                (book.title, book.author, book.publication_year, book.isbn)
            )
            new_book = cursor.fetchone()
            conn.commit()
            return Book(**dict(new_book))
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail="ISBN already exists")

@app.put("/items/{id}", response_model=Book)
async def update_book(id: int, book: BookCreate):
    with get_db() as conn:
        cursor = conn.execute(
            """
            UPDATE books 
            SET title = ?, author = ?, publication_year = ?, isbn = ?
            WHERE id = ?
            RETURNING *
            """,
            (book.title, book.author, book.publication_year, book.isbn, id)
        )
        updated_book = cursor.fetchone()
        if updated_book is None:
            raise HTTPException(status_code=404, detail="Book not found")
        conn.commit()
        return Book(**dict(updated_book))

@app.delete("/items/{id}")
async def delete_book(id: int):
    with get_db() as conn:
        cursor = conn.execute("DELETE FROM books WHERE id = ? RETURNING id", (id,))
        if cursor.fetchone() is None:
            raise HTTPException(status_code=404, detail="Book not found")
        conn.commit()
        return {"message": "Book deleted successfully"}