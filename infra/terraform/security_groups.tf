# ── ALB security group — public HTTP/HTTPS ─────────────────────────────────────
resource "aws_security_group" "alb" {
  name        = "argus-alb"
  description = "Allow HTTP/HTTPS from internet to ALB"
  vpc_id      = aws_vpc.argus.id
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "argus-alb-sg" }
}

# ── EC2 security group — SSH + traffic from ALB ────────────────────────────────
resource "aws_security_group" "ec2" {
  name        = "argus-ec2"
  description = "Allow SSH and ALB traffic to EC2"
  vpc_id      = aws_vpc.argus.id
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.allowed_ssh_cidr]
  }
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  ingress {
    from_port       = 5173
    to_port         = 5173
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  ingress {
    from_port       = 8501
    to_port         = 8501
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "argus-ec2-sg" }
}

# ── RDS security group — only from EC2 ────────────────────────────────────────
resource "aws_security_group" "rds" {
  name        = "argus-rds"
  description = "Allow PostgreSQL from EC2 only"
  vpc_id      = aws_vpc.argus.id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "argus-rds-sg" }
}

# ── ElastiCache security group — only from EC2 ────────────────────────────────
resource "aws_security_group" "redis" {
  name        = "argus-redis"
  description = "Allow Redis from EC2 only"
  vpc_id      = aws_vpc.argus.id
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ec2.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "argus-redis-sg" }
}
