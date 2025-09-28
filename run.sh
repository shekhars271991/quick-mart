#!/bin/bash

# QuickMart Services Management Script
# Simple and crisp script to manage all QuickMart services

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Emojis for better UX
ROCKET="🚀"
DATABASE="🗄️"
BRAIN="🧠"
CART="🛒"
CHECK="✅"
CROSS="❌"
GEAR="⚙️"
TEST="🧪"

# Function to print colored output
print_status() {
    echo -e "${2}${1}${NC}"
}

print_header() {
    echo -e "\n${BLUE}================================${NC}"
    echo -e "${BLUE}${1}${NC}"
    echo -e "${BLUE}================================${NC}\n"
}

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    
    if curl -s -f "http://localhost:${port}/health" > /dev/null 2>&1; then
        print_status "${CHECK} ${service_name} is running on port ${port}" $GREEN
        return 0
    else
        print_status "${CROSS} ${service_name} is not responding on port ${port}" $RED
        return 1
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    print_status "${GEAR} Waiting for ${service_name} to be ready..." $YELLOW
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s -f "http://localhost:${port}/health" > /dev/null 2>&1; then
            print_status "${CHECK} ${service_name} is ready!" $GREEN
            return 0
        fi
        
        echo -n "."
        sleep 2
        attempt=$((attempt + 1))
    done
    
    print_status "${CROSS} ${service_name} failed to start within timeout" $RED
    return 1
}

# Function to start shared infrastructure
start_infrastructure() {
    print_header "${DATABASE} Starting Shared Infrastructure"
    
    print_status "${GEAR} Starting Aerospike database..." $YELLOW
    docker-compose up -d
    
    # Wait for Aerospike to be healthy
    print_status "${GEAR} Waiting for Aerospike to be ready..." $YELLOW
    sleep 5
    
    # Check if Aerospike is running
    if docker ps --filter "name=quickmart_aerospike" --filter "status=running" | grep -q quickmart_aerospike; then
        print_status "${CHECK} Aerospike is running" $GREEN
    else
        print_status "${CROSS} Aerospike failed to start" $RED
        exit 1
    fi
}

# Function to start RecoEngine
start_recoengine() {
    print_header "${BRAIN} Starting RecoEngine Service"
    
    cd RecoEngine-featurestore
    print_status "${GEAR} Starting RecoEngine API..." $YELLOW
    docker-compose up -d
    cd ..
    
    # Wait for RecoEngine to be ready
    wait_for_service "RecoEngine" "8000"
}

# Function to start QuickMart Backend
start_quickmart() {
    print_header "${CART} Starting QuickMart Backend"
    
    cd QuickMart-backend
    print_status "${GEAR} Starting QuickMart Backend API..." $YELLOW
    docker-compose up -d
    cd ..
    
    # Wait for QuickMart Backend to be ready
    wait_for_service "QuickMart Backend" "3010"
}

# Function to train RecoEngine model
train_model() {
    print_header "${BRAIN} Training RecoEngine Model"
    
    cd RecoEngine-featurestore
    print_status "${GEAR} Starting model training (this may take a few minutes)..." $YELLOW
    docker-compose --profile training up training-service
    cd ..
    
    print_status "${CHECK} Model training completed!" $GREEN
}

# Function to run tests
run_tests() {
    print_header "${TEST} Running Health Checks"
    
    print_status "${GEAR} Testing RecoEngine..." $YELLOW
    if python3 test_recoengine.py --quick; then
        print_status "${CHECK} RecoEngine tests passed!" $GREEN
    else
        print_status "${CROSS} RecoEngine tests failed!" $RED
    fi
    
    print_status "${GEAR} Testing QuickMart Backend..." $YELLOW
    if python3 test_quickmart_backend.py --quick; then
        print_status "${CHECK} QuickMart Backend tests passed!" $GREEN
    else
        print_status "${CROSS} QuickMart Backend tests failed!" $RED
    fi
}

