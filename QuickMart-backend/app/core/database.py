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
                    'write': {'key': aerospike.POLICY_KEY_SEND}
                }
            }
            
            self.client = aerospike.client(config)
            self.client.connect()
            
            logger.info(f"Connected to Aerospike at {settings.AEROSPIKE_HOST}:{settings.AEROSPIKE_PORT}")
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
    
    # ============ LangGraph Store Format Methods ============
    # These methods read data stored by LangGraph AerospikeStore
    # Key format: {namespace}|{key}, data in 'value' bin
    
    async def get_from_store(self, set_name: str, namespace: str, key: str) -> Optional[Dict[str, Any]]:
        """Get a record stored in LangGraph Store format.
        
        Args:
            set_name: Aerospike set name
            namespace: LangGraph namespace (e.g., 'products')
            key: Record key (e.g., 'prod_001')
        
        Returns:
            The record data from 'value' bin, or None if not found
        """
        try:
            # LangGraph Store uses key format: namespace|key
            store_key = f"{namespace}|{key}"
            key_tuple = (self.namespace, set_name, store_key)
            (key_tuple, metadata, bins) = self.client.get(key=key_tuple)
            # LangGraph Store uses 'value' bin instead of 'data'
            return bins.get('value') if bins else None
        except aerospike.exception.RecordNotFound:
            return None
        except Exception as e:
            logger.error(f"Failed to get store record {namespace}|{key} from {set_name}: {e}")
            return None
    
    async def scan_store_set(self, set_name: str, namespace: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Scan records stored in LangGraph Store format.
        
        Args:
            set_name: Aerospike set name
            namespace: LangGraph namespace to filter by (e.g., 'products')
            limit: Optional limit on number of records
        
        Returns:
            List of record data from 'value' bin
        """
        try:
            records = []
            scan = self.client.scan(self.namespace, set_name)
            
            def callback(input_tuple):
                key, metadata, bins = input_tuple
                if bins:
                    # Check if this is a LangGraph Store record (has 'value' bin)
                    # and matches the namespace
                    record_namespace = bins.get('namespace', [])
                    if isinstance(record_namespace, list) and record_namespace:
                        if record_namespace[0] == namespace:
                            value = bins.get('value')
                            if value and isinstance(value, dict):
                                records.append(value)
            
            scan.foreach(callback)
            
            if limit:
                return records[:limit]
            return records
            
        except Exception as e:
            logger.error(f"Failed to scan store set {set_name} for namespace {namespace}: {e}")
            return []
    
    async def store_exists(self, set_name: str, namespace: str, key: str) -> bool:
        """Check if a LangGraph Store record exists."""
        try:
            store_key = f"{namespace}|{key}"
            key_tuple = (self.namespace, set_name, store_key)
            (key_tuple, metadata) = self.client.exists(key_tuple)
            return metadata is not None
        except Exception as e:
            logger.error(f"Failed to check store existence of {namespace}|{key} in {set_name}: {e}")
            return False
    
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
