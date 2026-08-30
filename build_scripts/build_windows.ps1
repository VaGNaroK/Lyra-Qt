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

# 4.1 Baixar libmpv (100% compativel com Windows 10/11 sem exigir drivers de Vulkan)
Write-Host "[*] Baixando biblioteca libmpv..." -ForegroundColor Yellow
$mpvApiUrl = "https://api.github.com/repos/mpvnet-player/mpv.net/releases/latest"
$mpvZipUrl = "https://github.com/mpvnet-player/mpv.net/releases/download/v7.1.2.0/mpv.net-v7.1.2.0-portable-x64.zip"
try {
    $mpvRelease = Invoke-RestMethod -Uri $mpvApiUrl
    $mpvAsset = ($mpvRelease.assets | Where-Object { $_.name -match "portable-x64\.zip$" })[0]
    if ($mpvAsset) { $mpvZipUrl = $mpvAsset.browser_download_url }
} catch {
    Write-Host "[!] Usando URL de fallback para libmpv..." -ForegroundColor Gray
}

Invoke-WebRequest -Uri $mpvZipUrl -OutFile "mpv_portable.zip"
Expand-Archive -Path "mpv_portable.zip" -DestinationPath "mpv_temp" -Force
if (Test-Path "mpv_temp\libmpv-2.dll") {
    Copy-Item "mpv_temp\libmpv-2.dll" -Destination "assets\bin\mpv-2.dll" -Force
    Copy-Item "mpv_temp\libmpv-2.dll" -Destination "assets\bin\libmpv-2.dll" -Force
}
Remove-Item "mpv_portable.zip" -Force
Remove-Item "mpv_temp" -Recurse -Force

# 5. Empacotar com PyInstaller
Write-Host "[*] Iniciando PyInstaller..." -ForegroundColor Cyan
.\venv\Scripts\pyinstaller.exe --noconfirm --windowed --name "Lyra-Qt" --icon "assets\icons\lyra.ico" `
    --add-data "assets\sounds;assets\sounds" `
    --add-data "assets\icons;assets\icons" `
    --add-data "assets\models;assets\models" `
    --add-data "assets\translations;assets\translations" `
    --add-data "assets\bin\ffmpeg.exe;assets\bin" `
    --add-data "assets\bin\ffprobe.exe;assets\bin" `
    --add-data "assets\bin\yt-dlp.exe;assets\bin" `
    --add-binary "assets\bin\mpv-2.dll;assets\bin" `
    --add-binary "assets\bin\mpv-2.dll;." `
    --add-binary "assets\bin\libmpv-2.dll;assets\bin" `
    main.py

Write-Host "[*] Extraindo versao do main.py..." -ForegroundColor Cyan
$versionLine = Get-Content -Path "main.py" | Where-Object { $_ -match '^__version__\s*=\s*"([^"]+)"' } | Select-Object -First 1
$version = "unknown"
if ($versionLine -match '^__version__\s*=\s*"([^"]+)"') {
    $version = $matches[1]
}

$zipName = "Lyra-Qt-Windows-v$version.zip"
Write-Host "[*] Compactando pasta dist\Lyra-Qt para $zipName..." -ForegroundColor Yellow
if (Test-Path $zipName) { Remove-Item $zipName -Force }
Compress-Archive -Path "dist\Lyra-Qt" -DestinationPath $zipName -Force

Write-Host "[*] Compilacao concluida com sucesso!" -ForegroundColor Green
Write-Host "[*] O seu aplicativo pronto esta no arquivo '$zipName'." -ForegroundColor Green
if (-not $env:CI) { Pause }