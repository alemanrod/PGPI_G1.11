@echo off
REM ---------------------------------------------------------
REM IMPORTANTE: Este archivo borra todos los datos de tu BD local (y la crea con los datos de sampleo).
REM
REM             También instala las dependencias necesarias definidas en 'requirements.txt' (si aun no lo están).
REM ---------------------------------------------------------

echo --- Instalando dependencias (pip)...
pip install -r requirements.txt && (

    echo --- Borrando TODOS los datos de la BD...
    python manage.py flush --noinput && (

        echo.
        echo --- Aplicando migraciones...
        python manage.py migrate --noinput && (
            
            echo.
            echo --- Cargando datos de USER...
            python manage.py loaddata user/sample/sample.json && (
                
                echo.
                echo --- Cargando datos de PRODUCT...
                python manage.py loaddata product/sample/sample.json && (
                    
                    echo.
                    echo --- Cargando datos de ORDER...
                    python manage.py loaddata order/sample/sample.json && (
                        
                        echo.
                        echo --- !Proceso completado! La base de datos esta lista. ---
                    )
                )
            )
        )
    )
)

@echo on