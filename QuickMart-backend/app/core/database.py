"""
Database connection and management for Aerospike
"""

import aerospike
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .config import settings

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Aerospike database connection manager"""
    
    def __init__(self):
        self.client: Optional[aerospike.Client] = None
        self.namespace = settings.AEROSPIKE_NAMESPACE
        
    async def connect(self):
        """Connect to Aerospike database"""
        try:
            config = {
                'hosts': [(settings.AEROSPIKE_HOST, settings.AEROSPIKE_PORT)],
                'policies': {
                    'write': {'key': aerospike.POLICY_KEY_SEND},
                    'timeout': 10000,  # 10 second timeout
                    'max_retries': 2,
                    'sleep_between_retries': 100  # 100ms between retries
                }
            }
            
            logger.info(f"Connecting to Aerospike: {settings.AEROSPIKE_HOST}:{settings.AEROSPIKE_PORT}")
            logger.info(f"TLS enabled: {settings.AEROSPIKE_USE_TLS}")
            
            # Add TLS configuration if enabled (only CA file required for Aerospike Cloud)
            if settings.AEROSPIKE_USE_TLS:
                tls_config = {}
                if settings.AEROSPIKE_TLS_CAFILE:
                    import os
                    tls_config['cafile'] = settings.AEROSPIKE_TLS_CAFILE
                    logger.info(f"TLS CA file: {settings.AEROSPIKE_TLS_CAFILE} (exists: {os.path.exists(settings.AEROSPIKE_TLS_CAFILE)})")
                if settings.AEROSPIKE_TLS_NAME:
                    tls_config['name'] = settings.AEROSPIKE_TLS_NAME
                    logger.info(f"TLS name (SNI): {settings.AEROSPIKE_TLS_NAME}")
                if tls_config:
                    config['tls'] = tls_config
                else:
                    logger.warning("TLS enabled but AEROSPIKE_TLS_CAFILE not provided")
            
            # Add authentication if credentials provided
            if settings.AEROSPIKE_USERNAME and settings.AEROSPIKE_PASSWORD:
                config['auth'] = {
                    'username': settings.AEROSPIKE_USERNAME,
                    'password': settings.AEROSPIKE_PASSWORD
                }
                logger.info(f"Using authentication: {settings.AEROSPIKE_USERNAME}")
            else:
                logger.warning("No authentication credentials provided")
            
            logger.info(f"Attempting connection with config: hosts={config['hosts']}")
            self.client = aerospike.client(config)
            self.client.connect()
            
            logger.info(f"Connected to Aerospike at {settings.AEROSPIKE_HOST}:{settings.AEROSPIKE_PORT}")
            if settings.AEROSPIKE_USE_TLS:
                logger.info("Using TLS connection")
            logger.info(f"Using namespace: {self.namespace}")
            
        except Exception as e:
            logger.error(f"Failed to connect to Aerospike: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from Aerospike database"""
        if self.client:
            self.client.close()
            self.client = None
            logger.info("Disconnected from Aerospike")
    
    async def health_check(self) -> str:
        """Check database health"""
        if not self.client:
            return "disconnected"
        
        try:
            # Try to get server info
            info = self.client.info_all("build")
            return "connected" if info else "error"
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return "error"
    
    def get_timestamp(self) -> str:
        """Get current timestamp"""
        return datetime.utcnow().isoformat()
    
    # Data transformation helpers
    
    def _prepare_data_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for Aerospike storage - convert to JSON-compatible format"""
        import json
        
        # Convert Pydantic models and complex objects to JSON-serializable format
        json_str = json.dumps(data, default=str)  # default=str handles datetime, enums, etc.
        json_data = json.loads(json_str)
        
        # Store in a single bin called 'data' to avoid bin name length limitations
        return {"data": json_data}
    
    # CRUD Operations
    
    async def put(self, set_name: str, key: str, data: Dict[str, Any]) -> bool:
        """Insert or update a record"""
        try:
            key_tuple = (self.namespace, set_name, key)
            bins = self._prepare_data_for_storage(data)
            
            # Use write policy like in the documentation example
            write_policy = {"key": aerospike.POLICY_KEY_SEND}
            self.client.put(key=key_tuple, bins=bins, policy=write_policy)
            return True
        except Exception as e:
            logger.error(f"Failed to put record {key} in {set_name}: {e}")
            return False
    
    async def get(self, set_name: str, key: str) -> Optional[Dict[str, Any]]:
        """Get a record by key"""
        try:
            key_tuple = (self.namespace, set_name, key)
            (key_tuple, metadata, bins) = self.client.get(key=key_tuple)
            # Extract the data from the 'data' bin
            return bins.get('data') if bins else None
        except aerospike.exception.RecordNotFound:
            return None
        except Exception as e:
            logger.error(f"Failed to get record {key} from {set_name}: {e}")
            return None
    
    async def delete(self, set_name: str, key: str) -> bool:
        """Delete a record by key"""
        try:
            key_tuple = (self.namespace, set_name, key)
            self.client.remove(key_tuple)
            return True
        except aerospike.exception.RecordNotFound:
            return False
        except Exception as e:
            logger.error(f"Failed to delete record {key} from {set_name}: {e}")
            return False
    
    async def scan_set(self, set_name: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scan all records in a set"""
        try:
            records = []
            scan = self.client.scan(self.namespace, set_name)
            
            if limit:
                scan.results(limit)
            
            def callback(input_tuple):
                key, metadata, bins = input_tuple
                if bins and 'data' in bins:
                    # Extract data and add the key for reference
                    data = bins['data']
                    if isinstance(data, dict):
                        data['_key'] = key[2] if len(key) > 2 else None
                    records.append(data)
            
            scan.foreach(callback)
            return records
            
        except Exception as e:
            logger.error(f"Failed to scan set {set_name}: {e}")
            return []
    
    async def query_by_field(self, set_name: str, field: str, value: Any) -> List[Dict[str, Any]]:
        """Query records by field value (requires secondary index)"""
        try:
            records = []
            query = self.client.query(self.namespace, set_name)
            query.where(aerospike.predicates.equals(field, value))
            
            def callback(input_tuple):
                key, metadata, bins = input_tuple
                if bins and 'data' in bins:
                    data = bins['data']
                    if isinstance(data, dict):
                        data['_key'] = key[2] if len(key) > 2 else None
                    records.append(data)
            
            query.foreach(callback)
            return records
            
        except Exception as e:
            logger.error(f"Failed to query {set_name} by {field}={value}: {e}")
            return []
    
    async def exists(self, set_name: str, key: str) -> bool:
        """Check if a record exists"""
        try:
            key_tuple = (self.namespace, set_name, key)
            (key_tuple, metadata) = self.client.exists(key_tuple)
            return metadata is not None
        except Exception as e:
            logger.error(f"Failed to check existence of {key} in {set_name}: {e}")
            return False
    
    async def count_records(self, set_name: str) -> int:
        """Count records in a set"""
        try:
            records = await self.scan_set(set_name)
            return len(records)
        except Exception as e:
            logger.error(f"Failed to count records in {set_name}: {e}")
            return 0
    
    async def is_set_empty(self, set_name: str) -> bool:
        """Check if a set is empty"""
        count = await self.count_records(set_name)
        return count == 0
    
    async def store_coupon(self, coupon) -> bool:
        """Store a coupon in the database"""
        try:
            coupon_data = coupon.dict() if hasattr(coupon, 'dict') else coupon.__dict__
            return await self.put("coupons", coupon.code, coupon_data)
        except Exception as e:
            logger.error(f"Failed to store coupon {coupon.code}: {e}")
            return False

# Global database manager instance
database_manager = DatabaseManager()
