-- Catalogo de zonas de taxi de la TLC (LocationID -> distrito y zona).
--
-- scripts/create_database.py ejecuta esta sentencia despues de crear `trips`
-- cuando existe data/raw/zones/taxi_zone_lookup.csv (lo descarga
-- scripts/download_data.py). El marcador $zones_file se sustituye por la ruta
-- del CSV.
--
-- Permite mostrar nombres de zona en lugar de identificadores numericos:
--   trips.pu_location_id / trips.do_location_id = zones.location_id
-- Los ids 264 y 265 corresponden a zonas desconocidas o fuera de Nueva York.

CREATE TABLE zones AS
SELECT
    LocationID::INTEGER AS location_id,
    Borough AS borough,
    Zone AS zone,
    service_zone
FROM read_csv($zones_file, header = true);
