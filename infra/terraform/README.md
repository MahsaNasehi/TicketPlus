# TicketPlus Infrastructure (Terraform)

Declarative provisioning for the resilient environment shown in the
[Deployment Diagram](../../diagrams/08-deployment-diagram.puml).

| File | Provisions |
|---|---|
| `providers.tf` | AWS provider configuration |
| `variables.tf` | Environment-configurable inputs (region, instance sizes, scaling bounds) |
| `network.tf` | VPC, public/private subnets across AZs, NAT gateways, route tables |
| `eks.tf` | EKS cluster + autoscaling node group hosting the microservice pods |
| `rds.tf` | Managed PostgreSQL (Multi-AZ + read replica) for events/reservations/payments/tickets |
| `redis.tf` | Managed Redis (cluster + replicas) for seat-lock TTLs and search caching |
| `msk.tf` | Managed Kafka brokers and CloudWatch logging for asynchronous domain events |
| `loadbalancer.tf` | Public ALB, listener, and target group fronting the Ingress controller |
| `outputs.tf` | ALB, cluster, database, Redis, and Kafka connection outputs for CI/CD and app config |

## Usage

```bash
terraform init
terraform plan -var="environment=dev"
terraform apply -var="environment=dev"
```

After installing the NGINX Ingress Controller, the delivery pipeline registers
its private endpoints with `ingress_target_group_arn`. TLS termination can be
added by supplying an ACM certificate and changing the listener to HTTPS for a
real environment; the HTTP listener keeps this reference implementation
self-contained.

Kubernetes manifests / Helm charts for the individual microservices
(API Gateway, Reservation Engine, Checkout, Notification, etc.) are applied
against `eks_cluster_endpoint` separately and are out of scope for this
Terraform layer, which only provisions the underlying cloud resources.
