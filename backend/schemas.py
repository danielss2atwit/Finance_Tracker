from typing import Optional, List
from pydantic import BaseModel
import datetime 
from enum import Enum


#Enum for transaction types
class TransactionType(str,Enum):
    income = "income"
    expense="expense"

# Create transaction schema
class TransactionCreate(BaseModel):
    transaction_date: Optional[datetime.date] = None
    description: str
    amount: float
    category_id: int
    transaction_type: TransactionType

# Update transaction schema
class TransactionUpdate(BaseModel):
    transaction_date: Optional[datetime.date] = None
    description: Optional[str] = None
    amount: Optional[float] = None
    category_id: Optional[int] = None
    transaction_type: Optional[TransactionType] = None

# Response schema
class TransactionResponse(BaseModel):
    transaction_id: int
    transaction_date: datetime.date
    description: str
    amount: float
    category_id: int
    transaction_type: TransactionType

# Response with category name
class TransactionWithCategory(BaseModel):
    transaction_id: int
    transaction_date: datetime.date
    description: str
    amount: float
    category_id: Optional[int] = None
    category: Optional[str] = None
    transaction_type: TransactionType

class TransactionDeleteResponse(BaseModel):
    message: str

class CategoryCreate(BaseModel):
    name: str

class CategoryResponse(BaseModel):
    category_id: int
    name: str

class MonthlySummaryResponse(BaseModel):
    month: int
    year: int
    total_income: float
    total_expenses: float
    top_category: Optional[str] = None
    top_category_spent: float = 0.0


class SpendingByCategoryItem(BaseModel):
    category: str
    total_spent: float


class SpendingByCategoryResponse(BaseModel):
    month: int
    year: int
    spending: List[SpendingByCategoryItem]