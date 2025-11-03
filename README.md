# QuickMart - E-commerce Platform with AI-Powered Churn Prevention

A comprehensive e-commerce platform that integrates machine learning-based churn prediction and personalized nudging to improve customer retention.

## 🏗️ Architecture

- **QuickMart Backend**: FastAPI-based e-commerce API with authentication, product catalog, and coupon management
- **RecoEngine**: Churn prediction microservice using XGBoost and Aerospike feature store
- **Shared Aerospike Database**: Real-time feature store and application data storage

## 🚀 Getting Started

Follow these 5 simple steps to get the complete QuickMart platform up and running:

### Step 1: Start All Application Components
```bash
# Start all services (infrastructure + RecoEngine + QuickMart Backend + Frontend)
./run.sh start

# Check that all services are running
./run.sh status
```

### Step 2: Load User Data
```bash
# Load demo users with features into the system
curl -X POST "http://localhost:3010/api/admin/load-data"

# Verify users are loaded
curl "http://localhost:3010/api/admin/users" | jq
```

### Step 3: Generate Training Data
```bash
# Generate synthetic training data for the ML model (1000 samples)
curl -X POST "http://localhost:8000/train/generate-data?samples=1000&clear_existing=true&random_seed=42"

# Check data quality
curl "http://localhost:8000/train/data-quality" | jq
```

### Step 4: Run Training Job
```bash
# Train the churn prediction model
curl -X POST "http://localhost:8000/train/start?test_size=0.2&random_state=42"

# Check training status
curl "http://localhost:8000/train/status" | jq
```

### Step 5: Test Predict API for Seed User
```bash
# Test churn prediction for a demo user
curl -X POST "http://localhost:8000/predict/user_001" | jq

# Test with different users
curl -X POST "http://localhost:8000/predict/user_002" | jq
curl -X POST "http://localhost:8000/predict/user_003" | jq
```

### 🎉 Success! Your platform is ready!

**Access Points:**
- **Frontend**: http://localhost:3000
- **QuickMart Backend API**: http://localhost:3010/docs
- **RecoEngine API**: http://localhost:8000/docs
- **Postman Collection**: Import `QuickMart_Complete_APIs.postman_collection.json`

### Alternative: Fast Local Development
For faster development with instant code changes:
```bash
# Run backend services locally (no Docker rebuilds needed)
./run.sh local

# Services will run on different ports:
# - QuickMart Backend: http://localhost:3011
# - RecoEngine: http://localhost:8001
```

## 📡 Services & Ports

### Shared Infrastructure (Base docker-compose)
| Service | Port | Description |
|---------|------|-------------|
| Aerospike | 3000-3003 | Unified database (namespace: `churnprediction`) |

### Microservices (Individual docker-compose files)
| Service | Port | Location | Description |
|---------|------|----------|-------------|
| RecoEngine API | 8000 | `RecoEngine-featurestore/` | Churn prediction and nudge generation |
| QuickMart Backend | 3010 | `QuickMart-backend/` | E-commerce API (authentication, catalog, coupons) |

## 🗃️ Database Namespaces

### Aerospike Configuration
- **`churnprediction`**: Unified namespace containing all data (user features, training data, application data)

## 🔄 Integration Flow

```
User Login → QuickMart Backend → RecoEngine Predict API
                    ↓
RecoEngine Nudge Response → Create User Coupon → Store in churnprediction namespace
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
asinfo -h aerospike -p 3000 -v "namespace/churnprediction"
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

### RecoEngine (churnprediction namespace)
- User behavior features (profile, transactional, engagement)
- Churn predictions and scores
- Nudge generation results

### QuickMart (churnprediction namespace)
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
AEROSPIKE_NAMESPACE=churnprediction
```

### QuickMart Backend Specific
```bash
AEROSPIKE_NAMESPACE=churnprediction
RECO_ENGINE_URL=http://reco-api:8000
JWT_SECRET=your_jwt_secret_here
NODE_ENV=development
```

## 👤 Sample Application Users

The QuickMart Backend automatically creates 5 sample users for testing and demonstration. These users can login and use all application features.

### Pre-loaded Test Users

| User ID | Email | Password | Name | Age | Location | Loyalty Tier | Preferred Categories | Preferred Brands |
|---------|-------|----------|------|-----|----------|--------------|---------------------|------------------|
| `user_001` | `john.doe@example.com` | `admin` | John Doe | 28 | New York, NY | Gold | Electronics, Books & Media | Apple, Samsung |
| `user_002` | `jane.smith@example.com` | `admin` | Jane Smith | 34 | Los Angeles, CA | Platinum | Clothing, Home & Garden | Nike, Dyson |
| `user_003` | `mike.johnson@example.com` | `admin` | Mike Johnson | 22 | Chicago, IL | Bronze | Sports & Fitness, Electronics | Peloton, Sony |
| `user_004` | `sarah.wilson@example.com` | `admin` | Sarah Wilson | 45 | Houston, TX | Silver | Home & Garden, Books & Media | Instant Pot, Levi's |
| `user_005` | `demo@quickmart.com` | `admin` | Demo User | 30 | San Francisco, CA | Gold | Electronics, Clothing | Apple, Nike |

### Quick Login Test
```bash
# Login as demo user
curl -X POST "http://localhost:3010/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=demo@quickmart.com&password=admin'

# Login as John Doe  
curl -X POST "http://localhost:3010/api/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d 'username=john.doe@example.com&password=admin'
```

**Note**: All demo users have the default password `admin` for easy testing.

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
