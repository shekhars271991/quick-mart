# LangGraph Agent for Churn Prediction

This module provides an AI agent-based approach to the churn prediction and nudge generation workflow using **LangGraph** with **Aerospike checkpointing**.

## Overview

The agent orchestrates the entire churn prediction pipeline through a series of nodes, with state being checkpointed to Aerospike after each step. This enables:

- **Workflow resumption** - If a step fails, the workflow can resume from the last checkpoint
- **Debugging** - Complete state history for troubleshooting
- **Auditability** - Full trace of agent reasoning and decisions

## Agent Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        CHURN PREDICTION AGENT WORKFLOW                       │
└─────────────────────────────────────────────────────────────────────────────┘

                              ┌──────────────┐
                              │   START      │
                              │  /predict/   │
                              │  {user_id}   │
                              └──────┬───────┘
                                     │
                                     ▼
                    ┌────────────────────────────────┐
                    │     1. RETRIEVE FEATURES       │
                    │ ─────────────────────────────  │
                    │ • Query Aerospike feature store│
                    │ • Collect: profile, behavior,  │
                    │   transactional, engagement,   │
                    │   support, realtime features   │
                    │ • Track feature freshness      │
                    └────────────────┬───────────────┘
                                     │
                         ┌───────────┴───────────┐
                         │                       │
                    [features found]        [no features]
                         │                       │
                         ▼                       ▼
         ┌───────────────────────────┐    ┌─────────────┐
         │   2. PREDICT CHURN        │    │   ERROR     │
         │ ───────────────────────── │    │   HANDLER   │
         │ • Run XGBoost ML model    │    └──────┬──────┘
         │ • Calculate probability   │           │
         │ • Determine risk segment  │           ▼
         │ • Identify churn reasons  │         [END]
         └───────────────┬───────────┘
                         │
                         ▼
         ┌───────────────────────────┐
         │    3. DECIDE NUDGE        │
         │ ───────────────────────── │
         │ • Evaluate risk threshold │
         │ • Match nudge rules       │
         │ • Determine nudge type:   │
         │   - cart_recovery         │
         │   - re_engagement         │
         │   - retention_offer       │
         │   - win_back              │
         │   - engagement_boost      │
         │ • Set priority level      │
         └───────────────┬───────────┘
                         │
              ┌──────────┴──────────┐
              │                     │
         [should_nudge]       [no nudge needed]
              │                     │
              ▼                     ▼
┌─────────────────────────┐       [END]
│  4. GENERATE NUDGE      │
│ ─────────────────────── │
│ • Call Gemini LLM for   │
│   personalized message  │
│ • Consider user context:│
│   - loyalty tier        │
│   - purchase history    │
│   - churn reasons       │
│ • Determine if coupon   │
│   should be included    │
│ • Select delivery       │
│   channel               │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│    5. SEND NUDGE        │
│ ─────────────────────── │
│ • Store nudge record    │
│ • Create coupon if      │
│   applicable            │
│ • Track in Aerospike    │
│ • Return nudge_id       │
└───────────┬─────────────┘
            │
            ▼
         [END]


                    ┌─────────────────────────────────────┐
                    │        AEROSPIKE CHECKPOINTING      │
                    │ ─────────────────────────────────── │
                    │  State saved after each node:       │
                    │  • messages (agent reasoning)       │
                    │  • user_features                    │
                    │  • churn_prediction                 │
                    │  • nudge_decision                   │
                    │  • generated_nudge                  │
                    │  • current_step                     │
                    │  • error (if any)                   │
                    └─────────────────────────────────────┘
