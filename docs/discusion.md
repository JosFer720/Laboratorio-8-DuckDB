# Discusión

Estas respuestas salen del trabajo hecho con 121.2 millones de viajes de taxi
yellow y green de 2024, 2025 y de enero a agosto de 2026, que en total ocupan
1.9 GB en archivos Parquet. Los números que se mencionan vienen de
[`benchmark.md`](benchmark.md), [`data_quality.md`](data_quality.md),
[`incorporacion_2025.md`](incorporacion_2025.md) y
[`analisis_tres_anios.md`](analisis_tres_anios.md).

## 9.1 ¿Qué características de DuckDB resultaron más útiles durante el laboratorio?

Lo más útil fue poder consultar los archivos Parquet con SQL sin tener que
cargarlos antes en una base de datos. Con `read_parquet` y un comodín como
`data/raw/yellow/*/*.parquet`, DuckDB trata los 32 archivos de yellow como si
fueran una sola tabla. Contar y promediar los 119.6 millones de viajes yellow
tardó 0.3 segundos.

También ayudó mucho la opción `union_by_name`. Los archivos no tienen siempre las
mismas columnas, porque `cbd_congestion_fee` aparece en 2025 y `request_source` a
mediados de 2026. Con esa opción DuckDB junta las columnas por su nombre y deja
vacías las que faltan en un archivo, sin dar error y sin que tuviéramos que
escribir código especial para cada año. Otras funciones como `glob()`,
`parquet_schema()` y la opción `filename = true` sirvieron para revisar que la
descarga estuviera completa, saber en qué mes apareció cada columna y sacar el año
y el mes del nombre de cada archivo.

DuckDB además trae muchas funciones de análisis listas para usar en SQL, como
contar con condiciones (`count_if`), calcular medianas y percentiles, o comparar un
año con el anterior (`lag`). Gracias a eso todo el análisis, incluidos los 15
indicadores del tablero, quedó escrito en archivos SQL que se pueden guardar en
Git y volver a correr.

Por último, DuckDB funciona como una librería dentro de Python y guarda la base en
un solo archivo. El mismo `taxi.duckdb` lo usan los scripts, los notebooks y
Metabase, sin necesidad de instalar ni mantener un servidor de base de datos. Y es
rápido, porque usa varios núcleos del procesador a la vez. Crear la tabla con 121
millones de filas tardó 7.8 segundos y la mayoría de las consultas respondió en
menos de medio segundo.

## 9.2 ¿Qué ventajas y limitaciones encontró al consultar directamente archivos Parquet?

La mayor ventaja es que no hay que cargar nada antes de empezar. Un mes recién
descargado se puede consultar al instante. Parquet guarda los datos por columnas,
entonces DuckDB solo lee las columnas que la consulta necesita. Cada archivo
también guarda algunos datos sobre su contenido, como cuántas filas tiene, y eso
hizo que contar los 121 millones de viajes tardara apenas 16 milésimas de segundo.
Los archivos originales siguen siendo la única copia de los datos, y ocupan menos
espacio, 1.9 GB contra 3.4 GB de la tabla de DuckDB. Además, consultar los Parquet
permite usar columnas que no se pasaron a la tabla, como el peaje de congestión,
que solo existe desde 2025.

La limitación principal es la velocidad cuando se repiten consultas. Cada vez que
se pregunta algo, DuckDB tiene que abrir otra vez los 64 archivos y descomprimirlos.
Con los tres años, las consultas que agrupan y resumen datos fueron entre 2.3 y 4
veces más lentas que sobre la tabla. Por ejemplo, contar los viajes por hora tardó
0.44 segundos con Parquet y 0.12 con la tabla. Las consultas que buscan pocos
viajes muy específicos fueron entre 7 y 12 veces más lentas, porque los archivos no
tienen tanta información para saltarse las partes que no sirven.

Otra limitación es que los cambios de limpieza se repiten en cada consulta. Hay que
renombrar las columnas de fecha, que se llaman distinto en yellow y green, fijar los
tipos de datos y calcular la duración cada vez, o guardar todo eso en una vista.
También hay que tener cuidado porque las columnas y los tipos de datos cambian entre
archivos de distintos meses.

## 9.3 ¿Qué ventajas y limitaciones observó al utilizar tablas materializadas en DuckDB?