# Function to show service status
show_status() {
    print_header "${GEAR} Service Status"
    
    echo -e "${CYAN}Docker Containers:${NC}"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=quickmart" --filter "name=reco"
    
    echo -e "\n${CYAN}Service Health:${NC}"
    check_service "Aerospike Tools" "3000" || true
    check_service "RecoEngine" "8000" || true
    check_service "QuickMart Backend" "3010" || true
    
    echo -e "\n${CYAN}Quick Access URLs:${NC}"
    echo -e "${BLUE}RecoEngine API:${NC} http://localhost:8000/docs"
    echo -e "${BLUE}QuickMart Backend API:${NC} http://localhost:3010/docs"
    echo -e "${BLUE}RecoEngine Health:${NC} http://localhost:8000/health"
    echo -e "${BLUE}QuickMart Health:${NC} http://localhost:3010/health"
}

# Function to stop all services
stop_services() {
    print_header "${CROSS} Stopping All Services"
    
    print_status "${GEAR} Stopping QuickMart Backend..." $YELLOW
    cd QuickMart-backend && docker-compose down && cd ..
    
    print_status "${GEAR} Stopping RecoEngine..." $YELLOW
    cd RecoEngine-featurestore && docker-compose down && cd ..
    
    print_status "${GEAR} Stopping shared infrastructure..." $YELLOW
    docker-compose down
    
    print_status "${CHECK} All services stopped!" $GREEN
}

# Function to restart all services
restart_services() {
    print_header "${GEAR} Restarting All Services"
    
    print_status "${GEAR} Restarting QuickMart Backend (with volume mounts)..." $YELLOW
    cd QuickMart-backend && docker-compose restart quickmart-backend && cd ..
    
    print_status "${GEAR} Restarting RecoEngine..." $YELLOW
    cd RecoEngine-featurestore && docker-compose restart && cd ..
    
    print_status "${GEAR} Restarting shared infrastructure..." $YELLOW
    docker-compose restart
    
    sleep 3
    print_status "${CHECK} All services restarted!" $GREEN
    show_status
}

# Function to quickly restart just the backend (for development)
restart_backend() {
    print_header "${CART} Quick Backend Restart"
    
    print_status "${GEAR} Restarting QuickMart Backend only..." $YELLOW
    cd QuickMart-backend && docker-compose restart quickmart-backend && cd ..
    
    # Wait for backend to be ready
    wait_for_service "QuickMart Backend" "3010"
    
    print_status "${CHECK} Backend restarted successfully!" $GREEN
}

# Function to show logs
show_logs() {
    local service=$1
    
    case $service in
        "aerospike"|"infra")
            print_status "${GEAR} Showing Aerospike logs..." $YELLOW
            docker-compose logs -f aerospike
            ;;
        "reco"|"recoengine")
            print_status "${GEAR} Showing RecoEngine logs..." $YELLOW
            cd RecoEngine-featurestore && docker-compose logs -f && cd ..
            ;;
        "quickmart"|"backend")
            print_status "${GEAR} Showing QuickMart Backend logs..." $YELLOW
            cd QuickMart-backend && docker-compose logs -f && cd ..
            ;;
        *)
            print_status "${GEAR} Showing all service logs..." $YELLOW
            docker-compose logs -f &
            cd RecoEngine-featurestore && docker-compose logs -f &
            cd ../QuickMart-backend && docker-compose logs -f &
            wait
            ;;
    esac
}

# Function to run services locally for development
run_local() {
    local service=$1
    
    if [ -z "$service" ]; then
        # Run all services locally
        run_all_local
    elif [ "$service" = "backend" ] || [ "$service" = "quickmart" ]; then
        run_backend_local
    elif [ "$service" = "reco" ] || [ "$service" = "recoengine" ]; then
        run_reco_local
    else
        print_status "${CROSS} Unknown service: $service" $RED
        print_status "Available services: backend, reco" $YELLOW
        print_status "Usage: ./run.sh local [backend|reco]" $YELLOW
        return 1
    fi
}

