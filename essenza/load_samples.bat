@echo off


IF "%VIRTUAL_ENV%"=="" (
    echo.
    echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    echo ERROR: No se detecta un entorno virtual activo. 
    echo Por favor, activa tu '.venv' antes de ejecutar este script. 
    echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
    pause
    exit /b 1
)

echo.
echo --- Instalando dependencias (pip)...
pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 GOTO :ERROR

echo.
echo --- Borrando TODOS los datos de la BD...
python manage.py flush --noinput
IF %ERRORLEVEL% NEQ 0 GOTO :ERROR

echo.
echo --- Aplicando migraciones...
python manage.py migrate --noinput
IF %ERRORLEVEL% NEQ 0 GOTO :ERROR

echo.
echo --- Copiando imagenes de sampleo a 'media/'...
XCOPY _sample_assets media /E /I /Y
IF %ERRORLEVEL% NEQ 0 GOTO :ERROR

echo.
echo --- Cargando datos de USER...
python manage.py loaddata user/sample/sample.json
IF %ERRORLEVEL% NEQ 0 GOTO :ERROR

echo.
echo --- Cargando datos de PRODUCT...
python manage.py loaddata product/sample/sample.json
IF %ERRORLEVEL% NEQ 0 GOTO :ERROR

echo.
echo --- Cargando datos de ORDER...
python manage.py loaddata order/sample/sample.json
IF %ERRORLEVEL% NEQ 0 GOTO :ERROR

echo.
echo ========================================================
echo !PROCESO COMPLETADO CON EXITO! 
echo Los datos de sampleo se han cargado en la base de datos. 
echo ========================================================
GOTO :END

:ERROR
echo.
echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
echo ERROR -> El script se detuvo porque un comando ha fallado. 
echo !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
pause
exit /b 1

:END

@echo on