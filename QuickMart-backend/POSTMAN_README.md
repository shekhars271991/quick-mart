# QuickMart Backend API - Postman Collection

This directory contains a comprehensive Postman collection for testing the QuickMart Backend API.

## 📁 Files

- `QuickMart_Backend_APIs.postman_collection.json` - Complete API collection
- `QuickMart_Environment.postman_environment.json` - Environment variables
- `POSTMAN_README.md` - This documentation

## 🚀 Quick Setup

### 1. Import Collection & Environment
1. Open Postman
2. Click **Import** → **Upload Files**
3. Select both JSON files:
   - `QuickMart_Backend_APIs.postman_collection.json`
   - `QuickMart_Environment.postman_environment.json`

### 2. Set Environment
1. Click the environment dropdown (top right)
2. Select **"QuickMart Environment"**
3. Verify the `base_url` is set to `http://localhost:3010`

### 3. Start Services
```bash
# From QuickMart root directory
docker-compose up -d                    # Start shared infrastructure
cd RecoEngine-featurestore && docker-compose up -d  # Start RecoEngine
cd ../QuickMart-backend && docker-compose up -d     # Start QuickMart Backend
```

## 📡 API Collection Structure

### 🏥 Health & Status
- **Health Check** - Verify API is running
- **Root Endpoint** - Get API information

### 🔐 Authentication
- **Register User** - Create new user account
- **Login User** - Authenticate and get JWT token
- **Get User Profile** - Retrieve current user info
- **Update User Profile** - Modify user information
- **Logout User** - End user session

### 🛍️ Products
- **Get All Products** - Browse product catalog with pagination
- **Get Products with Filters** - Filter by category, price, featured status
- **Search Products** - Search by name, description, tags
- **Get Product by ID** - Retrieve specific product details
- **Get Products by Category** - Browse category-specific products
- **Get Featured Products** - Display promoted products
- **Get Categories** - List all product categories

### 🎫 Coupons
- **Get Available Coupons** - Public discount codes
- **Get User Coupons** - Personalized coupons from nudges
- **Validate Coupon** - Check coupon validity for order
- **Apply Coupon** - Use coupon and mark as consumed
- **Get Coupon History** - User's coupon usage history

### 👤 Users
- **Get User Preferences** - Retrieve shopping preferences
- **Update User Preferences** - Modify categories, brands, price range
- **Get Purchase History** - View past orders

### ⚙️ Admin
- **Get Data Status** - Check database initialization
- **Initialize Data** - Load test data (products, users, coupons)
- **Reset Data** - Clear and reload test data

## 🔄 Automated Workflows

### Authentication Flow
1. **Login User** → Automatically sets `access_token` environment variable
2. All authenticated endpoints use `{{access_token}}` automatically

### Test Data Flow
1. **Get Data Status** → Check if data is initialized
2. **Initialize Data** → Load test products and users if needed
3. **Login User** → Use demo credentials: `demo@quickmart.com` / `demo`

## 🧪 Testing Scenarios

### Scenario 1: New User Registration
```
1. Register User → Creates new account
2. Login User → Get authentication token
3. Get User Profile → Verify account details
4. Update User Preferences → Customize shopping preferences
```

### Scenario 2: Product Browsing
```
1. Get Categories → See available product categories
2. Get All Products → Browse full catalog
3. Get Products with Filters → Filter by electronics, price range
4. Search Products → Find specific items
5. Get Product by ID → View detailed product information
```

### Scenario 3: Coupon Management
```
1. Get Available Coupons → See public discount codes
2. Login User → Authenticate for personalized coupons
3. Get User Coupons → View personalized offers from AI nudges
4. Validate Coupon → Check discount for order total
5. Apply Coupon → Use discount code
```

### Scenario 4: Admin Operations
```
1. Get Data Status → Check database state
2. Initialize Data → Load test data if needed
3. Reset Data → Clear and reload for testing
```

## 🔧 Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `base_url` | QuickMart Backend URL | `http://localhost:3010` |
| `reco_engine_url` | RecoEngine API URL | `http://localhost:8000` |
| `access_token` | JWT authentication token | Auto-set by login |
| `user_id` | Current user ID | Auto-set by login |
| `user_email` | Current user email | Auto-set by login |
| `test_product_id` | Sample product ID | `prod_001` |
| `test_coupon_code` | Sample coupon code | `WELCOME10` |
| `test_order_total` | Test order amount | `150.00` |

## 📝 Pre-loaded Test Data

### Test Users
- **Email**: `demo@quickmart.com` **Password**: `demo`
- **Email**: `john.doe@example.com` **Password**: `john.doe`
- **Email**: `jane.smith@example.com` **Password**: `jane.smith`

### Sample Products
- `prod_001` - iPhone 15 Pro
- `prod_002` - Samsung Galaxy S24
- `prod_003` - MacBook Air M3
- `prod_004` - Sony WH-1000XM5

### Available Coupons
- `WELCOME10` - 10% off first order (min $50)
- `SAVE20` - $20 off orders over $100
- `FREESHIP` - Free shipping on any order
- `ELECTRONICS15` - 15% off electronics
- `SUMMER25` - 25% off summer collection

## 🚨 Troubleshooting

### Common Issues

**❌ Connection Refused**
- Ensure QuickMart Backend is running: `docker ps`
- Check port 3010 is available: `lsof -i :3010`
- Verify environment `base_url` is correct

**❌ Authentication Failed**
- Use pre-loaded demo user: `demo@quickmart.com` / `demo`
- Check if JWT token expired (24-hour expiration)
- Re-run login request to refresh token

**❌ Empty Product List**
- Run **Initialize Data** request first
- Check **Get Data Status** to verify initialization
- Ensure Aerospike database is running

**❌ Coupon Validation Failed**
- Verify coupon code exists: use **Get Available Coupons**
- Check minimum order value requirements
- Ensure coupon hasn't expired or reached usage limit

### Debug Steps
1. **Health Check** - Verify API connectivity
2. **Get Data Status** - Check database initialization
3. **Initialize Data** - Load test data if needed
4. **Login User** - Get authentication token
5. Test specific endpoints

## 🔗 Integration with RecoEngine

The QuickMart Backend integrates with RecoEngine for AI-powered features:

- **Churn Prediction**: Called automatically on user login
- **Personalized Coupons**: Generated from RecoEngine nudges
- **Behavior Tracking**: User actions sent to RecoEngine for analysis

To test the full integration:
1. Ensure RecoEngine is running on port 8000
2. Login to QuickMart Backend
3. Browse products and use coupons
4. Check **Get User Coupons** for AI-generated offers

## 📚 Additional Resources

- **API Documentation**: `http://localhost:3010/docs` (Swagger UI)
- **RecoEngine APIs**: Import `RecoEngine-featurestore/Churn_Prediction_APIs.postman_collection.json`
- **Test Scripts**: Use `test_quickmart_backend.py` for automated testing

---

*Happy Testing! 🚀*
