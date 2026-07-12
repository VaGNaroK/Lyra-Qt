#!/bin/bash
# ==============================================================================
# Script de Automação de Compilação e Instalação - Lyra-Qt
# Este script automatiza a extração da versão, resolução de dependências,
# geração e instalação do pacote final (.deb ou .flatpak).
# ==============================================================================

# Sai imediatamente se algum comando falhar
set -e

# Garante que estamos na raiz do projeto (mesmo se executado de outro diretório)
cd "$(dirname "$0")/.."

# ==============================================================================
# 1. ANÁLISE DA VERSÃO DO APP
# ==============================================================================
echo "🔍 Analisando a versão do Lyra-Qt..."
# Extrai a versão diretamente do main.py (Single Source of Truth)
VERSION=$(grep '^__version__' main.py | head -n 1 | cut -d'"' -f2)

if [ -z "$VERSION" ]; then
    echo "❌ Erro: Não foi possível detectar a versão em main.py."
    exit 1
fi
echo "✅ Versão detectada: v$VERSION"
echo "------------------------------------------------------------"

# ==============================================================================
# 2. MENU INTERATIVO PARA ESCOLHA DO FORMATO
# ==============================================================================
echo "Escolha o formato de pacote que deseja gerar e instalar:"
echo "1) 📦 Pacote Universal (Flatpak Standalone)"
echo "2) 📦 Pacote Debian (.deb) para Ubuntu/Mint/Debian"
echo "3) 📦 Ambos (Flatpak e Debian)"
echo "4) 🧹 Apenas Limpar Caches de Compilação"
echo "5) ❌ Sair"
read -p "Digite a opção (1 a 5): " OPTION
echo "------------------------------------------------------------"

if [[ ! "$OPTION" =~ ^[1-5]$ ]]; then
    echo "❌ Opção inválida. Saindo do script."
    exit 1
fi

if [ "$OPTION" == "5" ]; then
    echo "Saindo sem realizar nenhuma ação."
    exit 0
fi

if [ "$OPTION" == "1" ] || [ "$OPTION" == "3" ]; then
    # ==============================================================================
    # 3. COMPILAÇÃO E INSTALAÇÃO: FLATPAK
    # ==============================================================================
    echo "⚙️  Preparando ambiente para compilação via Flatpak..."
    
    # 3.1. Resolve dependências citadas no README (flatpak-builder e KDE Sdk)
    if ! command -v flatpak-builder &> /dev/null; then
        echo "🔧 Instalando dependência principal: flatpak-builder (requer sudo)..."
        sudo apt update
        sudo apt install flatpak-builder -y
    fi

    echo "🔧 Verificando e instalando dependências do Flathub (KDE Sdk 6.8)..."
    # Adiciona o repositório Flathub se não existir
    flatpak remote-add --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
    # Instala o SDK necessário para compilar o app (dependência listada no README)
    flatpak install flathub org.kde.Sdk/x86_64/6.8 -y

    # 3.2. Gerar Repositório Local
    echo "🔨 Compilando o projeto em um repositório local (flatpak-builder)..."
    # Utiliza o manifesto YAML existente dentro de build_scripts
    flatpak-builder --repo=lyra-repo --force-clean diretorio-build build_scripts/com.github.vagnarok.lyra.yml

    # 3.3. Gerar Pacote Final com a versão no nome
    PACKAGE_NAME="Lyra-Qt_v${VERSION}.flatpak"
    echo "📦 Gerando o arquivo de pacote bundle ($PACKAGE_NAME)..."
    flatpak build-bundle lyra-repo "$PACKAGE_NAME" com.github.vagnarok.lyra stable

    # 3.4. Instalação no Sistema
    echo "Deseja instalar o pacote Flatpak gerado agora? (s/N)"
    read -p "Opção: " INSTALL_OPT
    if [[ "$INSTALL_OPT" == "s" || "$INSTALL_OPT" == "S" ]]; then
        echo "🚀 Instalando o pacote final gerado no sistema (nível de usuário)..."
        # Atualiza o bundle caso ele já esteja instalado (ou instala)
        flatpak install --user "$PACKAGE_NAME" -y || flatpak update --user "$PACKAGE_NAME" -y
        echo "------------------------------------------------------------"
        echo "🎉 SUCESSO! O pacote Flatpak v$VERSION foi compilado e instalado."
        echo "Você já pode executar o Lyra-Qt pesquisando no menu do sistema."
    else
        echo "------------------------------------------------------------"
        echo "✅ Compilação finalizada! O pacote $PACKAGE_NAME está disponível na raiz do projeto."
    fi

    echo "------------------------------------------------------------"
    echo "Deseja limpar os diretórios de cache da compilação Flatpak? (s/N)"
    read -p "Opção: " CLEAN_OPT
    if [[ "$CLEAN_OPT" == "s" || "$CLEAN_OPT" == "S" ]]; then
        echo "🧹 Limpando cache (.flatpak-builder, diretorio-build, lyra-repo, lyra-package)..."
        rm -rf .flatpak-builder diretorio-build lyra-repo lyra-package
        echo "✅ Cache limpo com sucesso."
    fi

fi

