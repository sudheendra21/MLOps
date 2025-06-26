terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}
 
provider "aws" {
  region = var.aws_region
}
 
# Data sources
data "aws_availability_zones" "available" {
  state = "available"
}
 
data "aws_caller_identity" "current" {}
 
# VPC and Networking
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true
 
  tags = {
    Name = "${var.project_name}-vpc"
  }
}
 
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
 
  tags = {
    Name = "${var.project_name}-igw"
  }
}
 
resource "aws_subnet" "public" {
  count = 2
 
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.${count.index + 1}.0/24"
  availability_zone       = data.aws_availability_zones.available.names[count.index]
  map_public_ip_on_launch = true
 
  tags = {
    Name = "${var.project_name}-public-subnet-${count.index + 1}"
  }
}
 
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id
 
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }
 
  tags = {
    Name = "${var.project_name}-public-rt"
  }
}
 
resource "aws_route_table_association" "public" {
  count = 2
 
  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
 
# Security Groups
resource "aws_security_group" "alb" {
  name        = "${var.project_name}-alb-sg"
  description = "Security group for ALB"
  vpc_id      = aws_vpc.main.id
 
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
 
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
 
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
 
  tags = {
    Name = "${var.project_name}-alb-sg"
  }
}
 
resource "aws_security_group" "ecs_tasks" {
  name        = "${var.project_name}-ecs-tasks-sg"
  description = "Security group for ECS tasks"
  vpc_id      = aws_vpc.main.id
 
  ingress {
    from_port       = 0
    to_port         = 65535
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
 
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
 
  tags = {
    Name = "${var.project_name}-ecs-tasks-sg"
  }
}
 
# Application Load Balancer
resource "aws_lb" "main" {
  name               = "${var.project_name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
 
  enable_deletion_protection = false
 
  tags = {
    Name = "${var.project_name}-alb"
  }
}
 
# Target Groups
resource "aws_lb_target_group" "frontend" {
  name        = "${var.project_name}-frontend-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "instance"
 
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/"
    matcher             = "200"
  }
 
  lifecycle {
    create_before_destroy = true
    ignore_changes        = [name]
  }
 
  tags = {
    Name = "${var.project_name}-frontend-tg"
  }
}
 
resource "aws_lb_target_group" "detect_backend" {
  name        = "${var.project_name}-detect-tg"
  port        = 5000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "instance"
 
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }
 
  lifecycle {
    create_before_destroy = true
    ignore_changes        = [name]
  }
 
  tags = {
    Name = "${var.project_name}-detect-tg"
  }
}
 
resource "aws_lb_target_group" "depth_backend" {
  name        = "${var.project_name}-depth-tg"
  port        = 5000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "instance"
 
  health_check {
    enabled             = true
    healthy_threshold   = 2
    unhealthy_threshold = 2
    timeout             = 5
    interval            = 30
    path                = "/health"
    matcher             = "200"
  }
 
  lifecycle {
    create_before_destroy = true
    ignore_changes        = [name]
  }
 
  tags = {
    Name = "${var.project_name}-depth-tg"
  }
}
 
 
# ALB Listener
resource "aws_lb_listener" "main" {
  load_balancer_arn = aws_lb.main.arn
  port              = "80"
  protocol          = "HTTP"
 
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}
 
# ALB Listener Rules
resource "aws_lb_listener_rule" "detect_api" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 100
 
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.detect_backend.arn
  }
 
  condition {
    path_pattern {
      values = ["/detect/*"]
    }
  }
}
 
resource "aws_lb_listener_rule" "depth_api" {
  listener_arn = aws_lb_listener.main.arn
  priority     = 200
 
  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.depth_backend.arn
  }
 
  condition {
    path_pattern {
      values = ["/depth/*"]
    }
  }
}
 
# CloudWatch Log Groups
resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/ecs/${var.project_name}-frontend"
  retention_in_days = 7
}
 
resource "aws_cloudwatch_log_group" "detect_backend" {
  name              = "/ecs/${var.project_name}-detect-backend"
  retention_in_days = 7
}
 
resource "aws_cloudwatch_log_group" "depth_backend" {
  name              = "/ecs/${var.project_name}-depth-backend"
  retention_in_days = 7
}
 
# ECS Cluster
resource "aws_ecs_cluster" "main" {
  name = "${var.project_name}-cluster"
 
  configuration {
    execute_command_configuration {
      logging = "OVERRIDE"
      log_configuration {
        cloud_watch_log_group_name = aws_cloudwatch_log_group.frontend.name
      }
    }
  }
}
 
# ECS Task Definitions
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${var.project_name}-frontend"
  network_mode             = "bridge"