# Function to run all services locally
run_all_local() {
    print_header "${ROCKET} Running All Services Locally for Development"
    
    # Check if Python virtual environments exist, create if not
    setup_local_env
    
    # Start infrastructure (Aerospike) in Docker
    print_status "${GEAR} Starting infrastructure services..." $YELLOW
    start_infrastructure
    
    # Run backend services locally
    print_status "${GEAR} Starting backend services locally..." $YELLOW
    
    # Start QuickMart Backend locally
    start_quickmart_local &
    QUICKMART_PID=$!
    
    # Start RecoEngine locally  
    start_recoengine_local &
    RECO_PID=$!
    
    # Wait a bit for services to start
    sleep 5
    
    print_status "${CHECK} Services starting locally!" $GREEN
    print_status "QuickMart Backend: http://localhost:3011 (PID: $QUICKMART_PID)" $CYAN
    print_status "RecoEngine API: http://localhost:8001 (PID: $RECO_PID)" $CYAN
    print_status "Aerospike: localhost:3000 (Docker)" $CYAN
    print_status "" $NC
    print_status "Press Ctrl+C to stop all services" $YELLOW
    
    # Wait for interrupt
    trap 'kill $QUICKMART_PID $RECO_PID 2>/dev/null; exit' INT
    wait
}

# Function to run only QuickMart Backend locally
run_backend_local() {
    print_header "${CART} Running QuickMart Backend Locally"
    
    # Setup environment
    setup_local_env
    
    # Start infrastructure and RecoEngine in Docker
    print_status "${GEAR} Starting infrastructure services..." $YELLOW
    start_infrastructure
    
    print_status "${GEAR} Starting RecoEngine in Docker..." $YELLOW
    cd RecoEngine-featurestore && docker-compose up -d && cd ..
    
    # Wait for RecoEngine to be ready
    wait_for_service "RecoEngine (Docker)" "8000"
    
    # Start QuickMart Backend locally
    print_status "${GEAR} Starting QuickMart Backend locally on port 3011..." $YELLOW
    start_quickmart_local &
    QUICKMART_PID=$!
    
    # Wait a bit for service to start
    sleep 3
    
    print_status "${CHECK} QuickMart Backend running locally!" $GREEN
    print_status "QuickMart Backend: http://localhost:3011 (PID: $QUICKMART_PID)" $CYAN
    print_status "RecoEngine API: http://localhost:8000 (Docker)" $CYAN
    print_status "Aerospike: localhost:3000 (Docker)" $CYAN
    print_status "" $NC
    print_status "Press Ctrl+C to stop local backend" $YELLOW
    
    # Wait for interrupt
    trap 'kill $QUICKMART_PID 2>/dev/null; exit' INT
    wait
}

# Function to run only RecoEngine locally
run_reco_local() {
    print_header "${BRAIN} Running RecoEngine Locally"
    
    # Setup environment
    setup_local_env
    
    # Start infrastructure and QuickMart Backend in Docker
    print_status "${GEAR} Starting infrastructure services..." $YELLOW
    start_infrastructure
    
    print_status "${GEAR} Starting QuickMart Backend in Docker..." $YELLOW
    cd QuickMart-backend && docker-compose up -d && cd ..
    
    # Wait for QuickMart Backend to be ready
    wait_for_service "QuickMart Backend (Docker)" "3010"
    
    # Start RecoEngine locally
    print_status "${GEAR} Starting RecoEngine locally on port 8001..." $YELLOW
    start_recoengine_local &
    RECO_PID=$!
    
    # Wait a bit for service to start
    sleep 3
    
    print_status "${CHECK} RecoEngine running locally!" $GREEN
    print_status "RecoEngine API: http://localhost:8001 (PID: $RECO_PID)" $CYAN
    print_status "QuickMart Backend: http://localhost:3010 (Docker)" $CYAN
    print_status "Aerospike: localhost:3000 (Docker)" $CYAN
    print_status "" $NC
    print_status "Press Ctrl+C to stop local RecoEngine" $YELLOW
    
    # Wait for interrupt
    trap 'kill $RECO_PID 2>/dev/null; exit' INT
    wait
}

