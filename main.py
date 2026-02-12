import os
import json
import uuid
from datetime import datetime

from azure.identity import DefaultAzureCredential
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.resource import ResourceManagementClient
from azure.mgmt.monitor import MonitorManagementClient

# Import the LLM from your separate file
from hf_llm_client import HuggingFaceLLM

# =====================================================
# ENVIRONMENT
# =====================================================
SUBSCRIPTION_ID = os.getenv("AZURE_SUBSCRIPTION_ID")
RESOURCE_GROUP = os.getenv("RESOURCE_GROUP")
HF_API_TOKEN = os.getenv("HF_API_TOKEN")

print("Using subscription:", SUBSCRIPTION_ID)
print("Using resource group:", RESOURCE_GROUP)

# =====================================================
# BASE AGENT
# =====================================================
class BaseAgent:
    def __init__(self, subscription_id, agent_name):
        self.agent_name = agent_name
        self.credential = DefaultAzureCredential()
        self.compute_client = ComputeManagementClient(self.credential, subscription_id)
        self.resource_client = ResourceManagementClient(self.credential, subscription_id)
        self.monitor_client = MonitorManagementClient(self.credential, subscription_id)

    def log(self, msg):
        print(f"[{datetime.now()}] [{self.agent_name}] {msg}")

# =====================================================
# RESOURCE OPTIMIZATION AGENT
# =====================================================
class ResourceOptimizationAgent(BaseAgent):
    def __init__(self, subscription_id):
        super().__init__(subscription_id, "ResourceOptimizer")

    def analyze_vm_utilization(self, resource_group):
        cid = uuid.uuid4()
        self.log(f"[CID={cid}] Analyzing VM utilization")

        vms = self.compute_client.virtual_machines.list(resource_group)
        return [ {
            "vm": vm.name,
            "size": vm.hardware_profile.vm_size,
            "recommendation": "Review CPU & memory metrics"
        } for vm in vms]

    def identify_idle_resources(self, resource_group):
        cid = uuid.uuid4()
        self.log(f"[CID={cid}] Checking idle VMs")

        idle = []
        vms = self.compute_client.virtual_machines.list(resource_group)

        for vm in vms:
            iv = self.compute_client.virtual_machines.instance_view(resource_group, vm.name)
            for status in iv.statuses:
                if status.code == "PowerState/deallocated":
                    idle.append({
                        "vm": vm.name,
                        "status": "Deallocated",
                        "action": "Delete or stop billing"
                    })
        return idle

    def trigger_test_log(self, resource_group):
        cid = uuid.uuid4()
        self.log(f"[CID={cid}] Triggering Activity Log")

        rg = self.resource_client.resource_groups.get(resource_group)
        rg.tags = rg.tags or {}
        rg.tags["activity-log-test"] = datetime.utcnow().isoformat()
        self.resource_client.resource_groups.create_or_update(resource_group, rg)

        self.log(f"[CID={cid}] Activity Log triggered")

# =====================================================
# COST MANAGEMENT AGENT
# =====================================================
class CostManagementAgent(BaseAgent):
    def __init__(self, subscription_id):
        super().__init__(subscription_id, "CostManager")

    def get_resource_costs(self, resource_group):
        resources = self.resource_client.resources.list_by_resource_group(resource_group)
        return [{
            "name": r.name,
            "type": r.type,
            "location": r.location,
            "estimated_cost": "Fetch via Cost API"
        } for r in resources]

# =====================================================
# SECURITY AGENT
# =====================================================
class SecurityComplianceAgent(BaseAgent):
    def __init__(self, subscription_id):
        super().__init__(subscription_id, "SecurityCompliance")

    def check_security_posture(self, resource_group):
        vms = self.compute_client.virtual_machines.list(resource_group)
        return [{
            "vm": vm.name,
            "issues": ["Check NSG", "Verify disk encryption"]
        } for vm in vms]

# =====================================================
# ORCHESTRATOR
# =====================================================
class AIOrchestrator:
    def __init__(self, subscription_id):
        self.resource_agent = ResourceOptimizationAgent(subscription_id)
        self.cost_agent = CostManagementAgent(subscription_id)
        self.security_agent = SecurityComplianceAgent(subscription_id)

        # ✅ Use the HuggingFace LLM from hf_llm_client.py
        self.llm = HuggingFaceLLM()
        print("[INFO] Using FREE Hugging Face LLM")

    def process_request(self, resource_group):
        data = {
            "resource_optimization": {
                "utilization": self.resource_agent.analyze_vm_utilization(resource_group),
                "idle": self.resource_agent.identify_idle_resources(resource_group)
            },
            "costs": self.cost_agent.get_resource_costs(resource_group),
            "security": self.security_agent.check_security_posture(resource_group)
        }

        prompt = f"""
You are an Azure cloud optimization assistant.

Analyze this data and provide:
1. Optimization summary
2. Cost-saving actions
3. Security risks

DATA:
{json.dumps(data, indent=2)}
"""
        data["llm_decision"] = self.llm.generate(prompt)
        return data

# =====================================================
# MAIN
# =====================================================
if __name__ == "__main__":
    orchestrator = AIOrchestrator(SUBSCRIPTION_ID)

    # Step 1: Trigger Activity Log
    orchestrator.resource_agent.trigger_test_log(RESOURCE_GROUP)

    # Step 2: Run agents + LLM
    output = orchestrator.process_request(RESOURCE_GROUP)

    print(json.dumps(output, indent=2))
