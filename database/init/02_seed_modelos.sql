-- ============================================================
--  TallerDB — Init automático: datos iniciales del catálogo
--  Archivo: database/init/02_seed_modelos.sql
--  Se ejecuta automáticamente por la imagen oficial de MariaDB
--  después de 01_schema.sql (orden alfabético). La base de datos
--  ya está seleccionada por el entrypoint.
-- ============================================================

INSERT IGNORE INTO modelos
    (marca, nombre, anio, precio, color, tipo, transmision, disponible, descripcion)
VALUES
    ('Toyota',   'Corolla',     2024, 28900.00,  'Blanco',   'sedan',      'automatica', 1, 'Sedán compacto, excelente consumo y confiabilidad.'),
    ('Toyota',   'Corolla',     2025, 29900.00,  'Plata',    'sedan',      'cvt',        1, 'Nueva versión con seguridad Toyota Safety Sense.'),
    ('Toyota',   'Hilux',       2024, 52500.00,  'Gris',     'pickup',     'manual',     1, 'Camioneta doble cabina, motor 2.8 turbo.'),
    ('Honda',    'Civic',       2024, 31500.00,  'Negro',    'sedan',      'cvt',        1, 'Sedán deportivo con suspensión multilink.'),
    ('Honda',    'HR-V',        2025, 35900.00,  'Rojo',     'suv',        'cvt',        1, 'SUV compacto para ciudad.'),
    ('Nissan',   'Versa',       2024, 21500.00,  'Blanco',   'sedan',      'manual',     1, 'Sedán económico de bajo mantenimiento.'),
    ('Chevrolet','Aveo',        2024, 19800.00,  'Azul',     'sedan',      'manual',     1, 'Compacto urbano, ideal primer auto.'),
    ('Ford',     'Mustang',     2024, 98000.00,  'Amarillo', 'deportivo',  'manual',     1, 'Deportivo icónico, motor V8 5.0.'),
    ('Volkswagen','Jetta',      2025, 38200.00,  'Plata',    'sedan',      'automatica', 1, 'Sedán europeo con acabados premium.'),
    ('Volkswagen','T-Cross',    2024, 33400.00, 'Gris',     'suv',        'automatica', 1, 'SUV urbano de la familia VW.'),
    ('Kia',      'Rio',         2024, 22900.00, 'Blanco',   'hatchback',  'manual',     1, 'Hatchback ágil con buena equipación.'),
    ('Kia',      'Sportage',    2025, 47800.00, 'Azul',     'suv',        'automatica', 1, 'SUV familiar con pantalla curva.'),
    ('Hyundai',  'Tucson',      2024, 45200.00, 'Verde',    'suv',        'automatica', 1, 'SUV con motor turbo híbrido disponible.'),
    ('Mazda',    'Mazda 3',     2025, 34700.00, 'Rojo',     'hatchback',  'automatica', 1, 'Diseño Kodo, interior de alta calidad.'),
    ('Renault',  'Duster',      2024, 29300.00, 'Naranja',  'suv',        'manual',     1, 'SUV robusto para todo terreno.'),
    ('Seat',     'Ibiza',       2024, 24600.00, 'Gris',     'hatchback',  'manual',     0, 'No disponible temporalmente.'),
    ('BMW',      'Serie 3',     2025, 89500.00, 'Negro',    'sedan',      'automatica', 1, 'Berlina deportiva premium.'),
    ('Tesla',    'Model 3',     2025, 74900.00, 'Blanco',   'sedan',      'automatica', 1, 'Eléctrico, autonomía 500 km.');
