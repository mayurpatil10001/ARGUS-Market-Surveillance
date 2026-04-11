resource "aws_elasticache_subnet_group" "argus" {
  name       = "argus-redis-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_replication_group" "argus" {
  replication_group_id       = "argus-redis"
  description                = "ARGUS Redis cache and pub/sub"
  node_type                  = "cache.t3.micro"
  num_cache_clusters         = 1
  port                       = 6379
  subnet_group_name          = aws_elasticache_subnet_group.argus.name
  security_group_ids         = [aws_security_group.redis.id]
  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
  auth_token                 = var.redis_password
  engine_version             = "7.1"
  automatic_failover_enabled = false
  snapshot_retention_limit   = 3
  snapshot_window            = "02:00-03:00"
  tags                       = { Name = "argus-redis" }
}
