resource "aws_db_subnet_group" "argus" {
  name       = "argus-db-subnet"
  subnet_ids = aws_subnet.private[*].id
  tags       = { Name = "argus-db-subnet-group" }
}

resource "aws_db_parameter_group" "argus" {
  name   = "argus-postgres16"
  family = "postgres16"
  parameter {
    name  = "log_min_duration_statement"
    value = "1000"   # log queries > 1 second
  }
  parameter {
    name         = "shared_preload_libraries"
    value        = "pg_stat_statements"
    apply_method = "pending-reboot"
  }
}

resource "aws_db_instance" "argus" {
  identifier              = "argus-postgres"
  engine                  = "postgres"
  engine_version          = "16.2"
  instance_class          = var.db_instance_class
  allocated_storage       = 50
  max_allocated_storage   = 200
  storage_encrypted       = true
  db_name                 = "argus"
  username                = "argus"
  password                = var.db_password
  db_subnet_group_name    = aws_db_subnet_group.argus.name
  vpc_security_group_ids  = [aws_security_group.rds.id]
  multi_az                = var.db_multi_az
  backup_retention_period = 7
  backup_window           = "03:00-04:00"
  maintenance_window      = "sun:04:00-sun:05:00"
  deletion_protection     = true
  skip_final_snapshot     = false
  final_snapshot_identifier = "argus-final-snapshot"
  performance_insights_enabled          = true
  enabled_cloudwatch_logs_exports       = ["postgresql", "upgrade"]
  parameter_group_name    = aws_db_parameter_group.argus.name
  tags                    = { Name = "argus-rds" }
}
