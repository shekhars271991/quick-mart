"""
Aerospike Checkpointer Setup for LangGraph

Provides the AerospikeSaver configuration for checkpointing
agent state across workflow steps.
"""

import logging
import os
from typing import Optional

import aerospike
from langgraph.checkpoint.aerospike import AerospikeSaver

logger = logging.getLogger(__name__)

# Singleton instance
_aerospike_saver: Optional[AerospikeSaver] = None
_aerospike_client = None


def get_aerospike_saver(
    client: Optional[aerospike.Client] = None,
    namespace: str = None,
    host: str = None,
    port: int = None,
) -> AerospikeSaver:
    """
    Get or create an AerospikeSaver instance for LangGraph checkpointing.
    
    Args:
        client: Optional existing Aerospike client to reuse
        namespace: Aerospike namespace (defaults to env var or 'churnprediction')
        host: Aerospike host (defaults to env var or 'localhost')
        port: Aerospike port (defaults to env var or 3000)
        
    Returns:
        Configured AerospikeSaver instance
    """
    global _aerospike_saver, _aerospike_client
    
    if _aerospike_saver is not None:
        return _aerospike_saver
    
    # Get configuration from environment or parameters
    namespace = namespace or os.getenv("AEROSPIKE_NAMESPACE", "churnprediction")
    host = host or os.getenv("AEROSPIKE_HOST", "localhost")
    port = port or int(os.getenv("AEROSPIKE_PORT", "3000"))
    
    # Reuse provided client or create new one
    if client is not None:
        _aerospike_client = client
        logger.info("Reusing existing Aerospike client for checkpointer")
    else:
        config = {
            "hosts": [(host, port)],
            "policies": {
                "write": {"key": aerospike.POLICY_KEY_SEND}
            }
        }
        try:
            _aerospike_client = aerospike.client(config).connect()
            logger.info(f"Created new Aerospike client for checkpointer at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to Aerospike for checkpointer: {e}")
            raise
    
    # Create the AerospikeSaver
    _aerospike_saver = AerospikeSaver(
        client=_aerospike_client,
        namespace=namespace
    )
    
    logger.info(f"AerospikeSaver initialized with namespace: {namespace}")
    return _aerospike_saver


def reset_checkpointer():
    """Reset the checkpointer singleton (useful for testing)."""
    global _aerospike_saver, _aerospike_client
    _aerospike_saver = None
    # Don't close the client if it was shared
    _aerospike_client = None


def get_checkpoint_config(user_id: str, checkpoint_ns: str = "churn_prediction") -> dict:
    """
    Generate a checkpoint configuration for a specific user workflow.
    
    Args:
        user_id: The user identifier to use as thread_id
        checkpoint_ns: Namespace for the checkpoint (default: churn_prediction)
        
    Returns:
        Configuration dict for LangGraph invoke
    """
    return {
        "configurable": {
            "thread_id": f"predict_{user_id}",
            "checkpoint_ns": checkpoint_ns
        }
    }

