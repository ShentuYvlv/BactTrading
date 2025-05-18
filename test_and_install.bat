@echo off
echo ==========================
echo 币安交易复盘工具 - 依赖安装和连接测试
echo ==========================

echo 安装所需依赖...
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo 依赖安装失败，请检查错误信息
    pause
    exit /b 1
)

echo.
echo 依赖安装完成，现在开始测试币安API连接...
echo.
python test_connection.py

echo.
if %errorlevel% equ 0 (
    echo 连接测试成功，现在可以尝试运行主应用程序了
    echo 输入 y 启动主应用程序，输入其他键退出
    set /p choice=是否立即启动主应用程序? (y/n):
    if /i "%choice%"=="y" (
        echo 启动主应用程序...
        start python app.py
    )
) else (
    echo 连接测试失败，请检查错误信息并修复问题后再试
    pause
) 