from base_agent import BaseAgent

class CostManagementAgent(BaseAgent):
    def __init__(self, subscription_id):
        super().__init__(subscription_id, "CostManager")

    def get_resource_costs(self, resource_group):
        self.log(f"Retrieving cost data for {resource_group}...")
        # Note: In a real scenario, this would likely query the Cost Management API.
        # For this example, we list resources as a proxy for cost centers.
        resources = self.resource_client.resources.list_by_resource_group(
            resource_group
        )

        return [{
            "name": r.name,
            "type": r.type,
            "location": r.location
        } for r in resources]