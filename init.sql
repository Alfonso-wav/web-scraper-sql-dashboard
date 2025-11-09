-- Crear tabla de productos
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
    asin VARCHAR(20) UNIQUE,
    title TEXT,
    brand VARCHAR(255),
    price VARCHAR(50),
    price_numeric DECIMAL(10, 2),
    original_price VARCHAR(50),
    discount VARCHAR(50),
    rating VARCHAR(50),
    rating_numeric DECIMAL(3, 2),
    reviews_count VARCHAR(100),
    has_prime BOOLEAN DEFAULT FALSE,
    free_shipping BOOLEAN DEFAULT FALSE,
    availability VARCHAR(255),
    seller VARCHAR(255),
    url TEXT,
    image_url TEXT,
    search_term VARCHAR(255),
    position INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de especificaciones del producto
CREATE TABLE IF NOT EXISTS product_specifications (
    id SERIAL PRIMARY KEY,
    product_asin VARCHAR(20) REFERENCES products(asin) ON DELETE CASCADE,
    label VARCHAR(255),
    value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de información nutricional
CREATE TABLE IF NOT EXISTS nutrition_facts (
    id SERIAL PRIMARY KEY,
    product_asin VARCHAR(20) REFERENCES products(asin) ON DELETE CASCADE,
    nutrient VARCHAR(255),
    value VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear tabla de características del producto
CREATE TABLE IF NOT EXISTS product_features (
    id SERIAL PRIMARY KEY,
    product_asin VARCHAR(20) REFERENCES products(asin) ON DELETE CASCADE,
    feature TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Crear índices para mejorar el rendimiento
CREATE INDEX IF NOT EXISTS idx_products_asin ON products(asin);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products(brand);
CREATE INDEX IF NOT EXISTS idx_products_search_term ON products(search_term);
CREATE INDEX IF NOT EXISTS idx_products_rating ON products(rating_numeric);
CREATE INDEX IF NOT EXISTS idx_products_price ON products(price_numeric);
CREATE INDEX IF NOT EXISTS idx_product_specs_asin ON product_specifications(product_asin);
CREATE INDEX IF NOT EXISTS idx_nutrition_facts_asin ON nutrition_facts(product_asin);
CREATE INDEX IF NOT EXISTS idx_product_features_asin ON product_features(product_asin);

-- Crear función para actualizar timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Crear trigger para actualizar automáticamente updated_at
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
