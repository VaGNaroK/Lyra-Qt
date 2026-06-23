#!/bin/bash

# Cores para o output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Iniciando limpeza dos diretórios de compilação (Flatpak / DEB)...${NC}"

# Lista de diretórios para apagar
DIRS=(
    ".flatpak-builder"
    "diretorio-build"
    "lyra-repo"
    "lyra-package"
)

# Loop para remover cada diretório
for DIR in "${DIRS[@]}"; do
    if [ -d "$DIR" ]; then
        echo -e "Removendo: ${RED}$DIR${NC}"
        rm -rf "$DIR"
    else
        echo -e "Ignorando: ${GREEN}$DIR (já não existe)${NC}"
    fi
done

# Remover arquivos gerados na raiz (.flatpak e .deb)
echo -e "${YELLOW}Limpando pacotes residuais (.flatpak e .deb) na raiz...${NC}"
for EXT in flatpak deb; do
    for FILE in *.$EXT; do
        if [ -f "$FILE" ]; then
            echo -e "Removendo pacote: ${RED}$FILE${NC}"
            rm -f "$FILE"
        fi
    done
done
echo -e "${GREEN}Limpeza concluída! O ambiente está pronto para uma compilação do zero.${NC}"
