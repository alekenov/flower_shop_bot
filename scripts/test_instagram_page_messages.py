import requests
import json

def test_instagram_page_messages():
    # Данные для доступа
    page_access_token = 'EAAW4km4ocGkBO7FI3X021kpiaJMbaeg5gtWby8gXZBitl98aCAJ6SKoYz0YJUBqeRhd0qNlRMwo1TT8SjA4ILLkoBuRjGjMedNeLaCfkKZAznzw2I8j8NCEK7vHrdbEgfsNGRwwCE04yT9QY7UDyJ6vZAJRSRyXttB2UfKSQ14yedfUIUo2GSYNmanXJt8PxA43SPqlOUZCQgZC55Hgc2l1Po'
    page_id = '103684722137046'
    instagram_account_id = '17841401762853582'
    
    try:
        # 1. Проверяем доступ к Instagram аккаунту через Page Access Token
        url = f'https://graph.facebook.com/v18.0/{instagram_account_id}'
        params = {
            'access_token': page_access_token,
            'fields': 'id,username,profile_picture_url,name,biography'
        }
        
        response = requests.get(url, params=params)
        account_data = response.json()
        
        print("\n1. Информация об Instagram аккаунте:")
        print(json.dumps(account_data, indent=2, ensure_ascii=False))
        
        # 2. Пробуем получить входящие сообщения
        messages_url = f'https://graph.facebook.com/v18.0/{instagram_account_id}/messages'
        messages_params = {
            'access_token': page_access_token,
            'fields': 'id,from,to,message,created_time'
        }
        
        response = requests.get(messages_url, params=messages_params)
        messages_data = response.json()
        
        print("\n2. Входящие сообщения:")
        print(json.dumps(messages_data, indent=2, ensure_ascii=False))
        
        # 3. Проверяем возможность отправки сообщения
        send_url = f'https://graph.facebook.com/v18.0/{instagram_account_id}/messages'
        send_data = {
            'recipient': {'id': instagram_account_id},
            'message': {'text': 'Тестовое сообщение'},
            'access_token': page_access_token
        }
        
        print("\n3. Проверка возможности отправки сообщения:")
        print("Endpoint:", send_url)
        print("Data:", json.dumps(send_data, indent=2, ensure_ascii=False))
        
        # Закомментировано, чтобы случайно не отправить сообщение
        # response = requests.post(send_url, json=send_data)
        # print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"Ошибка при выполнении запроса: {str(e)}")

if __name__ == '__main__':
    test_instagram_page_messages()
