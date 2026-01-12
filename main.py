import os
import json
from datetime import datetime
from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.monitor import MonitorManagementClient
from openai import AzureOpenAI

class BaseAgent:
    def __init__(self, subscription_id, agent_name):
        self.subscription_id = subscription_id
        self.agent_name = agent_name
        self.credential = DefaultAzureCredential()
        self.compute_client = ComputeManagementClient(self.credential, subscription_id)
        self.resource_client = ResourceManagementClient(self.credential, subscription_id)
        self.monitor_client = MonitorManagementClient(self.credential, subscription_id)
        
    def log(self, message):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{self.agent_name}] {message}")

class ResourceOptimizationAgent(BaseAgent):
    def __init__(self, subscription_id):
        super().__init__(subscription_id, "ResourceOptimizer")
        
    def analyze_vm_utilization(self, resource_group):
        self.log("Analyzing VM utilization...")
        vms = self.compute_client.virtual_machines.list(resource_group)
        
        recommendations = []
        for vm in vms:
            self.log(f"Checking VM: {vm.name}")
            vm_info = {
                "name": vm.name,
                "size": vm.hardware_profile.vm_size,
                "location": vm.location
            }
            recommendations.append({
                "vm": vm.name,
                "current_size": vm.hardware_profile.vm_size,
                "recommendation": "Analyze actual metrics",
                "potential_savings": "TBD"
            })
            
        return recommendations
    
    def identify_idle_resources(self, resource_group):
        self.log("Identifying idle resources...")
        idle_resources = []
        vms = self.compute_client.virtual_machines.list(resource_group)
        
        for vm in vms:
            instance_view = self.compute_client.virtual_machines.instance_view(
                resource_group, vm.name
            )
            
            for status in instance_view.statuses:
                if 'PowerState' in status.code:
                    if status.code == 'PowerState/deallocated':
                        idle_resources.append({
                            "name": vm.name,
                            "type": "VM",
                            "status": "Deallocated",
                            "action": "Consider deletion if unused"
                        })
                        
        return idle_resources

class CostManagementAgent(BaseAgent):
    def __init__(self, subscription_id):
        super().__init__(subscription_id, "CostManager")
        
    def get_resource_costs(self, resource_group):
        self.log("Analyzing costs...")
        resources = self.resource_client.resources.list_by_resource_group(
            resource_group
        )
        
        cost_summary = []
        for resource in resources:
            cost_summary.append({
                "name": resource.name,
                "type": resource.type,
                "location": resource.location,
                "estimated_cost": "Use Azure Cost Management API"
            })
            
        return cost_summary
    
    def generate_savings_recommendations(self, resource_group):
        """Generate cost-saving recommendations"""
        self.log("Generating savings recommendations...")
        
        recommendations = [
            {
                "category": "Right-sizing",
                "description": "Review oversized VMs and downsize",
                "priority": "High"
            },
            {
                "category": "Reserved Instances",
                "description": "Purchase reserved instances for steady workloads",
                "priority": "Medium"
            },
            {
                "category": "Storage Optimization",
                "description": "Move infrequently accessed data to cool/archive tiers",
                "priority": "Medium"
            }
        ]
        
        return recommendations

class SecurityComplianceAgent(BaseAgent):
    def __init__(self, subscription_id):
        super().__init__(subscription_id, "SecurityCompliance")
        
    def check_security_posture(self, resource_group):
        self.log("Checking security posture...")
        
        issues = []
        vms = self.compute_client.virtual_machines.list(resource_group)
        
        for vm in vms:
            security_checks = {
                "vm": vm.name,
                "checks": [
                    "Network Security Groups configured",
                    "Disk encryption enabled",
                    "Azure AD authentication",
                    "Patch management status"
                ],
                "status": "Review required"
            }
            issues.append(security_checks)
            
        return issues

class AIOrchestrator:
    
    def __init__(self, subscription_id, azure_openai_endpoint, azure_openai_key):
        self.subscription_id = subscription_id
        self.resource_agent = ResourceOptimizationAgent(subscription_id)
        self.cost_agent = CostManagementAgent(subscription_id)
        self.security_agent = SecurityComplianceAgent(subscription_id)
        self.llm_client = AzureOpenAI(
            azure_endpoint=azure_openai_endpoint,
            api_key=azure_openai_key,
            api_version="2024-02-15-preview"
        )
        
    def process_request(self, user_query, resource_group):
        print(f"\n=== Processing Request: {user_query} ===\n")
        system_prompt = """You are an AI assistant managing Azure cloud resources.
        Analyze the user's request and determine which agents to invoke:
        - ResourceOptimizationAgent: VM optimization, resource utilization
        - CostManagementAgent: Cost analysis, savings recommendations
        - SecurityComplianceAgent: Security checks, compliance
        
        Return a JSON with: {"agents": ["agent_name"], "action": "description"}
        """
        
        response = self.llm_client.chat.completions.create(
            model="gpt-4", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ]
        )
        try:
            decision = json.loads(response.choices[0].message.content)
            results = self.execute_agents(decision, resource_group)
            return results
        except Exception as e:
            return {"error": str(e)}
            
    def execute_agents(self, decision, resource_group):
        results = {}
        
        for agent_name in decision.get("agents", []):
            if agent_name == "ResourceOptimizationAgent":
                results["resource_optimization"] = {
                    "utilization": self.resource_agent.analyze_vm_utilization(resource_group),
                    "idle_resources": self.resource_agent.identify_idle_resources(resource_group)
                }
            elif agent_name == "CostManagementAgent":
                results["cost_management"] = {
                    "costs": self.cost_agent.get_resource_costs(resource_group),
                    "recommendations": self.cost_agent.generate_savings_recommendations(resource_group)
                }
            elif agent_name == "SecurityComplianceAgent":
                results["security"] = self.security_agent.check_security_posture(resource_group)
                
        return results

if __name__ == "__main__":
    SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
    RESOURCE_GROUP = os.getenv("AZURE_RESOURCE_GROUP", "my-resource-group")
    OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
    OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
    orchestrator = AIOrchestrator(SUBSCRIPTION_ID, OPENAI_ENDPOINT, OPENAI_KEY)
    queries = [
        "Check my VM utilization and find ways to reduce costs",
        "Are there any security issues I should be aware of?",
        "Show me idle resources that are wasting money"
    ]
    
    for query in queries:
        results = orchestrator.process_request(query, RESOURCE_GROUP)
        print(f"\nResults: {json.dumps(results, indent=2)}\n")