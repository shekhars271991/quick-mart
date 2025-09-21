# QuickMart Backend Development Plan

## 🎯 Overview
The QuickMart backend will serve as the main API layer for the e-commerce application, handling user authentication, session management, and integration with the RecoEngine for churn prediction and nudge delivery.

## 🏗️ Architecture

### Core Components
1. **API Gateway** - FastAPI REST API server
2. **Authentication Service** - User login/session management
3. **Product Catalog Service** - Product management and display
4. **Database Layer** - Aerospike (separate namespace from RecoEngine)
5. **Data Initialization Service** - Test data loader for products and users
6. **Coupon Management Service** - Available coupons and user-specific coupon handling
7. **RecoEngine Integration** - Calls to prediction/ingestion APIs (includes nudge engine)

### Database Strategy
- **Aerospike Container**: Shared with RecoEngine but different namespace
  - RecoEngine namespace: `reco_features`
  - QuickMart namespace: `quickmart_app`

## 🔐 Authentication & Session Management

### User Authentication
- **Login System**: Email/password based authentication
- **Session Tracking**: JWT tokens or session-based authentication
- **User Profiles**: Store user preferences, purchase history, demographics

### Session Data Collection
- Track user behavior for RecoEngine ingestion:
  - Login frequency
  - Session duration
  - Page views
  - Cart interactions
  - Purchase patterns

## 📡 API Endpoints

### Authentication APIs
```
POST /api/auth/register
POST /api/auth/login
POST /api/auth/logout
GET  /api/auth/profile
PUT  /api/auth/profile
```

### User Management APIs
```
GET  /api/users/profile
PUT  /api/users/profile
GET  /api/users/preferences
PUT  /api/users/preferences
GET  /api/users/purchase-history
```

### Product Catalog APIs
```
GET  /api/products                    # Get all products with pagination/filtering
GET  /api/products/:id                # Get specific product details
GET  /api/products/category/:category # Get products by category
GET  /api/products/search?q=query     # Search products
GET  /api/categories                  # Get all product categories
GET  /api/products/featured           # Get featured/recommended products
```

### Shopping Cart APIs
```
POST /api/cart/add                    # Add item to cart
GET  /api/cart                        # Get current user's cart
PUT  /api/cart/update                 # Update cart item quantity
DELETE /api/cart/remove/:item_id      # Remove item from cart
DELETE /api/cart/clear                # Clear entire cart
POST /api/cart/checkout               # Proceed to checkout
```


### RecoEngine Integration APIs
```
POST /api/reco/ingest-behavior    # Internal: Send user behavior to RecoEngine
POST /api/reco/predict-churn      # Internal: Get churn prediction
GET  /api/reco/nudges/:user_id    # Get active nudges for user
POST /api/reco/nudge-response     # Track nudge interactions
```

### Coupon Management APIs
```
GET  /api/coupons/available       # Get all available coupons
GET  /api/coupons/user            # Get user-specific coupons (from nudges)
POST /api/coupons/apply           # Apply coupon code to cart
GET  /api/coupons/history         # User's coupon usage history
POST /api/coupons/validate        # Validate coupon code
```

### Data Management APIs
```
POST /api/admin/init-data         # Initialize test data (products & users)
POST /api/admin/reset-data        # Reset all test data
GET  /api/admin/data-status       # Check data initialization status
```

## 🎁 Coupon & Nudge System Implementation

### Coupon System Overview
- **Available Coupons**: General discount codes available to all users
- **User-Specific Coupons**: Personalized coupons from RecoEngine nudges
- **Coupon Types**: Percentage discounts, fixed amount discounts, free shipping
- **Application**: Applied during checkout process

### Login-Triggered Prediction Workflow
1. **User Login**: User authenticates successfully
2. **Behavior Ingestion**: Send recent user actions to RecoEngine
3. **Churn Prediction**: Automatically call RecoEngine predict API
4. **Nudge Processing**: If RecoEngine returns nudges with discount codes:
   - Create user-specific coupon in QuickMart database
   - Add to user's available coupons list
   - Track nudge delivery
5. **Coupon Availability**: User can view and apply coupons during shopping

### RecoEngine Integration Flow
```
User Login → QuickMart Backend → RecoEngine Predict API
                    ↓
RecoEngine Response (with nudges) → Create User Coupons → Store in Database
                    ↓
User Shopping → GET /api/coupons/user → Display Available Coupons
```

## 🔄 RecoEngine Integration Details

### Data Flow
```
User Action → QuickMart Backend → RecoEngine Ingest API
                    ↓
User Login → QuickMart Backend → RecoEngine Predict API
                    ↓
RecoEngine Nudge Response → Create User Coupon → Store in Database
```

### Feature Ingestion Schedule
- **Real-time**: Cart actions, page views, session data
- **Batch**: Daily purchase summaries, weekly behavior patterns
- **Event-driven**: Login events, checkout completions

