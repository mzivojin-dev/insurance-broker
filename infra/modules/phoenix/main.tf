# Arize Phoenix: trace store and UI for the agents.
#   UI:     <alb>/phoenix (login: admin@localhost, password in the secret's admin_password key)
#   Ingest: agents send OTLP/HTTP straight to http://phoenix.<namespace>:6006, authenticated with
#           PHOENIX_ADMIN_SECRET as the bearer token, so no API key has to be made by hand after
#           each daily rebuild.
# Traces are kept in SQLite on the task's own disk: they last as long as the task, which is fine
# while prod is torn down daily. For keeps, point PHOENIX_POSTGRES_* at the RDS instance.

locals {
  name      = "phoenix"
  prefix    = "ai4all-${var.env}-${local.name}" # IAM roles must start with ai4all- (see infra/bootstrap)
  root_path = "/phoenix"
  port      = 6006
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/ai4all/${var.env}/${local.name}"
  retention_in_days = var.ephemeral ? 1 : 30
}

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# Used by ECS itself: write logs and read the secret into env vars. The image is public.
resource "aws_iam_role" "exec" {
  name               = "${local.prefix}-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "exec" {
  role       = aws_iam_role.exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "exec_secret" {
  name = "read-secret"
  role = aws_iam_role.exec.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "secretsmanager:GetSecretValue", Resource = var.secret_arn }]
  })
}

resource "aws_ecs_task_definition" "this" {
  family                   = local.prefix
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 1024
  memory                   = 2048
  execution_role_arn       = aws_iam_role.exec.arn
  container_definitions = jsonencode([{
    name         = local.name
    image        = var.image
    portMappings = [{ containerPort = local.port }]
    environment = [
      { name = "PHOENIX_HOST_ROOT_PATH", value = local.root_path }, # UI links carry /phoenix
      { name = "PHOENIX_ENABLE_AUTH", value = "true" },             # the UI is on the public ALB
      { name = "PHOENIX_WORKING_DIR", value = "/tmp/phoenix" },
    ]
    secrets = [
      { name = "PHOENIX_SECRET", valueFrom = "${var.secret_arn}:secret::" },
      { name = "PHOENIX_ADMIN_SECRET", valueFrom = "${var.secret_arn}:admin_secret::" },
      { name = "PHOENIX_DEFAULT_ADMIN_INITIAL_PASSWORD", valueFrom = "${var.secret_arn}:admin_password::" },
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options   = { awslogs-group = aws_cloudwatch_log_group.this.name, awslogs-region = var.region, awslogs-stream-prefix = "app" }
    }
  }])
}

# Agents find the task at phoenix.ai4all-<env>.local without going through the public ALB.
resource "aws_service_discovery_private_dns_namespace" "this" {
  name = "ai4all-${var.env}.local"
  vpc  = var.vpc_id
}

resource "aws_service_discovery_service" "this" {
  name = local.name
  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.this.id
    dns_records {
      type = "A"
      ttl  = 10
    }
  }
  force_destroy = true # deregister leftover task records on destroy
}

resource "aws_security_group" "this" {
  name   = local.prefix
  vpc_id = var.vpc_id
  ingress {
    description     = "UI through the load balancer, traces from the agents"
    from_port       = local.port
    to_port         = local.port
    protocol        = "tcp"
    security_groups = concat([var.alb_security_group_id], var.client_security_group_ids)
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] # image pull from Docker Hub and Secrets Manager through the NAT gateway
  }
}

resource "aws_lb_target_group" "this" {
  name                 = substr(local.prefix, 0, 32)
  port                 = local.port
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = var.vpc_id
  deregistration_delay = 30
  health_check {
    path    = "${local.root_path}/healthz" # Phoenix accepts paths with or without the root path
    matcher = "200"
  }
}

resource "aws_lb_listener_rule" "this" {
  listener_arn = var.listener_arn
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }
  condition {
    path_pattern { values = [local.root_path, "${local.root_path}/*"] }
  }
}

resource "aws_ecs_service" "this" {
  name                              = local.name
  cluster                           = var.cluster_arn
  task_definition                   = aws_ecs_task_definition.this.arn
  desired_count                     = 1 # SQLite on local disk: one task only
  health_check_grace_period_seconds = 120
  launch_type                       = "FARGATE"
  # Stop the old task before starting the new one, as two SQLite stores would split the traces.
  deployment_minimum_healthy_percent = 0
  deployment_maximum_percent         = 100
  network_configuration {
    subnets         = var.subnet_ids
    security_groups = [aws_security_group.this.id]
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.this.arn
    container_name   = local.name
    container_port   = local.port
  }
  service_registries {
    registry_arn = aws_service_discovery_service.this.arn
  }
  depends_on = [aws_lb_listener_rule.this]
}
