flowchart TD
    %% ═══════════════════════════════════════════════════════════════
    %% Churn Prediction Agent - LangGraph Workflow
    %% Checkpointed to Aerospike at each node transition
    %% ═══════════════════════════════════════════════════════════════

    %% Entry Point
    subgraph init["🚀 Initialization"]
        Start(["▶ run_agent_prediction"])
        InitState["create_initial_state(user_id)<br/>━━━━━━━━━━━━━━━━━━<br/>current_step: 'start'<br/>completed: false"]
    end
    Start --> InitState --> retrieve_features

    %% ─────────────────────────────────────────────────────────────────
    %% MAIN WORKFLOW NODES
    %% ─────────────────────────────────────────────────────────────────
    
    subgraph main["📊 Main Workflow"]
        direction TB
        
        %% Node 1: Retrieve Features
        retrieve_features["🔍 <b>retrieve_features_node</b><br/>━━━━━━━━━━━━━━━━━━━━<br/>• Call retrieve_user_features_tool<br/>• Fetch from feature store<br/>━━━━━━━━━━━━━━━━━━━━<br/>State Updates:<br/>→ user_features<br/>→ feature_freshness<br/>→ current_step: 'features_retrieved'"]
        
        %% Node 2: Predict Churn
        predict_churn["🤖 <b>predict_churn_node</b><br/>━━━━━━━━━━━━━━━━━━━━<br/>• Call predict_churn_tool<br/>• ML model inference<br/>━━━━━━━━━━━━━━━━━━━━<br/>State Updates:<br/>→ churn_prediction.churn_probability<br/>→ churn_prediction.risk_segment<br/>→ churn_prediction.churn_reasons<br/>→ churn_prediction.confidence_score<br/>→ current_step: 'churn_predicted'"]
        
        %% Node 3: Decide Nudge
        decide_nudge{"💡 <b>decide_nudge_node</b><br/>━━━━━━━━━━━━━━━━━━<br/>• Call decide_nudge_tool<br/>• Rule-based decision<br/>━━━━━━━━━━━━━━━━━━<br/>State Updates:<br/>→ nudge_decision.should_nudge<br/>→ nudge_decision.nudge_type<br/>→ nudge_decision.priority<br/>→ nudge_decision.rule_matched<br/>→ current_step: 'nudge_decided'"}
        
        %% Node 4: Generate Nudge (async)
        generate_nudge["✨ <b>generate_nudge_node</b> 🔄<br/>━━━━━━━━━━━━━━━━━━━━<br/>• Call generate_nudge_message_tool<br/>• LLM-powered message generation<br/>• Coupon code selection<br/>━━━━━━━━━━━━━━━━━━━━<br/>State Updates:<br/>→ generated_nudge.message<br/>→ generated_nudge.channel<br/>→ generated_nudge.coupon_code<br/>→ generated_nudge.discount_value<br/>→ current_step: 'nudge_generated'"]
        
        %% Node 5: Send Nudge (async)
        send_nudge["📤 <b>send_nudge_node</b> 🔄<br/>━━━━━━━━━━━━━━━━━━<br/>• Call send_nudge_tool<br/>• Dispatch via channel<br/>• Register coupon if present<br/>━━━━━━━━━━━━━━━━━━<br/>State Updates:<br/>→ current_step: 'completed'<br/>→ completed: true"]
    end

    %% ─────────────────────────────────────────────────────────────────
    %% ROUTING LOGIC (Conditional Edges)
    %% ─────────────────────────────────────────────────────────────────
    
    %% Routing after features
    retrieve_features -->|"should_continue_after_features<br/>✓ features present"| predict_churn
    retrieve_features -->|"✗ error OR<br/>no features"| error_handler

    %% Routing after prediction
    predict_churn -->|"should_continue_after_prediction<br/>✓ prediction ok"| decide_nudge
    predict_churn -->|"✗ error"| error_handler

    %% Routing after decision
    decide_nudge -->|"should_continue_after_decision<br/>should_nudge = true"| generate_nudge
    decide_nudge -->|"should_nudge = false"| End_NoNudge
    decide_nudge -->|"✗ error"| error_handler

    %% Routing after generation
    generate_nudge -->|"should_continue_after_generation<br/>✓ message generated"| send_nudge
    generate_nudge -->|"✗ error"| error_handler

    %% Terminal edge from send
    send_nudge --> End_Success

    %% ─────────────────────────────────────────────────────────────────
    %% TERMINAL STATES
    %% ─────────────────────────────────────────────────────────────────
    
    subgraph terminals["🏁 Terminal States"]
        End_Success([" ✅ END<br/>Nudge Sent<br/>━━━━━━━━━━<br/>completed: true"])
        End_NoNudge(["⏭️ END<br/>No Nudge Required<br/>━━━━━━━━━━━━<br/>Low churn risk"])
        End_Error(["❌ END<br/>Workflow Failed<br/>━━━━━━━━━━━━<br/>error captured"])
    end

    %% ─────────────────────────────────────────────────────────────────
    %% ERROR HANDLING
    %% ─────────────────────────────────────────────────────────────────
    
    subgraph errors["⚠️ Error Handling"]
        error_handler["🔴 <b>error_handler_node</b><br/>━━━━━━━━━━━━━━━━━━<br/>• Log error details<br/>• Append error message to state<br/>• Set completed = true<br/>━━━━━━━━━━━━━━━━━━<br/>State Updates:<br/>→ messages += error info<br/>→ completed: true"]
    end
    
    error_handler --> End_Error

    %% ═══════════════════════════════════════════════════════════════
    %% STYLING
    %% ═══════════════════════════════════════════════════════════════
    
    %% Node colors
    style Start fill:#4CAF50,stroke:#2E7D32,color:#fff
    style InitState fill:#E8F5E9,stroke:#4CAF50,color:#1B5E20
    
    style retrieve_features fill:#2196F3,stroke:#1565C0,color:#fff
    style predict_churn fill:#9C27B0,stroke:#6A1B9A,color:#fff
    style decide_nudge fill:#FF9800,stroke:#E65100,color:#fff
    style generate_nudge fill:#00BCD4,stroke:#00838F,color:#fff
    style send_nudge fill:#8BC34A,stroke:#558B2F,color:#fff
    
    style error_handler fill:#f44336,stroke:#c62828,color:#fff
    
    style End_Success fill:#4CAF50,stroke:#2E7D32,color:#fff
    style End_NoNudge fill:#9E9E9E,stroke:#616161,color:#fff
    style End_Error fill:#f44336,stroke:#c62828,color:#fff
    
    %% Subgraph styling
    style init fill:#E8F5E9,stroke:#4CAF50
    style main fill:#E3F2FD,stroke:#2196F3
    style terminals fill:#F5F5F5,stroke:#9E9E9E
    style errors fill:#FFEBEE,stroke:#f44336
