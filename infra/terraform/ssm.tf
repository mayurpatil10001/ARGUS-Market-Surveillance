# Store all secrets in SSM Parameter Store (KMS-encrypted via SecureString)
# Values come from terraform.tfvars — nothing sensitive in source control

locals {
  ssm_params = {
    "/argus/db_password"          = var.db_password
    "/argus/redis_password"       = var.redis_password
    "/argus/jwt_secret"           = var.jwt_secret
    "/argus/admin_password"       = var.admin_password
    "/argus/zerodha_api_key"      = var.zerodha_api_key
    "/argus/zerodha_access_token" = var.zerodha_access_token
    "/argus/twitter_bearer_token" = var.twitter_bearer_token
  }
}

resource "aws_ssm_parameter" "secrets" {
  for_each  = local.ssm_params
  name      = each.key
  type      = "SecureString"
  value     = each.value == "" ? "NOT_SET" : each.value
  overwrite = true
  tags      = { Name = each.key }
}
