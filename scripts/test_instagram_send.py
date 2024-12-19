import requests

def send_test_message():
    # Используем Page Access Token
    page_access_token = 'EAAW4km4ocGkBO7FI3X021kpiaJMbaeg5gtWby8gXZBitl98aCAJ6SKoYz0YJUBqeRhd0qNlRMwo1TT8SjA4ILLkoBuRjGjMedNeLaCfkKZAznzw2I8j8NCEK7vHrdbEgfsNGRwwCE04yT9QY7UDyJ6vZAJRSRyXttB2UfKSQ14yedfUIUo2GSYNmanXJt8PxA43SPqlOUZCQgZC55Hgc2l1Po'
    page_id = '103684722137046'  # ID Facebook страницы
    
    # 1. Сначала получим ID Instagram аккаунта
    url = f'https://graph.facebook.com/v21.0/{page_id}'
    params = {
        'access_token': page_access_token,
        'fields': 'instagram_business_account'
    }
    
    response = requests.get(url, params=params)
    print("\n1. Информация о привязанном Instagram аккаунте:")
    print(response.json())
    
    # 2. Отправляем тестовое сообщение
    messages_url = f'https://graph.facebook.com/v21.0/{page_id}/messages'
    data = {
        'recipient': {'id': page_id},  # Отправляем на ID страницы
        'message': {'text': 'Тестовое сообщение от бота! 🤖\nВремя: 14:47'},
        'messaging_type': 'RESPONSE',
        'access_token': page_access_token
    }
    
    response = requests.post(messages_url, json=data)
    print("\n2. Результат отправки:")
    print(response.json())
    
    if response.status_code == 200:
        print("\n✅ Сообщение успешно отправлено!")
    else:
        print(f"\n❌ Ошибка при отправке: {response.status_code}")
        print(response.text)

if __name__ == '__main__':
    send_test_message()
