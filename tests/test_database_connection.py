import os
import sys
import logging
import psycopg2
from psycopg2.extras import RealDictCursor

# Настраиваем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Добавляем путь к src
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_direct_connection():
    """Тест прямого подключения к БД"""
    logger.info("Testing direct database connection...")
    
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres.dkohweivbdwweyvyvcbc",
            password="vigkif-nesJy2-kivraq",
            host="aws-0-eu-central-1.pooler.supabase.com",
            port="6543"
        )
        conn.set_session(autocommit=True)
        cur = conn.cursor(cursor_factory=RealDictCursor)
        
        # Пробуем выполнить простой запрос
        cur.execute("SELECT 1 as test")
        result = cur.fetchall()
        
        if result and result[0]['test'] == 1:
            logger.info("✅ Direct database connection successful!")
            
            # Проверяем существование таблицы credentials
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'credentials'
                );
            """)
            table_exists = cur.fetchone()['exists']
            
            if table_exists:
                logger.info("✅ Credentials table exists!")
                
                # Проверяем записи в таблице credentials
                cur.execute("""
                    SELECT * FROM credentials 
                    WHERE service_name = 'supabase'
                """)
                credentials = cur.fetchall()
                logger.info(f"Found {len(credentials)} credentials records")
                
                for cred in credentials:
                    logger.info(f"- {cred['service_name']}: {cred['credential_key']}")
            else:
                logger.warning("⚠️ Credentials table does not exist!")
            
            return True
        else:
            logger.error("❌ Database query failed!")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        return False
    finally:
        if 'cur' in locals():
            cur.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    logger.info("Starting database connection test...")
    
    if test_direct_connection():
        logger.info("✅ All tests passed successfully!")
        sys.exit(0)
    else:
        logger.error("❌ Test failed!")
        sys.exit(1)
