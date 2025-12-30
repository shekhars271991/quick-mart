"""
LangGraph Agent for Churn Prediction and Nudge Generation

This module provides an AI agent-based approach to the churn prediction
and nudge generation workflow using LangGraph with Aerospike checkpointing
and store for feature retrieval.

Compatible with:
- LangGraph 1.0+
- langgraph-checkpoint 3.0+
- langgraph-checkpoint-aerospike
- langgraph-store-aerospike
- Python 3.10+
"""

import sys

# Version check
if sys.version_info < (3, 10):
    raise ImportError(
        f"Agent module requires Python 3.10+, but you have Python {sys.version_info.major}.{sys.version_info.minor}. "
        "Please upgrade Python or disable agent flow with USE_AGENT_FLOW=false"
    )

from .graph import create_churn_prediction_graph, run_agent_prediction
from .checkpointer import get_aerospike_saver
from .store_helper import (
    get_aerospike_store,
    store_user_features,
    store_user_features_async,
    retrieve_all_user_features,
    retrieve_all_user_features_async,
)
from .state import AgentState
from .tools import (
    predict_churn_tool,
    decide_nudge_tool,
    generate_nudge_message_tool,
    send_nudge_tool,
    configure_tools,
)
# Recommendations graph
from .reco_state import RecommendationState, create_initial_reco_state, DISCOUNT_TIERS
from .reco_graph import create_recommendations_graph, run_recommendations_workflow
from .product_indexer import (
    index_products_in_store,
    search_similar_products,
    check_products_indexed,
)
# Graph logging
from .graph_logger import setup_graph_loggers, get_churn_logger, get_reco_logger

__all__ = [
    # Churn Graph and workflow
    "create_churn_prediction_graph",
    "run_agent_prediction",
    # Recommendations Graph and workflow
    "create_recommendations_graph",
    "run_recommendations_workflow",
    "RecommendationState",
    "create_initial_reco_state",
    "DISCOUNT_TIERS",
    # Product indexing
    "index_products_in_store",
    "search_similar_products",
    "check_products_indexed",
    # Checkpointer
    "get_aerospike_saver",
    # Store
    "get_aerospike_store",
    "store_user_features",
    "store_user_features_async",
    "retrieve_all_user_features",
    "retrieve_all_user_features_async",
    # State
    "AgentState",
    # Tools
    "predict_churn_tool",
    "decide_nudge_tool",
    "generate_nudge_message_tool",
    "send_nudge_tool",
    "configure_tools",
]

