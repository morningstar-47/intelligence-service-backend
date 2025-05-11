#!/bin/bash

# Démarrer l'API Gateway
cd api-gateway
uvicorn app.main:app --reload --port 8080 &
API_GATEWAY_PID=$!

echo "API Gateway démarré avec PID $API_GATEWAY_PID"

# Démarrer l'Auth Service
cd ../auth-service
uvicorn app.main:app --reload --port 8000 &
AUTH_SERVICE_PID=$!

echo "Auth Service démarré avec PID $AUTH_SERVICE_PID"

# Fonction pour arrêter tous les services
function stop_services {
    echo "Arrêt des services..."
    kill $API_GATEWAY_PID $AUTH_SERVICE_PID
    exit 0
}

# Intercepter CTRL+C
trap stop_services SIGINT

# Maintenir le script en cours d'exécution
echo "Services démarrés. Appuyez sur CTRL+C pour arrêter tous les services."
wait