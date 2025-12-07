import sqlite3
import os
import json
from datetime import datetime

class Database:
    def __init__(self, db_path='data/finance_bot.db'):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.create_tables()   

    def create_tables(self):
        # Таблица пользователей
        users_query = """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        
        # Таблица кредитов (обновленная)
        credits_query = """
        CREATE TABLE IF NOT EXISTS credits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            debt_amount REAL,
            current_debt REAL,
            annual_rate REAL,
            months INTEGER,
            months_paid INTEGER DEFAULT 0,
            monthly_payment REAL,
            total_payment REAL,
            overpayment REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        """
        
        # Таблица платежей по кредитам
        payments_query = """
        CREATE TABLE IF NOT EXISTS credit_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            credit_id INTEGER,
            user_id INTEGER,
            payment_amount REAL,
            principal_amount REAL,
            interest_amount REAL,
            remaining_debt REAL,
            payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (credit_id) REFERENCES credits (id),
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        """
        
        # Таблица вкладов
        investments_query = """
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            annual_rate REAL,
            monthly_income REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        """
        
        self.conn.execute(users_query)
        self.conn.execute(credits_query)
        self.conn.execute(payments_query)
        self.conn.execute(investments_query)
        self.conn.commit()
    
    def get_or_create_user(self, user_id, username, first_name, last_name):
        query = "SELECT * FROM users WHERE user_id = ?"
        cursor = self.conn.execute(query, (user_id,))
        user = cursor.fetchone()
        
        if not user:
            query = """
            INSERT INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            """
            self.conn.execute(query, (user_id, username, first_name, last_name))
            self.conn.commit()
        
        return user_id
    
    def add_credit(self, user_id, debt_amount, annual_rate, months, monthly_payment, total_payment, overpayment):
        query = """
        INSERT INTO credits (user_id, debt_amount, current_debt, annual_rate, months, monthly_payment, total_payment, overpayment)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        cursor = self.conn.cursor()
        cursor.execute(query, (user_id, debt_amount, debt_amount, annual_rate, months, monthly_payment, total_payment, overpayment))
        self.conn.commit()
        return cursor.lastrowid 

    def delete_credit(self, credit_id, user_id):
        """Удаляет кредит пользователя"""
        query = "DELETE FROM credits WHERE id = ? AND user_id = ?"
        cursor = self.conn.cursor()
        cursor.execute(query, (credit_id, user_id))
        self.conn.commit()
        success = cursor.rowcount > 0
        cursor.close()
        return success

    def get_user_credits(self, user_id):
        query = """
        SELECT * FROM credits 
        WHERE user_id = ? 
        ORDER BY created_at DESC
        """
        cursor = self.conn.execute(query, (user_id,))
        return cursor.fetchall()
    
    def get_credit_by_id(self, credit_id, user_id):
        query = "SELECT * FROM credits WHERE id = ? AND user_id = ?"
        cursor = self.conn.execute(query, (credit_id, user_id))
        return cursor.fetchone()
    
    def add_payment(self, credit_id, user_id, payment_amount, principal_amount, interest_amount, remaining_debt):
        query = """
        INSERT INTO credit_payments (credit_id, user_id, payment_amount, principal_amount, interest_amount, remaining_debt)
        VALUES (?, ?, ?, ?, ?, ?)
        """
        self.conn.execute(query, (credit_id, user_id, payment_amount, principal_amount, interest_amount, remaining_debt))
        
        # Обновляем текущий долг и количество оплаченных месяцев
        update_query = """
        UPDATE credits 
        SET current_debt = ?, months_paid = months_paid + 1 
        WHERE id = ?
        """
        self.conn.execute(update_query, (remaining_debt, credit_id))
        self.conn.commit()
    
    def get_credit_payments(self, credit_id):
        query = "SELECT * FROM credit_payments WHERE credit_id = ? ORDER BY payment_date DESC"
        cursor = self.conn.execute(query, (credit_id,))
        return cursor.fetchall()
    
    def get_user_investments(self, user_id):
        return []
    
    def close(self):
        if self.conn:
            self.conn.close()

def init_database():
    """Инициализация БД при первом запуске в Docker"""
    db_path = 'data/finance_bot.db'
    
    if not os.path.exists(db_path):
        print(f"📦 Инициализирую базу данных: {db_path}")
        db = Database(db_path)
        db.close()
        return True
    return False

if __name__ == '__main__':
    # Тест для Docker
    init_database()
    print("✅ База данных готова к работе")
