@echo off
echo === Orbit - Build APK ===

set /p APK_NAME="Nome do APK (sem .apk, Enter para 'orbit'): "
if "%APK_NAME%"=="" set APK_NAME=orbit
echo APK sera salvo como: %APK_NAME%.apk
echo.

set JAVA_HOME=C:\Program Files\Eclipse Adoptium\jdk-21.0.11.10-hotspot
set ANDROID_HOME=C:\Android
set PATH=%JAVA_HOME%\bin;%ANDROID_HOME%\platform-tools;%PATH%

if not exist "%JAVA_HOME%\bin\java.exe" (
    echo ERRO: JDK nao encontrado em %JAVA_HOME%. Ajuste JAVA_HOME neste arquivo.
    pause
    exit /b 1
)
if not exist "%ANDROID_HOME%\licenses" (
    echo ERRO: Android SDK nao encontrado em %ANDROID_HOME%. Ajuste ANDROID_HOME neste arquivo.
    pause
    exit /b 1
)

cd /d "%~dp0app"

if not exist node_modules (
    echo [0/2] Instalando dependencias do app...
    call npm install
    if errorlevel 1 (
        echo ERRO no npm install. Abortando.
        pause
        exit /b 1
    )
)

echo [1/2] Buildando assets web...
call npm run build:android
if errorlevel 1 (
    echo ERRO no build web. Abortando.
    pause
    exit /b 1
)

echo [2/2] Compilando APK (a 1a vez baixa o Gradle e as dependencias: pode demorar)...
cd android
call gradlew.bat assembleDebug
if errorlevel 1 (
    echo ERRO no Gradle. Abortando.
    pause
    exit /b 1
)
cd ..

set APK_SRC=android\app\build\outputs\apk\debug\app-debug.apk
set APK_DEST=android\app\build\outputs\apk\debug\%APK_NAME%.apk

if not "%APK_NAME%"=="app-debug" (
    if exist "%APK_DEST%" del "%APK_DEST%"
    rename "%APK_SRC%" "%APK_NAME%.apk"
)

echo.
echo === APK gerado com sucesso! ===
echo Localizacao: %CD%\android\app\build\outputs\apk\debug\%APK_NAME%.apk
echo Copie esse arquivo para o tablet e instale.
echo.
pause
