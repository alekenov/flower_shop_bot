#!/usr/bin/env python3
import os
import sys
import subprocess
import logging

# Добавляем путь к src в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.services.config_service import config_service

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_command(command, cwd=None):
    """Выполнить команду и вернуть результат"""
    try:
        result = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            shell=True,
            capture_output=True,
            text=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.cmd}")
        logger.error(f"Error output: {e.stderr}")
        raise

def deploy_webhook():
    """Деплой вебхука в Supabase"""
    try:
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        webhook_dir = os.path.join(project_dir, 'supabase', 'functions', 'python-webhook')
        
        logger.info("Starting webhook deployment...")
        
        # Проверяем наличие необходимых переменных окружения
        required_vars = [
            'TELEGRAM_BOT_TOKEN_PROD',
            'TELEGRAM_WEBHOOK_SECRET',
            'OPENAI_API_KEY'
        ]
        
        for var in required_vars:
            value = config_service.get_config(var)
            if not value:
                raise ValueError(f"Missing required configuration: {var}")
            logger.info(f"Found {var} in database")
        
        # Проверяем установлен ли Supabase CLI
        try:
            version = run_command("supabase --version")
            logger.info(f"Found Supabase CLI version: {version}")
        except:
            raise RuntimeError("Supabase CLI not found. Please install it first.")
        
        # Деплоим функцию
        logger.info("Deploying webhook function...")
        result = run_command(
            "supabase functions deploy python-webhook --project-ref dkohweivbdwweyvyvcbc",
            cwd=project_dir
        )
        logger.info("Deployment result:")
        logger.info(result)
        
        # Получаем URL функции
        function_url = f"https://dkohweivbdwweyvyvcbc.supabase.co/functions/v1/python-webhook"
        logger.info(f"Function deployed at: {function_url}")
        
        return function_url
        
    except Exception as e:
        logger.error(f"Deployment failed: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        webhook_url = deploy_webhook()
        print(f"\nWebhook successfully deployed!")
        print(f"URL: {webhook_url}")
    except Exception as e:
        print(f"\nDeployment failed: {str(e)}")
        sys.exit(1)
