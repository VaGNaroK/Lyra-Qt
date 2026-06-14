#!/bin/bash

# Cores para o output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Iniciando limpeza dos diretórios de compilação do Flatpak...${NC}"

# Lista de diretórios para apagar
DIRS=(
    ".flatpak-builder"
    "diretorio-build"
    "lyra-repo"
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

# Remover arquivos .flatpak gerados na raiz
echo -e "${YELLOW}Limpando pacotes (bundles) .flatpak residuais na raiz...${NC}"
for FLATPAK_FILE in *.flatpak; do
    if [ -f "$FLATPAK_FILE" ]; then
        echo -e "Removendo bundle: ${RED}$FLATPAK_FILE${NC}"
        rm -f "$FLATPAK_FILE"
    fi
done
echo -e "${GREEN}Limpeza concluída! O ambiente está pronto para uma compilação do zero.${NC}"