# Function to setup local development environment
setup_local_env() {
    print_status "${GEAR} Setting up local development environment..." $YELLOW
    
    # Setup QuickMart Backend
    if [ ! -d "QuickMart-backend/venv" ]; then
        print_status "Creating Python virtual environment for QuickMart Backend..." $YELLOW
        cd QuickMart-backend
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        cd ..
    fi
    
    # Setup RecoEngine
    if [ ! -d "RecoEngine-featurestore/api-service/venv" ]; then
        print_status "Creating Python virtual environment for RecoEngine..." $YELLOW
        cd RecoEngine-featurestore/api-service
        python3 -m venv venv
        source venv/bin/activate
        pip install -r requirements.txt
        cd ../..
    fi
    
    print_status "${CHECK} Local development environment ready!" $GREEN
}

# Function to start QuickMart Backend locally
start_quickmart_local() {
    print_status "${CART} Starting QuickMart Backend locally on port 3011..." $YELLOW
    cd QuickMart-backend
    source venv/bin/activate
    
    export AEROSPIKE_HOST=localhost
    export AEROSPIKE_PORT=3000
    export AEROSPIKE_NAMESPACE=quick_mart
    export RECO_ENGINE_URL=http://localhost:8001
    export JWT_SECRET=quickmart-jwt-secret-change-in-production
    export DEBUG=true
    
    python -m uvicorn app.main:app --host 0.0.0.0 --port 3011 --reload
}

# Function to start RecoEngine locally
start_recoengine_local() {
    print_status "${BRAIN} Starting RecoEngine locally on port 8001..." $YELLOW
    cd RecoEngine-featurestore/api-service
    source venv/bin/activate
    
    export AEROSPIKE_HOST=localhost
    export AEROSPIKE_PORT=3000
    export AEROSPIKE_NAMESPACE=churn_features
    
    python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
}

# Function to stop local services
stop_local() {
    print_header "${CROSS} Stopping Local Services"
    
    print_status "${GEAR} Stopping local backend services..." $YELLOW
    
    # Kill processes by port
    lsof -ti:3011 | xargs kill -9 2>/dev/null || true
    lsof -ti:8001 | xargs kill -9 2>/dev/null || true
    
    print_status "${CHECK} Local services stopped!" $GREEN
}

