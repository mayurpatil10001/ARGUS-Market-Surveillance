terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
  # Remote state — comment out for first run, enable after S3 bucket exists
  # backend "s3" {
  #   bucket  = "argus-terraform-state"
  #   key     = "argus/terraform.tfstate"
  #   region  = var.aws_region
  #   encrypt = true
  # }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "ARGUS"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
