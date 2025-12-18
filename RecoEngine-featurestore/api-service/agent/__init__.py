"""
LangGraph Agent for Churn Prediction and Nudge Generation

This module provides an AI agent-based approach to the churn prediction
and nudge generation workflow using LangGraph with Aerospike checkpointing.

Compatible with:
- LangGraph 1.0+
- langgraph-checkpoint 3.0+
- langgraph-checkpoint-aerospike
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
from .state import AgentState
from .tools import (
    retrieve_user_features_tool,
    predict_churn_tool,
    decide_nudge_tool,
    generate_nudge_message_tool,
    send_nudge_tool,
    configure_tools,
)

__all__ = [
    "create_churn_prediction_graph",
    "run_agent_prediction",
    "get_aerospike_saver",
    "AgentState",
    "retrieve_user_features_tool",
    "predict_churn_tool",
    "decide_nudge_tool",
    "generate_nudge_message_tool",
    "send_nudge_tool",
    "configure_tools",
]

