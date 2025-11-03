# Unified Aerospike Namespace Structure

## Namespace: `churnprediction`

All data for both QuickMart backend and RecoEngine is stored in a single namespace called `churnprediction`.

### Sets Structure:

#### QuickMart Backend Sets:
- **`users`** - User account information and profiles
- **`products`** - Product catalog data
- **`categories`** - Product categories
- **`orders`** - Order history and details
- **`coupons`** - Available coupons and promotions
- **`user_coupons`** - User-specific coupon assignments

#### RecoEngine Sets:
- **`user_features`** - User feature data for ML (profile, behavior, transactional, engagement, support, realtime)
- **`training_data`** - Synthetic training data for model training
- **`models`** - Trained model metadata and versions

### Key Benefits:
1. **Simplified Management**: Single namespace to monitor and maintain
2. **Unified Access**: Both applications can access shared data easily
3. **Better Performance**: Reduced namespace switching overhead
4. **Easier Backup/Restore**: Single namespace to backup
5. **Cost Efficiency**: Consolidated memory allocation (2GB total)

### Data Flow:
1. QuickMart loads user data → `users` set
2. QuickMart uploads user features → `user_features` set (via RecoEngine API)
3. RecoEngine generates training data → `training_data` set
4. RecoEngine trains models → stores metadata in `models` set
5. RecoEngine predicts churn → reads from `user_features` set
6. RecoEngine assigns coupons → writes to `user_coupons` set (via QuickMart API)
