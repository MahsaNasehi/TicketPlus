# TicketPlus Infrastructure (Terraform)

Declarative provisioning for the resilient environment shown in the
[Deployment Diagram](../../docs/section3/diagrams/08-deployment-diagram.puml).

| File | Provisions |
|---|---|
| `providers.tf` | AWS provider configuration |
| `variables.tf` | Environment-configurable inputs (region, instance sizes, scaling bounds) |
| `network.tf` | VPC, public/private subnets across AZs, NAT gateways, route tables |
| `eks.tf` | EKS cluster + autoscaling node group hosting the microservice pods |
| `rds.tf` | Managed PostgreSQL (Multi-AZ + read replica) for events/reservations/payments/tickets |
| `redis.tf` | Managed Redis (cluster + replicas) for seat-lock TTLs and search caching |
| `loadbalancer.tf` | Security group for the public ALB fronting the Ingress controller |
| `outputs.tf` | Cluster endpoint, DB endpoints, Redis endpoint for CI/CD and app config |

## Usage

```bash
terraform init
terraform plan -var="environment=dev"
terraform apply -var="environment=dev"
```

Kubernetes manifests / Helm charts for the individual microservices
(API Gateway, Reservation Engine, Checkout, Notification, etc.) are applied
against `eks_cluster_endpoint` separately and are out of scope for this
Terraform layer, which only provisions the underlying cloud resources.