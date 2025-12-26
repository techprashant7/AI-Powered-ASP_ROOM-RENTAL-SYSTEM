Write-Host "Starting PostgreSQL..."
Set-Location "C:\Program Files\PostgreSQL\18\bin"
& .\pg_ctl.exe -D "C:\PostgreSQL\data" -l logfile start
Write-Host "PostgreSQL started!"
