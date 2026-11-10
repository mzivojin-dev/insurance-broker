resource "aws_ecr_repository" "this" {
  name                 = "ai4all/${var.name}"
  image_tag_mutability = "IMMUTABLE"
  force_delete         = var.ephemeral   # destroy even with images in it
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
      options = { awslogs-group = "/ai4all/${var.env}/${var.name}", awslogs-region = var.region, awslogs-stream-prefix = "app" }
    }
    healthCheck = { command = ["CMD-SHELL", "python -c \"import urllib.request;urllib.request.urlopen('http://localhost:8080/health')\""] }
  }])
}

resource "aws_ecs_service" "this" {
  name            = var.name
  cluster         = var.cluster_arn
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"
  network_configuration {
    subnets         = var.subnet_ids
    security_groups = [aws_security_group.task.id]
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