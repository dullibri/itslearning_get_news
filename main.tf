# Configure the AWS provider
provider "aws" {
  region = "eu-central-1"
}

# Create an ECR repository
resource "aws_ecr_repository" "app_repo" {
  name = "itslearning-scraper"
}

# Create an ECS cluster
resource "aws_ecs_cluster" "app_cluster" {
  name = "itslearning-scraper-cluster"
}

# Create an ECS task definition
resource "aws_ecs_task_definition" "app_task" {
  family                   = "itslearning-scraper-task"
  container_definitions    = jsonencode([
    {
      name  = "itslearning-scraper"
      image = "${aws_ecr_repository.app_repo.repository_url}:latest"
      environment = [
        { name = "ITSLEARNING_USERNAME", value = var.itslearning_username },
        { name = "ITSLEARNING_PASSWORD", value = var.itslearning_password },
        { name = "SMTP_SERVER", value = var.smtp_server },
        { name = "SMTP_PORT", value = var.smtp_port },
        { name = "SMTP_USERNAME", value = var.smtp_username },
        { name = "SMTP_PASSWORD", value = var.smtp_password },
        { name = "EMAIL_FROM", value = var.email_from },
        { name = "EMAIL_TO", value = var.email_to }
      ]
    }
  ])
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.ecs_execution_role.arn
}

# Create an IAM role for ECS task execution
resource "aws_iam_role" "ecs_execution_role" {
  name = "ecs_execution_role"

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

# Attach necessary policies to the ECS execution role
resource "aws_iam_role_policy_attachment" "ecs_execution_role_policy" {
  role       = aws_iam_role.ecs_execution_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# Create an EventBridge rule to trigger the ECS task daily
resource "aws_cloudwatch_event_rule" "daily_task" {
  name                = "run-itslearning-scraper-daily"
  description         = "Triggers itslearning scraper daily at 12:00 PM CET"
  schedule_expression = "cron(0 11 * * ? *)"  # 11:00 UTC = 12:00 CET (adjust for daylight saving time if needed)
}

# Create an EventBridge target for the ECS task
resource "aws_cloudwatch_event_target" "ecs_task_target" {
  rule      = aws_cloudwatch_event_rule.daily_task.name
  target_id = "RunItslearningScraper"
  arn       = aws_ecs_cluster.app_cluster.arn
  role_arn  = aws_iam_role.eventbridge_role.arn

  ecs_target {
    task_count          = 1
    task_definition_arn = aws_ecs_task_definition.app_task.arn
    launch_type         = "FARGATE"
    network_configuration {
      subnets         = ["subnet-xxxxxxxxxxxxxxxxx"]  # Replace with your subnet ID
      security_groups = ["sg-xxxxxxxxxxxxxxxxx"]      # Replace with your security group ID
      assign_public_ip = true
    }
  }
}

# Create an IAM role for EventBridge to run ECS tasks
resource "aws_iam_role" "eventbridge_role" {
  name = "eventbridge_ecs_role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })
}

# Attach necessary policies to the EventBridge role
resource "aws_iam_role_policy_attachment" "eventbridge_role_policy" {
  role       = aws_iam_role.eventbridge_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceEventsRole"
}

# Define variables for sensitive information
variable "itslearning_username" {
  type = string
}

variable "itslearning_password" {
  type = string
}

variable "smtp_server" {
  type = string
}

variable "smtp_port" {
  type = string
}

variable "smtp_username" {
  type = string
}

variable "smtp_password" {
  type = string
}

variable "email_from" {
  type = string
}

variable "email_to" {
  type = string
}