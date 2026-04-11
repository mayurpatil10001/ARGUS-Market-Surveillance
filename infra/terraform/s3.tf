data "aws_caller_identity" "current" {}

# ── PDF reports bucket ─────────────────────────────────────────────────────────
resource "aws_s3_bucket" "reports" {
  bucket        = "argus-reports-${var.environment}-${data.aws_caller_identity.current.account_id}"
  force_destroy = false
  tags          = { Name = "argus-reports" }
}
resource "aws_s3_bucket_versioning" "reports" {
  bucket = aws_s3_bucket.reports.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_lifecycle_configuration" "reports" {
  bucket = aws_s3_bucket.reports.id
  rule {
    id     = "archive-old-reports"
    status = "Enabled"
    transition { days = 90  storage_class = "STANDARD_IA" }
    transition { days = 365 storage_class = "GLACIER" }
  }
}
resource "aws_s3_bucket_public_access_block" "reports" {
  bucket                  = aws_s3_bucket.reports.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# ── Model weights backup bucket ────────────────────────────────────────────────
resource "aws_s3_bucket" "models" {
  bucket        = "argus-models-${var.environment}-${data.aws_caller_identity.current.account_id}"
  force_destroy = false
  tags          = { Name = "argus-models" }
}
resource "aws_s3_bucket_versioning" "models" {
  bucket = aws_s3_bucket.models.id
  versioning_configuration { status = "Enabled" }
}
resource "aws_s3_bucket_server_side_encryption_configuration" "models" {
  bucket = aws_s3_bucket.models.id
  rule {
    apply_server_side_encryption_by_default { sse_algorithm = "AES256" }
  }
}
resource "aws_s3_bucket_public_access_block" "models" {
  bucket                  = aws_s3_bucket.models.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}
