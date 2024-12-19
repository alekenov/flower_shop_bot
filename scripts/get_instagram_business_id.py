import requests
import json

def get_instagram_business_id():
    # Токен доступа
    access_token = 'EAAW4km4ocGkBO9nkPGiP62dEkFE12kgmtTJIs8g2BdegW6LnXoNtWEHXnZC26qIZALwkq61qYdvxwyUcL1cov6fYr57xtjXLayTRHzk505TgBA7lWew4ni4jsdZCbLxlksr09IneI4azdnZCZCNQcGGq3v8aI2SCrXJEjV4xmGFXHnnDLBNovGohsqpcHK02mgMHwpIknJBlQU4AjbXSiq4TvCZCGo'
    
    # URL для получения информации о страницах
    url = 'https://graph.facebook.com/v18.0/me/accounts'
    
    # Параметры запроса
    params = {
        'access_token': access_token,
        'fields': 'instagram_business_account,name,id'
    }
    
    try:
        # Делаем запрос
        response = requests.get(url, params=params)
        data = response.json()
        
        print("Ответ от API:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        # Если есть данные, проверяем каждую страницу
        if 'data' in data and data['data']:
            for page in data['data']:
                print(f"\nСтраница: {page.get('name', 'Имя не указано')}")
                print(f"ID страницы: {page.get('id', 'ID не найден')}")
                if 'instagram_business_account' in page:
                    ig_account_id = page['instagram_business_account']['id']
                    print(f"Instagram Business Account ID: {ig_account_id}")
                else:
                    print("❌ Эта страница не связана с Instagram Business аккаунтом")
        else:
            print("\n❌ Не найдено ни одной страницы Facebook. Убедитесь, что:")
            print("1. У вас есть страница Facebook")
            print("2. Токен имеет разрешение pages_show_list")
            print("3. Токен связан с правильным аккаунтом")
        
    except Exception as e:
        print(f"Ошибка при выполнении запроса: {str(e)}")

if __name__ == '__main__':
    get_instagram_business_id()
