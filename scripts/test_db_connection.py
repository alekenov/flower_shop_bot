import psycopg2
from psycopg2.extras import DictCursor

def test_db_connection():
    try:
        # Подключение через URL
        conn = psycopg2.connect(
            "postgresql://postgres.dkohweivbdwweyvyvcbc:vigkif-nesJy2-kivraq@aws-0-eu-central-1.pooler.supabase.com:6543/postgres"
        )
        
        print("✅ Подключение к БД успешно установлено")
        
        # Получаем учетные данные OpenAI
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT credential_key, credential_value, description 
                FROM credentials 
                WHERE service_name = 'openai'
            """)
            credentials = cur.fetchall()
            
            print("\nНайденные учетные данные OpenAI:")
            print("-" * 50)
            for cred in credentials:
                key = cred['credential_key']
                value = cred['credential_value']
                desc = cred['description']
                
                # Маскируем значение, показывая только первые 8 символов
                masked_value = value[:8] + "..." if value else "None"
                print(f"{key}: {masked_value}")
                print(f"Description: {desc}")
                print("-" * 30)
                
        return True
        
    except Exception as e:
        print(f"❌ Ошибка: {str(e)}")
        return False
    
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    test_db_connection()
