from src.services.database_service import database_service

def check_instagram_credentials():
    query = """
    SELECT service_name, credential_key, credential_value, description
    FROM credentials
    WHERE service_name = 'instagram';
    """
    
    results = database_service.fetch_all(query)
    
    if not results:
        print("❌ Учетные данные Instagram не найдены")
        return
    
    print("Найденные учетные данные Instagram:")
    print("-" * 50)
    for row in results:
        print(f"{row['credential_key']}: {row['credential_value'][:10]}...")
        print(f"Description: {row['description']}")
        print("-" * 30)

if __name__ == '__main__':
    check_instagram_credentials()
