# QuickMart Backend Test Data

This directory contains JSON files that define the test data loaded when the QuickMart Backend starts up. You can easily modify these files to customize the sample data for your needs.

## Data Files

### 📂 categories.json
Defines product categories available in the store.

**Structure:**
```json
{
  "category_id": "unique_id",
  "name": "Display Name",
  "description": "Category description"
}
```

### 👤 users.json
Defines sample users that can login to the application.

**Structure:**
```json
{
  "email": "user@example.com",
  "name": "Full Name",
  "age": 25,
  "location": "City, State",
  "loyalty_tier": "bronze|silver|gold|platinum",
  "categories": ["preferred_category_ids"],
  "brands": ["preferred_brand_names"]
}
```

**Login Credentials:**
- Password is always the part before @ in the email address
- Example: `john.doe@example.com` → password: `john.doe`

### 🛍️ products.json
Defines products available in the catalog.

**Structure:**
```json
{
  "name": "Product Name",
  "category": "category_id",
  "subcategory": "optional_subcategory",
  "price": 99.99,
  "original_price": 129.99,
  "brand": "Brand Name",
  "description": "Product description",
  "specifications": {
    "key": "value"
  },
  "stock_quantity": 100,
  "rating": 4.5,
  "review_count": 1250,
  "tags": ["tag1", "tag2"],
  "is_featured": true
}
```

### 🎫 coupons.json
Defines available discount coupons.

**Structure:**
```json
{
  "code": "COUPON_CODE",
  "name": "Coupon Name",
  "description": "Coupon description",
  "discount_type": "percentage|fixed|free_shipping",
  "discount_value": 10,
  "minimum_order_value": 50,
  "maximum_discount": 100,
  "usage_limit": 1000,
  "days_valid": 365,
  "categories": ["applicable_category_ids"]
}
```

## Modifying Data

### Adding New Users
1. Add a new user object to `users.json`
2. Restart the backend to reload data
3. Login with `email` and password as the part before `@`

### Adding New Products
1. Add a new product object to `products.json`
2. Ensure the `category` matches an ID from `categories.json`
3. Restart the backend to reload data

### Adding New Coupons
1. Add a new coupon object to `coupons.json`
2. Use unique `code` values
3. Set `discount_type` to: `percentage`, `fixed`, or `free_shipping`
4. Restart the backend to reload data

### Adding New Categories
1. Add a new category object to `categories.json`
2. Use unique `category_id` values
3. Update products to reference the new category
4. Restart the backend to reload data

## Data Validation

The system validates:
- ✅ JSON syntax is valid
- ✅ Required fields are present
- ✅ Data types match expected formats
- ✅ File paths are accessible

If validation fails, check the backend logs for specific error messages.

## Reset Data

To reset all data:
1. Stop the backend
2. Clear the Aerospike database
3. Restart the backend - it will reload from these JSON files

## Tips

- **Backup**: Keep backups of your custom data files
- **Testing**: Use the demo user (`demo@quickmart.com` / `demo`) for quick testing
- **IDs**: Product and user IDs are auto-generated (prod_001, user_001, etc.)
- **Images**: Product images reference auto-generated filenames (prod_001_1.jpg, etc.)
- **Validation**: Invalid JSON will prevent startup - validate your JSON before restarting

---

*This approach makes it easy to maintain test data without touching code!*
