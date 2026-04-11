# ── ALB ───────────────────────────────────────────────────────────────────────
resource "aws_lb" "argus" {
  name                       = "argus-alb"
  internal                   = false
  load_balancer_type         = "application"
  security_groups            = [aws_security_group.alb.id]
  subnets                    = aws_subnet.public[*].id
  enable_deletion_protection = true

  access_logs {
    bucket  = aws_s3_bucket.alb_logs.id
    prefix  = "alb"
    enabled = true
  }
  tags = { Name = "argus-alb" }
}

# ALB access log bucket
resource "aws_s3_bucket" "alb_logs" {
  bucket        = "argus-alb-logs-${data.aws_caller_identity.current.account_id}"
  force_destroy = true
}
resource "aws_s3_bucket_policy" "alb_logs" {
  bucket = aws_s3_bucket.alb_logs.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "elasticloadbalancing.amazonaws.com" }
      Action    = "s3:PutObject"
      Resource  = "${aws_s3_bucket.alb_logs.arn}/alb/AWSLogs/${data.aws_caller_identity.current.account_id}/*"
    }]
  })
}

# ── ACM Certificate (free, auto-renews) ────────────────────────────────────────
resource "aws_acm_certificate" "argus" {
  domain_name               = var.domain_name
  subject_alternative_names = ["www.${var.domain_name}", "api.${var.domain_name}"]
  validation_method         = "DNS"
  lifecycle { create_before_destroy = true }
  tags = { Name = "argus-cert" }
}

# ── Target Groups ──────────────────────────────────────────────────────────────
resource "aws_lb_target_group" "api" {
  name     = "argus-api"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.argus.id
  health_check {
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 15
    timeout             = 5
    matcher             = "200"
  }
  tags = { Name = "argus-api-tg" }
}
resource "aws_lb_target_group" "dashboard" {
  name     = "argus-dashboard"
  port     = 5173
  protocol = "HTTP"
  vpc_id   = aws_vpc.argus.id
  health_check {
    path                = "/"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 15
    timeout             = 5
    matcher             = "200"
  }
  tags = { Name = "argus-dashboard-tg" }
}

resource "aws_lb_target_group_attachment" "api" {
  target_group_arn = aws_lb_target_group.api.arn
  target_id        = aws_instance.argus.id
  port             = 8000
}
resource "aws_lb_target_group_attachment" "dashboard" {
  target_group_arn = aws_lb_target_group.dashboard.arn
  target_id        = aws_instance.argus.id
  port             = 5173
}

# ── Listeners ───────────────────────────────────────────────────────────────────
# HTTP → HTTPS redirect
resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.argus.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type = "redirect"
    redirect {
      port        = "443"
      protocol    = "HTTPS"
      status_code = "HTTP_301"
    }
  }
}

# HTTPS — default to dashboard
resource "aws_lb_listener" "https" {
  load_balancer_arn = aws_lb.argus.arn
  port              = 443
  protocol          = "HTTPS"
  ssl_policy        = "ELBSecurityPolicy-TLS13-1-2-2021-06"
  certificate_arn   = aws_acm_certificate.argus.arn
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.dashboard.arn
  }
}

# SSE live stream rule (highest priority — no buffering at ALB)
resource "aws_lb_listener_rule" "sse" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 5
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  condition {
    path_pattern { values = ["/api/alerts/live"] }
  }
}

# /api/* → argus-api target group
resource "aws_lb_listener_rule" "api" {
  listener_arn = aws_lb_listener.https.arn
  priority     = 10
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
  condition {
    path_pattern { values = ["/api/*", "/docs", "/openapi.json"] }
  }
}