# Function to show local service status
status_local() {
    print_header "${GEAR} Local Development Services Status"
    
    print_status "${CYAN}Checking all possible local configurations...${NC}" $NC
    print_status "" $NC
    
    # Check local services
    print_status "${CYAN}Local Services:${NC}" $NC
    local quickmart_local_running=false
    local reco_local_running=false
    
    if check_service "QuickMart Backend (Local)" 3011 2>/dev/null; then
        quickmart_local_running=true
    fi
    
    if check_service "RecoEngine (Local)" 8001 2>/dev/null; then
        reco_local_running=true
    fi
    
    # Check Docker services
    print_status "${CYAN}Docker Services:${NC}" $NC
    local quickmart_docker_running=false
    local reco_docker_running=false
    
    if check_service "QuickMart Backend (Docker)" 3010 2>/dev/null; then
        quickmart_docker_running=true
    fi
    
    if check_service "RecoEngine (Docker)" 8000 2>/dev/null; then
        reco_docker_running=true
    fi
    
    check_service "Aerospike" 3000
    
    # Determine configuration
    print_status "" $NC
    print_status "${CYAN}Current Configuration:${NC}" $NC
    
    if [ "$quickmart_local_running" = true ] && [ "$reco_local_running" = true ]; then
        print_status "${GREEN}✅ All services running locally${NC}" $NC
        print_status "Mode: Full Local Development" $CYAN
    elif [ "$quickmart_local_running" = true ] && [ "$reco_docker_running" = true ]; then
        print_status "${GREEN}✅ Backend local, RecoEngine in Docker${NC}" $NC
        print_status "Mode: Backend Local Development" $CYAN
    elif [ "$reco_local_running" = true ] && [ "$quickmart_docker_running" = true ]; then
        print_status "${GREEN}✅ RecoEngine local, Backend in Docker${NC}" $NC
        print_status "Mode: RecoEngine Local Development" $CYAN
    elif [ "$quickmart_docker_running" = true ] && [ "$reco_docker_running" = true ]; then
        print_status "${BLUE}ℹ️  All services running in Docker${NC}" $NC
        print_status "Mode: Full Docker Development" $CYAN
    else
        print_status "${YELLOW}⚠️  Mixed or incomplete configuration${NC}" $NC
        print_status "Mode: Unknown/Partial" $CYAN
    fi
    
    print_status "" $NC
    print_status "${CYAN}Quick Access URLs:${NC}" $NC
    
    if [ "$quickmart_local_running" = true ]; then
        print_status "${BLUE}QuickMart Backend (Local):${NC} http://localhost:3011/docs" $NC
    elif [ "$quickmart_docker_running" = true ]; then
        print_status "${BLUE}QuickMart Backend (Docker):${NC} http://localhost:3010/docs" $NC
    fi
    
    if [ "$reco_local_running" = true ]; then
        print_status "${BLUE}RecoEngine (Local):${NC} http://localhost:8001/docs" $NC
    elif [ "$reco_docker_running" = true ]; then
        print_status "${BLUE}RecoEngine (Docker):${NC} http://localhost:8000/docs" $NC
    fi
}

# Function to rebuild all services
rebuild_all() {
    print_header "${GEAR} Rebuilding All Services"
    
    print_status "${GEAR} Stopping all services..." $YELLOW
    stop_services
    
    print_status "${GEAR} Rebuilding shared infrastructure..." $YELLOW
    docker-compose build --no-cache
    
    print_status "${GEAR} Rebuilding RecoEngine services..." $YELLOW
    cd RecoEngine-featurestore
    docker-compose build --no-cache
    cd ..
    
    print_status "${GEAR} Rebuilding QuickMart Backend..." $YELLOW
    cd QuickMart-backend
    docker-compose build --no-cache
    cd ..
    
    print_status "${GEAR} Rebuilding QuickMart Frontend..." $YELLOW
    cd Quickmart-frontend
    docker-compose build --no-cache
    cd ..
    
    print_status "${CHECK} All services rebuilt successfully!" $GREEN
}

# Function to start all services
start_all() {
    print_header "${ROCKET} Starting QuickMart Platform"
    
    start_infrastructure
    sleep 3
    start_recoengine
    sleep 3
    start_quickmart
    
    print_status "${CHECK} All services started successfully!" $GREEN
    show_status
}

# Function to rebuild and start all services
rebuild_and_start() {
    print_header "${ROCKET} Rebuilding and Starting QuickMart Platform"
    
    rebuild_all
    sleep 2
    start_all
}

