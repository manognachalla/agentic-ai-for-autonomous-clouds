import pytest
from orchestrator import OrchestratorAgent, AgentType

def test_intent_detection():
    """Test that orchestrator detects correct intent"""
    # Mock LLM and agents
    orchestrator = create_test_orchestrator()
    
    test_cases = [
        ("show idle VMs", AgentType.RESOURCE_OPTIMIZATION),
        ("how much am I spending", AgentType.COST_MANAGEMENT),
        ("check security", AgentType.SECURITY_COMPLIANCE),
    ]
    
    for query, expected_agent in test_cases:
        plan = orchestrator._create_fallback_plan(query)
        assert any(t.agent_type == expected_agent for t in plan.tasks)

def test_multi_agent_routing():
    """Test queries that require multiple agents"""
    orchestrator = create_test_orchestrator()
    
    query = "find idle resources and calculate cost savings"
    plan = orchestrator._create_fallback_plan(query)
    
    agent_types = {t.agent_type for t in plan.tasks}
    assert AgentType.RESOURCE_OPTIMIZATION in agent_types
    assert AgentType.COST_MANAGEMENT in agent_types