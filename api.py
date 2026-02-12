import os
from typing import Optional, List
from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel

# --- New Imports for Orchestrator ---
from agents.orchestrator import OrchestratorAgent, AgentType
from core.llm import get_azure_openai_client

# Assuming your agents are accessible from 'main' or their respective files
# Adjust import paths if you fully separated them into files (e.g., resource_agent.py)
from agents.resource_agent import ResourceOptimizationAgent
from agents.cost_agent import CostManagementAgent
from agents.security_agent import SecurityComplianceAgent

load_dotenv()

# -------------------------------------------------------------------------
# App Definition & Global State
# -------------------------------------------------------------------------
app = FastAPI(
    title="Azure Agentic Cloud API",
    description="AI-powered autonomous cloud management for Azure",
    version="1.1.0"
)

# Global instances
orchestrator: Optional[OrchestratorAgent] = None
agents_registry = {}

@app.on_event("startup")
async def startup_event():
    """Initialize orchestrator and agents on startup to reuse connections"""
    global orchestrator, agents_registry
    
    print("Initializing Azure Agents and LLM...")
    
    try:
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        if not subscription_id:
            print("WARNING: AZURE_SUBSCRIPTION_ID not set.")

        llm_client = get_azure_openai_client()
        
        # Initialize agents once and store in registry
        agents_registry = {
            AgentType.RESOURCE_OPTIMIZATION: ResourceOptimizationAgent(subscription_id),
            AgentType.COST_MANAGEMENT: CostManagementAgent(subscription_id),
            AgentType.SECURITY_COMPLIANCE: SecurityComplianceAgent(subscription_id),
        }
        
        orchestrator = OrchestratorAgent(llm_client, agents_registry)
        print("System initialized successfully.")
        
    except Exception as e:
        print(f"Startup Error: {e}")

# -------------------------------------------------------------------------
# Pydantic Models
# -------------------------------------------------------------------------
class QueryRequest(BaseModel):
    query: str
    resource_group: Optional[str] = None

class OptimizationRequest(BaseModel):
    resource_group: str
    auto_apply: bool = False

class AgentResponse(BaseModel):
    status: str
    results: dict
    recommendations: Optional[List[dict]] = None

# -------------------------------------------------------------------------
# Core Endpoints
# -------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Health check that also reports orchestrator status"""
    return {
        "status": "healthy", 
        "service": "azure-agent-system",
        "orchestrator_initialized": orchestrator is not None
    }

@app.get("/ready")
async def readiness_check():
    return {"status": "ready"}

@app.post("/query")
async def process_query(request: QueryRequest):
    """
    Smart endpoint - automatically routes natural language to appropriate agents
    """
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    
    try:
        result = orchestrator.process_query(
            query=request.query,
            context={
                "resource_group": request.resource_group or os.getenv("AZURE_RESOURCE_GROUP")
            }
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# -------------------------------------------------------------------------
# Legacy / Specific Endpoints (Preserved)
# -------------------------------------------------------------------------

@app.post("/optimize/resources", response_model=AgentResponse)
async def optimize_resources(request: OptimizationRequest, background_tasks: BackgroundTasks):
    """Directly trigger resource optimization agent"""
    try:
        # Reuse global agent if available, else instantiate (fallback)
        if AgentType.RESOURCE_OPTIMIZATION in agents_registry:
            agent = agents_registry[AgentType.RESOURCE_OPTIMIZATION]
        else:
            subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
            agent = ResourceOptimizationAgent(subscription_id)
        
        utilization = agent.analyze_vm_utilization(request.resource_group)
        idle_resources = agent.identify_idle_resources(request.resource_group)
        
        return AgentResponse(
            status="success",
            results={
                "utilization": utilization,
                "idle_resources": idle_resources
            },
            recommendations=[
                {"type": "optimization", "action": "Review idle resources for deletion"},
                {"type": "cost", "action": "Consider resizing underutilized VMs"}
            ]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/costs", response_model=AgentResponse)
async def analyze_costs(request: OptimizationRequest):
    """Directly trigger cost management agent"""
    try:
        if AgentType.COST_MANAGEMENT in agents_registry:
            agent = agents_registry[AgentType.COST_MANAGEMENT]
        else:
            subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
            agent = CostManagementAgent(subscription_id)
        
        costs = agent.get_resource_costs(request.resource_group)
        # Assuming generate_savings_recommendations exists in your agent, or we skip it
        recommendations = [] 
        if hasattr(agent, "generate_savings_recommendations"):
            recommendations = agent.generate_savings_recommendations(request.resource_group)
        
        return AgentResponse(
            status="success",
            results={"costs": costs},
            recommendations=recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/check/security", response_model=AgentResponse)
async def check_security(request: OptimizationRequest):
    """Directly trigger security agent"""
    try:
        if AgentType.SECURITY_COMPLIANCE in agents_registry:
            agent = agents_registry[AgentType.SECURITY_COMPLIANCE]
        else:
            subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
            agent = SecurityComplianceAgent(subscription_id)
        
        issues = agent.check_security_posture(request.resource_group)
        
        return AgentResponse(
            status="success",
            results={"security_issues": issues}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)