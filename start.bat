@echo off
chcp 65001 >nul
echo ======================================
echo   Airplane Shooter - 打飞机游戏
echo ======================================
echo.
python airplane_shooter.py
if errorlevel 1 (
    echo.
    echo 错误：请确保已安装 Python 和 pygame
    echo 运行以下命令安装依赖:
    echo   pip install pygame numpy
    pause
)
