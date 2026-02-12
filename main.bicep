targetScope = 'resourceGroup'

param location string = resourceGroup().location

// --- Virtual Network and Subnet ---

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2023-09-01' = {
  name: 'vnet-webapp'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'subnet-frontend'
        properties: {
          addressPrefix: '10.0.0.0/24'
        }
      }
    ]
  }
}

// --- Public IP Address for VM ---

resource publicIpAddress 'Microsoft.Network/publicIPAddresses@2023-09-01' = {
  name: 'pip-webapp-webserver'
  location: location
  sku: {
    name: 'Standard' // Standard SKU for Public IP
  }
  properties: {
    publicIPAllocationMethod: 'Static' // Static allocation
    idleTimeoutInMinutes: 4
  }
}

// --- Network Interface Card for VM ---

resource networkInterface 'Microsoft.Network/networkInterfaces@2023-09-01' = {
  name: 'nic-webapp-webserver'
  location: location
  properties: {
    ipConfigurations: [
      {
        name: 'ipconfig1'
        properties: {
          privateIPAllocationMethod: 'Dynamic'
          subnet: {
            id: virtualNetwork.properties.subnets[0].id // Reference the 'subnet-frontend'
          }
          publicIPAddress: {
            id: publicIpAddress.id // Attach the Public IP to the NIC
          }
        }
      }
    ]
  }
}

// --- Virtual Machine (Web Server) ---

resource virtualMachine 'Microsoft.Compute/virtualMachines@2023-09-01' = {
  name: 'vm-webapp-webserver'
  location: location
  properties: {
    hardwareProfile: {
      vmSize: 'Standard_B1s' // Rule 2: Use 'Standard_B1s' for VMs
    }
    osProfile: {
      computerName: 'webserver'
      adminUsername: 'azureuser'
      adminPassword: 'P@ssw0rd1234!' // Rule 4: Hardcoded complex default password
    }
    storageProfile: {
      imageReference: {
        publisher: 'MicrosoftWindowsServer'
        offer: 'WindowsServer'
        sku: '2019-Datacenter' // Example Windows Server image
        version: 'latest'
      }
      osDisk: {
        createOption: 'FromImage'
        managedDisk: {
          storageAccountType: 'Standard_LRS'
        }
      }
    }
    networkProfile: {
      networkInterfaces: [
        {
          id: networkInterface.id // Attach the Network Interface Card
        }
      ]
    }
    diagnosticsProfile: {
      bootDiagnostics: {
        enabled: true
      }
    }
  }
}

// --- Azure SQL Server and Database ---

// Logical SQL Server (globally unique name)
resource sqlServer 'Microsoft.Sql/servers@2022-05-01-preview' = {
  name: 'sqlserver-webapp-${uniqueString(resourceGroup().id)}'
  location: location
  properties: {
    administratorLogin: 'sqladmin'
    administratorLoginPassword: 'P@ssw0rd1234!' // Rule 4: Hardcoded complex default password
    version: '12.0' // SQL Server 2014, often used as a stable version
  }
}

// SQL Database
resource sqlDatabase 'Microsoft.Sql/servers/databases@2022-05-01-preview' = {
  parent: sqlServer
  name: 'sqldb-webapp'
  location: location
  sku: {
    name: 'S0' // Standard Tier, S0 service objective (10 DTUs, 250 GB storage)
    tier: 'Standard'
  }
  properties: {
    collation: 'SQL_Latin1_General_CP1_CI_AS'
    maxSizeBytes: 268435456000 // 250 GB (max for S0)
  }
}

// SQL Server Firewall Rule to allow traffic from the VM's subnet
resource sqlFirewallRule 'Microsoft.Sql/servers/firewallRules@2022-05-01-preview' = {
  parent: sqlServer
  name: 'AllowWebVMSubnet'
  properties: {
    // Allows the entire 10.0.0.0/24 subnet to connect to the SQL Server
    startIpAddress: '10.0.0.0'
    endIpAddress: '10.0.0.255'
  }
}