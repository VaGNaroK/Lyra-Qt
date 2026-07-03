# Garante que o script está rodando na raiz do projeto (um nível acima de build_scripts)
Set-Location -Path "$PSScriptRoot\.."

Write-Host "[*] Preparando ambiente para compilar Lyra-Qt no Windows..." -ForegroundColor Cyan

# 0. Verificar se o Python esta instalado
Write-Host "[*] Verificando se o Python esta instalado..." -ForegroundColor Yellow
if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[!] ERRO: Python nao foi encontrado no sistema!" -ForegroundColor Red
    Write-Host "Por favor, baixe e instale a versao mais recente do Python para Windows em: https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "IMPORTANTE: Durante a instalacao, certifique-se de marcar a opcao 'Add Python to PATH'." -ForegroundColor Yellow
    if (-not $env:CI) { Pause }
    Exit
}
Write-Host "[*] Python encontrado!" -ForegroundColor Green

# 1. Criar Ambiente Virtual
Write-Host "[*] Criando ambiente virtual (venv)..." -ForegroundColor Yellow
python -m venv venv

# 2. Instalar dependencias usando diretamente os executaveis do venv
Write-Host "[*] Instalando dependencias (PySide6, yt-dlp, PyInstaller)..." -ForegroundColor Yellow
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\pip.exe install -r requirements.txt pyinstaller

# 3. Baixar FFmpeg estatico (Gyan.dev - release essentials)
Write-Host "[*] Baixando binarios do FFmpeg (Gyan.dev)..." -ForegroundColor Yellow
$ffmpegUrl = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
Invoke-WebRequest -Uri $ffmpegUrl -OutFile "ffmpeg.zip"
Expand-Archive -Path "ffmpeg.zip" -DestinationPath "ffmpeg_temp" -Force
New-Item -ItemType Directory -Force -Path "assets\bin"
$ffmpegDir = Get-ChildItem "ffmpeg_temp" | Where-Object { $_.PSIsContainer } | Select-Object -First 1
Copy-Item "$($ffmpegDir.FullName)\bin\ffmpeg.exe" -Destination "assets\bin"
Copy-Item "$($ffmpegDir.FullName)\bin\ffprobe.exe" -Destination "assets\bin"
Remove-Item "ffmpeg.zip"
Remove-Item "ffmpeg_temp" -Recurse -Force

# 4. Baixar yt-dlp autônomo para o Windows
Write-Host "[*] Baixando executavel autonomo do yt-dlp..." -ForegroundColor Yellow
Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -OutFile "assets\bin\yt-dlp.exe"

# 4.1 Baixar libmpv (Shinchiro) para o Windows
Write-Host "[*] Baixando 7zr.exe e biblioteca libmpv..." -ForegroundColor Yellow
Invoke-WebRequest -Uri "https://www.7-zip.org/a/7zr.exe" -OutFile "7zr.exe"
$apiUrl = "https://api.github.com/repos/shinchiro/mpv-winbuild-cmake/releases/latest"
$releaseData = Invoke-RestMethod -Uri $apiUrl
$mpvUrl = ($releaseData.assets | Where-Object { $_.name -match "mpv-dev-x86_64-v3-.*\.7z" })[0].browser_download_url
Invoke-WebRequest -Uri $mpvUrl -OutFile "mpv_dev.7z"
.\7zr.exe e "mpv_dev.7z" -o"assets\bin" "libmpv-2.dll" -r -y
if (Test-Path "assets\bin\libmpv-2.dll") {
    Rename-Item -Path "assets\bin\libmpv-2.dll" -NewName "mpv-2.dll"
}
Remove-Item "mpv_dev.7z"
Remove-Item "7zr.exe"

# 5. Empacotar com PyInstaller
Write-Host "[*] Iniciando PyInstaller..." -ForegroundColor Cyan
.\venv\Scripts\pyinstaller.exe --noconfirm --windowed --name "Lyra-Qt" --icon "assets\icons\lyra.ico" `
    --add-data "assets\sounds\done.wav;assets\sounds" `
    --add-data "assets\icons\lyra.svg;assets\icons" `
    --add-data "assets\bin\ffmpeg.exe;assets\bin" `
    --add-data "assets\bin\ffprobe.exe;assets\bin" `
    --add-data "assets\bin\yt-dlp.exe;assets\bin" `
    --add-binary "assets\bin\mpv-2.dll;assets\bin" `
    main.py

Write-Host "[*] Compilacao concluida com sucesso!" -ForegroundColor Green
Write-Host "[*] O seu aplicativo pronto esta dentro da pasta 'dist\Lyra-Qt'." -ForegroundColor Green
if (-not $env:CI) { Pause }