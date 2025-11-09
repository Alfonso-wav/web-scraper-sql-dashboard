#!/bin/bash

echo "🚀 Preparando para subir a GitHub..."
echo ""
echo "Por favor, introduce la URL de tu repositorio de GitHub:"
echo "Ejemplo: https://github.com/tu-usuario/web-scraper-sql-dashboard.git"
read -p "URL del repositorio: " REPO_URL

if [ -z "$REPO_URL" ]; then
    echo "❌ Error: Debes proporcionar una URL"
    exit 1
fi

echo ""
echo "📡 Configurando remote..."
git remote add origin "$REPO_URL" 2>/dev/null || git remote set-url origin "$REPO_URL"

echo "🔄 Cambiando a rama 'main'..."
git branch -M main

echo "⬆️  Subiendo código a GitHub..."
git push -u origin main

if [ $? -eq 0 ]; then
    echo ""
    echo "✅ ¡CÓDIGO SUBIDO EXITOSAMENTE!"
    echo "🌐 Tu repositorio está en: $REPO_URL"
else
    echo ""
    echo "❌ Error al subir. Verifica:"
    echo "   1. La URL del repositorio es correcta"
    echo "   2. Tienes permisos para hacer push"
    echo "   3. Tu token de acceso es válido"
fi
