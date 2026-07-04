resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name}-redis-subnets"
  subnet_ids = values(aws_subnet.private)[*].id
}

resource "aws_security_group" "redis" {
  name   = "${local.name}-redis-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_eks_cluster.main.vpc_config[0].cluster_security_group_id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Managed Redis backs the temporary seat-lock TTL mechanism and search
# result caching. Cluster mode + replicas per shard give HA; if Redis is
# ever fully unavailable, the Reservation Engine falls back to DB-level
# advisory locks (see Risk Analysis document, section on Redis fallback).
resource "aws_elasticache_replication_group" "main" {
  replication_group_id = "${local.name}-redis"
  description           = "TicketPlus seat-lock and cache store"

  engine         = "redis"
  engine_version = "7.1"
  node_type      = var.redis_node_type

  num_node_groups         = 1
  replicas_per_node_group = var.redis_num_replicas

  automatic_failover_enabled = true
  multi_az_enabled           = true

  subnet_group_name = aws_elasticache_subnet_group.main.name
  security_group_ids = [aws_security_group.redis.id]

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
}