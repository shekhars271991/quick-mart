# QuickMart - E-commerce Platform with AI-Powered Churn Prevention

A comprehensive e-commerce platform that integrates machine learning-based churn prediction and personalized nudging to improve customer retention.

## 🏗️ Architecture

- **QuickMart Backend**: FastAPI-based e-commerce API with authentication, product catalog, and coupon management
- **RecoEngine**: Churn prediction microservice using XGBoost and Aerospike feature store
- **Shared Aerospike Database**: Real-time feature store and application data storage

## 🚀 Quick Start

### Simple One-Command Startup
```bash
# Start all services (infrastructure + RecoEngine + QuickMart Backend)
./run.sh start

# Check service status
./run.sh status

# Run health checks
./run.sh test
```

### Manual Step-by-Step (Alternative)
```bash
# 1. Start shared infrastructure
./run.sh infra

# 2. Start RecoEngine
./run.sh reco

# 3. Start QuickMart Backend
./run.sh quickmart

# 4. Train the model (optional)
./run.sh train
```

### Test the System
```bash
# Test RecoEngine prediction
curl -X POST "http://localhost:8000/ingest/profile" \
  -H "Content-Type: application/json" \
  -d '{"user_id": "test_001", "acc_age_days": 365, "loyalty_tier": "gold"}'

curl -X POST "http://localhost:8000/predict/test_001"

# Test QuickMart Backend
curl http://localhost:3010/api/products
curl http://localhost:3010/api/coupons/available
```

## 📡 Services & Ports

### Shared Infrastructure (Base docker-compose)
| Service | Port | Description |
|---------|------|-------------|
| Aerospike | 3000-3003 | Shared database (namespaces: `churn_features`, `quick_mart`) |

### Microservices (Individual docker-compose files)
| Service | Port | Location | Description |
|---------|------|----------|-------------|
| RecoEngine API | 8000 | `RecoEngine-featurestore/` | Churn prediction and nudge generation |
| QuickMart Backend | 3010 | `QuickMart-backend/` | E-commerce API (authentication, catalog, coupons) |

## 🗃️ Database Namespaces

### Aerospike Configuration
- **`churn_features`**: RecoEngine feature store (user behavior, predictions)
- **`quick_mart`**: QuickMart application data (users, products, orders, coupons)

## 🔄 Integration Flow

```
User Login → QuickMart Backend → RecoEngine Predict API
                    ↓
RecoEngine Nudge Response → Create User Coupon → Store in quick_mart namespace
                    ↓
User Shopping → GET /api/coupons/user → Display Personalized Coupons
```

## 🛠️ Development

### Microservices Architecture

This project follows a **microservices architecture** with:

1. **`/docker-compose.yml`** - **Shared Infrastructure Services**
   - Aerospike database (shared by all microservices)
   - Shared network for inter-service communication

2. **`/RecoEngine-featurestore/docker-compose.yml`** - **RecoEngine Microservice**
   - API service for churn prediction
   - Training service for model development
   - Uses external shared Aerospike

3. **`/QuickMart-backend/docker-compose.yml`** - **QuickMart Backend Microservice** (to be created)
   - E-commerce API service
   - Uses external shared Aerospike and RecoEngine

### Development Workflow

**1. Start Shared Infrastructure:**
```bash
# Always start shared services first
docker-compose up -d
```

**2. Start Individual Microservices:**
```bash
# Start RecoEngine
cd RecoEngine-featurestore
docker-compose up -d

# Start QuickMart Backend (when implemented)
cd ../QuickMart-backend
docker-compose up -d
```

**3. Scale Individual Services:**
```bash
# Scale specific microservice
cd RecoEngine-featurestore
docker-compose up -d --scale api-service=3
```

### Database Management
```bash
# Access Aerospike tools
docker exec -it quickmart_aerospike_tools bash

# Inside container - check namespaces
asinfo -h aerospike -p 3000 -v "namespaces"

# Check namespace statistics
asinfo -h aerospike -p 3000 -v "namespace/churn_features"
asinfo -h aerospike -p 3000 -v "namespace/quick_mart"
```

### Logs and Debugging
```bash
# View service logs
docker-compose logs aerospike
docker-compose logs reco-api
docker-compose logs quickmart-backend

# Follow logs
docker-compose logs -f reco-api
```

## 📊 Data Models

### RecoEngine (churn_features namespace)
- User behavior features (profile, transactional, engagement)
- Churn predictions and scores
- Nudge generation results

### QuickMart (quick_mart namespace)
- User profiles and authentication
- Product catalog and categories
- Shopping carts and orders
- Available and user-specific coupons
- Nudge tracking and effectiveness

## 🔧 Environment Variables

### Shared Configuration
```bash
AEROSPIKE_HOST=aerospike
AEROSPIKE_PORT=3000
```

### RecoEngine Specific
```bash
AEROSPIKE_NAMESPACE=churn_features
```

### QuickMart Backend Specific
```bash
AEROSPIKE_NAMESPACE=quick_mart
RECO_ENGINE_URL=http://reco-api:8000
JWT_SECRET=your_jwt_secret_here
NODE_ENV=development
```

## 📈 Monitoring & Health Checks

### Health Endpoints
- **Aerospike**: `asinfo -h localhost -p 3000 -v build`
- **RecoEngine**: `http://localhost:8000/health`
- **QuickMart**: `http://localhost:3010/health`

### Service Dependencies
- QuickMart Backend depends on Aerospike and RecoEngine
- RecoEngine depends on Aerospike
- All services use the shared `quickmart_network`

## 🚦 Profiles

- **Default**: Aerospike + RecoEngine API
- **`training`**: Include model training service
- **`backend`**: Include QuickMart backend service

## 📝 Next Steps

1. **Implement QuickMart Backend** following the plan in `QuickMart-backend/plan.md`
2. **Create Frontend Application** to consume both APIs
3. **Add Monitoring** with Prometheus/Grafana
4. **Implement CI/CD** pipeline
5. **Add Authentication** and security layers

---

*This setup provides a production-ready foundation for an AI-powered e-commerce platform with intelligent customer retention capabilities.*