```

## LangGraph Technical Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────────────┐
│                              StateGraph(AgentState)                                      │
├─────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                          │
│   ENTRY_POINT                                                                            │
│       │                                                                                  │
│       ▼                                                                                  │
│  ┌─────────────────────┐                                                                 │
│  │  retrieve_features  │ ◄─── Node: retrieve_features_node                               │
│  │                     │      Tool: retrieve_user_features_tool                          │
│  │  Queries Aerospike  │      - get_profile_features()                                   │
│  │  for user features  │      - get_behavioral_features()                                │
│  └──────────┬──────────┘      - get_transactional_features()                             │
│             │                 - get_engagement_features()                                │
│             ▼                 - get_support_features()                                   │
│  ┌──────────────────────┐     - get_realtime_features()                                  │
│  │ should_continue_     │                                                                │
│  │ after_features       │ ◄─── Conditional Edge Function                                 │
│  │                      │      Returns: "predict" | "error"                              │
│  │ if error → "error"   │      Condition: state.get("error") is None                     │
│  │ else → "predict"     │                                                                │
│  └──────────┬───────────┘                                                                │
│             │                                                                            │
│     ┌───────┴───────┐                                                                    │
│     │               │                                                                    │
│     ▼               ▼                                                                    │
│  "predict"       "error"                                                                 │
│     │               │                                                                    │
│     ▼               │                                                                    │
│  ┌─────────────────────┐                                                                 │
│  │   predict_churn     │ ◄─── Node: predict_churn_node                                   │
│  │                     │      Tool: predict_churn_tool                                   │
│  │  XGBoost ML Model   │      - ChurnPredictor.predict()                                 │
│  │  churn_probability  │      - risk_segment: low/medium/high/critical                   │
│  │  risk_segment       │      - confidence_score                                         │
│  │  churn_reasons      │      - churn_reasons[]                                          │
│  └──────────┬──────────┘                                                                 │
│             │                                                                            │
│             ▼                                                                            │
│  ┌──────────────────────┐                                                                │
│  │ should_continue_     │ ◄─── Conditional Edge Function                                 │
│  │ after_prediction     │      Returns: "decide" | "error"                               │
│  │                      │      Condition: state.get("error") is None                     │
│  │ if error → "error"   │                                                                │
│  │ else → "decide"      │                                                                │
│  └──────────┬───────────┘                                                                │
│             │                                                                            │
│     ┌───────┴───────┐                                                                    │
│     │               │                                                                    │
│     ▼               │                                                                    │
│  "decide"           │                                                                    │
│     │               │                                                                    │
│     ▼               │                                                                    │
│  ┌─────────────────────┐                                                                 │
│  │   decide_nudge      │ ◄─── Node: decide_nudge_node                                    │
│  │                     │      Tool: decide_nudge_tool                                    │
│  │  NudgeEngine rules  │      - NudgeEngine.select_nudge_rule()                          │
│  │  should_nudge: bool │      - evaluate_user_state()                                    │
│  │  nudge_type: str    │      Types: cart_recovery, re_engagement,                       │
│  │  priority: str      │              retention_offer, win_back                          │
│  └──────────┬──────────┘      Priority: low, normal, high, urgent                        │
│             │                                                                            │
│             ▼                                                                            │
│  ┌──────────────────────┐                                                                │
│  │ should_continue_     │ ◄─── Conditional Edge Function                                 │
│  │ after_decision       │      Returns: "generate" | "end" | "error"                     │
│  │                      │      Condition: nudge_decision.should_nudge                    │
│  │ if error → "error"   │                                                                │
│  │ if !nudge → "end"    │                                                                │
│  │ else → "generate"    │                                                                │
│  └──────────┬───────────┘                                                                │
│             │                                                                            │
│     ┌───────┼───────┬──────────────────────────────────────────────┐                     │
│     │       │       │                                              │                     │
│     ▼       ▼       ▼                                              │                     │
│ "generate" "end"  "error"                                          │                     │
│     │       │       │                                              │                     │
│     │       ▼       │                                              │                     │
│     │     [END]     │                                              │                     │
│     │               │                                              │                     │
│     ▼               │                                              │                     │
│  ┌─────────────────────┐                                           │                     │
│  │  generate_nudge     │ ◄─── Node: generate_nudge_node            │                     │
│  │                     │      Tool: generate_nudge_message_tool    │                     │
│  │  Gemini LLM API     │      - Google Generative AI (Gemini)      │                     │
│  │  Personalized msg   │      - User context: name, tier, history  │                     │
│  │  Channel selection  │      Channels: push, email, sms, in_app   │                     │
│  │  Coupon decision    │      - Discount: percentage/fixed         │                     │
│  └──────────┬──────────┘                                           │                     │
│             │                                                      │                     │
│             ▼                                                      │                     │
│  ┌──────────────────────┐                                          │                     │
│  │ should_continue_     │ ◄─── Conditional Edge Function           │                     │
│  │ after_generation     │      Returns: "send" | "error"           │                     │
│  │                      │      Condition: state.get("error") is None│                    │
│  │ if error → "error"   │                                          │                     │
│  │ else → "send"        │                                          │                     │
│  └──────────┬───────────┘                                          │                     │
│             │                                                      │                     │
│     ┌───────┴───────┐                                              │                     │
│     │               │                                              │                     │
│     ▼               │                                              │                     │
│   "send"            │                                              │                     │
│     │               │                                              │                     │
│     ▼               ▼                                              │                     │
│  ┌─────────────────────┐   ┌─────────────────────┐                 │                     │
│  │    send_nudge       │   │   error_handler     │ ◄───────────────┘                     │
│  │                     │   │                     │                                       │
│  │  Store in Aerospike │   │  Log error          │ ◄─── Node: error_handler_node         │
│  │  Create coupon      │   │  Set error state    │      Captures and logs failures       │
│  │  Track delivery     │   │  Return gracefully  │                                       │
│  └──────────┬──────────┘   └──────────┬──────────┘                                       │
│             │                         │                                                  │
│             ▼                         ▼                                                  │
│          [END] ◄───────────────────[END]                                                 │
│                                                                                          │
└──────────────────────────────────────────────────────────────────────────────────────────┘


 LEGEND:
 ┌─────────────────────────────────────────────────────────────────────────────────────────┐
 │  ┌──────────────┐                                                                       │
 │  │    Node      │  = LangGraph Node (builder.add_node)                                  │
 │  └──────────────┘                                                                       │
 │                                                                                         │
 │  ┌──────────────────┐                                                                   │
 │  │ conditional_edge │  = Conditional Edge Function (builder.add_conditional_edges)      │
 │  └──────────────────┘                                                                   │
 │                                                                                         │
 │      "string"         = Edge routing value                                              │
 │                                                                                         │
 │       [END]           = Terminal state (langgraph.graph.END)                            │
 │                                                                                         │
 │       ◄───            = Tool/Function used by node                                      │
 └─────────────────────────────────────────────────────────────────────────────────────────┘
```

