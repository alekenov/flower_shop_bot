from .inventory_service import InventoryService

def test_inventory_operations():
    # Создаем экземпляр сервиса
    inventory = InventoryService("1Cqk6yXfblRvTN0m_BmJVqn9zf4AQZZdQeyFcjPlM1jk")
    
    # 1. Получаем все товары
    print("\nПолучаем список всех товаров:")
    products = inventory.get_all_products()
    for product in products:
        print(f"- {product['name']}: {product['price']} тг, {product['quantity']} шт")
    
    # 2. Проверяем конкретный товар
    product_name = "Красные розы"
    print(f"\nИщем товар '{product_name}':")
    product = inventory.get_product_by_name(product_name)
    if product:
        print(f"Найдено: {product['name']}, цена: {product['price']} тг, количество: {product['quantity']} шт")
    else:
        print("Товар не найден")
    
    # 3. Проверяем доступность
    required_quantity = 10
    print(f"\nПроверяем доступность {required_quantity} шт товара '{product_name}':")
    is_available = inventory.check_availability(product_name, required_quantity)
    print(f"Доступно: {'Да' if is_available else 'Нет'}")
    
    # 4. Добавляем новый товар
    new_product = {
        'name': 'Желтые хризантемы',
        'price': '2500',
        'quantity': '40',
        'description': 'Свежие желтые хризантемы'
    }
    print(f"\nДобавляем новый товар '{new_product['name']}'")
    inventory.add_product(
        new_product['name'],
        new_product['price'],
        new_product['quantity'],
        new_product['description']
    )
    
    # 5. Обновляем количество
    update_name = "Желтые хризантемы"
    new_quantity = 35
    print(f"\nОбновляем количество товара '{update_name}' на {new_quantity}")
    inventory.update_quantity(update_name, new_quantity)
    
    # Проверяем обновленные данные
    print("\nПроверяем обновленные данные:")
    updated_product = inventory.get_product_by_name(update_name)
    if updated_product:
        print(f"Обновлено: {updated_product['name']}, количество: {updated_product['quantity']} шт")

if __name__ == "__main__":
    test_inventory_operations()
