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

__all__ = [
    # Graph and workflow
    "create_churn_prediction_graph",
    "run_agent_prediction",
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