## Node & Tool Reference

| Node | Function | Tool | Description |
|------|----------|------|-------------|
| `retrieve_features` | `retrieve_features_node` | `retrieve_user_features_tool` | Fetches all user features from Aerospike |
| `predict_churn` | `predict_churn_node` | `predict_churn_tool` | Runs XGBoost model for churn probability |
| `decide_nudge` | `decide_nudge_node` | `decide_nudge_tool` | Evaluates rules to determine nudge action |
| `generate_nudge` | `generate_nudge_node` | `generate_nudge_message_tool` | Calls Gemini LLM for personalized message |
| `send_nudge` | `send_nudge_node` | `send_nudge_tool` | Stores nudge record and creates coupons |
| `error_handler` | `error_handler_node` | - | Handles and logs workflow errors |

## Conditional Edge Functions

| Function | Source Node | Possible Routes | Condition |
|----------|-------------|-----------------|-----------|
| `should_continue_after_features` | `retrieve_features` | `predict`, `error` | `error is None` |
| `should_continue_after_prediction` | `predict_churn` | `decide`, `error` | `error is None` |
| `should_continue_after_decision` | `decide_nudge` | `generate`, `end`, `error` | `should_nudge == True` |
| `should_continue_after_generation` | `generate_nudge` | `send`, `error` | `error is None` |

## Terminal Edges

| Source Node | Target |
|-------------|--------|
| `send_nudge` | `END` |
| `error_handler` | `END` |

## Module Structure

```
agent/
├── __init__.py          # Package exports
├── README.md            # This documentation
├── state.py             # TypedDict state definitions
├── tools.py             # Agent tools (feature retrieval, prediction, etc.)
├── graph.py             # LangGraph workflow definition
└── checkpointer.py      # Aerospike checkpointer setup
```

## 🔧 Configuration

### Environment Variable

```bash
# Enable agent flow (in env.config or .env)
USE_AGENT_FLOW=true

# Disable agent flow (default - uses manual step-by-step)
USE_AGENT_FLOW=false
```

### Check Current Mode

