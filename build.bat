@echo off
color 0B
echo ==========================================
echo   Building BlueFalcon MKV Batch Muxer
echo ==========================================
echo.

echo Cleaning old builds...
if exist "build" rmdir /s /q "build"

echo Compiling executable...
pyinstaller --clean BlueFalcon_MKV_Batch_Muxer.spec

echo.
echo ==========================================
echo   Build Complete!
echo   Executable is located in the \dist\ folder.
echo ==========================================
pause
