@echo off
echo Starting PostgreSQL...
cd "C:\Program Files\PostgreSQL\18\bin"
pg_ctl -D "C:\PostgreSQL\data" -l logfile start
pause
