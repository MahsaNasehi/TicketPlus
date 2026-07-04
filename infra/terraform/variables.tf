variable "aws_region" {
  description = "AWS region to deploy TicketPlus infrastructure into"
  type        = string
  default     = "eu-central-1"
}

variable "environment" {
  description = "Deployment environment name (e.g. dev, staging, prod)"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Prefix applied to all provisioned resources"
  type        = string
  default     = "ticketplus"
}

variable "vpc_cidr" {
  description = "CIDR block for the TicketPlus VPC"
  type        = string
  default     = "10.20.0.0/16"
}

variable "az_count" {
  description = "Number of availability zones to spread resources across"
  type        = number
  default     = 3
}

variable "eks_node_instance_type" {
  description = "Instance type for EKS worker nodes running the microservices"
  type        = string
  default     = "t3.large"
}

variable "eks_node_min_size" {
  type    = number
  default = 3
}

variable "eks_node_max_size" {
  description = "Upper bound for the autoscaler during ticket-release traffic spikes"
  type        = number
  default     = 12
}

variable "db_instance_class" {
  description = "Instance class for the managed PostgreSQL (RDS) database"
  type        = string
  default     = "db.r6g.large"
}

variable "db_multi_az" {
  description = "Enable Multi-AZ failover for the reservation/billing database"
  type        = bool
  default     = true
}

variable "redis_node_type" {
  description = "Instance class for the managed Redis (ElastiCache) cluster used for seat locks"
  type        = string
  default     = "cache.r6g.large"
}

variable "redis_num_replicas" {
  description = "Number of read replicas per Redis shard for HA seat-lock storage"
  type        = number
  default     = 2
}