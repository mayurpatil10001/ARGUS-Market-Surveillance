# ── Log groups ────────────────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "argus_api" {
  name              = "/argus/api"
  retention_in_days = 30
}
resource "aws_cloudwatch_log_group" "argus_worker" {
  name              = "/argus/worker"
  retention_in_days = 14
}
resource "aws_cloudwatch_log_group" "argus_nginx" {
  name              = "/argus/nginx"
  retention_in_days = 7
}
resource "aws_cloudwatch_log_group" "argus_bootstrap" {
  name              = "/argus/bootstrap"
  retention_in_days = 7
}
resource "aws_cloudwatch_log_group" "argus_app" {
  name              = "/argus/app"
  retention_in_days = 30
}

# ── SNS topic for all alerts ───────────────────────────────────────────────────
resource "aws_sns_topic" "argus_alerts" {
  name = "argus-infrastructure-alerts"
}

# ── CloudWatch alarms ─────────────────────────────────────────────────────────
resource "aws_cloudwatch_metric_alarm" "api_5xx" {
  alarm_name          = "argus-api-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "ARGUS API returning excessive 5XX errors"
  dimensions = {
    LoadBalancer = aws_lb.argus.arn_suffix
    TargetGroup  = aws_lb_target_group.api.arn_suffix
  }
  alarm_actions = [aws_sns_topic.argus_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_latency" {
  alarm_name          = "argus-api-high-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "TargetResponseTime"
  namespace           = "AWS/ApplicationELB"
  period              = 60
  extended_statistic  = "p99"
  threshold           = 5   # seconds
  alarm_description   = "ARGUS API P99 latency > 5s"
  dimensions = {
    LoadBalancer = aws_lb.argus.arn_suffix
    TargetGroup  = aws_lb_target_group.api.arn_suffix
  }
  alarm_actions = [aws_sns_topic.argus_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "ec2_cpu" {
  alarm_name          = "argus-ec2-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = 120
  statistic           = "Average"
  threshold           = 85
  dimensions          = { InstanceId = aws_instance.argus.id }
  alarm_actions       = [aws_sns_topic.argus_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "rds_cpu" {
  alarm_name          = "argus-rds-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "CPUUtilization"
  namespace           = "AWS/RDS"
  period              = 120
  statistic           = "Average"
  threshold           = 80
  dimensions          = { DBInstanceIdentifier = aws_db_instance.argus.identifier }
  alarm_actions       = [aws_sns_topic.argus_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "rds_storage" {
  alarm_name          = "argus-rds-low-storage"
  comparison_operator = "LessThanThreshold"
  evaluation_periods  = 1
  metric_name         = "FreeStorageSpace"
  namespace           = "AWS/RDS"
  period              = 300
  statistic           = "Average"
  threshold           = 5368709120   # 5 GB in bytes
  alarm_description   = "RDS free storage < 5 GB"
  dimensions          = { DBInstanceIdentifier = aws_db_instance.argus.identifier }
  alarm_actions       = [aws_sns_topic.argus_alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "redis_cpu" {
  alarm_name          = "argus-redis-high-cpu"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "CPUUtilization"
  namespace           = "AWS/ElastiCache"
  period              = 120
  statistic           = "Average"
  threshold           = 75
  dimensions          = { CacheClusterId = "${aws_elasticache_replication_group.argus.replication_group_id}-0001" }
  alarm_actions       = [aws_sns_topic.argus_alerts.arn]
}

# ── CloudWatch Dashboard ───────────────────────────────────────────────────────
resource "aws_cloudwatch_dashboard" "argus" {
  dashboard_name = "ARGUS-Production"
  dashboard_body = jsonencode({
    widgets = [
      {
        type       = "metric"
        x = 0; y = 0; width = 12; height = 6
        properties = {
          title   = "API Request Count"
          metrics = [["AWS/ApplicationELB", "RequestCount",
            "LoadBalancer", aws_lb.argus.arn_suffix]]
          period  = 60
          stat    = "Sum"
          view    = "timeSeries"
        }
      },
      {
        type       = "metric"
        x = 12; y = 0; width = 12; height = 6
        properties = {
          title   = "API Latency P99"
          metrics = [["AWS/ApplicationELB", "TargetResponseTime",
            "LoadBalancer", aws_lb.argus.arn_suffix]]
          period  = 60
          stat    = "p99"
        }
      },
      {
        type       = "metric"
        x = 0; y = 6; width = 8; height = 6
        properties = {
          title   = "EC2 CPU %"
          metrics = [["AWS/EC2", "CPUUtilization",
            "InstanceId", aws_instance.argus.id]]
          period  = 60
          stat    = "Average"
        }
      },
      {
        type       = "metric"
        x = 8; y = 6; width = 8; height = 6
        properties = {
          title   = "RDS CPU %"
          metrics = [["AWS/RDS", "CPUUtilization",
            "DBInstanceIdentifier", aws_db_instance.argus.identifier]]
          period  = 60
          stat    = "Average"
        }
      },
      {
        type       = "metric"
        x = 16; y = 6; width = 8; height = 6
        properties = {
          title   = "RDS Free Storage (GB)"
          metrics = [["AWS/RDS", "FreeStorageSpace",
            "DBInstanceIdentifier", aws_db_instance.argus.identifier]]
          period  = 300
          stat    = "Average"
        }
      },
      {
        type       = "metric"
        x = 0; y = 12; width = 12; height = 6
        properties = {
          title   = "API 5XX Errors"
          metrics = [["AWS/ApplicationELB", "HTTPCode_Target_5XX_Count",
            "LoadBalancer", aws_lb.argus.arn_suffix]]
          period  = 60
          stat    = "Sum"
        }
      },
      {
        type       = "metric"
        x = 12; y = 12; width = 12; height = 6
        properties = {
          title   = "Healthy Hosts"
          metrics = [
            ["AWS/ApplicationELB", "HealthyHostCount",
              "TargetGroup", aws_lb_target_group.api.arn_suffix,
              "LoadBalancer", aws_lb.argus.arn_suffix, { label = "API" }],
            ["AWS/ApplicationELB", "HealthyHostCount",
              "TargetGroup", aws_lb_target_group.dashboard.arn_suffix,
              "LoadBalancer", aws_lb.argus.arn_suffix, { label = "Dashboard" }]
          ]
          period  = 60
          stat    = "Average"
        }
      }
    ]
  })
}
