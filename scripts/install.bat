@echo off
chcp 65001 >nul
echo ==========================================
echo    企业知识库迁移系统 - 安装脚本
echo ==========================================
echo.

cd ..\backend

REM 创建虚拟环境
echo [信息] 创建虚拟环境...
python -m venv venv

REM 激活虚拟环境
call venv\Scripts\activate

REM 升级pip
echo [信息] 升级pip...
python -m pip install --upgrade pip

REM 安装依赖 - 使用预编译版本避免C编译器问题
echo [信息] 安装依赖...
pip install --only-binary :all: -r ..\requirements.txt

echo.
echo ==========================================
echo    安装完成！
echo    运行 start.bat 启动服务
echo ==========================================
pause
