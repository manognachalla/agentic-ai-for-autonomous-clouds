from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Azure Agentic Cloud API",
    description="AI-powered autonomous cloud management for Azure",
    version="1.0.0"
)

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

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "azure-agent-system"}

@app.get("/ready")
async def readiness_check():
    return {"status": "ready"}

@app.post("/query", response_model=AgentResponse)
async def process_query(request: QueryRequest):
    """Process natural language queries about Azure resources"""
    try:
        from main import AIOrchestrator
        
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        openai_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        openai_key = os.getenv("AZURE_OPENAI_KEY")
        resource_group = request.resource_group or os.getenv("AZURE_RESOURCE_GROUP")
        
        orchestrator = AIOrchestrator(subscription_id, openai_endpoint, openai_key)
        results = orchestrator.process_request(request.query, resource_group)
        
        return AgentResponse(
            status="success",
            results=results
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize/resources", response_model=AgentResponse)
async def optimize_resources(request: OptimizationRequest, background_tasks: BackgroundTasks):
    """Optimize Azure resources in a resource group"""
    try:
        from main import ResourceOptimizationAgent
        
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

@app.post("/analyze/costs")
async def analyze_costs(request: OptimizationRequest):
    """Analyze costs for a resource group"""
    try:
        from main import CostManagementAgent
        
        subscription_id = os.getenv("AZURE_SUBSCRIPTION_ID")
        agent = CostManagementAgent(subscription_id)
        
        costs = agent.get_resource_costs(request.resource_group)
        recommendations = agent.generate_savings_recommendations(request.resource_group)
        
        return AgentResponse(
            status="success",
            results={"costs": costs},
            recommendations=recommendations
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/check/security")
async def check_security(request: OptimizationRequest):
    """Check security posture of resources"""
    try:
        from main import SecurityComplianceAgent
        
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