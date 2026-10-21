@echo off
chcp 65001 >nul
title Meikova Harvest - Build Tool GUI
echo Đang khởi chạy Build Tool GUI...
.\venv\Scripts\python.exe build_tool\builder_cli.py --gui
pause
