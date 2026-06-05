# Garante que o script está rodando na raiz do projeto (um nível acima de build_scripts)
Set-Location -Path "$PSScriptRoot\.."

Write-Host "[*] Preparando ambiente para compilar Lyra-Qt no Windows..." -ForegroundColor Cyan

# 1. Criar Ambiente Virtual
Write-Host "[*] Criando ambiente virtual (venv)..." -ForegroundColor Yellow
python -m venv venv

# 2. Instalar dependencias usando diretamente os executaveis do venv
Write-Host "[*] Instalando dependencias (PySide6, yt-dlp, PyInstaller)..." -ForegroundColor Yellow
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\pip.exe install PySide6 yt-dlp pyinstaller

# 3. Baixar FFmpeg estatico do BtbN (versao Windows)
Write-Host "[*] Baixando binarios do FFmpeg..." -ForegroundColor Yellow
$ffmpegUrl = "https://github.com/BtbN/FFmpeg-Builds/releases/download/latest/ffmpeg-master-latest-win64-gpl.zip"
Invoke-WebRequest -Uri $ffmpegUrl -OutFile "ffmpeg.zip"
Expand-Archive -Path "ffmpeg.zip" -DestinationPath "ffmpeg_temp" -Force
New-Item -ItemType Directory -Force -Path "assets\bin"
Copy-Item "ffmpeg_temp\ffmpeg-master-latest-win64-gpl\bin\ffmpeg.exe" -Destination "assets\bin"
Copy-Item "ffmpeg_temp\ffmpeg-master-latest-win64-gpl\bin\ffprobe.exe" -Destination "assets\bin"
Remove-Item "ffmpeg.zip"
Remove-Item "ffmpeg_temp" -Recurse -Force

# 4. Baixar yt-dlp autônomo para o Windows
Write-Host "[*] Baixando executavel autonomo do yt-dlp..." -ForegroundColor Yellow
Invoke-WebRequest -Uri "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" -OutFile "assets\bin\yt-dlp.exe"

# 5. Empacotar com PyInstaller
Write-Host "[*] Iniciando PyInstaller..." -ForegroundColor Cyan
.\venv\Scripts\pyinstaller.exe --noconfirm --windowed --name "Lyra-Qt" --icon "assets\icons\lyra.ico" `
    --add-data "assets\sounds\done.wav;assets\sounds" `
    --add-data "assets\icons\lyra.svg;assets\icons" `
    --add-data "assets\bin\ffmpeg.exe;assets\bin" `
    --add-data "assets\bin\ffprobe.exe;assets\bin" `
    --add-data "assets\bin\yt-dlp.exe;assets\bin" `
    main.py

Write-Host "[*] Compilacao concluida com sucesso!" -ForegroundColor Green
Write-Host "[*] O seu aplicativo pronto esta dentro da pasta 'dist\Lyra-Qt'." -ForegroundColor Green
Pause