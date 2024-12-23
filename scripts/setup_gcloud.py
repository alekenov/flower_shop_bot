#!/usr/bin/env python3
import os
import sys
import json
import tempfile
import subprocess
from pathlib import Path
from psycopg2.extras import DictCursor

# Добавляем путь к src в PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from src.services.config_service import config_service

def run_command(command, **kwargs):
    """Выполнить команду и вернуть результат"""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            text=True,
            capture_output=True,
            **kwargs
        )
        print(f"✓ {result.stdout.strip()}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e.stderr}")
        raise

def setup_gcloud():
    """Настройка Google Cloud CLI"""
    try:
        print("\n🔄 Настройка Google Cloud CLI...")
        
        # Получаем сервисный ключ из таблицы credentials
        print("\n1️⃣ Получение сервисного ключа из таблицы credentials...")
        with config_service.conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute(
                """
                SELECT credential_value
                FROM credentials
                WHERE service_name = 'google'
                AND credential_key = 'flower_shop_bot_service_account'
                """
            )
            result = cur.fetchone()
            if not result:
                raise ValueError("Сервисный ключ Google не найден в таблице credentials")
            service_key = result['credential_value']
        
        # Создаем временный файл для ключа
        print("\n2️⃣ Сохранение ключа во временный файл...")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp:
            json.dump(json.loads(service_key), temp)
            key_path = temp.name
            
        try:
            # Активируем сервисный аккаунт
            print("\n3️⃣ Активация сервисного аккаунта...")
            run_command(f"gcloud auth activate-service-account --key-file={key_path}")
            
            # Получаем project_id из ключа
            key_data = json.loads(service_key)
            project_id = key_data.get('project_id')
            if not project_id:
                raise ValueError("project_id не найден в сервисном ключе")
                
            # Устанавливаем проект
            print(f"\n4️⃣ Установка проекта {project_id}...")
            run_command(f"gcloud config set project {project_id}")
            
            # Включаем необходимые API
            print("\n5️⃣ Включение необходимых API...")
            apis = [
                "cloudbuild.googleapis.com",
                "run.googleapis.com",
                "containerregistry.googleapis.com"
            ]
            for api in apis:
                print(f"\nВключение {api}...")
                run_command(f"gcloud services enable {api}")
                
            print("\n✨ Google Cloud CLI успешно настроен!")
            
        finally:
            # Удаляем временный файл
            print("\n🧹 Очистка временных файлов...")
            os.unlink(key_path)
            
    except Exception as e:
        print(f"\n❌ Ошибка: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    setup_gcloud()
