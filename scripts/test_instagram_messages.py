import requests

def test_instagram_messages():
    # Используем Page Access Token
    page_access_token = 'EAAW4km4ocGkBO7FI3X021kpiaJMbaeg5gtWby8gXZBitl98aCAJ6SKoYz0YJUBqeRhd0qNlRMwo1TT8SjA4ILLkoBuRjGjMedNeLaCfkKZAznzw2I8j8NCEK7vHrdbEgfsNGRwwCE04yT9QY7UDyJ6vZAJRSRyXttB2UfKSQ14yedfUIUo2GSYNmanXJt8PxA43SPqlOUZCQgZC55Hgc2l1Po'
    instagram_account_id = '17841401762853582'  # ID вашего Instagram Business Account
    
    # 1. Проверяем информацию об Instagram аккаунте
    url = f'https://graph.facebook.com/v21.0/{instagram_account_id}'
    params = {
        'access_token': page_access_token,
        'fields': 'name,username,profile_picture_url'
    }
    
    response = requests.get(url, params=params)
    print("\n1. Информация об Instagram аккаунте:")
    print(response.json())
    
    # 2. Получаем сообщения из Instagram
    messages_url = f'https://graph.facebook.com/v21.0/{instagram_account_id}/messages'
    messages_params = {
        'access_token': page_access_token,
        'fields': 'from,message,created_time'
    }
    
    response = requests.get(messages_url, params=messages_params)
    print("\n2. Сообщения из Instagram:")
    print(response.json())

if __name__ == '__main__':
    test_instagram_messages()
