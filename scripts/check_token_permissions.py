import requests
import json

def check_token_permissions():
    access_token = 'EAAW4km4ocGkBO9nkPGiP62dEkFE12kgmtTJIs8g2BdegW6LnXoNtWEHXnZC26qIZALwkq61qYdvxwyUcL1cov6fYr57xtjXLayTRHzk505TgBA7lWew4ni4jsdZCbLxlksr09IneI4azdnZCZCNQcGGq3v8aI2SCrXJEjV4xmGFXHnnDLBNovGohsqpcHK02mgMHwpIknJBlQU4AjbXSiq4TvCZCGo'
    
    # URL для проверки токена
    url = 'https://graph.facebook.com/debug_token'
    
    # Параметры запроса
    params = {
        'input_token': access_token,
        'access_token': access_token
    }
    
    try:
        response = requests.get(url, params=params)
        data = response.json()
        
        print("Информация о токене:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        if 'data' in data:
            print("\nРазрешения токена:")
            if 'scopes' in data['data']:
                for scope in data['data']['scopes']:
                    print(f"- {scope}")
            else:
                print("Разрешения не найдены")
                
            print("\nСрок действия токена:")
            if 'expires_at' in data['data']:
                print(f"Истекает: {data['data']['expires_at']}")
            else:
                print("Бессрочный токен")
                
    except Exception as e:
        print(f"Ошибка при проверке токена: {str(e)}")

if __name__ == '__main__':
    check_token_permissions()
