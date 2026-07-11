"""
Configurações globais para os testes do Pytest.
"""
import sys
import os

# Garante que o diretório raiz do projeto esteja no sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
