-- Обновляем таблицу products
ALTER TABLE public.products
DROP COLUMN IF EXISTS last_synced_at;

-- Удаляем старую таблицу если она существует
DROP TABLE IF EXISTS public.products CASCADE;

-- Создаем таблицу products
CREATE TABLE public.products (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    price DECIMAL(10, 2) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Создаем уникальный индекс для быстрого поиска по имени
CREATE UNIQUE INDEX idx_products_name ON public.products(name);

-- Создаем триггер для автоматического обновления updated_at
CREATE OR REPLACE FUNCTION public.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_products_updated_at ON public.products;
CREATE TRIGGER update_products_updated_at
    BEFORE UPDATE ON public.products
    FOR EACH ROW
    EXECUTE FUNCTION public.update_updated_at_column();

-- Даем права на таблицу и последовательность
GRANT ALL ON public.products TO postgres, anon, authenticated, service_role;
GRANT ALL ON public.products_id_seq TO postgres, anon, authenticated, service_role;

-- Создаем функцию для очистки всех продуктов
CREATE OR REPLACE FUNCTION public.clear_products()
RETURNS void AS $$
BEGIN
    DELETE FROM public.products;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Создаем функцию для добавления продукта
CREATE OR REPLACE FUNCTION public.add_product(
    p_name TEXT,
    p_price DECIMAL,
    p_quantity INTEGER,
    p_description TEXT DEFAULT NULL
) RETURNS public.products AS $$
DECLARE
    v_product public.products;
BEGIN
    INSERT INTO public.products (name, price, quantity, description)
    VALUES (p_name, p_price, p_quantity, p_description)
    RETURNING * INTO v_product;
    
    RETURN v_product;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Создаем функцию для обновления продукта
CREATE OR REPLACE FUNCTION public.update_product(
    p_id INTEGER,
    p_name TEXT,
    p_price DECIMAL,
    p_quantity INTEGER,
    p_description TEXT DEFAULT NULL
) RETURNS public.products AS $$
DECLARE
    v_product public.products;
BEGIN
    UPDATE public.products
    SET name = p_name,
        price = p_price,
        quantity = p_quantity,
        description = p_description
    WHERE id = p_id
    RETURNING * INTO v_product;
    
    RETURN v_product;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Создаем функцию для получения продукта по имени
CREATE OR REPLACE FUNCTION public.get_product_by_name(p_name TEXT)
RETURNS public.products AS $$
DECLARE
    v_product public.products;
BEGIN
    SELECT * INTO v_product
    FROM public.products
    WHERE name = p_name;
    
    RETURN v_product;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
