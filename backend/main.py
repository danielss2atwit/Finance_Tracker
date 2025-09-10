from fastapi import FastAPI, HTTPException, Path, Query, Request
from schemas import (
    TransactionCreate, TransactionUpdate, TransactionResponse,
    TransactionWithCategory, TransactionDeleteResponse,
    CategoryCreate, CategoryResponse, MonthlySummaryResponse, SpendingByCategoryResponse, SpendingByCategoryItem
)
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os
from typing import List, Optional
from pathlib import Path as FilePath
import datetime

# Load .env
env_path = FilePath('.') / '.env'
print("Does .env exist?", env_path.exists())
load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in environment variables.")

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



@app.post("/transactions/")
async def create_transaction(request: Request):
    data = await request.json()
    print("Raw JSON:", data)

@app.get("/transactions", response_model=List[TransactionWithCategory])
def get_transactions(
    start_date: Optional[datetime.date] = Query(None),
    end_date: Optional[datetime.date] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    year: Optional[int] = Query(None),
    category_id: Optional[int] = Query(None)
):
    try:
        conn = get_connection()
        cur = conn.cursor()
        query = """
            SELECT t.transaction_id, t.transaction_date, t.description, 
                   t.amount, t.transaction_type, c.name AS category
            FROM transactions t
            LEFT JOIN categories c ON t.category_id = c.category_id
        """
        filters, params = [], []

        if start_date:
            filters.append("t.transaction_date >= %s")
            params.append(start_date)
        if end_date:
            filters.append("t.transaction_date <= %s")
            params.append(end_date)
        if month and year:
            filters.append("EXTRACT(MONTH FROM t.transaction_date) = %s")
            params.append(month)
            filters.append("EXTRACT(YEAR FROM t.transaction_date) = %s")
            params.append(year)
        if category_id:
            filters.append("t.category_id = %s")
            params.append(category_id)

        if filters:
            query += " WHERE " + " AND ".join(filters)

        query += " ORDER BY t.transaction_date DESC;"

        cur.execute(query, params)
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [TransactionWithCategory(**row) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/transactions", response_model=TransactionResponse)
def create_transaction(transaction: TransactionCreate):
    print("Recieved:",transaction)
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO transactions (transaction_date, description, amount, category_id, transaction_type)
            VALUES (%s, %s, %s, %s, %s)
            RETURNING transaction_id, transaction_date, description, amount, category_id, transaction_type;
            """,
            (
                transaction.transaction_date,
                transaction.description,
                transaction.amount,
                transaction.category_id,
                transaction.transaction_type,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=400, detail="Transaction could not be created")

        return TransactionResponse(**row)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/transactions/{transaction_id}", response_model=TransactionResponse)
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
            (
                transaction.transaction_date,
                transaction.description,
                transaction.amount,
                transaction.category_id,
                transaction.transaction_type,
                transaction_id,
            ),
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return TransactionResponse(**row)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/transactions/{transaction_id}", response_model=TransactionDeleteResponse)
def delete_transaction(transaction_id: int = Path(...)):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM transactions WHERE transaction_id = %s RETURNING transaction_id;",
            (transaction_id,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Transaction not found")

        return TransactionDeleteResponse(message=f"Transaction {transaction_id} deleted successfully")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/categories", response_model=CategoryResponse)
def create_category(category: CategoryCreate):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT category_id FROM categories WHERE LOWER(name) = LOWER(%s);",
            (category.name,)
        )
        existing = cur.fetchone()

        if existing:
            cur.close()
            conn.close()
            raise HTTPException(status_code=400, detail=f"Category '{category.name}' already exists.")

        cur.execute(
            "INSERT INTO categories (name) VALUES (%s) RETURNING category_id, name;",
            (category.name,)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        return CategoryResponse(**row)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/categories", response_model=List[CategoryResponse])
def get_categories():
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT category_id, name FROM categories ORDER BY name ASC;")
        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [CategoryResponse(**row) for row in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/categories/{category_id}", response_model=CategoryResponse)
def edit_category(category: CategoryCreate, category_id: int = Path(...)):
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute(
            "SELECT category_id FROM categories WHERE LOWER(name) = LOWER(%s) AND category_id != %s;",
            (category.name, category_id)
        )
        existing = cur.fetchone()

        if existing:
            cur.close()
            conn.close()
            raise HTTPException(status_code=400, detail=f"Category '{category.name}' already exists.")

        cur.execute(
            "UPDATE categories SET name = %s WHERE category_id = %s RETURNING category_id, name;",
            (category.name, category_id)
        )
        row = cur.fetchone()
        conn.commit()
        cur.close()
        conn.close()

        if not row:
            raise HTTPException(status_code=404, detail="Category not found")

        return CategoryResponse(**row)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
########################################################    
# monthly summary 
@app.get("/summary/monthly", response_model=MonthlySummaryResponse)
def get_monthly_summary(
    month: int = Query(default=None, ge=1, le=12),
    year: int = Query(default=None, ge=2000)
):
    try:
        today = datetime.date.today()
        if not month:
            month = today.month
        if not year:
            year = today.year

        first_day = datetime.date(year, month, 1)

        conn = get_connection()
        cur = conn.cursor()

        # Total income
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total_income
            FROM transactions
            WHERE transaction_type = 'income'
              AND DATE_TRUNC('month', transaction_date) = DATE_TRUNC('month', %s::date)
        """, (first_day,))
        total_income = cur.fetchone()["total_income"]

        # Total expenses
        cur.execute("""
            SELECT COALESCE(SUM(amount), 0) AS total_expenses
            FROM transactions
            WHERE transaction_type = 'expense'
              AND DATE_TRUNC('month', transaction_date) = DATE_TRUNC('month', %s::date)
        """, (first_day,))
        total_expenses = cur.fetchone()["total_expenses"]

        # Most purchased category
        cur.execute("""
            SELECT c.name, SUM(t.amount) AS total_spent
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE t.transaction_type = 'expense'
              AND DATE_TRUNC('month', t.transaction_date) = DATE_TRUNC('month', %s::date)
            GROUP BY c.name
            ORDER BY total_spent DESC
            LIMIT 1
        """, (first_day,))
        top_category = cur.fetchone()

        cur.close()
        conn.close()

        return MonthlySummaryResponse(
            month=month,
            year=year,
            total_income=float(total_income or 0),
            total_expenses=float(total_expenses or 0),
            top_category=top_category["name"] if top_category else None,
            top_category_spent=float(top_category["total_spent"]) if top_category else 0
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# spending by category
@app.get("/summary/spending-by-category", response_model=SpendingByCategoryResponse)
def spending_by_category(
    year: int = Query(..., description="Year (e.g., 2025)"),
    month: int = Query(..., ge=1, le=12, description="Month (1-12)")
):
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT c.name AS category, 
                   SUM(t.amount) AS total_spent
            FROM transactions t
            JOIN categories c ON t.category_id = c.category_id
            WHERE EXTRACT(YEAR FROM t.transaction_date) = %s
              AND EXTRACT(MONTH FROM t.transaction_date) = %s
              AND t.transaction_type = 'expense'
            GROUP BY c.name
            ORDER BY total_spent DESC;
            """,
            (year, month)
        )
        rows = cur.fetchall()
        cur.close()
        conn.close()

        spending = [SpendingByCategoryItem(category=row["category"], total_spent=float(row["total_spent"])) for row in rows]

        return SpendingByCategoryResponse(
            month=month,
            year=year,
            spending=spending
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))