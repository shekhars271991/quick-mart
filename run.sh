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
    stop_services
    sleep 2
    start_all
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

# Function to show help
show_help() {
    echo -e "${CYAN}QuickMart Services Management${NC}"
    echo -e "${CYAN}=============================${NC}\n"
    
    echo -e "${YELLOW}Usage:${NC} ./run.sh [command] [options]"
    echo ""
    echo -e "${YELLOW}Commands:${NC}"
    echo -e "  ${GREEN}start${NC}           Start all services (infrastructure + RecoEngine + QuickMart)"
    echo -e "  ${GREEN}stop${NC}            Stop all services"
    echo -e "  ${GREEN}restart${NC}         Restart all services"
    echo -e "  ${GREEN}status${NC}          Show service status and health"
    echo -e "  ${GREEN}train${NC}           Train RecoEngine model with synthetic data"
    echo -e "  ${GREEN}test${NC}            Run health checks for all services"
    echo -e "  ${GREEN}logs [service]${NC}  Show logs (service: aerospike, reco, quickmart, or all)"
    echo ""
    echo -e "${YELLOW}Individual Services:${NC}"
    echo -e "  ${GREEN}infra${NC}           Start only shared infrastructure (Aerospike)"
    echo -e "  ${GREEN}reco${NC}            Start only RecoEngine service"
    echo -e "  ${GREEN}quickmart${NC}       Start only QuickMart Backend service"
    echo ""
    echo -e "${YELLOW}Examples:${NC}"
    echo -e "  ${BLUE}./run.sh start${NC}        # Start all services"
    echo -e "  ${BLUE}./run.sh status${NC}       # Check service health"
    echo -e "  ${BLUE}./run.sh train${NC}        # Train ML model"
    echo -e "  ${BLUE}./run.sh logs reco${NC}    # Show RecoEngine logs"
    echo -e "  ${BLUE}./run.sh restart${NC}      # Restart everything"
    echo ""
    echo -e "${YELLOW}Service URLs:${NC}"
    echo -e "  ${BLUE}RecoEngine API:${NC}      http://localhost:8000/docs"
    echo -e "  ${BLUE}QuickMart Backend:${NC}   http://localhost:3010/docs"
}

# Main script logic
case "${1:-help}" in
    "start"|"up")
        start_all
        ;;
    "stop"|"down")
        stop_services
        ;;
    "restart")
        restart_services
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
