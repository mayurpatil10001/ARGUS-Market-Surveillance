# DNS Setup for ARGUS
# Follow Option A if your domain is in Route 53 (fully automated).
# Follow Option B if your domain is at an external registrar (manual CNAME).

---

## Option A — Domain registered in Route 53 (fully automatic)

Terraform creates all DNS records automatically via `route53.tf`.
ACM certificate validates automatically via DNS. No manual steps needed.

```bash
cd infra/terraform
terraform apply   # creates A records + ACM validation CNAMEs
```

Certificate validates within 5–30 minutes.

---

## Option B — External domain registrar (GoDaddy, Namecheap, Cloudflare, etc.)

### Step 1 — Get ALB DNS name after Terraform apply

```bash
cd infra/terraform
terraform output alb_dns_name
# e.g. argus-alb-1234567890.ap-south-1.elb.amazonaws.com
```

### Step 2 — Create CNAME records at your registrar

| Type  | Name                        | Value (ALB DNS name)                                          | TTL |
|-------|-----------------------------|---------------------------------------------------------------|-----|
| CNAME | argus.yourdomain.com        | argus-alb-XXXX.ap-south-1.elb.amazonaws.com                  | 300 |
| CNAME | api.argus.yourdomain.com    | argus-alb-XXXX.ap-south-1.elb.amazonaws.com                  | 300 |

> **Cloudflare users:** Enable "Proxied" (orange cloud) for DDoS protection.
> Use `CNAME` flattening at the apex if your registrar supports it.

### Step 3 — ACM certificate DNS validation

1. In AWS Console → Certificate Manager → Your certificate → "Create records in Route 53" (if using R53)
2. Or copy the CNAME validation records shown in ACM and add them at your registrar:

| Type  | Name                               | Value                                      | TTL  |
|-------|------------------------------------|--------------------------------------------|------|
| CNAME | _abc123.argus.yourdomain.com       | _xyz789.acm-validations.aws.               | 3600 |

Certificate validates within 5–30 minutes after DNS propagates.

### Step 4 — Verify everything is working

```bash
# Check DNS resolution (after TTL expires)
nslookup argus.yourdomain.com
dig argus.yourdomain.com CNAME

# Verify HTTPS (after cert validates)
curl -I https://argus.yourdomain.com/health
# Expected: HTTP/2 200

curl -I https://api.argus.yourdomain.com/health
# Expected: HTTP/2 200
```

---

## HTTPS Notes

- ACM certificates are **FREE** and **auto-renew** — no manual cert management
- All TLS termination happens at the ALB — EC2 serves plain HTTP internally
- HTTP→HTTPS redirect is enforced by ALB (`aws_lb_listener.http`)
- TLS 1.3 is the preferred protocol (`ELBSecurityPolicy-TLS13-1-2-2021-06`)
- Perfect Forward Secrecy (PFS) is enabled by default on ALB

---

## Troubleshooting

| Issue | Check |
|-------|-------|
| Certificate stuck "Pending validation" | Verify CNAME records added correctly at registrar; DNS propagation can take up to 72h |
| HTTPS returns "ERR_SSL_VERSION_OR_CIPHER_MISMATCH" | Client TLS version too old (< TLS 1.2) |
| 503 from ALB | EC2 health check failing — check `/health` returns 200 on port 8000 |
| 404 on `/api/` | API listener rule not matching — check ALB rules in AWS Console |
