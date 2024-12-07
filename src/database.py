import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import os
from typing import List, Dict, Optional

# Load environment variables
load_dotenv()

# Database connection string
DATABASE_URL = "postgresql://postgres.dkohweivbdwweyvyvcbc:vigkif-nesJy2-kivraq@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"

class Database:
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL)
        self.cur = self.conn.cursor(cursor_factory=RealDictCursor)

    def create_tables(self):
        # Create products table
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                description TEXT,
                availability BOOLEAN DEFAULT true
            );
        """)

        # Create knowledge_base table
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id SERIAL PRIMARY KEY,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                category VARCHAR(50),
                keywords TEXT[]
            );
        """)

        # Create chat_logs table
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS chat_logs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                message TEXT,
                bot_response TEXT,
                context TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        self.conn.commit()

    # Products methods
    def add_product(self, name: str, price: float, description: str = None) -> Dict:
        self.cur.execute(
            """
            INSERT INTO products (name, price, description)
            VALUES (%s, %s, %s)
            RETURNING *
            """,
            (name, price, description)
        )
        self.conn.commit()
        return self.cur.fetchone()

    def get_all_products(self) -> List[Dict]:
        self.cur.execute("SELECT * FROM products WHERE availability = true")
        return self.cur.fetchall()

    def get_product(self, product_id: int) -> Optional[Dict]:
        self.cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
        return self.cur.fetchone()

    # Knowledge base methods
    def add_knowledge(self, question: str, answer: str, category: str = None, keywords: List[str] = None) -> Dict:
        self.cur.execute(
            """
            INSERT INTO knowledge_base (question, answer, category, keywords)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (question, answer, category, keywords)
        )
        self.conn.commit()
        return self.cur.fetchone()

    def search_knowledge(self, query: str) -> List[Dict]:
        self.cur.execute(
            """
            SELECT * FROM knowledge_base
            WHERE question ILIKE %s
            OR answer ILIKE %s
            OR %s = ANY(keywords)
            """,
            (f"%{query}%", f"%{query}%", query)
        )
        return self.cur.fetchall()

    # Chat logs methods
    def log_chat(self, user_id: int, message: str, bot_response: str, context: str = None) -> Dict:
        self.cur.execute(
            """
            INSERT INTO chat_logs (user_id, message, bot_response, context)
            VALUES (%s, %s, %s, %s)
            RETURNING *
            """,
            (user_id, message, bot_response, context)
        )
        self.conn.commit()
        return self.cur.fetchone()

    def get_user_chat_history(self, user_id: int, limit: int = 10) -> List[Dict]:
        self.cur.execute(
            """
            SELECT * FROM chat_logs
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (user_id, limit)
        )
        return self.cur.fetchall()

    def close(self):
        self.cur.close()
        self.conn.close()

# Test connection
if __name__ == "__main__":
    try:
        db = Database()
        print("Successfully connected to the database!")
        db.create_tables()
        print("Tables created successfully!")

        # Test adding a product
        product = db.add_product("Роза красная", 100.00, "Красивая красная роза")
        print(f"Added product: {product}")

        # Test getting all products
        products = db.get_all_products()
        print(f"All products: {products}")

        db.close()
    except Exception as e:
        print(f"Error: {e}")
