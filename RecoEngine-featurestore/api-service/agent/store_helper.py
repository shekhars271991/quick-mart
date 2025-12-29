"""
Aerospike Store Helper for LangGraph

Provides the AerospikeStore configuration for storing and retrieving
user features using the LangGraph Store API.

Data Format (Store API):
- namespace: ("user_features", feature_type)  e.g., ("user_features", "profile")
- key: user_id  e.g., "user_005"
- value: dict with all features
"""

import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any

import aerospike
from langgraph.store.aerospike import AerospikeStore

logger = logging.getLogger(__name__)

# Singleton instance
_aerospike_store: Optional[AerospikeStore] = None
_store_client = None

# Feature types supported
FEATURE_TYPES = ["profile", "behavior", "transactional", "engagement", "support", "realtime"]


def get_aerospike_store(
    client: Optional[aerospike.Client] = None,
    namespace: str = None,
    set_name: str = "user_features",
    host: str = None,
    port: int = None,
) -> AerospikeStore:
    """
    Get or create an AerospikeStore instance for LangGraph store operations.
    
    Args:
        client: Optional existing Aerospike client to reuse
        namespace: Aerospike namespace (defaults to env var or 'churnprediction')
        set_name: Aerospike set name (defaults to 'user_features')
        host: Aerospike host (defaults to env var or 'localhost')
        port: Aerospike port (defaults to env var or 3000)
        
    Returns:
        Configured AerospikeStore instance
    """
    global _aerospike_store, _store_client
    
    if _aerospike_store is not None:
        return _aerospike_store
    
    namespace = namespace or os.getenv("AEROSPIKE_NAMESPACE", "churnprediction")
    host = host or os.getenv("AEROSPIKE_HOST", "localhost")
    port = port or int(os.getenv("AEROSPIKE_PORT", "3000"))
    
    if client is not None:
        _store_client = client
        logger.info("Reusing existing Aerospike client for store")
    else:
        config = {
            "hosts": [(host, port)],
            "policies": {
                "write": {"key": aerospike.POLICY_KEY_SEND}
            }
        }
        try:
            _store_client = aerospike.client(config).connect()
            logger.info(f"Created new Aerospike client for store at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to Aerospike for store: {e}")
            raise
    
    _aerospike_store = AerospikeStore(
        client=_store_client,
        namespace=namespace,
        set=set_name
    )
    
    logger.info(f"AerospikeStore initialized with namespace: {namespace}, set: {set_name}")
    return _aerospike_store


def reset_store():
    """Reset the store singleton (useful for testing)."""
    global _aerospike_store, _store_client
    _aerospike_store = None
    _store_client = None


# =============================================================================
# SYNC METHODS - Using store.get() and store.put()
# =============================================================================

def store_user_features(
    store: AerospikeStore,
    user_id: str,
    features: Dict[str, Any],
    feature_type: str
) -> None:
    """
    Store user features using the LangGraph Store API (sync).
    
    Args:
        store: The AerospikeStore instance
        user_id: User identifier
        features: Dictionary of feature values
        feature_type: Type of features (profile, behavior, transactional, etc.)
    """
    # Get existing features to merge
    existing_item = store.get(
        namespace=("user_features", feature_type),
        key=user_id
    )
    
    existing_features = existing_item.value if existing_item else {}
    # Remove metadata from existing before merge
    existing_features = {k: v for k, v in existing_features.items() 
                        if k not in ["timestamp", "feature_type"]}
    
    # Merge existing with new (new overrides existing)
    merged_features = {**existing_features, **features}
    
    # Store with metadata
    store.put(
        namespace=("user_features", feature_type),
        key=user_id,
        value={
            **merged_features,
            "timestamp": datetime.utcnow().isoformat(),
            "feature_type": feature_type
        }
    )
    
    logger.info(f"Stored {feature_type} features for user {user_id} via Store API")


