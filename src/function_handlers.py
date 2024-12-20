import json
import logging
from typing import Dict, Any, List
from datetime import datetime

from services.sheets_service import SheetsService

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize services
sheets_service = SheetsService()

# Определение инструментов для OpenAI
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_bouquet_info",
            "description": "Получить информацию о букете по его названию",
            "parameters": {
                "type": "object",
                "properties": {
                    "bouquet_id": {
                        "type": "string",
                        "description": "Название букета"
                    }
                },
                "required": ["bouquet_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_bouquets",
            "description": "Поиск букетов по параметрам",
            "parameters": {
                "type": "object",
                "properties": {
                    "price_min": {
                        "type": "number",
                        "description": "Минимальная цена"
                    },
                    "price_max": {
                        "type": "number",
                        "description": "Максимальная цена"
                    },
                    "flower_type": {
                        "type": "string",
                        "description": "Тип цветов (розы, тюльпаны и т.д.)"
                    },
                    "occasion": {
                        "type": "string",
                        "description": "Повод (день рождения, свадьба и т.д.)"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "check_delivery",
            "description": "Проверить возможность доставки по адресу",
            "parameters": {
                "type": "object",
                "properties": {
                    "address": {
                        "type": "string",
                        "description": "Адрес доставки"
                    },
                    "delivery_time": {
                        "type": "string",
                        "description": "Желаемое время доставки (формат: YYYY-MM-DD HH:MM)"
                    }
                },
                "required": ["address"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_order",
            "description": "Создать новый заказ",
            "parameters": {
                "type": "object",
                "properties": {
                    "bouquet_name": {
                        "type": "string",
                        "description": "Название букета"
                    },
                    "customer_name": {
                        "type": "string",
                        "description": "Имя заказчика"
                    },
                    "customer_phone": {
                        "type": "string",
                        "description": "Телефон заказчика"
                    },
                    "delivery_address": {
                        "type": "string",
                        "description": "Адрес доставки"
                    },
                    "delivery_time": {
                        "type": "string",
                        "description": "Время доставки (формат: YYYY-MM-DD HH:MM)"
                    }
                },
                "required": ["bouquet_name", "customer_name", "customer_phone", "delivery_address"]
            }
        }
    }
]

async def execute_function(function_name: str, arguments: Dict[str, Any]) -> str:
    """
    Выполнить функцию с заданными аргументами
    """
    try:
        logger.info(f"Executing function {function_name} with arguments: {arguments}")
        
        if function_name == "get_bouquet_info":
            # Получаем информацию о букете из Google Sheets
            bouquet_name = arguments.get("bouquet_id")
            inventory = sheets_service.get_inventory_data()
            
            for item in inventory:
                if item["name"].lower() == bouquet_name.lower():
                    return json.dumps({
                        "name": item["name"],
                        "price": item["price"],
                        "description": item["description"],
                        "available": item["quantity"] > 0
                    }, ensure_ascii=False)
            return "Букет не найден"

        elif function_name == "search_bouquets":
            # Поиск букетов по параметрам в Google Sheets
            inventory = sheets_service.get_inventory_data()
            matching_bouquets = []
            
            price_min = arguments.get("price_min")
            price_max = arguments.get("price_max")
            flower_type = arguments.get("flower_type", "").lower()
            occasion = arguments.get("occasion", "").lower()
            
            for item in inventory:
                # Получаем числовое значение цены
                try:
                    price = float(item["price"].split()[0])
                except (ValueError, IndexError):
                    price = 0
                
                # Проверяем соответствие параметрам
                if price_min and price < price_min:
                    continue
                if price_max and price > price_max:
                    continue
                if flower_type and flower_type not in item["name"].lower():
                    continue
                if occasion and occasion not in item["description"].lower():
                    continue
                
                matching_bouquets.append({
                    "name": item["name"],
                    "price": item["price"],
                    "description": item["description"]
                })
            
            return json.dumps(matching_bouquets[:5], ensure_ascii=False)

        elif function_name == "check_delivery":
            # Проверка возможности доставки
            address = arguments.get("address")
            delivery_time = arguments.get("delivery_time")
            
            # Здесь должна быть логика проверки доставки
            # Пока возвращаем заглушку
            return json.dumps({
                "available": True,
                "price": 1500,
                "estimated_time": "1-2 часа"
            }, ensure_ascii=False)

        elif function_name == "create_order":
            # Создание нового заказа
            required_fields = ["bouquet_name", "customer_name", "customer_phone", "delivery_address"]
            if not all(field in arguments for field in required_fields):
                return "Не все обязательные поля заполнены"
            
            # Проверяем наличие букета
            inventory = sheets_service.get_inventory_data()
            bouquet_exists = False
            for item in inventory:
                if item["name"].lower() == arguments["bouquet_name"].lower():
                    bouquet_exists = True
                    if item["quantity"] <= 0:
                        return "К сожалению, этот букет сейчас недоступен"
                    break
            
            if not bouquet_exists:
                return "Букет не найден"
            
            # В реальном приложении здесь должно быть сохранение заказа
            return json.dumps({
                "order_id": "TEST-" + datetime.now().strftime("%Y%m%d-%H%M%S"),
                "status": "created",
                "message": "Заказ успешно создан"
            }, ensure_ascii=False)

        else:
            return f"Неизвестная функция: {function_name}"

    except Exception as e:
        logger.error(f"Error executing function {function_name}: {str(e)}", exc_info=True)
        return f"Произошла ошибка при выполнении функции: {str(e)}"
