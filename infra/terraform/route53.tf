# Route 53 — if domain is managed in Route 53.
# If using an external registrar, comment this file out and follow infra/DNS_SETUP.md.

data "aws_route53_zone" "argus" {
  name         = var.domain_name
  private_zone = false
}

resource "aws_route53_record" "argus" {
  zone_id = data.aws_route53_zone.argus.zone_id
  name    = var.domain_name
  type    = "A"
  alias {
    name                   = aws_lb.argus.dns_name
    zone_id                = aws_lb.argus.zone_id
    evaluate_target_health = true
  }
}

resource "aws_route53_record" "api" {
  zone_id = data.aws_route53_zone.argus.zone_id
  name    = "api.${var.domain_name}"
  type    = "A"
  alias {
    name                   = aws_lb.argus.dns_name
    zone_id                = aws_lb.argus.zone_id
    evaluate_target_health = true
  }
}

# ACM DNS validation records (auto-validates certificate)
resource "aws_route53_record" "acm_validation" {
  for_each = {
    for dvo in aws_acm_certificate.argus.domain_validation_options : dvo.domain_name => {
      name   = dvo.resource_record_name
      record = dvo.resource_record_value
      type   = dvo.resource_record_type
    }
  }
  zone_id         = data.aws_route53_zone.argus.zone_id
  name            = each.value.name
  type            = each.value.type
  records         = [each.value.record]
  ttl             = 60
  allow_overwrite = true
}

resource "aws_acm_certificate_validation" "argus" {
  certificate_arn         = aws_acm_certificate.argus.arn
  validation_record_fqdns = [for record in aws_route53_record.acm_validation : record.fqdn]
}
