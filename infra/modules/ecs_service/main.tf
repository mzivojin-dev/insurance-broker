resource "aws_ecr_repository" "this" {
  name                 = "ai4all/${var.name}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = var.ephemeral # destroy even with images in it
  image_scanning_configuration { scan_on_push = true }
}

resource "aws_ecs_task_definition" "this" {
  family                   = "ai4all-${var.env}-${var.name}"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.exec.arn
  task_role_arn            = aws_iam_role.task.arn
  container_definitions = jsonencode([{
    name         = var.name
    image        = "${aws_ecr_repository.this.repository_url}:${var.image_tag}"
    portMappings = [{ containerPort = 8080 }]
    environment  = [for k, v in var.environment : { name = k, value = v }]
    secrets      = [for k, arn in var.secrets : { name = k, valueFrom = arn }]
    logConfiguration = {
      logDriver = "awslogs"
      options   = { awslogs-group = "/ai4all/${var.env}/${var.name}", awslogs-region = var.region, awslogs-stream-prefix = "app" }
    }
    healthCheck = { command = ["CMD-SHELL", "python -c \"import urllib.request;urllib.request.urlopen('http://localhost:8080/health')\""] }
  }])
}

resource "aws_ecs_service" "this" {
  name                              = var.name
  cluster                           = var.cluster_arn
  task_definition                   = aws_ecs_task_definition.this.arn
  desired_count                     = var.desired_count
  health_check_grace_period_seconds = 60
  launch_type                       = "FARGATE"
  network_configuration {
    subnets         = var.subnet_ids
    security_groups = concat([aws_security_group.task.id], var.extra_security_group_ids)
  }
  load_balancer {
    target_group_arn = aws_lb_target_group.this.arn
    container_name   = var.name
    container_port   = 8080
  }
  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }
}

resource "aws_lb_listener_rule" "this" {
  listener_arn = var.listener_arn
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.this.arn
  }
  condition {
    path_pattern { values = ["/${var.name}/*"] }
  }
}
locals {
  prefix = "ai4all-${var.env}-${var.name}" # IAM roles must start with ai4all- (see infra/bootstrap)
  # "<arn>:username::" -> "<arn>" for the IAM policy
  secret_arns = distinct([for v in values(var.secrets) : regex("^arn:[^:]+:secretsmanager:[^:]+:[^:]+:secret:[^:]+", v)])
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/ai4all/${var.env}/${var.name}"
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

# Used by ECS itself: pull from ECR, write logs, read the secrets into env vars.
resource "aws_iam_role" "exec" {
  name               = "${local.prefix}-exec"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "exec" {
  role       = aws_iam_role.exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "exec_secrets" {
  count = length(var.secrets) > 0 ? 1 : 0
  name  = "read-secrets"
  role  = aws_iam_role.exec.id
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [{ Effect = "Allow", Action = "secretsmanager:GetSecretValue", Resource = local.secret_arns }]
  })
}

# Used by the agent code. Empty for now; agents that call AWS (S3, Textract, SQS) add policies later.
resource "aws_iam_role" "task" {
  name               = "${local.prefix}-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_security_group" "task" {
  name   = local.prefix
  vpc_id = var.vpc_id
  ingress {
    from_port       = 8080
    to_port         = 8080
    protocol        = "tcp"
    security_groups = [var.alb_security_group_id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"] # Anthropic API, ECR and Secrets Manager through the NAT gateway
  }
}

resource "aws_lb_target_group" "this" {
  name                 = substr(replace(local.prefix, "_", "-"), 0, 32) # letters, digits and hyphens only
  port                 = 8080
  protocol             = "HTTP"
  target_type          = "ip"
  vpc_id               = var.vpc_id
  deregistration_delay = 30
  health_check {
    path    = "/${var.name}/health" # the ALB keeps the prefix; agent_core.http.StripPrefix handles it
    matcher = "200"
  }
}
