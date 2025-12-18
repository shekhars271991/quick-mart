"""
LangGraph Definition for Churn Prediction Agent

Defines the workflow graph that orchestrates the churn prediction
and nudge generation process using LangGraph.
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from .state import AgentState, create_initial_state
from .tools import (
    retrieve_user_features_tool,
    predict_churn_tool,
    decide_nudge_tool,
    generate_nudge_message_tool,
    send_nudge_tool,
)
from .checkpointer import get_aerospike_saver, get_checkpoint_config

logger = logging.getLogger(__name__)


# Node Functions

def retrieve_features_node(state: AgentState) -> AgentState:
    """Node: Retrieve user features from the feature store."""
    user_id = state["user_id"]
    
    logger.info(f"[Agent] Retrieving features for user {user_id}")
    
    try:
        result = retrieve_user_features_tool.invoke({"user_id": user_id})
        features = result.get("features", {})
        freshness = result.get("freshness", "")
        
        state["user_features"] = features
        state["feature_freshness"] = freshness
        state["current_step"] = "features_retrieved"
        
        # Add reasoning to messages
        feature_summary = f"Retrieved {len(features)} features for user {user_id}"
        state["messages"].append(
            AIMessage(content=f"[Feature Retrieval] {feature_summary}. Feature freshness: {freshness}")
        )
        
        logger.info(f"[Agent] {feature_summary}")
        
    except Exception as e:
        state["error"] = f"Feature retrieval failed: {str(e)}"
        state["current_step"] = "error"
        logger.error(f"[Agent] Feature retrieval error: {e}")
    
    return state


def predict_churn_node(state: AgentState) -> AgentState:
    """Node: Predict churn probability based on user features."""
    user_id = state["user_id"]
    features = state.get("user_features", {})
    
    logger.info(f"[Agent] Predicting churn for user {user_id}")
    
    if not features:
        state["error"] = "No features available for prediction"
        state["current_step"] = "error"
        return state
    
    try:
        prediction = predict_churn_tool.invoke({"user_features": features})
        
        if "error" in prediction:
            state["error"] = prediction["error"]
            state["current_step"] = "error"
            return state
        
        state["churn_prediction"] = {
            "churn_probability": prediction["churn_probability"],
            "risk_segment": prediction["risk_segment"],
            "churn_reasons": prediction["churn_reasons"],
            "confidence_score": prediction["confidence_score"]
        }
        state["current_step"] = "churn_predicted"
        
        # Add reasoning to messages
        risk_msg = (
            f"[Churn Prediction] User {user_id}: "
            f"{prediction['churn_probability']:.1%} churn probability, "
            f"segment: {prediction['risk_segment']}, "
            f"reasons: {', '.join(prediction['churn_reasons'][:3])}"
        )
        state["messages"].append(AIMessage(content=risk_msg))
        
        logger.info(f"[Agent] {risk_msg}")
        
    except Exception as e:
        state["error"] = f"Churn prediction failed: {str(e)}"
        state["current_step"] = "error"
        logger.error(f"[Agent] Prediction error: {e}")
    
    return state


def decide_nudge_node(state: AgentState) -> AgentState:
    """Node: Decide whether and what type of nudge to send."""
    user_id = state["user_id"]
    prediction = state.get("churn_prediction")
    
    logger.info(f"[Agent] Deciding nudge for user {user_id}")
    
    if not prediction:
        state["error"] = "No prediction available for nudge decision"
        state["current_step"] = "error"
        return state
    
    try:
        decision = decide_nudge_tool.invoke({
            "user_id": user_id,
            "churn_probability": prediction["churn_probability"],
            "risk_segment": prediction["risk_segment"],
            "churn_reasons": prediction["churn_reasons"]
        })
        
        state["nudge_decision"] = {
            "should_nudge": decision["should_nudge"],
            "nudge_type": decision["nudge_type"],
            "priority": decision["priority"],
            "rule_matched": decision.get("rule_matched")
        }
        state["current_step"] = "nudge_decided"
        
        # Add reasoning to messages
        if decision["should_nudge"]:
            decision_msg = (
                f"[Nudge Decision] Will send {decision['nudge_type']} nudge "
                f"with {decision['priority']} priority. "
                f"Reasoning: {decision.get('reasoning', 'N/A')}"
            )
        else:
            decision_msg = f"[Nudge Decision] No nudge needed for user {user_id}"
        
        state["messages"].append(AIMessage(content=decision_msg))
        logger.info(f"[Agent] {decision_msg}")
        
    except Exception as e:
        state["error"] = f"Nudge decision failed: {str(e)}"
        state["current_step"] = "error"
        logger.error(f"[Agent] Decision error: {e}")
    
    return state


async def generate_nudge_node(state: AgentState) -> AgentState:
    """Node: Generate personalized nudge message."""
    user_id = state["user_id"]
    decision = state.get("nudge_decision")
    prediction = state.get("churn_prediction")
    features = state.get("user_features", {})
    
    logger.info(f"[Agent] Generating nudge message for user {user_id}")
    
    if not decision or not decision.get("should_nudge"):
        state["current_step"] = "completed"
        state["completed"] = True
        state["messages"].append(
            AIMessage(content="[Complete] No nudge generation needed.")
        )
        return state
    
    try:
        generated = await generate_nudge_message_tool.ainvoke({
            "user_id": user_id,
            "nudge_type": decision["nudge_type"],
            "churn_probability": prediction["churn_probability"],
            "churn_reasons": prediction["churn_reasons"],
            "user_features": features
        })
        
        state["generated_nudge"] = {
            "message": generated["message"],
            "channel": generated["channel"],
            "coupon_code": generated.get("coupon_code"),
            "discount_value": generated.get("discount_value"),
            "discount_type": generated.get("discount_type")
        }
        state["current_step"] = "nudge_generated"
        
        # Add to messages
        gen_msg = f"[Nudge Generated] Channel: {generated['channel']}, Message: {generated['message'][:100]}..."
        if generated.get("coupon_code"):
            gen_msg += f" Coupon: {generated['coupon_code']} ({generated['discount_value']}% off)"
        
        state["messages"].append(AIMessage(content=gen_msg))
        logger.info(f"[Agent] Nudge generated for user {user_id}")
        
    except Exception as e:
        state["error"] = f"Nudge generation failed: {str(e)}"
        state["current_step"] = "error"
        logger.error(f"[Agent] Generation error: {e}")
    
    return state


async def send_nudge_node(state: AgentState) -> AgentState:
    """Node: Send the generated nudge to the user."""
    user_id = state["user_id"]
    nudge = state.get("generated_nudge")
    
    logger.info(f"[Agent] Sending nudge to user {user_id}")
    
    if not nudge:
        state["current_step"] = "completed"
        state["completed"] = True
        return state
    
    try:
        result = await send_nudge_tool.ainvoke({
            "user_id": user_id,
            "message": nudge["message"],
            "channel": nudge["channel"],
            "nudge_type": state["nudge_decision"]["nudge_type"],
            "coupon_code": nudge.get("coupon_code"),
            "discount_value": nudge.get("discount_value"),
            "discount_type": nudge.get("discount_type")
        })
        
        state["current_step"] = "completed"
        state["completed"] = True
        
        # Final message
        final_msg = f"[Complete] Nudge {result['nudge_id']} sent via {result['channel']}"
        if result.get("coupon_created"):
            final_msg += " with coupon"
        
        state["messages"].append(AIMessage(content=final_msg))
        logger.info(f"[Agent] {final_msg}")
        
    except Exception as e:
        state["error"] = f"Nudge sending failed: {str(e)}"
        state["current_step"] = "error"
        logger.error(f"[Agent] Send error: {e}")
    
    return state


def error_handler_node(state: AgentState) -> AgentState:
    """Node: Handle errors in the workflow."""
    error = state.get("error", "Unknown error")
    logger.error(f"[Agent] Workflow error: {error}")
    
    state["messages"].append(
        AIMessage(content=f"[Error] Workflow failed: {error}")
    )
    state["completed"] = True
    return state


# Routing Functions

def should_continue_after_features(state: AgentState) -> str:
    """Route after feature retrieval."""
    if state.get("error"):
        return "error"
    if not state.get("user_features"):
        return "error"
    return "predict"


def should_continue_after_prediction(state: AgentState) -> str:
    """Route after churn prediction."""
    if state.get("error"):
        return "error"
    return "decide"


def should_continue_after_decision(state: AgentState) -> str:
    """Route after nudge decision."""
    if state.get("error"):
        return "error"
    
    decision = state.get("nudge_decision", {})
    if not decision.get("should_nudge"):
        return "end"
    return "generate"


def should_continue_after_generation(state: AgentState) -> str:
    """Route after nudge generation."""
    if state.get("error"):
        return "error"
    return "send"


# Graph Builder

def create_churn_prediction_graph(checkpointer=None) -> StateGraph:
    """
    Create the LangGraph for churn prediction workflow.
    
    Args:
        checkpointer: Optional checkpointer for state persistence
        
    Returns:
        Compiled StateGraph
    """
    builder = StateGraph(AgentState)
    
    # Add nodes
    builder.add_node("retrieve_features", retrieve_features_node)
    builder.add_node("predict_churn", predict_churn_node)
    builder.add_node("decide_nudge", decide_nudge_node)
    builder.add_node("generate_nudge", generate_nudge_node)
    builder.add_node("send_nudge", send_nudge_node)
    builder.add_node("error_handler", error_handler_node)
    
    # Set entry point
    builder.set_entry_point("retrieve_features")
    
    # Add conditional edges
    builder.add_conditional_edges(
        "retrieve_features",
        should_continue_after_features,
        {
            "predict": "predict_churn",
            "error": "error_handler"
        }
    )
    
    builder.add_conditional_edges(
        "predict_churn",
        should_continue_after_prediction,
        {
            "decide": "decide_nudge",
            "error": "error_handler"
        }
    )
    
    builder.add_conditional_edges(
        "decide_nudge",
        should_continue_after_decision,
        {
            "generate": "generate_nudge",
            "end": END,
            "error": "error_handler"
        }
    )
    
    builder.add_conditional_edges(
        "generate_nudge",
        should_continue_after_generation,
        {
            "send": "send_nudge",
            "error": "error_handler"
        }
    )
    
    # Terminal edges
    builder.add_edge("send_nudge", END)
    builder.add_edge("error_handler", END)
    
    # Compile with checkpointer
    if checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
    else:
        graph = builder.compile()
    
    logger.info("Churn prediction graph compiled")
    return graph


async def run_agent_prediction(
    user_id: str,
    aerospike_client=None,
    use_checkpointer: bool = True
) -> Dict[str, Any]:
    """
    Run the agent-based churn prediction workflow.
    
    Args:
        user_id: The user to predict churn for
        aerospike_client: Optional Aerospike client for checkpointing
        use_checkpointer: Whether to use checkpointing
        
    Returns:
        Dictionary containing prediction results and nudge information
    """
    # Get or create checkpointer (using local checkpointer with async support)
    checkpointer = None
    if use_checkpointer and aerospike_client:
        try:
            checkpointer = get_aerospike_saver(client=aerospike_client)
            logger.info("Aerospike checkpointer enabled with async support")
        except Exception as e:
            logger.warning(f"Could not create checkpointer: {e}")
    
    # Create the graph
    graph = create_churn_prediction_graph(checkpointer=checkpointer)
    
    # Create initial state
    initial_state = create_initial_state(user_id)
    initial_state["messages"].append(
        HumanMessage(content=f"Predict churn and generate nudge for user {user_id}")
    )
    
    # Run the graph
    config = get_checkpoint_config(user_id) if use_checkpointer else {}
    
    try:
        result = await graph.ainvoke(initial_state, config=config)
        
        # Build response
        response = {
            "user_id": user_id,
            "workflow_completed": result.get("completed", False),
            "current_step": result.get("current_step"),
            "error": result.get("error"),
            "feature_freshness": result.get("feature_freshness"),
            "agent_reasoning": [msg.content for msg in result.get("messages", [])],
        }
        
        # Add prediction results if available
        if result.get("churn_prediction"):
            response["churn_prediction"] = result["churn_prediction"]
        
        # Add nudge info if available
        if result.get("nudge_decision"):
            response["nudge_decision"] = result["nudge_decision"]
        
        if result.get("generated_nudge"):
            response["generated_nudge"] = result["generated_nudge"]
        
        return response
        
    except Exception as e:
        import traceback
        error_detail = str(e) if str(e) else f"{type(e).__name__}: {repr(e)}"
        logger.error(f"Agent workflow failed for user {user_id}: {error_detail}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "user_id": user_id,
            "workflow_completed": False,
            "error": error_detail
        }