Una tabla materializada es una copia de los datos guardada dentro de la base de
DuckDB, ya limpia y con las columnas calculadas. Su ventaja más clara es la
velocidad cuando se hacen muchas consultas. En nuestras pruebas fue hasta 12 veces
más rápida en las búsquedas muy específicas y cerca de 2.3 veces más rápida en el
conjunto de consultas que agrupan datos. Esto importa mucho en un tablero, porque
cada vez que se abre ejecuta sus 15 consultas. La tabla también deja un esquema
único y ordenado, con `trips` y `zones` y con columnas como el año, el mes y la
duración ya calculadas, entonces las consultas del análisis quedan más cortas y
fáciles de leer. Y como es un solo archivo, otras herramientas como Metabase lo
pueden abrir en modo de solo lectura.

Las limitaciones también se notaron. La tabla hay que volver a crearla cada vez que
llegan datos nuevos, y hasta que eso pasa no incluye el mes más reciente. En esta
computadora tardó 7.8 segundos, pero en la computadora donde se hizo la primera
medición tardaba 105 segundos con menos datos. Ocupa 1.8 veces más espacio que los
Parquet. Además, un archivo de DuckDB solo puede tener un programa escribiendo a la
vez, entonces Metabase tiene que abrirlo en solo lectura y la tabla se construye en
un archivo temporal que después reemplaza al anterior.

La tabla también obliga a decidir qué columnas tiene. Una columna que solo existe en
algunos años, como `cbd_congestion_fee`, no se puede incluir sin que falle la
construcción de una tabla solo con 2024, como la que usa el benchmark. Por último,
la ventaja depende de la consulta. La consulta de viajes por mes fue más rápida
sobre Parquet y la de percentiles tardó lo mismo en las dos formas.

## 9.4 ¿Qué ventajas ofrece este flujo de trabajo frente a cargar todos los datos utilizando una herramienta como Pandas?

La diferencia más importante es la memoria. Pandas carga todos los datos en la
memoria de la computadora antes de poder trabajar con ellos. Un solo mes de viajes
yellow, con 4.6 millones de filas, ocupa 652 MB en Pandas. Si se cargaran los 119.6
millones de viajes yellow, se necesitarían unos 16.6 GB, más del doble de la memoria
que tiene el contenedor de Docker (7.7 GB). DuckDB, en cambio, va leyendo los datos
por partes y solo las columnas que necesita, entonces puede trabajar con más datos
de los que caben en la memoria.

También hay una diferencia de velocidad. Pandas tardó 0.23 segundos solo en cargar
un mes, mientras que DuckDB respondió un conteo y un promedio sobre los 32 meses en
0.32 segundos.

Otra ventaja es que las consultas quedan escritas en archivos SQL aparte, que se
usan igual desde los scripts, los notebooks, Metabase y las pruebas. Con Pandas la
lógica suele quedar mezclada con el código del notebook y cuesta más reutilizarla.
Pandas igual sigue siendo útil al final del proceso. DuckDB entrega los resultados
ya resumidos, que son tablas pequeñas, y esas tablas se pasan a Pandas para hacer
las gráficas con matplotlib.

## 9.5 ¿Qué características del sistema desarrollado permiten incorporar nuevos datos con cambios mínimos?

La primera es el orden de las carpetas. Los archivos se guardan en
`data/raw/<tipo>/<año>/` con el mismo nombre que les pone la TLC, y las consultas
buscan los archivos con comodines en lugar de tener una lista escrita a mano. Así,
cualquier archivo nuevo que caiga en esas carpetas entra solo en las consultas.

La segunda es que hay un solo lugar donde se dice qué años se descargan. Agregar
2025 fue tan simple como sumarlo a la lista `ANIOS_PERMITIDOS`. La descarga además
pregunta al servidor qué meses existen y se salta los archivos que ya tiene, así que
se puede correr cuantas veces se quiera. La tercera vez que la corrimos no bajó
nada y reportó 65 archivos que ya existían.

La tercera es que el año y el mes de cada viaje se sacan del nombre del archivo, y
que las comparaciones entre años usan los meses comunes calculados a partir de los
datos, sin un mes escrito a mano. Además, los scripts que crean la base y el
benchmark buscan solos qué años hay descargados. Por eso el benchmark agregó la
prueba con los tres años sin que cambiáramos su código. Por último, cada indicador
está definido una sola vez en `sql/indicators/`, y ese mismo archivo lo usan el
cálculo de resultados, la imagen del tablero, Metabase y el notebook.

## 9.6 ¿Qué parte del proceso considera que debería automatizarse en un sistema de producción?