```bash
# Via API
curl http://localhost:8001/agent/status

# Response
{
  "agent_flow_enabled": true,
  "flow_mode": "agent",
  "description": "LangGraph agent with Aerospike checkpointing",
  "checkpointer": {
    "type": "AerospikeSaver",
    "namespace": "churnprediction"
  }
}
```

## 🚀 Usage

### Running with Agent Flow

```bash
# Set environment variable
export USE_AGENT_FLOW=true

# Start the service
cd RecoEngine-featurestore
./run.sh local  # or docker-compose up

# Test prediction
curl -X POST http://localhost:8001/predict/user_001
```

### Agent Response Example

```json
{
  "user_id": "user_001",
  "churn_probability": 0.72,
  "risk_segment": "high_risk",
  "churn_reasons": ["CART_ABANDONMENT", "INACTIVITY"],
  "confidence_score": 0.85,
  "features_retrieved": { "...": "..." },
  "feature_freshness": "2025-12-18T10:30:00.000Z",
  "prediction_timestamp": "2025-12-18T10:30:05.000Z",
  "nudges_triggered": [
    {
      "action_type": "cart_recovery",
      "channel": "push_notification",
      "message": "Hey! You left some great items...",
      "coupon_code": "SAVE15_0001",
      "discount_value": 15,
      "discount_type": "percentage",
      "priority": "high"
    }
  ],
  "nudge_rule_matched": "rule_cart_abandon"
}
```

## 🔗 State Definition

```python
class AgentState(TypedDict):
    # LangGraph message history
    messages: Annotated[List[BaseMessage], add_messages]
    
    # User identification
    user_id: str
    
    # Step outputs
    user_features: Optional[UserFeatures]
    feature_freshness: Optional[str]
    churn_prediction: Optional[ChurnPrediction]
    nudge_decision: Optional[NudgeDecision]
    generated_nudge: Optional[GeneratedNudge]
    
    # Workflow metadata
    current_step: str
    error: Optional[str]
    completed: bool
    intermediate: Optional[Dict[str, Any]]
```

## 🛠️ Agent Tools

| Tool | Description |
|------|-------------|
| `retrieve_user_features_tool` | Fetches all feature types from Aerospike |
| `predict_churn_tool` | Runs XGBoost model for churn prediction |
| `decide_nudge_tool` | Determines nudge type and priority |
| `generate_nudge_message_tool` | Uses Gemini LLM for personalized messages |
| `send_nudge_tool` | Stores nudge and creates coupons |

## 📊 Comparison: Manual vs Agent Flow

| Aspect | Manual Flow | Agent Flow |
|--------|-------------|------------|
| **Execution** | Sequential function calls | LangGraph node traversal |
| **State Management** | In-memory only | Checkpointed to Aerospike |
| **Resumability** | No | Yes (from last checkpoint) |
| **Debugging** | Log-based | Full state history |
| **Flexibility** | Fixed pipeline | Conditional routing |
| **Overhead** | Lower | Slightly higher |
| **Best For** | Simple, fast requests | Complex workflows, debugging |

## 🔍 Debugging

### View Agent Reasoning

The agent adds reasoning messages at each step:

```
[Feature Retrieval] Retrieved 15 features for user user_001. Feature freshness: 2025-12-18T10:30:00Z
[Churn Prediction] User user_001: 72.0% churn probability, segment: high_risk, reasons: CART_ABANDONMENT, INACTIVITY
[Nudge Decision] Will send cart_recovery nudge with high priority. Reasoning: User has high_risk with 72.0% churn probability...
[Nudge Generated] Channel: push_notification, Message: Hey! You left some great items...
[Complete] Nudge nudge_abc123def456 sent via push_notification with coupon
```

### Check Checkpoint Data

Checkpoints are stored in Aerospike under the namespace configured (default: `churnprediction`).

## 📦 Dependencies

```
langgraph>=0.2.0
langgraph-checkpoint>=2.0.0
langgraph-checkpoint-aerospike @ git+https://github.com/Aerospike-langgraph/checkpointer.git
langchain-core>=0.1.0
```

## 🔮 Future Enhancements

- [ ] Add human-in-the-loop approval for high-value nudges
- [ ] Implement A/B testing at the nudge generation step
- [ ] Add parallel execution for multi-channel nudge delivery
- [ ] Integrate with external notification services (Twilio, SendGrid)