def retrieve_all_user_features(
    store: AerospikeStore,
    user_id: str
) -> tuple[dict, str]:
    """
    Retrieve all features for a user across all feature types (sync).
    
    Uses the LangGraph Store API: store.get()
    
    Args:
        store: The AerospikeStore instance
        user_id: User identifier
        
    Returns:
        Tuple of (all_features dict, feature_freshness timestamp)
    """
    all_features = {}
    feature_freshness = None
    
    for feature_type in FEATURE_TYPES:
        item = store.get(
            namespace=("user_features", feature_type),
            key=user_id
        )
        
        if item and item.value:
            # Extract features (excluding metadata)
            features = {k: v for k, v in item.value.items() 
                       if k not in ["timestamp", "feature_type"]}
            all_features.update(features)
            
            # Track most recent timestamp
            item_timestamp = item.value.get("timestamp", "")
            if item_timestamp and (not feature_freshness or item_timestamp > feature_freshness):
                feature_freshness = item_timestamp
            
            logger.debug(f"Retrieved {len(features)} {feature_type} features for {user_id}")
    
    if all_features:
        logger.info(f"Retrieved total {len(all_features)} features for user {user_id}")
    else:
        logger.warning(f"No features found for user {user_id}")
    
    return all_features, feature_freshness or datetime.utcnow().isoformat()


# =============================================================================
# ASYNC METHODS - Using store.aget() and store.aput()
# =============================================================================

async def store_user_features_async(
    store: AerospikeStore,
    user_id: str,
    features: Dict[str, Any],
    feature_type: str
) -> None:
    """
    Store user features using the LangGraph Store API (async).
    
    Args:
        store: The AerospikeStore instance
        user_id: User identifier
        features: Dictionary of feature values
        feature_type: Type of features (profile, behavior, transactional, etc.)
    """
    # Get existing features to merge
    existing_item = await store.aget(
        namespace=("user_features", feature_type),
        key=user_id
    )
    
    existing_features = existing_item.value if existing_item else {}
    # Remove metadata from existing before merge
    existing_features = {k: v for k, v in existing_features.items() 
                        if k not in ["timestamp", "feature_type"]}
    
    # Merge existing with new (new overrides existing)
    merged_features = {**existing_features, **features}
    
    # Store with metadata
    await store.aput(
        namespace=("user_features", feature_type),
        key=user_id,
        value={
            **merged_features,
            "timestamp": datetime.utcnow().isoformat(),
            "feature_type": feature_type
        }
    )
    
    logger.info(f"Stored {feature_type} features for user {user_id} via Store API (async)")


async def retrieve_all_user_features_async(
    store: AerospikeStore,
    user_id: str
) -> tuple[dict, str]:
    """
    Retrieve all features for a user across all feature types (async).
    
    Uses the LangGraph Store API: store.aget()
    
    Args:
        store: The AerospikeStore instance
        user_id: User identifier
        
    Returns:
        Tuple of (all_features dict, feature_freshness timestamp)
    """
    all_features = {}
    feature_freshness = None
    
    for feature_type in FEATURE_TYPES:
        item = await store.aget(
            namespace=("user_features", feature_type),
            key=user_id
        )
        
        if item and item.value:
            # Extract features (excluding metadata)
            features = {k: v for k, v in item.value.items() 
                       if k not in ["timestamp", "feature_type"]}
            all_features.update(features)
            
            # Track most recent timestamp
            item_timestamp = item.value.get("timestamp", "")
            if item_timestamp and (not feature_freshness or item_timestamp > feature_freshness):
                feature_freshness = item_timestamp
            
            logger.debug(f"Retrieved {len(features)} {feature_type} features for {user_id}")
    
    if all_features:
        logger.info(f"Retrieved total {len(all_features)} features for user {user_id}")
    else:
        logger.warning(f"No features found for user {user_id}")
    
    return all_features, feature_freshness or datetime.utcnow().isoformat()
