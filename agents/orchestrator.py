import json
from enum import Enum

class AgentType(Enum):
    RESOURCE_OPTIMIZATION = "resource_optimization"
    COST_MANAGEMENT = "cost_management"
    SECURITY_COMPLIANCE = "security_compliance"

class OrchestratorAgent:
    def __init__(self, llm_client, agents_registry):
        self.llm_client = llm_client
        self.agents_registry = agents_registry

    def _identify_intent(self, query):
        """
        Uses LLM to classify the user query into an AgentType.
        """
        prompt = f"""
        You are an Azure Cloud Orchestrator. 
        Classify the following user query into one of these categories:
        1. RESOURCE_OPTIMIZATION (keywords: idle, utilization, resize, vm size)
        2. COST_MANAGEMENT (keywords: cost, price, bill, expensive, list resources)
        3. SECURITY_COMPLIANCE (keywords: security, firewall, encryption, nsg, compliance)
        
        User Query: "{query}"
        
        Return ONLY the category name exactly as written above. If unsure, default to COST_MANAGEMENT.
        """
        
        # Adaptation for different LLM client interfaces (Gemini/OpenAI)
        # Assuming the passed client has a generate_content or chat completion method
        try:
            if hasattr(self.llm_client, "models"): # Google GenAI style
                response = self.llm_client.models.generate_content(
                    model="models/gemini-2.5-flash", 
                    contents=prompt
                )
                text = response.text.strip()
            else: # Azure OpenAI style (mocked for compatibility)
                # You would implement specific Azure OpenAI call here
                text = "RESOURCE_OPTIMIZATION" # Default fallback for mock
                
            # Map text to Enum
            if "RESOURCE" in text:
                return AgentType.RESOURCE_OPTIMIZATION
            elif "SECURITY" in text:
                return AgentType.SECURITY_COMPLIANCE
            else:
                return AgentType.COST_MANAGEMENT
                
        except Exception as e:
            print(f"Error determining intent: {e}")
            return AgentType.COST_MANAGEMENT

    def process_query(self, query, context):
        resource_group = context.get("resource_group")
        
        # 1. Identify which agent needs to handle this
        agent_type = self._identify_intent(query)
        active_agent = self.agents_registry.get(agent_type)
        
        agents_used = [agent_type.value]
        agent_data = {}

        # 2. Execute Agent Logic
        if agent_type == AgentType.RESOURCE_OPTIMIZATION:
            agent_data = {
                "utilization": active_agent.analyze_vm_utilization(resource_group),
                "idle_vms": active_agent.identify_idle_resources(resource_group)
            }
        elif agent_type == AgentType.COST_MANAGEMENT:
            agent_data = {
                "resources": active_agent.get_resource_costs(resource_group)
            }
        elif agent_type == AgentType.SECURITY_COMPLIANCE:
            agent_data = {
                "security_scan": active_agent.check_security_posture(resource_group)
            }

        # 3. Synthesize Answer using LLM
        final_prompt = f"""
        You are a helpful Cloud Assistant.
        
        User Query: {query}
        Context: {context}
        
        Data retrieved from Azure Agent ({agent_type.name}):
        {json.dumps(agent_data, indent=2)}
        
        Please provide a concise, human-readable answer to the user based on this data.
        """
        
        try:
            if hasattr(self.llm_client, "models"):
                response = self.llm_client.models.generate_content(
                    model="models/gemini-2.5-flash", 
                    contents=final_prompt
                )
                final_response = response.text.strip()
            else:
                final_response = "Simulated response: Analysis complete based on agent data."
        except Exception:
            final_response = "I processed the data but had trouble generating a summary."

        return {
            "response": final_response,
            "agents_used": agents_used,
            "data": agent_data
        }