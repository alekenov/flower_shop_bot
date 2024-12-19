import requests
import json

def get_instagram_page_messages():
    access_token = 'EAAW4km4ocGkBO9nkPGiP62dEkFE12kgmtTJIs8g2BdegW6LnXoNtWEHXnZC26qIZALwkq61qYdvxwyUcL1cov6fYr57xtjXLayTRHzk505TgBA7lWew4ni4jsdZCbLxlksr09IneI4azdnZCZCNQcGGq3v8aI2SCrXJEjV4xmGFXHnnDLBNovGohsqpcHK02mgMHwpIknJBlQU4AjbXSiq4TvCZCGo'
    page_id = '103684722137046'  # ID страницы "Cvety.kz - маркетплейс цветов и подарков"
    
    try:
        # 1. Проверяем доступ к странице
        page_url = f'https://graph.facebook.com/v18.0/{page_id}'
        page_params = {
            'access_token': access_token,
            'fields': 'name,id,instagram_business_account'
        }
        
        response = requests.get(page_url, params=page_params)
        page_data = response.json()
        
        print("\n1. Информация о странице Facebook:")
        print(json.dumps(page_data, indent=2, ensure_ascii=False))
        
        # 2. Пробуем получить сообщения через Page ID
        messages_url = f'https://graph.facebook.com/v18.0/{page_id}/conversations'
        messages_params = {
            'access_token': access_token,
            'fields': 'participants,messages{message,from,to,created_time}'
        }
        
        response = requests.get(messages_url, params=messages_params)
        messages_data = response.json()
        
        print("\n2. Сообщения через Page ID:")
        print(json.dumps(messages_data, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Ошибка при выполнении запроса: {str(e)}")

if __name__ == '__main__':
    get_instagram_page_messages()