En un sistema real, la descarga debería correr sola cada cierto tiempo, por ejemplo
una vez al mes, y avisar si un mes que ya debería estar publicado no aparece o si
una descarga falla. Después de cada descarga deberían correr revisiones automáticas de los datos. Por ejemplo, contar las filas de cada mes, revisar con `parquet_schema` que las columnas sean las esperadas y vigilar el porcentaje de viajes inválidos de cada empresa. Con esas revisiones, problemas como las duraciones cero del `vendor_id` 7 o las tarifas negativas del `vendor_id` 2 en 2025 se habrían detectado el mismo mes en que aparecieron.

También debería automatizarse lo que viene después, que es volver a crear la
tabla, o agregarle solo los meses nuevos, y luego actualizar los indicadores y el
tablero con `setup_dashboard.py`. Y por último, cada cambio en el código debería correr las
pruebas y el benchmark de forma automática, con un límite de memoria, para darse
cuenta a tiempo de consultas que dejan de funcionar cuando crecen los datos, como
pasó con la de percentiles.

## 9.7 ¿Qué decisiones de diseño fueron importantes para mantener el proyecto reproducible?

Reproducible quiere decir que alguien más pueda repetir todo el trabajo y llegar a
los mismos resultados. La primera decisión importante fue usar Docker con versiones
fijas de todo. La imagen base de Python está fijada, las librerías de Python tienen
su versión exacta, y Metabase y su conector de DuckDB se descargan con una versión y una verificación fijas. Así todos usamos exactamente el mismo software.

La segunda fue no guardar los datos en Git, pero sí guardar el script que los
descarga desde la fuente original. Cualquiera puede volver a bajarlos con un
comando. La tercera fue escribir todas las transformaciones en archivos SQL
guardados en el repositorio, como `create_tables.sql` y `create_zones.sql`, y no
borrar ninguna fila. Los datos malos se dejan en la tabla y cada análisis decide
cuáles usar con la regla de viaje válido, que está escrita y explicada.

También fue importante que la descarga y la creación de la base escriban primero en
un archivo temporal y solo al final lo pongan en su lugar, para no dejar archivos a
medias si algo falla. El proyecto tiene 36 pruebas automáticas para la descarga, la
base y los indicadores, y una de ellas corre cada indicador sobre una base pequeña
con la misma estructura que la real. Por último, los resultados quedaron guardados
con la fecha en que se obtuvieron y con los comandos para volver a generarlos, en
los documentos de `docs/`, en `benchmark_results.csv` y en
`docs/dashboard/resultados/`.

## 9.8 ¿Qué aprendió sobre el manejo de datos que no habría sido evidente trabajando únicamente con conjuntos de datos pequeños?

Lo primero que aprendimos es que una consulta que funciona bien puede dejar de
funcionar solo porque crecen los datos. La consulta de percentiles con seis
llamadas separadas funcionaba con 72 millones de filas y se quedó sin memoria con
121 millones. Hubo que reescribirla para que guardara una sola copia de los valores. Con un conjunto pequeño nunca nos habríamos dado cuenta.

También vimos que los datos reales cambian con el tiempo. Aparecen columnas nuevas,
empresas nuevas y formas distintas de anotar las cosas, como las duraciones cero del `vendor_id` 7 o las tarifas negativas que el `vendor_id` 2 anotó solo en 2025. Con una muestra pequeña o con un solo año esos problemas no se ven, o se le atribuyen al año equivocado, como nos pasó al principio con 2026.

Aprendimos que las conclusiones dependen mucho de qué periodo se mira. Con 2024 y
2026 parecía que yellow crecía sin parar, y al agregar 2025 se vio que hubo un
máximo y después una caída. Con tantos datos también aparecen valores extremos de
verdad, como viajes de 398 mil millas o tarifas de 863 mil dólares, que mueven
mucho los promedios. Por eso hacen falta la mediana y una regla clara de qué viajes
son válidos.

Por último, vimos que en algunas consultas cuesta más hacer el cálculo que leer los
datos, como en los percentiles, y que la computadora importa mucho. La misma
consulta fue entre 3 y 25 veces más rápida en otra máquina, una diferencia más
grande que la que hay entre usar Parquet o la tabla en una misma máquina. También
aprendimos que para comparar años hay que comparar los mismos meses, y que conviene
calcular esos meses a partir de los datos para que la comparación siga siendo justa
cuando lleguen meses nuevos.