#   requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
 
  container_definitions = jsonencode([
    {
      name  = "frontend"
      image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/object-detection/frontend:latest"
     
      portMappings = [
        {
          containerPort = 3000
          protocol      = "tcp"
        }
      ]
 
      environment = [
        {
          name  = "REACT_APP_DETECT_API_URL"
          value = "http://${aws_lb.main.dns_name}/detect"
        },
        {
          name  = "REACT_APP_DEPTH_API_URL"
          value = "http://${aws_lb.main.dns_name}/depth"
        }
      ]
 
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.frontend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
 
      essential = true
    }
  ])
}
 
resource "aws_ecs_task_definition" "detect_backend" {
  family                   = "${var.project_name}-detect-backend"
  network_mode             = "bridge"
#   requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
 
  container_definitions = jsonencode([
    {
      name  = "detect-backend"
      image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/object-detection/detect:latest"
     
      portMappings = [
        {
          containerPort = 5000
          protocol      = "tcp"
        }
      ]
 
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.detect_backend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
 
      essential = true
    }
  ])
}
 
resource "aws_ecs_task_definition" "depth_backend" {
  family                   = "${var.project_name}-depth-backend"
  network_mode             = "bridge"
#   requires_compatibilities = ["FARGATE"]
  cpu                      = "1024"
  memory                   = "2048"
  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
 
  container_definitions = jsonencode([
    {
      name  = "depth-backend"
      image = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/object-detection/depth:latest"
     
      portMappings = [
        {
          containerPort = 5000
          protocol      = "tcp"
        }
      ]
 
      logConfiguration = {
        logDriver = "awslogs"
        options = {
          awslogs-group         = aws_cloudwatch_log_group.depth_backend.name
          awslogs-region        = var.aws_region
          awslogs-stream-prefix = "ecs"
        }
      }
 
      essential = true
    }
  ])
}
 
 
# ECS Services
resource "aws_ecs_service" "frontend" {
  name            = "${var.project_name}-frontend-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"
 
  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.public[*].id
    assign_public_ip = true
  }
 
  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 3000
  }
 
  depends_on = [
    aws_lb_listener.main,
    aws_lb_target_group.frontend
  ]
 
  lifecycle {
    ignore_changes = [desired_count]
  }
}
 
 
resource "aws_ecs_service" "detect_backend" {
  name            = "${var.project_name}-detect-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.detect_backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"
 
  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.public[*].id
    assign_public_ip = true
  }
 
  load_balancer {
    target_group_arn = aws_lb_target_group.detect_backend.arn
    container_name   = "detect-backend"
    container_port   = 5000
  }
 
  depends_on = [aws_lb_listener.main]
 
  lifecycle {
    ignore_changes = [desired_count]
  }
}
 
resource "aws_ecs_service" "depth_backend" {
  name            = "${var.project_name}-depth-service"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.depth_backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"
 
  network_configuration {
    security_groups  = [aws_security_group.ecs_tasks.id]
    subnets          = aws_subnet.public[*].id
    assign_public_ip = true
  }
 
  load_balancer {
    target_group_arn = aws_lb_target_group.depth_backend.arn
    container_name   = "depth-backend"
    container_port   = 5000
  }
 
  depends_on = [aws_lb_listener.main]
 
  lifecycle {
    ignore_changes = [desired_count]
  }
}
 
# Auto Scaling
resource "aws_appautoscaling_target" "frontend" {
  max_capacity       = 5
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.frontend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}
 
resource "aws_appautoscaling_policy" "frontend_up" {
  name               = "${var.project_name}-frontend-scale-up"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.frontend.resource_id
  scalable_dimension = aws_appautoscaling_target.frontend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.frontend.service_namespace
 
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
 
resource "aws_appautoscaling_target" "detect_backend" {
  max_capacity       = 5
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.detect_backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}
 
resource "aws_appautoscaling_policy" "detect_backend_up" {
  name               = "${var.project_name}-detect-scale-up"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.detect_backend.resource_id
  scalable_dimension = aws_appautoscaling_target.detect_backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.detect_backend.service_namespace
 
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
 
resource "aws_appautoscaling_target" "depth_backend" {
  max_capacity       = 5
  min_capacity       = 1
  resource_id        = "service/${aws_ecs_cluster.main.name}/${aws_ecs_service.depth_backend.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}
 
resource "aws_appautoscaling_policy" "depth_backend_up" {
  name               = "${var.project_name}-depth-scale-up"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.depth_backend.resource_id
  scalable_dimension = aws_appautoscaling_target.depth_backend.scalable_dimension
  service_namespace  = aws_appautoscaling_target.depth_backend.service_namespace
 
  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
 
# IAM Role for ECS Task Execution
resource "aws_iam_role" "ecs_task_execution_role" {
  name = "${var.project_name}-ecs-task-execution-role"
 
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ecs-tasks.amazonaws.com"
        }
      }
    ]
  })
}
 
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}
 
resource "aws_iam_role_policy_attachment" "ecs_task_execution_role_ecr_policy" {
  role       = aws_iam_role.ecs_task_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
}
 
variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"  # Change to your preferred region
}
 
variable "project_name" {
  description = "MLOps"
  type        = string
  default     = "mlops-yolo"
}
 