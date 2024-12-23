#!/usr/bin/env python3
import os
import sys
import subprocess
import logging
import time
from typing import Optional

# Добавляем путь к src в PYTHONPATH
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.services.config_service import config_service

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

class DeployProgress:
    def __init__(self):
        self.steps = [
            "Checking configuration",
            "Verifying Docker installation",
            "Verifying Supabase CLI",
            "Building Docker image",
            "Deploying to Supabase",
            "Verifying deployment"
        ]
        self.current_step = 0
        
    def next_step(self):
        """Переход к следующему шагу"""
        self.current_step += 1
        total_steps = len(self.steps)
        step_name = self.steps[self.current_step - 1]
        progress = f"[{self.current_step}/{total_steps}]"
        logger.info(f"\n{progress} {step_name}...")

def run_command(command: str, cwd: Optional[str] = None, show_output: bool = False) -> str:
    """Выполнить команду и вернуть результат"""
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        output = []
        if show_output:
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    output.append(line.strip())
                    logger.info(line.strip())
        else:
            stdout, stderr = process.communicate()
            output = stdout.splitlines()
            
        if process.returncode != 0:
            raise subprocess.CalledProcessError(
                process.returncode,
                command,
                output='\n'.join(output),
                stderr=process.stderr.read() if show_output else stderr
            )
            
        return '\n'.join(output)
        
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {e.cmd}")
        logger.error(f"Error output: {e.stderr}")
        raise

def deploy_to_supabase():
    """Деплой бота на Supabase Compute"""
    try:
        progress = DeployProgress()
        project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Шаг 1: Проверка конфигурации
        progress.next_step()
        required_vars = [
            'TELEGRAM_BOT_TOKEN_PROD',
            'TELEGRAM_WEBHOOK_SECRET',
            'OPENAI_API_KEY'
        ]
        
        for var in required_vars:
            value = config_service.get_config(var)
            if not value:
                raise ValueError(f"Missing required configuration: {var}")
            logger.info(f"✓ Found {var}")
            
        # Шаг 2: Проверка Docker
        progress.next_step()
        version = run_command("docker --version")
        logger.info(f"✓ {version}")
        
        # Шаг 3: Проверка Supabase CLI
        progress.next_step()
        version = run_command("supabase --version")
        logger.info(f"✓ Version {version}")
        
        # Шаг 4: Сборка Docker образа
        progress.next_step()
        image_name = "flower-shop-bot"
        logger.info("Building image (this may take a few minutes)...")
        run_command(
            f"docker build -t {image_name} .",
            cwd=project_dir,
            show_output=True
        )
        logger.info("✓ Image built successfully")
        
        # Шаг 5: Логин и пуш в Container Registry
        progress.next_step()
        logger.info("Deploying to Supabase...")
        
        # Создаем директорию для функции если её нет
        os.makedirs("supabase/functions/bot", exist_ok=True)
        
        # Копируем Dockerfile
        run_command("cp Dockerfile supabase/functions/bot/")
        
        # Копируем исходники
        run_command("cp -r src supabase/functions/bot/")
        run_command("cp -r scripts supabase/functions/bot/")
        run_command("cp requirements.txt supabase/functions/bot/")
        
        # Деплоим функцию
        run_command(
            "supabase functions deploy bot --project-ref dkohweivbdwweyvyvcbc",
            show_output=True
        )
        
        # Шаг 6: Деплой на Supabase Compute
        progress.next_step()
        logger.info("Waiting for deployment...")
        time.sleep(5)  # Даем время на применение изменений
        
        # Шаг 7: Проверка статуса
        progress.next_step()
        status = run_command(
            "supabase functions list --project-ref dkohweivbdwweyvyvcbc"
        )
        logger.info("\nDeployment Status:")
        logger.info(status)
        
        return True
        
    except Exception as e:
        logger.error(f"\n❌ Error: {str(e)}")
        raise

if __name__ == "__main__":
    try:
        deploy_to_supabase()
        logger.info("\n✨ Deployment successful! ✨")
    except Exception as e:
        logger.error(f"\n❌ Deployment failed: {str(e)}")
        sys.exit(1)
