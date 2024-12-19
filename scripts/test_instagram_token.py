import requests
from src.services.database_service import database_service

def test_instagram_token():
    # Получаем токен из базы данных
    token = database_service.get_credential('instagram', 'access_token')
    
    # URL для получения списка страниц
    url = 'https://graph.facebook.com/v18.0/me/accounts'
    
    # Параметры запроса
    params = {
        'access_token': token,
        'fields': 'instagram_business_account,name'
    }
    
    try:
        # Делаем запрос к API
        response = requests.get(url, params=params)
        data = response.json()
        
        print("Ответ от API:")
        print(data)
        
        # Если есть данные, ищем Instagram Business Account ID
        if 'data' in data:
            for page in data['data']:
                if 'instagram_business_account' in page:
                    ig_account_id = page['instagram_business_account']['id']
                    print(f"\n✅ Найден Instagram Business Account ID: {ig_account_id}")
                    
                    # Сохраняем ID в базу данных
                    save_query = """
                    INSERT INTO credentials (service_name, credential_key, credential_value, description)
                    VALUES (%(service_name)s, %(credential_key)s, %(credential_value)s, %(description)s)
                    ON CONFLICT (service_name, credential_key) 
                    DO UPDATE SET 
                        credential_value = EXCLUDED.credential_value,
                        description = EXCLUDED.description;
                    """
                    
                    database_service.execute_query(save_query, {
                        'service_name': 'instagram',
                        'credential_key': 'business_account_id',
                        'credential_value': ig_account_id,
                        'description': 'Instagram Business Account ID'
                    })
                    print("✅ ID сохранен в базу данных")
                    return
                    
        print("❌ Instagram Business Account ID не найден")
        
    except Exception as e:
        print(f"❌ Ошибка при проверке токена: {str(e)}")

if __name__ == '__main__':
    test_instagram_token()
