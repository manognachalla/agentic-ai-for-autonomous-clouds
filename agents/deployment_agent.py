from azure.mgmt.containerinstance import ContainerInstanceManagementClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient
from azure.identity import DefaultAzureCredential
import os
import zipfile
import tempfile
import uuid
import json

class DeploymentAgent:
    """
    Agent for deploying user applications to Azure Container Instances
    """
    
    def __init__(self, subscription_id):
        self.subscription_id = subscription_id
        self.credential = DefaultAzureCredential()
        self.container_client = ContainerInstanceManagementClient(
            self.credential,
            subscription_id
        )
        
    def upload_to_storage(self, file_path, container_name="deployments"):
        """
        Upload project files to Azure Blob Storage
        """
        try:
            # Get storage account connection string from env
            connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
            if not connection_string:
                raise ValueError("AZURE_STORAGE_CONNECTION_STRING not set")
            
            blob_service_client = BlobServiceClient.from_connection_string(
                connection_string,
                connection_timeout=300,  # 5 minutes timeout
                read_timeout=300
            )
            
            # Create container if it doesn't exist
            try:
                container_client = blob_service_client.get_container_client(container_name)
                if not container_client.exists():
                    blob_service_client.create_container(container_name)
            except:
                blob_service_client.create_container(container_name)
            
            # Upload file with unique name
            blob_name = f"{uuid.uuid4()}.zip"
            blob_client = blob_service_client.get_blob_client(
                container=container_name,
                blob=blob_name
            )
            
            # Get file size for progress tracking
            file_size = os.path.getsize(file_path)
            print(f"Uploading {file_size / 1024 / 1024:.2f} MB to Azure Storage...")
            
            with open(file_path, "rb") as data:
                blob_client.upload_blob(
                    data, 
                    overwrite=True,
                    timeout=300,  # 5 minutes timeout per chunk
                    max_concurrency=4  # Parallel upload for faster speeds
                )
            
            print(f"Upload complete: {blob_name}")
            
            return {
                "upload_id": blob_name,
                "url": blob_client.url
            }
        except Exception as e:
            print(f"Upload error: {str(e)}")
            raise Exception(f"Upload failed: {str(e)}")
    
    def deploy_to_container(self, upload_id, app_name, resource_group):
        """
        Deploy application to Azure Container Instances
        
        This is a simplified version that deploys a basic nginx container.
        In production, you would:
        1. Extract the uploaded zip
        2. Detect the project type (Node.js, Python, etc.)
        3. Build a Docker image
        4. Push to Azure Container Registry
        5. Deploy the custom image
        """
        try:
            deployment_id = str(uuid.uuid4())[:8]
            container_group_name = f"{app_name}-{deployment_id}"
            
            # Get region from environment variable
            location = os.getenv("AZURE_REGION", "centralus")
            
            # For this demo, we'll deploy a simple nginx container
            # In production, replace this with your custom built image
            container_group = {
                "location": location,
                "containers": [{
                    "name": container_group_name,
                    "image": "nginx:latest",  # Replace with custom image from ACR
                    "resources": {
                        "requests": {
                            "cpu": 1.0,
                            "memory_in_gb": 1.5
                        }
                    },
                    "ports": [{"port": 80}]
                }],
                "os_type": "Linux",
                "ip_address": {
                    "type": "Public",
                    "ports": [{"protocol": "TCP", "port": 80}]
                },
                "restart_policy": "Always"
            }
            
            # Start deployment (async operation)
            poller = self.container_client.container_groups.begin_create_or_update(
                resource_group,
                container_group_name,
                container_group
            )
            
            return {
                "deployment_id": deployment_id,
                "container_group_name": container_group_name,
                "status": "deploying",
                "message": "Container deployment initiated"
            }
            
        except Exception as e:
            raise Exception(f"Deployment failed: {str(e)}")
    
    def get_deployment_status(self, container_group_name, resource_group):
        """
        Get the status of a deployment
        """
        try:
            container_group = self.container_client.container_groups.get(
                resource_group,
                container_group_name
            )
            
            # Check provisioning state (this is more reliable than instance_view)
            provisioning_state = container_group.provisioning_state
            
            # Get container state if available
            containers_state = "Unknown"
            if container_group.containers and len(container_group.containers) > 0:
                first_container = container_group.containers[0]
                if hasattr(first_container, 'instance_view') and first_container.instance_view:
                    if first_container.instance_view.current_state:
                        containers_state = first_container.instance_view.current_state.state
            
            # Get the public IP if available
            url = None
            if container_group.ip_address:
                # The IP is directly on the ip_address object
                ip = container_group.ip_address.ip
                if ip:
                    url = f"http://{ip}"
            
            # Determine overall status
            is_succeeded = provisioning_state == "Succeeded"
            is_running = containers_state in ["Running", "Succeeded"]
            
            return {
                "status": "succeeded" if (is_succeeded and is_running) else "deploying",
                "state": f"{provisioning_state} - Container: {containers_state}",
                "url": url,
                "message": f"Provisioning: {provisioning_state}, Container: {containers_state}"
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": str(e)
            }
    
    def get_logs(self, container_name, resource_group):
        """
        Get deployment logs from container
        """
        try:
            logs = self.container_client.containers.list_logs(
                resource_group,
                container_name,
                container_name  # container name within the group
            )
            return logs.content.split('\n') if logs.content else []
        except:
            return []
