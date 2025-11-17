@echo off
REM ---------------------------------------------------------
REM IMPORTANTE: Este archivo borra todos los datos de tu BD local (y la crea con los datos de sampleo).
REM             Las imágenes de sampleo se copian a la carpeta 'media/'.
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
            echo --- Copiando imagenes de sampleo a 'media/'...
            REM XCOPY [origen] [destino] /E /I /Y
            REM /E = Copia subdirectorios (incluso vacíos)
            REM /I = Si el destino no existe, asume que es un directorio
            REM /Y = Suprime la pregunta de "sobreescribir archivo"
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