## 🛠️ Technology Stack

### Backend Framework
- **Option 1**: FastAPI (Python) - Easy integration with RecoEngine
- **Option 2**: Express.js (Node.js) - Fast development, good for APIs

### Database
- **Primary**: Aerospike (namespace: `quickmart_app`)
  - User profiles
  - Session data
  - Order history
  - Nudge tracking

### Authentication
- **JWT Tokens**: For stateless authentication
- **Session Storage**: In Aerospike for session management

### Integration
- **HTTP Client**: For RecoEngine API calls
- **Background Jobs**: For batch data ingestion
- **Caching**: Aerospike for frequently accessed data

## 📊 Data Models

### Product Catalog
```json
{
  "product_id": "string",
  "name": "string",
  "description": "string",
  "category": "string",
  "subcategory": "string",
  "price": "number",
  "original_price": "number",
  "discount_percentage": "number",
  "brand": "string",
  "images": ["array"],
  "specifications": "object",
  "stock_quantity": "number",
  "rating": "number",
  "review_count": "number",
  "tags": ["array"],
  "is_featured": "boolean",
  "is_active": "boolean",
  "created_at": "timestamp",
  "updated_at": "timestamp"
}
```

### Category
```json
{
  "category_id": "string",
  "name": "string",
  "description": "string",
  "parent_category": "string",
  "image_url": "string",
  "is_active": "boolean",
  "sort_order": "number"
}
```

### User Profile
```json
{
  "user_id": "string",
  "email": "string",
  "profile": {
    "name": "string",
    "age": "number",
    "location": "string",
    "loyalty_tier": "string"
  },
  "preferences": {
    "categories": ["array"],
    "brands": ["array"],
    "price_range": "object"
  },
  "created_at": "timestamp",
  "last_login": "timestamp"
}
```

### Session Data
```json
{
  "session_id": "string",
  "user_id": "string",
  "start_time": "timestamp",
  "end_time": "timestamp",
  "pages_viewed": ["array"],
  "cart_actions": ["array"],
  "purchase_intent": "number"
}
```

### Order Data
```json
{
  "order_id": "string",
  "user_id": "string",
  "items": ["array"],
  "total_amount": "number",
  "discount_applied": "object",
  "nudge_id": "string",
  "status": "string",
  "created_at": "timestamp"
}
```

### Available Coupons
```json
{
  "coupon_id": "string",
  "code": "string",
  "name": "string",
  "description": "string",
  "discount_type": "percentage|fixed|free_shipping",
  "discount_value": "number",
  "minimum_order_value": "number",
  "maximum_discount": "number",
  "usage_limit": "number",
  "usage_count": "number",
  "valid_from": "timestamp",
  "valid_until": "timestamp",
  "is_active": "boolean",
  "applicable_categories": ["array"],
  "applicable_products": ["array"]
}
```

### User-Specific Coupons
```json
{
  "user_coupon_id": "string",
  "user_id": "string",
  "coupon_id": "string",
  "source": "nudge|general|promotion",
  "nudge_id": "string",
  "churn_score": "number",
  "status": "available|used|expired",
  "assigned_at": "timestamp",
  "used_at": "timestamp",
  "order_id": "string"
}
```

### Nudge Tracking
```json
{
  "nudge_id": "string",
  "user_id": "string",
  "type": "discount_code",
  "churn_score": "number",
  "nudge_content": "object",
  "coupon_created": "boolean",
  "coupon_id": "string",
  "status": "delivered|viewed|used|expired",
  "created_at": "timestamp",
  "viewed_at": "timestamp",
  "used_at": "timestamp"
}
```

## 🚀 Implementation Phases

### Phase 1: Core Backend Setup
- [ ] Set up FastAPI server
- [ ] Implement authentication system
- [ ] Set up Aerospike connection (quickmart_app namespace)
- [ ] Create test data initialization service
- [ ] Implement product catalog APIs
- [ ] Create basic user management APIs

### Phase 2: Shopping & Cart Management
- [ ] Build shopping cart functionality
- [ ] Create order management system
- [ ] Add basic checkout flow
- [ ] Implement product search and filtering

### Phase 3: RecoEngine Integration & Coupon System
- [ ] Implement behavior ingestion to RecoEngine
- [ ] Add login-triggered churn prediction calls
- [ ] Create coupon management system
- [ ] Build user-specific coupon assignment from nudges
- [ ] Implement coupon validation and application logic

### Phase 4: Advanced Features
- [ ] Add nudge effectiveness tracking
- [ ] Implement A/B testing for nudges
- [ ] Add advanced user segmentation
- [ ] Create admin dashboard for nudge management

## 🗃️ Test Data Initialization

