#!/bin/bash
PACKAGE_NAME="lyra-multimedia-converter"
BUILD_DIR="lyra-package"

# ==============================================================================
# 🔒 CAPTURA DA ÚNICA FONTE DA VERDADE (SSOT)
# ==============================================================================
VERSION=$(grep '^__version__' main.py | head -n 1 | cut -d'"' -f2)
if [ -z "$VERSION" ]; then
    echo "❌ Erro: Não foi possível detectar a versão em main.py."
    exit 1
fi

echo "🔨 Preparando estrutura do pacote para a versão v$VERSION..."

rm -rf $BUILD_DIR
mkdir -p $BUILD_DIR/usr/games/lyra-app
mkdir -p $BUILD_DIR/usr/share/applications
mkdir -p $BUILD_DIR/usr/share/icons/hicolor/scalable/apps
mkdir -p $BUILD_DIR/DEBIAN

echo "📦 Copiando arquivos..."
# 🔒 done.wav é o padrão desde a v1.1.5 (QSoundEffect substituiu ffplay)
cp main.py $BUILD_DIR/usr/games/lyra-app/
cp requirements.txt $BUILD_DIR/usr/games/lyra-app/
cp -r assets $BUILD_DIR/usr/games/lyra-app/

# 🔒 Verificação de segurança: Copia as pastas apenas se existirem (Suporte a Flat/Modular)
if [ -d "gui" ]; then
    cp -r gui $BUILD_DIR/usr/games/lyra-app/
fi
if [ -d "core" ]; then
    cp -r core $BUILD_DIR/usr/games/lyra-app/
fi

cp assets/icons/lyra.svg $BUILD_DIR/usr/share/icons/hicolor/scalable/apps/

echo "📝 Criando metadados..."
cat << EOF > $BUILD_DIR/DEBIAN/control
Package: $PACKAGE_NAME
Version: $VERSION
Architecture: amd64
Maintainer: VaGNaroK
Depends: python3, python3-venv, ffmpeg, yt-dlp, libxcb-cursor0, libxkbcommon-x11-0, libegl1, libgl1, libmpv-dev
Section: utils
Priority: optional
Description: Conversor multimidia acelerado por GPU (NVENC).
EOF

# ==============================================================================
# 🔒 SCRIPT PÓS-INSTALAÇÃO (Ambiente Virtual Seguro PySide6)
# ==============================================================================
cat << 'EOF' > $BUILD_DIR/DEBIAN/postinst
#!/bin/bash
set -e
echo "🔧 Configurando ambiente virtual do Lyra..."
cd /usr/games/lyra-app

python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

echo "✅ Lyra configurado com sucesso."
EOF
chmod +x $BUILD_DIR/DEBIAN/postinst

# Script de desinstalação limpa
cat << 'EOF' > $BUILD_DIR/DEBIAN/prerm
#!/bin/bash
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    echo "🧹 Removendo ambiente virtual e cache do Lyra..."
    rm -rf /usr/games/lyra-app/venv
    rm -rf /usr/games/lyra-app/__pycache__
fi
EOF
chmod +x $BUILD_DIR/DEBIAN/prerm

cat << EOF > $BUILD_DIR/usr/share/applications/lyra-multimedia-converter.desktop
[Desktop Entry]
Version=1.0
Type=Application
Name=Lyra Multimedia Converter
Exec=/usr/games/lyra-app/venv/bin/python3 /usr/games/lyra-app/main.py
Icon=lyra
Categories=AudioVideo;Utility;
Terminal=false
StartupWMClass=Lyra Multimedia Converter
EOF

echo "🚀 Construindo pacote..."
dpkg-deb --build $BUILD_DIR "${PACKAGE_NAME}_${VERSION}_amd64.deb"
echo "✅ Pronto! Instale com: sudo apt install ./${PACKAGE_NAME}_${VERSION}_amd64.deb"