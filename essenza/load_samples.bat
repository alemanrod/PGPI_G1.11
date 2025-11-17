@echo off


echo --- Instalando dependencias (pip)...
pip install -r requirements.txt && (

    echo --- Borrando TODOS los datos de la BD...
    python manage.py flush --noinput && (

        echo.
        echo --- Aplicando migraciones...
        python manage.py migrate --noinput && (
            
            echo.
            echo --- Copiando imagenes de sampleo a 'media/'...
            XCOPY _sample_assets media /E /I /Y && (
            
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
)

@echo on