### Application Startup Data Loading
The backend will automatically initialize test data on application startup if the database is empty.

### Product Catalog Test Data
**Categories:**
- Electronics (Smartphones, Laptops, Headphones, Smart Watches)
- Clothing (Men's, Women's, Kids, Accessories)
- Home & Garden (Furniture, Kitchen, Decor, Tools)
- Books & Media (Fiction, Non-fiction, Educational, Entertainment)
- Sports & Fitness (Equipment, Apparel, Supplements, Outdoor)

**Sample Products (50-100 items):**
```json
{
  "product_id": "prod_001",
  "name": "iPhone 15 Pro",
  "description": "Latest iPhone with advanced camera system",
  "category": "Electronics",
  "subcategory": "Smartphones",
  "price": 999.99,
  "original_price": 1099.99,
  "discount_percentage": 9,
  "brand": "Apple",
  "images": ["iphone15pro_1.jpg", "iphone15pro_2.jpg"],
  "specifications": {
    "storage": "128GB",
    "color": "Natural Titanium",
    "display": "6.1-inch Super Retina XDR"
  },
  "stock_quantity": 50,
  "rating": 4.8,
  "review_count": 1250,
  "tags": ["smartphone", "apple", "premium", "5g"],
  "is_featured": true,
  "is_active": true
}
```

### Test Users Data
**User Profiles (20-30 users):**
```json
{
  "user_id": "user_001",
  "email": "john.doe@example.com",
  "password": "hashed_password",
  "profile": {
    "name": "John Doe",
    "age": 28,
    "location": "New York, NY",
    "loyalty_tier": "gold"
  },
  "preferences": {
    "categories": ["Electronics", "Books"],
    "brands": ["Apple", "Samsung", "Nike"],
    "price_range": {"min": 50, "max": 1000}
  },
  "purchase_history": [
    {
      "order_id": "ord_001",
      "total": 299.99,
      "date": "2024-01-15",
      "items": ["prod_045", "prod_067"]
    }
  ]
}
```

### Available Coupons Test Data
**General Coupons (10-15 coupons):**
```json
{
  "coupon_id": "coup_001",
  "code": "WELCOME10",
  "name": "Welcome Discount",
  "description": "10% off your first order",
  "discount_type": "percentage",
  "discount_value": 10,
  "minimum_order_value": 50,
  "maximum_discount": 100,
  "usage_limit": 1000,
  "usage_count": 45,
  "valid_from": "2024-01-01T00:00:00Z",
  "valid_until": "2024-12-31T23:59:59Z",
  "is_active": true,
  "applicable_categories": [],
  "applicable_products": []
}
```

### Data Initialization Service
```python
class DataInitializer:
    async def initialize_on_startup(self):
        if await self.is_database_empty():
            await self.load_categories()
            await self.load_products()
            await self.load_available_coupons()
            await self.load_test_users()
            await self.create_sample_orders()
            logger.info("Test data initialized successfully")
    
    async def load_products(self):
        # Load 50-100 diverse products across categories
        # Include mix of featured/regular, discounted/full-price
        
    async def load_available_coupons(self):
        # Create 10-15 general coupons
        # Mix of percentage, fixed amount, free shipping
        # Different validity periods and usage limits
        
    async def load_test_users(self):
        # Create 20-30 test users with varied profiles
        # Different loyalty tiers, preferences, purchase history
```

### Data Reset Functionality
- Admin endpoint to reset all test data
- Useful for demos and testing
- Preserves schema, reloads fresh test data

## 🔧 Development Setup

### Environment Configuration
```bash
# Database
AEROSPIKE_HOST=localhost
AEROSPIKE_PORT=3000
AEROSPIKE_NAMESPACE=quickmart_app

# RecoEngine Integration
RECO_ENGINE_URL=http://localhost:8000
RECO_ENGINE_API_KEY=your_api_key

# Authentication
JWT_SECRET=your_jwt_secret
SESSION_TIMEOUT=3600

# Application
PORT=3001
NODE_ENV=development
```

### Docker Integration
- Extend existing docker-compose.yml to include QuickMart backend
- Share Aerospike container with RecoEngine
- Add environment variables for service communication

## 📈 Success Metrics

### Business Metrics
- User retention rate improvement
- Conversion rate from nudges
- Average order value increase
- Churn reduction percentage

### Technical Metrics
- API response times
- RecoEngine integration latency
- Nudge delivery success rate
- System uptime and reliability

## 🔮 Future Enhancements

### Advanced Nudge Types
- Push notifications
- Email campaigns
- In-app banners
- Personalized product recommendations

### Machine Learning Integration
- Real-time personalization
- Dynamic pricing
- Inventory optimization
- Customer lifetime value prediction

---

*This plan serves as the foundation for building a comprehensive e-commerce backend that leverages machine learning for customer retention through intelligent nudging.*
