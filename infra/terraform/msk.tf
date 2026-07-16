resource "aws_security_group" "kafka" {
  name   = "${local.name}-kafka-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    description     = "TLS Kafka traffic from EKS workloads"
    from_port       = 9094
    to_port         = 9094
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

# Managed Kafka carries reservation, checkout, ticket, and notification events.
# One broker per availability zone keeps asynchronous workflows available when
# an individual broker or zone fails.
resource "aws_msk_cluster" "main" {
  cluster_name           = "${local.name}-kafka"
  kafka_version          = "3.7.x"
  number_of_broker_nodes = var.az_count

  broker_node_group_info {
    client_subnets  = values(aws_subnet.private)[*].id
    instance_type   = var.kafka_instance_type
    security_groups = [aws_security_group.kafka.id]

    storage_info {
      ebs_storage_info {
        volume_size = var.kafka_volume_size
      }
    }
  }

  encryption_info {
    encryption_in_transit {
      client_broker = "TLS"
      in_cluster    = true
    }
  }

  client_authentication {
    unauthenticated = true
  }

  logging_info {
    broker_logs {
      cloudwatch_logs {
        enabled   = true
        log_group = aws_cloudwatch_log_group.kafka.name
      }
    }
  }
}

resource "aws_cloudwatch_log_group" "kafka" {
  name              = "/aws/msk/${local.name}"
  retention_in_days = 30
}
