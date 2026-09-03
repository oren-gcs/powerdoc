terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = { source = "hashicorp/aws", version = "~> 5.0" }
  }
}

variable "region" { default = "us-east-1" }
variable "name" { default = "docflow" }

provider "aws" { region = var.region }

data "aws_availability_zones" "az" { state = "available" }

resource "aws_vpc" "this" {
  cidr_block           = "10.40.0.0/16"
  enable_dns_hostnames = true
  tags                 = { Name = "${var.name}-vpc" }
}

resource "aws_internet_gateway" "igw" { vpc_id = aws_vpc.this.id }

resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.this.id
  cidr_block              = cidrsubnet(aws_vpc.this.cidr_block, 8, count.index)
  availability_zone       = data.aws_availability_zones.az.names[count.index]
  map_public_ip_on_launch = true
}

resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.this.id
  cidr_block        = cidrsubnet(aws_vpc.this.cidr_block, 8, count.index + 10)
  availability_zone = data.aws_availability_zones.az.names[count.index]
}

resource "aws_s3_bucket" "docs" {
  bucket = "${var.name}-documents-${var.region}"
}

resource "aws_db_subnet_group" "db" {
  name       = "${var.name}-db"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "pg" {
  identifier             = "${var.name}-pg"
  engine                 = "postgres"
  engine_version         = "16"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  username               = "docflow"
  password               = "ChangeMeBeforeApply1"
  db_subnet_group_name   = aws_db_subnet_group.db.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = true
}

resource "aws_security_group" "alb" {
  name   = "${var.name}-alb"
  vpc_id = aws_vpc.this.id
  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "svc" {
  name   = "${var.name}-svc"
  vpc_id = aws_vpc.this.id
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_security_group" "db" {
  name   = "${var.name}-db"
  vpc_id = aws_vpc.this.id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.svc.id]
  }
}

resource "aws_ecs_cluster" "this" { name = var.name }

resource "aws_iam_role" "exec" {
  name = "${var.name}-ecs-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "exec" {
  role       = aws_iam_role.exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_lb" "this" {
  name               = var.name
  load_balancer_type = "application"
  subnets            = aws_subnet.public[*].id
  security_groups    = [aws_security_group.alb.id]
}

resource "aws_lb_target_group" "api" {
  name     = "${var.name}-api"
  port     = 8000
  protocol = "HTTP"
  vpc_id   = aws_vpc.this.id
  health_check { path = "/health" }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.this.arn
  port              = 80
  protocol          = "HTTP"
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }
}

output "alb_dns" { value = aws_lb.this.dns_name }
output "s3_bucket" { value = aws_s3_bucket.docs.bucket }
output "rds_endpoint" { value = aws_db_instance.pg.address }
