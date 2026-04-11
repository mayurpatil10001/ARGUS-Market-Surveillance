variable "aws_region" {
  default     = "ap-south-1"
  description = "AWS region — ap-south-1 (Mumbai) is closest to NSE/BSE"
}
variable "environment" {
  default = "production"
}
variable "domain_name" {
  description = "Primary domain, e.g. argus.yourdomain.com"
}
variable "db_password" {
  sensitive   = true
  description = "PostgreSQL master password"
}
variable "redis_password" {
  sensitive   = true
  description = "Redis AUTH token (min 16 chars)"
}
variable "jwt_secret" {
  sensitive   = true
  description = "64-char random string for JWT signing"
}
variable "admin_password" {
  sensitive   = true
  description = "ARGUS admin UI password"
}
variable "ec2_key_pair_name" {
  description = "Name of existing EC2 key pair for SSH access"
}
variable "ec2_instance_type" {
  default = "t3.xlarge"
}
variable "db_instance_class" {
  default = "db.t3.medium"
}
variable "db_multi_az" {
  default     = false
  description = "Enable RDS Multi-AZ for high availability (doubles cost)"
}
variable "allowed_ssh_cidr" {
  default     = "0.0.0.0/0"
  description = "CIDR allowed to SSH. Restrict to your IP in production: e.g. 203.0.113.10/32"
}
variable "zerodha_api_key" {
  default   = ""
  sensitive = true
}
variable "zerodha_access_token" {
  default   = ""
  sensitive = true
}
variable "twitter_bearer_token" {
  default   = ""
  sensitive = true
}
