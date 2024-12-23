#!/usr/bin/env python3
"""
Deployment script for the Flower Shop Bot to Google Cloud Run
"""

import os
import sys
import logging
import argparse
import subprocess
from pathlib import Path

import requests
from dotenv import load_dotenv

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class CloudRunDeployer:
    def __init__(self):
        """Initialize deployer with configuration"""
        load_dotenv()
        self.project_root = Path(__file__).parent.parent
        self.src_dir = self.project_root / "src"
        
        # Cloud Run конфигурация
        self.project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        self.region = "europe-west1"
        self.service_name = "flower-shop-bot"
        self.service_url = f"{self.service_name}-{self.project_id}.{self.region}.run.app"

    def deploy(self):
        """Deploy to Google Cloud Run"""
        try:
            logger.info("Starting deployment to Cloud Run...")
            
            # Сборка Docker образа
            image_name = f"gcr.io/{self.project_id}/{self.service_name}"
            subprocess.run(["docker", "build", "-t", image_name, "."], check=True)
            
            # Пуш образа в Container Registry
            subprocess.run(["docker", "push", image_name], check=True)
            
            # Деплой в Cloud Run
            deploy_cmd = [
                "gcloud", "run", "deploy", self.service_name,
                "--image", image_name,
                "--platform", "managed",
                "--region", self.region,
                "--project", self.project_id,
                "--allow-unauthenticated"
            ]
            subprocess.run(deploy_cmd, check=True)
            
            logger.info("Successfully deployed to Cloud Run")
            
            # Настраиваем webhook после деплоя
            self.setup_webhook()
            return True
            
        except Exception as e:
            logger.error(f"Error deploying to Cloud Run: {e}")
            return False

    def setup_webhook(self):
        """Setup or update webhook for Telegram bot"""
        try:
            from src.services.supabase import SupabaseService
            
            logger.info("Setting up webhook...")
            
            # Получаем токен бота
            supabase = SupabaseService()
            bot_token = supabase.get_credential('telegram', 'bot_token_prod')
            
            if not bot_token:
                raise ValueError("Bot token not found")
            
            # Формируем URL для вебхука
            webhook_url = f"https://{self.service_url}/webhook"
            
            # Настраиваем webhook
            api_url = f"https://api.telegram.org/bot{bot_token}/setWebhook"
            response = requests.post(api_url, json={"url": webhook_url})
            response.raise_for_status()
            
            webhook_info = response.json()
            if webhook_info.get("ok"):
                logger.info(f"Webhook successfully set to {webhook_url}")
                return True
            else:
                logger.error(f"Failed to set webhook: {webhook_info}")
                return False
                
        except Exception as e:
            logger.error(f"Error setting up webhook: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description='Deploy Flower Shop Bot to Cloud Run')
    parser.add_argument('--skip-webhook', action='store_true',
                       help='Skip webhook setup after deployment')
    args = parser.parse_args()
    
    deployer = CloudRunDeployer()
    success = deployer.deploy()
    
    sys.exit(0 if success else 1)

if __name__ == '__main__':
    main()
