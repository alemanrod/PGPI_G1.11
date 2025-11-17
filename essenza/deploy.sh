pip install -r requirements.txt && \
mkdir -p media && \
rsync -av --ignore-errors _sample_assets/ media/ && \
python manage.py makemigrations && \
python manage.py flush --noinput && \
python manage.py migrate --noinput && \
python manage.py collectstatic --noinput && \
python manage.py loaddata user/sample/sample.json && \
python manage.py loaddata product/sample/sample.json && \
python manage.py loaddata order/sample/sample.json