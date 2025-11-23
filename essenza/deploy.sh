# ---------------------------------------------------------
# IMPORTANTE: Este archivo RESTAURA TOTALMENTE la BD del proyecto.
# ---------------------------------------------------------

set -e

echo ""
echo "--- Instalando dependencias (pip)..."
pip install -r requirements.txt

echo ""
echo "--- Recolectando estáticos (CSS/JS)..."
python3 manage.py collectstatic --no-input

echo ""
echo "--- Vaciando DB..."
python3 manage.py flush --no-input

echo ""
echo "--- Aplicando Migraciones (Migrate)..."
python3 manage.py migrate --no-input

echo ""
echo "--- Copiando imagenes de sampleo a 'media/'..."
mkdir -p media
cp -r _sample_assets/* media/ 2>/dev/null || echo "Aviso: No se encontraron assets en _sample_assets/"

echo ""
echo "--- Cargando datos de USER..."
python3 manage.py loaddata user/sample/sample.json

echo ""
echo "--- Cargando datos de PRODUCT..."
python3 manage.py loaddata product/sample/sample.json

echo ""
echo "--- Cargando datos de ORDER..."
python3 manage.py loaddata order/sample/sample.json

echo ""
echo "========================================================"
echo "!PROCESO COMPLETADO CON EXITO!"
echo "========================================================"
