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

output "vpc_id" {
  value = aws_vpc.main.id
}