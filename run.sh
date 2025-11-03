#!/bin/bash

# QuickMart Services Management Script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

# Helper: Print colored message
msg() {
    echo -e "${2}${1}${NC}"
}

# Helper: Ensure shared network exists
ensure_network() {
    if ! docker network inspect quickmart_shared_network >/dev/null 2>&1; then
        msg "Creating shared network..." $YELLOW
        docker network create --driver bridge quickmart_shared_network || {
            msg "Failed to create network" $RED
            return 1
        }
    fi
}

# Helper: Run docker compose in directory
docker_compose() {
    local dir=$1
    shift
    if [ "$dir" = "." ]; then
        docker compose "$@"
    else
        (cd "$dir" && docker compose "$@")
    fi
}

# Helper: Wait for service health
wait_for() {
    local name=$1
    local port=$2
    local max=30
    
    for i in $(seq 1 $max); do
        if curl -sf "http://localhost:${port}/health" >/dev/null 2>&1; then
            msg "✓ $name ready" $GREEN
            return 0
        fi
        echo -n "."
        sleep 2
    done
    
    msg "✗ $name failed to start" $RED
    return 1
}

# Start all services
start_all() {
    msg "\n🚀 Starting QuickMart Platform\n" $BLUE
    
    ensure_network
    sleep 1
    
    msg "Starting RecoEngine..." $YELLOW
    docker_compose "RecoEngine-featurestore" up -d
    wait_for "RecoEngine" 8000
    
    msg "Starting QuickMart Backend..." $YELLOW
    docker_compose "QuickMart-backend" up -d
    wait_for "QuickMart Backend" 3010
    
    msg "\n✓ All services started\n" $GREEN
    msg "Note: Using Aerospike Cloud (configure via AEROSPIKE_HOST/PORT/TLS_* env vars)\n" $CYAN
    show_status
}

# Stop all services
stop_all() {
    msg "\nStopping all services...\n" $YELLOW
    
    docker_compose "QuickMart-backend" down
    docker_compose "RecoEngine-featurestore" down
    
    msg "✓ All services stopped\n" $GREEN
}

# Rebuild and start all services
rebuild_and_start() {
    msg "\n🔨 Rebuilding and starting...\n" $BLUE
    
    stop_all
    
    ensure_network
    
    msg "Rebuilding RecoEngine..." $YELLOW
    docker_compose "RecoEngine-featurestore" build --no-cache
    
    msg "Rebuilding QuickMart Backend..." $YELLOW
    docker_compose "QuickMart-backend" build --no-cache
    
    start_all
}

# Show status
show_status() {
    msg "\n📊 Service Status\n" $BLUE
    
    echo -e "${CYAN}Docker Containers:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=quickmart" --filter "name=reco"
    
    echo -e "\n${CYAN}Service Health:${NC}"
    curl -sf "http://localhost:8000/health" >/dev/null 2>&1 && \
        msg "✓ RecoEngine (http://localhost:8000)" $GREEN || \
        msg "✗ RecoEngine (not running)" $RED
    
    curl -sf "http://localhost:3010/health" >/dev/null 2>&1 && \
        msg "✓ QuickMart Backend (http://localhost:3010)" $GREEN || \
        msg "✗ QuickMart Backend (not running)" $RED
    
    echo -e "\n${CYAN}Quick Access:${NC}"
    echo -e "  RecoEngine:    http://localhost:8000/docs"
    echo -e "  QuickMart:     http://localhost:3010/docs"
}

# Train model
train_model() {
    msg "\n🧠 Training Model...\n" $BLUE
    
    msg "Generating training data..." $YELLOW
    curl -s -X POST "http://localhost:8000/train/generate-data?samples=5000&clear_existing=true" >/dev/null || {
        msg "Failed to generate data" $RED
        return 1
    }
    
    msg "Training model..." $YELLOW
    curl -s -X POST "http://localhost:8000/train/model" >/dev/null || {
        msg "Training failed" $RED
        return 1
    }
    
    msg "✓ Training completed" $GREEN
    curl -s "http://localhost:8000/train/status" | jq '.' 2>/dev/null || echo "Status unavailable"
}

