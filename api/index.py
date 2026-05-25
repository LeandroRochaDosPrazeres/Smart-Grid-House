"""
Entrypoint do Vercel — expõe o servidor Flask do Dash.
O Vercel roda este arquivo como serverless function.
"""
import sys
import os

# Adicionar a raiz do projeto ao path para importar app_dash
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app_dash import app

# O Vercel precisa de uma variável `app` (WSGI handler)
server = app.server
app = server  # alias para o Vercel encontrar
