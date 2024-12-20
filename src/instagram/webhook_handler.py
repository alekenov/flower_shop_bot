from flask import Flask, request, jsonify
import hmac
import hashlib
import json
import requests
import os

app = Flask(__name__)

VERIFY_TOKEN = 'f46a6797028932fea46fe712747c7c7b6f423cb44126c4682d4e08868710bab1'
APP_SECRET = '7c4df0e85dbbfb2cdd054a3fd59b9178'
PAGE_ACCESS_TOKEN = 'EAAW4km4ocGkBO7FI3X021kpiaJMbaeg5gtWby8gXZBitl98aCAJ6SKoYz0YJUBqeRhd0qNlRMwo1TT8SjA4ILLkoBuRjGjMedNeLaCfkKZAznzw2I8j8NCEK7vHrdbEgfsNGRwwCE04yT9QY7UDyJ6vZAJRSRyXttB2UfKSQ14yedfUIUo2GSYNmanXJt8PxA43SPqlOUZCQgZC55Hgc2l1Po'

@app.route('/webhook/instagram', methods=['GET'])
def verify_webhook():
    """Подтверждение вебхука для Instagram Messaging"""
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')
    
    print(f"Получен запрос на верификацию вебхука:")
    print(f"mode: {mode}")
    print(f"token: {token}")
    print(f"challenge: {challenge}")
    
    if mode and token:
        if mode == 'subscribe' and token == VERIFY_TOKEN:
            print("✅ Вебхук верифицирован!")
            return challenge
        else:
            print("❌ Ошибка верификации: неверный токен")
            return 'Forbidden', 403
    return 'Bad Request', 400

@app.route('/webhook/instagram', methods=['POST'])
def webhook():
    """Обработка входящих уведомлений"""
    signature = request.headers.get('X-Hub-Signature-256', '')
    
    print("\nПолучен POST запрос:")
    print(f"Заголовки: {dict(request.headers)}")
    print(f"Подпись: {signature}")
    
    if not verify_signature(request.data, signature):
        print("❌ Ошибка проверки подписи")
        return 'Invalid signature', 403
    
    data = request.json
    print("\nПолучены данные:", json.dumps(data, indent=2, ensure_ascii=False))
    
    try:
        if data['object'] == 'instagram':
            for entry in data.get('entry', []):
                # Обработка сообщений
                if 'messaging' in entry:
                    for messaging in entry['messaging']:
                        sender_id = messaging.get('sender', {}).get('id')
                        message = messaging.get('message', {}).get('text')
                        
                        if sender_id and message:
                            print(f"\n✉️ Новое сообщение от {sender_id}: {message}")
                            # Отправляем эхо-ответ
                            response = send_message(sender_id, f"Эхо: {message}")
                            print(f"Ответ отправлен: {response}")
                
                # Обработка изменений
                if 'changes' in entry:
                    for change in entry['changes']:
                        print(f"\nИзменение: {json.dumps(change, indent=2, ensure_ascii=False)}")
        
        return 'OK', 200
    
    except Exception as e:
        print(f"❌ Ошибка обработки запроса: {str(e)}")
        return 'Internal Server Error', 500

def verify_signature(payload, signature):
    """Проверка подписи от Instagram"""
    if not signature:
        return False
    
    expected_signature = hmac.new(
        bytes(APP_SECRET, 'utf-8'),
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)

def send_message(recipient_id, message_text):
    """Отправка сообщения пользователю"""
    url = f"https://graph.facebook.com/v21.0/me/messages"
    
    data = {
        "recipient": {"id": recipient_id},
        "message": {"text": message_text},
        "access_token": PAGE_ACCESS_TOKEN
    }
    
    try:
        response = requests.post(url, json=data)
        print(f"\nОтправка сообщения:")
        print(f"URL: {url}")
        print(f"Данные: {json.dumps(data, indent=2, ensure_ascii=False)}")
        print(f"Ответ: {response.text}")
        
        if response.status_code != 200:
            print(f"❌ Ошибка отправки: {response.status_code}")
            print(response.text)
        
        return response.json()
    
    except Exception as e:
        print(f"❌ Ошибка при отправке сообщения: {str(e)}")
        return None

if __name__ == '__main__':
    print("🚀 Запуск сервера для обработки вебхуков Instagram...")
    app.run(host='0.0.0.0', port=5002, debug=True)
