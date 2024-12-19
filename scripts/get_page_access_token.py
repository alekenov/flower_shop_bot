import requests
import json

def get_page_access_token():
    user_access_token = 'EAAW4km4ocGkBO9nkPGiP62dEkFE12kgmtTJIs8g2BdegW6LnXoNtWEHXnZC26qIZALwkq61qYdvxwyUcL1cov6fYr57xtjXLayTRHzk505TgBA7lWew4ni4jsdZCbLxlksr09IneI4azdnZCZCNQcGGq3v8aI2SCrXJEjV4xmGFXHnnDLBNovGohsqpcHK02mgMHwpIknJBlQU4AjbXSiq4TvCZCGo'
    page_id = '103684722137046'
    
    try:
        # Получаем Page Access Token
        url = 'https://graph.facebook.com/v18.0/me/accounts'
        params = {
            'access_token': user_access_token
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        print("Список страниц и их токены:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Ищем нужную страницу
        if 'data' in data:
            for page in data['data']:
                if page['id'] == page_id:
                    print(f"\nНайден Page Access Token для страницы {page['name']}:")
                    print(f"Token: {page['access_token']}")
                    
                    # Проверяем токен
                    check_url = 'https://graph.facebook.com/debug_token'
                    check_params = {
                        'input_token': page['access_token'],
                        'access_token': user_access_token
                    }
                    
                    check_response = requests.get(check_url, params=check_params)
                    check_data = check_response.json()
                    
                    print("\nИнформация о токене страницы:")
                    print(json.dumps(check_data, indent=2, ensure_ascii=False))
                    
                    return
                    
        print("❌ Страница не найдена")
        
    except Exception as e:
        print(f"Ошибка при получении токена: {str(e)}")

if __name__ == '__main__':
    get_page_access_token()