# Function to show help
show_help() {
    echo -e "${CYAN}QuickMart Services Management${NC}"
    echo -e "${CYAN}=============================${NC}\n"
    
    echo -e "${YELLOW}Usage:${NC} ./run.sh [command] [options]"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo -e "  ${GREEN}start${NC}           Start all services (infrastructure + RecoEngine + QuickMart + Frontend)"
    echo -e "  ${GREEN}rebuild${NC}         Rebuild all Docker containers with --no-cache"
    echo -e "  ${GREEN}fresh${NC}           Rebuild and start all services (recommended for updates)"
    echo -e "  ${GREEN}stop${NC}            Stop all services"
    echo -e "  ${GREEN}restart${NC}         Restart all services"
    echo -e "  ${GREEN}restart-backend${NC} Quick restart of just the backend (for development)"
    echo -e "  ${GREEN}status${NC}          Show service status and health"
    echo -e "  ${GREEN}train${NC}           Train RecoEngine model with synthetic data"
    echo -e "  ${GREEN}test${NC}            Run health checks for all services"
    echo -e "  ${GREEN}logs [service]${NC}  Show logs (service: aerospike, reco, quickmart, or all)"
    echo ""
    echo -e "${YELLOW}Local Development (Fast):${NC}"
    echo -e "  ${GREEN}local${NC}           Run all backend services locally (QuickMart:3011, RecoEngine:8001)"
    echo -e "  ${GREEN}local backend${NC}   Run only QuickMart Backend locally (RecoEngine in Docker)"
    echo -e "  ${GREEN}local reco${NC}      Run only RecoEngine locally (QuickMart Backend in Docker)"
    echo -e "  ${GREEN}local-status${NC}    Show status of local development services"
    echo -e "  ${GREEN}local-stop${NC}      Stop local development services"
    echo ""
    echo -e "${YELLOW}Individual Services:${NC}"
    echo -e "  ${GREEN}infra${NC}           Start only shared infrastructure (Aerospike)"
    echo -e "  ${GREEN}reco${NC}            Start only RecoEngine service"
    echo -e "  ${GREEN}quickmart${NC}       Start only QuickMart Backend service"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  ${BLUE}./run.sh fresh${NC}        # Rebuild and start all services (recommended)"
    echo -e "  ${BLUE}./run.sh start${NC}        # Start all services"
    echo -e "  ${BLUE}./run.sh local${NC}        # Run all services locally for fast development"
    echo -e "  ${BLUE}./run.sh local backend${NC} # Run only backend locally (RecoEngine in Docker)"
    echo -e "  ${BLUE}./run.sh local reco${NC}    # Run only RecoEngine locally (Backend in Docker)"
    echo -e "  ${BLUE}./run.sh rebuild${NC}      # Rebuild all containers"
    echo -e "  ${BLUE}./run.sh status${NC}       # Check service health"
    echo -e "  ${BLUE}./run.sh local-status${NC} # Check local development services"
    echo -e "  ${BLUE}./run.sh train${NC}        # Train ML model"
    echo -e "  ${BLUE}./run.sh logs reco${NC}    # Show RecoEngine logs"
    echo -e "  ${BLUE}./run.sh restart${NC}      # Restart everything"
    echo -e "  ${BLUE}./run.sh restart-backend${NC} # Quick backend restart (for dev)"
    echo ""
    echo -e "${YELLOW}Service URLs:${NC}"
        echo -e "  ${BLUE}RecoEngine API:${NC}      http://localhost:8000/docs"
        echo -e "  ${BLUE}QuickMart Backend:${NC}   http://localhost:3010/docs"
        echo -e "  ${BLUE}QuickMart Frontend:${NC}  http://localhost:3000"
}

# Main script logic
case "${1:-help}" in
    "start"|"up")
        start_all
        ;;
    "rebuild")
        rebuild_all
        ;;
    "rebuild-start"|"fresh")
        rebuild_and_start
        ;;
    "stop"|"down")
        stop_services
        ;;
    "restart")
        restart_services
        ;;
    "restart-backend"|"backend-restart")
        restart_backend
        ;;
    "local"|"dev"|"local-dev")
        run_local $2
        ;;
    "local-status"|"dev-status")
        status_local
        ;;
    "local-stop"|"dev-stop")
        stop_local
        ;;
    "status"|"ps")
        show_status
        ;;
    "train"|"model")
        train_model
        ;;
    "test"|"health")
        run_tests
        ;;
    "logs")
        show_logs "${2:-all}"
        ;;
    "infra"|"infrastructure")
        start_infrastructure
        ;;
    "reco"|"recoengine")
        start_recoengine
        ;;
    "quickmart"|"backend")
        start_quickmart
        ;;
    "help"|"-h"|"--help")
        show_help
        ;;
    *)
        print_status "${CROSS} Unknown command: $1" $RED
        echo ""
        show_help
        exit 1
        ;;
esac