# Show logs
show_logs() {
    local service=${1:-all}
    
    case $service in
        reco)
            docker_compose "RecoEngine-featurestore" logs -f
            ;;
        backend)
            docker_compose "QuickMart-backend" logs -f
            ;;
        *)
            msg "Showing all logs (Ctrl+C to exit)..." $YELLOW
            docker_compose "RecoEngine-featurestore" logs -f &
            docker_compose "QuickMart-backend" logs -f &
            wait
            ;;
    esac
}

# Local development - run all services locally
run_local() {
    msg "\n💻 Local Development Mode\n" $BLUE
    
    # Setup virtual environments
    if [ ! -d "QuickMart-backend/venv" ]; then
        msg "Setting up QuickMart Backend..." $YELLOW
        (cd QuickMart-backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt -q)
    fi
    
    if [ ! -d "RecoEngine-featurestore/api-service/venv" ]; then
        msg "Setting up RecoEngine..." $YELLOW
        (cd RecoEngine-featurestore/api-service && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt -q)
    fi
    
    # Ensure shared network exists
    ensure_network
    sleep 1
    
    # Start services locally
    msg "\nStarting services locally...\n" $YELLOW
    
    (cd QuickMart-backend && source venv/bin/activate && \
     export AEROSPIKE_HOST=localhost AEROSPIKE_PORT=3000 AEROSPIKE_NAMESPACE=churnprediction \
     RECO_ENGINE_URL=http://localhost:8001 JWT_SECRET=quickmart-jwt-secret-change-in-production DEBUG=true && \
     python -m uvicorn app.main:app --host 0.0.0.0 --port 3011 --reload) &
    BACKEND_PID=$!
    
    (cd RecoEngine-featurestore/api-service && source venv/bin/activate && \
     export AEROSPIKE_HOST=localhost AEROSPIKE_PORT=3000 AEROSPIKE_NAMESPACE=churnprediction && \
     python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload) &
    RECO_PID=$!
    
    msg "Backend: http://localhost:3011 (PID: $BACKEND_PID)" $CYAN
    msg "RecoEngine: http://localhost:8001 (PID: $RECO_PID)" $CYAN
    msg "\nPress Ctrl+C to stop\n" $YELLOW
    
    trap "kill $BACKEND_PID $RECO_PID 2>/dev/null; exit" INT
    wait
}

# Help
show_help() {
    echo -e "${CYAN}QuickMart Services Management${NC}"
    echo -e "${CYAN}=============================${NC}\n"
    echo -e "${YELLOW}Usage:${NC} ./run.sh [command]\n"
    echo -e "${YELLOW}Commands:${NC}"
    echo -e "  ${GREEN}start${NC}        Start all services"
    echo -e "  ${GREEN}stop${NC}         Stop all services"
    echo -e "  ${GREEN}fresh${NC}        Rebuild and start"
    echo -e "  ${GREEN}status${NC}       Show service status"
    echo -e "  ${GREEN}logs [service]${NC}  Show logs (reco, backend, or all)"
    echo -e "  ${GREEN}local${NC}        Run services locally (fast dev)"
    echo -e "  ${GREEN}train${NC}        Train ML model"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  ./run.sh fresh"
    echo -e "  ./run.sh local"
    echo -e "  ./run.sh logs reco"
}

# Main
case "${1:-help}" in
    start)
        start_all
        ;;
    stop)
        stop_all
        ;;
    fresh)
        rebuild_and_start
        ;;
    status)
        show_status
        ;;
    train)
        train_model
        ;;
    logs)
        show_logs "$2"
        ;;
    local)
        run_local
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        msg "Unknown command: $1" $RED
        echo
        show_help
        exit 1
        ;;
esac