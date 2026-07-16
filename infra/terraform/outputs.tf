output "eks_cluster_name" {
  value = aws_eks_cluster.main.name
}

output "eks_cluster_endpoint" {
  value = aws_eks_cluster.main.endpoint
}

output "postgres_endpoint" {
  value     = aws_db_instance.main.endpoint
  sensitive = true
}

output "postgres_read_replica_endpoint" {
  value     = aws_db_instance.read_replica.endpoint
  sensitive = true
}

output "redis_primary_endpoint" {
  value = aws_elasticache_replication_group.main.primary_endpoint_address
}

output "kafka_tls_bootstrap_brokers" {
  value     = aws_msk_cluster.main.bootstrap_brokers_tls
  sensitive = true
}

output "public_load_balancer_dns_name" {
  value = aws_lb.public.dns_name
}

output "ingress_target_group_arn" {
  description = "Target group used when registering Kubernetes ingress endpoints"
  value       = aws_lb_target_group.ingress.arn
}

output "vpc_id" {
  value = aws_vpc.main.id
}
