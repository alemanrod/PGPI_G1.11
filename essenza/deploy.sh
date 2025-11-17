pip install -r requirements.txt && \
python manage.py flush --noinput && \
python manage.py migrate --noinput && \
python manage.py collectstatic --noinput && \
python manage.py loaddata user/sample/sample.json && \
python manage.py loaddata product/sample/sample.json && \
python manage.py loaddata order/sample/sample.json