if [ "$OPTION" == "2" ] || [ "$OPTION" == "3" ]; then
    # ==============================================================================
    # 4. COMPILAÇÃO E INSTALAÇÃO: DEBIAN (.DEB)
    # ==============================================================================
    echo "⚙️  Preparando ambiente para compilação via Debian (.deb)..."
    
    DEB_PACKAGE_NAME="lyra-multimedia-converter"
    BUILD_DIR="lyra-package"
    
    echo "🔨 Preparando estrutura do pacote para a versão v$VERSION..."
    rm -rf $BUILD_DIR
    mkdir -p $BUILD_DIR/usr/games/lyra-app
    mkdir -p $BUILD_DIR/usr/share/applications
    mkdir -p $BUILD_DIR/usr/share/icons/hicolor/scalable/apps
    mkdir -p $BUILD_DIR/DEBIAN
    
    echo "📦 Copiando arquivos..."
    cp main.py $BUILD_DIR/usr/games/lyra-app/
    cp requirements.txt $BUILD_DIR/usr/games/lyra-app/
    cp -r assets $BUILD_DIR/usr/games/lyra-app/
    
    if [ -d "gui" ]; then
        cp -r gui $BUILD_DIR/usr/games/lyra-app/
    fi
    if [ -d "core" ]; then
        cp -r core $BUILD_DIR/usr/games/lyra-app/
    fi
    
    cp assets/icons/lyra.svg $BUILD_DIR/usr/share/icons/hicolor/scalable/apps/
    
    echo "📝 Criando metadados..."
    cat << EOF > $BUILD_DIR/DEBIAN/control
Package: $DEB_PACKAGE_NAME
Version: $VERSION
Architecture: amd64
Maintainer: VaGNaroK
Depends: python3, python3-venv, yt-dlp, libxcb-cursor0, libxkbcommon-x11-0, libegl1, libgl1, libmpv-dev, ffmpeg
Section: utils
Priority: optional
Description: Conversor multimidia acelerado por GPU (NVENC).
EOF

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

    echo "🚀 Construindo pacote Debian..."
    dpkg-deb --build $BUILD_DIR "${DEB_PACKAGE_NAME}_${VERSION}_amd64.deb"

    PACKAGE_NAME="${DEB_PACKAGE_NAME}_${VERSION}_amd64.deb"
    
    # 4.1. Instalação no Sistema
    if [ -f "$PACKAGE_NAME" ]; then
        echo "Deseja instalar o pacote Debian gerado agora? (s/N)"
        read -p "Opção: " INSTALL_OPT
        if [[ "$INSTALL_OPT" == "s" || "$INSTALL_OPT" == "S" ]]; then
            echo "🚀 Instalando o pacote final gerado no sistema (requer sudo)..."
            # O apt se encarrega de instalar dependências listadas no pacote .deb (ffmpeg, etc)
            sudo apt install "./$PACKAGE_NAME" -y
            
            echo "------------------------------------------------------------"
            echo "🎉 SUCESSO! O pacote Debian v$VERSION foi compilado e instalado."
            echo "Você já pode executar o Lyra-Qt pesquisando no menu do sistema."
        else
            echo "------------------------------------------------------------"
            echo "✅ Compilação finalizada! O pacote $PACKAGE_NAME está disponível na raiz do projeto."
        fi

        echo "------------------------------------------------------------"
        echo "Deseja limpar o diretório de cache da compilação Debian? (s/N)"
        read -p "Opção: " CLEAN_OPT
        if [[ "$CLEAN_OPT" == "s" || "$CLEAN_OPT" == "S" ]]; then
            echo "🧹 Limpando cache ($BUILD_DIR)..."
            rm -rf "$BUILD_DIR"
            echo "✅ Cache limpo com sucesso."
        fi
    else
        echo "❌ Erro: O pacote $PACKAGE_NAME não foi encontrado após a compilação."
        exit 1
    fi
fi

if [ "$OPTION" == "4" ]; then
    # ==============================================================================
    # 5. APENAS LIMPEZA DE CACHE E PACOTES
    # ==============================================================================
    echo "🔍 Verificando pastas de cache e pacotes compilados na raiz..."
    
    FOUND_CACHE=false
    if [ -d ".flatpak-builder" ] || [ -d "diretorio-build" ] || [ -d "lyra-repo" ] || [ -d "lyra-package" ]; then
        FOUND_CACHE=true
        echo "🧹 Apagando pastas de cache (.flatpak-builder, diretorio-build, lyra-repo, lyra-package)..."
        rm -rf .flatpak-builder diretorio-build lyra-repo lyra-package
    fi
    
    # Verifica se existem pacotes ignorando erros se uma das extensões não existir
    PKG_COUNT=$(find . -maxdepth 1 \( -name "*.flatpak" -o -name "*.deb" \) 2>/dev/null | wc -l)
    if [ "$PKG_COUNT" -gt 0 ]; then
        FOUND_CACHE=true
        echo "🧹 Apagando pacotes compilados (*.flatpak, *.deb)..."
        rm -f *.flatpak *.deb
    fi

    if [ "$FOUND_CACHE" = true ]; then
        echo "✅ Limpeza concluída com sucesso!"
    else
        echo "✨ Nenhum cache ou pacote encontrado. O diretório do projeto já está limpo."
    fi
fi

