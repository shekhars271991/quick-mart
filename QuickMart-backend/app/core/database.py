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
                    'timeout': 1000,
                    'key': aerospike.POLICY_KEY_SEND,
                    'retry': aerospike.POLICY_RETRY_ONCE,
                    'exists': aerospike.POLICY_EXISTS_CREATE_OR_REPLACE
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
    
    # CRUD Operations
    
    async def put(self, set_name: str, key: str, data: Dict[str, Any]) -> bool:
        """Insert or update a record"""
        try:
            key_tuple = (self.namespace, set_name, key)
            self.client.put(key_tuple, data)
            return True
        except Exception as e:
            logger.error(f"Failed to put record {key} in {set_name}: {e}")
            return False
    
    async def get(self, set_name: str, key: str) -> Optional[Dict[str, Any]]:
        """Get a record by key"""
        try:
            key_tuple = (self.namespace, set_name, key)
            (key_tuple, metadata, record) = self.client.get(key_tuple)
            return record
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
                key, metadata, record = input_tuple
                if record:
                    # Add the key to the record for reference
                    record['_key'] = key[2] if len(key) > 2 else None
                    records.append(record)
            
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
                key, metadata, record = input_tuple
                if record:
                    record['_key'] = key[2] if len(key) > 2 else None
                    records.append(record)
            
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

# Global database manager instance
database_manager = DatabaseManager()
