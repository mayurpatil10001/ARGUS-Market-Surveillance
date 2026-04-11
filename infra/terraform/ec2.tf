# Latest Amazon Linux 2023 AMI (x86_64)
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
}

resource "aws_instance" "argus" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.ec2_instance_type
  key_name               = var.ec2_key_pair_name
  subnet_id              = aws_subnet.public[0].id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  root_block_device {
    volume_size           = 60
    volume_type           = "gp3"
    iops                  = 3000
    encrypted             = true
    delete_on_termination = false
    tags                  = { Name = "argus-root-vol" }
  }

  user_data = base64encode(templatefile("${path.module}/userdata.sh", {
    aws_region     = var.aws_region
    domain_name    = var.domain_name
    db_endpoint    = aws_db_instance.argus.endpoint
    redis_endpoint = aws_elasticache_replication_group.argus.primary_endpoint_address
    reports_bucket = aws_s3_bucket.reports.id
    models_bucket  = aws_s3_bucket.models.id
    ecr_registry   = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com"
  }))

  monitoring = true   # detailed CloudWatch monitoring

  lifecycle {
    create_before_destroy = true
    ignore_changes        = [ami, user_data]   # don't replace on AMI update
  }

  tags = { Name = "argus-server" }
}

# Elastic IP — stable address across stop/start
resource "aws_eip" "argus" {
  instance = aws_instance.argus.id
  domain   = "vpc"
  tags     = { Name = "argus-eip" }
}
