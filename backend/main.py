from fastapi import FastAPI, HTTPException
from schemas import TransactionCreate, TransactionUpdate, TransactionResponse, TransactionWithCategory, TransactionDeleteResponse, CategoryCreate, CategoryResponse
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os
from typing import List
from pathlib import Path



# Load .env
env_path = Path('.') / '.env'
print("Does .env exist?", env_path.exists())
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not found in environment variables. "
        "Make sure you have a .env file in the project root with DATABASE_URL set."
    )

app = FastAPI()

def get_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except psycopg2.OperationalError as e:
        raise ConnectionError(f"Could not connect to the database: {e}")

@app.get("/")
def home():
    return {"message": "Welcome to the Finance Tracker API"}

@app.get("/debug-env")
def debug_env():
    return {"DATABASE_URL": os.getenv("DATABASE_URL")}

# Get all transactions
@app.get("/transactions", response_model=List[TransactionWithCategory])
def get_transactions():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT t.transaction_id, t.transaction_date, t.description, t.amount, c.name AS category
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.category_id
            ORDER BY t.transaction_date DESC;
        """)
        results = cur.fetchall()
        cur.close()
        conn.close()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add transaction
@app.post("/transactions", response_model=List[TransactionResponse])
def create_transaction(transaction: TransactionCreate):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO transactions (transaction_date, description, amount, category_id, transaction_type)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING transaction_id, transaction_date, description, amount, category_id, transaction_type;
            """,
            (transaction.transaction_date,  # ✅ use transaction_date
        transaction.description,
        transaction.amount,
        transaction.category_id,
        transaction.transaction_type,),
        )
        new_transaction = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not new_transaction:
            raise HTTPException(status_code=400, detail="Transaction could not be created")

        return [new_transaction]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Edit a transaction
@app.put("/transactions/{transaction_id}", response_model=List[TransactionResponse])
def edit_transaction(transaction_id: int, transaction: TransactionUpdate):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE transactions
            SET
                transaction_date = COALESCE(%s, transaction_date),
                description = COALESCE(%s, description),
                amount = COALESCE(%s, amount),
                category_id = COALESCE(%s, category_id),
                transaction_type = COALESCE(%s, transaction_type)
            WHERE transaction_id = %s
            RETURNING transaction_id, transaction_date, description, amount, category_id, transaction_type;
            """,
            ( transaction.transaction_date,  # ✅ use transaction_date
        transaction.description,
        transaction.amount,
        transaction.category_id,
        transaction.transaction_type,
        transaction_id,),
        )
        updated_transaction = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not updated_transaction:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return [updated_transaction]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.delete("/transactions/{transaction_id}", response_model=TransactionDeleteResponse)
def delete_transaction(transaction_id: int = Path(description="The ID of the transaction to delete")):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            DELETE FROM transactions
            WHERE transaction_id = %s
            RETURNING transaction_id;
            """,
            (transaction_id,)
        )
        deleted = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not deleted:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return TransactionDeleteResponse(message=f"Transaction {transaction_id} deleted successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Create a new category
@app.post("/categories", response_model=CategoryResponse)
def create_category(category: CategoryCreate):
    try:
        conn = get_connection()
        cur = conn.cursor()

        # Check if the category already exists (case-insensitive)
        cur.execute(
            "SELECT category_id FROM categories WHERE LOWER(name) = LOWER(%s);",
            (category.name,)
        )
        existing = cur.fetchone()

        if existing:
            cur.close()
            conn.close()
            raise HTTPException(
                status_code=400,
                detail=f"Category '{category.name}' already exists."
            )

        # Insert new category
        cur.execute(
            "INSERT INTO categories (name) VALUES (%s) RETURNING category_id, name;",
            (category.name,)
        )
        new_category = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        return new_category

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/categories", response_model=List[CategoryResponse])
def get_categories():
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT category_id, name
            FROM categories
            ORDER BY name ASC;
            """
        )
        categories = cur.fetchall()
        cur.close()
        conn.close()

        return categories

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
