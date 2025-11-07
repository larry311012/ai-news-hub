# ============================================================================
# AWS Infrastructure for AI Post Generator
# ============================================================================
# This Terraform configuration deploys a production-ready FastAPI backend
# with PostgreSQL RDS, Redis ElastiCache, S3 storage, and CloudFront CDN.
# ============================================================================

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Backend for state management
  backend "s3" {
    bucket         = "ai-post-generator-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-locks"
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "ai-post-generator"
      Environment = var.environment
      ManagedBy   = "terraform"
      CostCenter  = "engineering"
    }
  }
}

# ============================================================================
# Variables
# ============================================================================

variable "aws_region" {
  description = "AWS region for resources"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name (dev, staging, production)"
  type        = string
  default     = "production"
}

variable "project_name" {
  description = "Project name for resource naming"
  type        = string
  default     = "ai-post-gen"
}

variable "domain_name" {
  description = "Domain name for the application"
  type        = string
  default     = "app.aipostgenerator.com"
}

variable "api_domain_name" {
  description = "API subdomain"
  type        = string
  default     = "api.aipostgenerator.com"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"  # Free tier eligible, upgrade to db.t3.small for production
}

variable "ecs_task_cpu" {
  description = "ECS task CPU units"
  type        = number
  default     = 512  # 0.5 vCPU
}

variable "ecs_task_memory" {
  description = "ECS task memory in MB"
  type        = number
  default     = 1024  # 1 GB
}

variable "ecs_desired_count" {
  description = "Desired number of ECS tasks"
  type        = number
  default     = 2
}

variable "enable_deletion_protection" {
  description = "Enable deletion protection on critical resources"
  type        = bool
  default     = true
}

# ============================================================================
# Data Sources
# ============================================================================

data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

# ============================================================================
# VPC and Networking
# ============================================================================

module "vpc" {
  source = "./modules/vpc"

  project_name = var.project_name
  environment  = var.environment

  vpc_cidr            = "10.0.0.0/16"
  availability_zones  = slice(data.aws_availability_zones.available.names, 0, 3)

  public_subnet_cidrs  = ["10.0.1.0/24", "10.0.2.0/24", "10.0.3.0/24"]
  private_subnet_cidrs = ["10.0.11.0/24", "10.0.12.0/24", "10.0.13.0/24"]
  database_subnet_cidrs = ["10.0.21.0/24", "10.0.22.0/24", "10.0.23.0/24"]

  enable_nat_gateway = true
  single_nat_gateway = var.environment != "production"  # Use single NAT for dev/staging
}

# ============================================================================
# Security Groups
# ============================================================================

module "security_groups" {
  source = "./modules/security"

  project_name = var.project_name
  environment  = var.environment
  vpc_id       = module.vpc.vpc_id
}

# ============================================================================
# RDS PostgreSQL Database
# ============================================================================

module "rds" {
  source = "./modules/rds"

  project_name = var.project_name
  environment  = var.environment

  instance_class         = var.db_instance_class
  allocated_storage      = 20
  max_allocated_storage  = 100

  database_name = "aipostsdb"
  username      = "aipostadmin"

  vpc_id                  = module.vpc.vpc_id
  subnet_ids              = module.vpc.database_subnet_ids
  security_group_ids      = [module.security_groups.rds_security_group_id]

  multi_az                = var.environment == "production"
  backup_retention_period = var.environment == "production" ? 7 : 3
  deletion_protection     = var.enable_deletion_protection

  enable_performance_insights = var.environment == "production"
}

# ============================================================================
# ElastiCache Redis
# ============================================================================

module "redis" {
  source = "./modules/elasticache"

  project_name = var.project_name
  environment  = var.environment

  node_type          = "cache.t3.micro"
  num_cache_nodes    = 1
  parameter_group    = "default.redis7"
  engine_version     = "7.0"

  subnet_ids         = module.vpc.private_subnet_ids
  security_group_ids = [module.security_groups.redis_security_group_id]
}

# ============================================================================
# S3 Buckets
# ============================================================================

# Frontend static assets
module "s3_frontend" {
  source = "./modules/s3"

  bucket_name = "${var.project_name}-frontend-${var.environment}"

  enable_versioning = true
  enable_website    = true

  cors_rules = [
    {
      allowed_headers = ["*"]
      allowed_methods = ["GET", "HEAD"]
      allowed_origins = ["https://${var.domain_name}"]
      expose_headers  = ["ETag"]
      max_age_seconds = 3600
    }
  ]
}

# Instagram images and user uploads
module "s3_uploads" {
  source = "./modules/s3"

  bucket_name = "${var.project_name}-uploads-${var.environment}"

  enable_versioning = true

  lifecycle_rules = [
    {
      id      = "delete-old-thumbnails"
      enabled = true
      prefix  = "thumbnails/"
      expiration_days = 90
    }
  ]

  cors_rules = [
    {
      allowed_headers = ["*"]
      allowed_methods = ["GET", "PUT", "POST"]
      allowed_origins = ["https://${var.domain_name}", "https://${var.api_domain_name}"]
      expose_headers  = ["ETag"]
      max_age_seconds = 3600
    }
  ]
}

# Backups and logs
module "s3_backups" {
  source = "./modules/s3"

  bucket_name = "${var.project_name}-backups-${var.environment}"

  enable_versioning = true

  lifecycle_rules = [
    {
      id              = "archive-old-backups"
      enabled         = true
      prefix          = "database/"
      transition_days = 30
      storage_class   = "GLACIER"
    },
    {
      id              = "delete-very-old-backups"
      enabled         = true
      prefix          = "database/"
      expiration_days = 365
    }
  ]
}

# ============================================================================
# CloudFront CDN
# ============================================================================

module "cloudfront_frontend" {
  source = "./modules/cloudfront"

  project_name = var.project_name
  environment  = var.environment

  domain_name     = var.domain_name
  s3_bucket_name  = module.s3_frontend.bucket_name
  s3_bucket_domain = module.s3_frontend.bucket_regional_domain_name

  enable_ipv6 = true
  price_class = "PriceClass_100"  # US, Canada, Europe

  certificate_arn = aws_acm_certificate.frontend.arn
}

module "cloudfront_uploads" {
  source = "./modules/cloudfront"

  project_name = var.project_name
  environment  = var.environment

  domain_name     = "cdn.${var.domain_name}"
  s3_bucket_name  = module.s3_uploads.bucket_name
  s3_bucket_domain = module.s3_uploads.bucket_regional_domain_name

  enable_ipv6 = true
  price_class = "PriceClass_100"

  certificate_arn = aws_acm_certificate.cdn.arn
}

# ============================================================================
# ECS Cluster and Services
# ============================================================================

module "ecs_cluster" {
  source = "./modules/ecs"

  project_name = var.project_name
  environment  = var.environment

  # Cluster settings
  enable_container_insights = true

  # Service configuration
  task_cpu              = var.ecs_task_cpu
  task_memory           = var.ecs_task_memory
  desired_count         = var.ecs_desired_count
  min_capacity          = 1
  max_capacity          = 10

  # Networking
  vpc_id                = module.vpc.vpc_id
  private_subnet_ids    = module.vpc.private_subnet_ids
  public_subnet_ids     = module.vpc.public_subnet_ids
  security_group_ids    = [module.security_groups.ecs_security_group_id]

  # Load Balancer
  alb_security_group_id = module.security_groups.alb_security_group_id
  certificate_arn       = aws_acm_certificate.api.arn

  # Container settings
  container_image       = "${data.aws_caller_identity.current.account_id}.dkr.ecr.${var.aws_region}.amazonaws.com/${var.project_name}-backend:latest"
  container_port        = 8000

  # Environment variables
  environment_variables = {
    ENVIRONMENT           = var.environment
    DATABASE_URL          = module.rds.connection_string
    REDIS_URL             = module.redis.endpoint
    AWS_S3_BUCKET         = module.s3_uploads.bucket_name
    AWS_CLOUDFRONT_DOMAIN = module.cloudfront_uploads.domain_name
    IMAGE_STORAGE_BACKEND = "s3"
    LOG_LEVEL             = "INFO"
  }

  # Secrets from AWS Secrets Manager
  secrets = {
    ENCRYPTION_KEY            = aws_secretsmanager_secret.encryption_key.arn
    OPENAI_API_KEY            = aws_secretsmanager_secret.openai_api_key.arn
    GOOGLE_CLIENT_SECRET      = aws_secretsmanager_secret.google_oauth.arn
    GITHUB_CLIENT_SECRET      = aws_secretsmanager_secret.github_oauth.arn
    LINKEDIN_CLIENT_SECRET    = aws_secretsmanager_secret.linkedin_oauth.arn
    TWITTER_API_SECRET        = aws_secretsmanager_secret.twitter_oauth.arn
    THREADS_CLIENT_SECRET     = aws_secretsmanager_secret.threads_oauth.arn
    INSTAGRAM_APP_SECRET      = aws_secretsmanager_secret.instagram_oauth.arn
    SENDGRID_API_KEY          = aws_secretsmanager_secret.sendgrid_api_key.arn
  }

  # Health check
  health_check_path     = "/health"
  health_check_interval = 30

  # Auto-scaling based on CPU and memory
  cpu_target_value    = 70
  memory_target_value = 80
}

# ============================================================================
# ECR Repository
# ============================================================================

resource "aws_ecr_repository" "backend" {
  name                 = "${var.project_name}-backend"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }

  encryption_configuration {
    encryption_type = "AES256"
  }

  tags = {
    Name = "${var.project_name}-backend"
  }
}

resource "aws_ecr_lifecycle_policy" "backend" {
  repository = aws_ecr_repository.backend.name

  policy = jsonencode({
    rules = [
      {
        rulePriority = 1
        description  = "Keep last 10 images"
        selection = {
          tagStatus     = "tagged"
          tagPrefixList = ["v"]
          countType     = "imageCountMoreThan"
          countNumber   = 10
        }
        action = {
          type = "expire"
        }
      },
      {
        rulePriority = 2
        description  = "Delete untagged images after 7 days"
        selection = {
          tagStatus   = "untagged"
          countType   = "sinceImagePushed"
          countUnit   = "days"
          countNumber = 7
        }
        action = {
          type = "expire"
        }
      }
    ]
  })
}

# ============================================================================
# AWS Secrets Manager
# ============================================================================

resource "aws_secretsmanager_secret" "encryption_key" {
  name                    = "${var.project_name}/${var.environment}/encryption-key"
  description             = "Encryption key for user API keys and sensitive data"
  recovery_window_in_days = 30
}

resource "aws_secretsmanager_secret" "openai_api_key" {
  name                    = "${var.project_name}/${var.environment}/openai-api-key"
  description             = "OpenAI API key for AI content generation"
  recovery_window_in_days = 30
}

resource "aws_secretsmanager_secret" "google_oauth" {
  name                    = "${var.project_name}/${var.environment}/google-oauth"
  description             = "Google OAuth client secret"
  recovery_window_in_days = 30
}

resource "aws_secretsmanager_secret" "github_oauth" {
  name                    = "${var.project_name}/${var.environment}/github-oauth"
  description             = "GitHub OAuth client secret"
  recovery_window_in_days = 30
}

resource "aws_secretsmanager_secret" "linkedin_oauth" {
  name                    = "${var.project_name}/${var.environment}/linkedin-oauth"
  description             = "LinkedIn OAuth client secret"
  recovery_window_in_days = 30
}

resource "aws_secretsmanager_secret" "twitter_oauth" {
  name                    = "${var.project_name}/${var.environment}/twitter-oauth"
  description             = "Twitter OAuth API secret"
  recovery_window_in_days = 30
}

resource "aws_secretsmanager_secret" "threads_oauth" {
  name                    = "${var.project_name}/${var.environment}/threads-oauth"
  description             = "Threads OAuth client secret"
  recovery_window_in_days = 30
}

resource "aws_secretsmanager_secret" "instagram_oauth" {
  name                    = "${var.project_name}/${var.environment}/instagram-oauth"
  description             = "Instagram OAuth app secret"
  recovery_window_in_days = 30
}

resource "aws_secretsmanager_secret" "sendgrid_api_key" {
  name                    = "${var.project_name}/${var.environment}/sendgrid-api-key"
  description             = "SendGrid API key for email notifications"
  recovery_window_in_days = 30
}

# ============================================================================
# ACM Certificates
# ============================================================================

resource "aws_acm_certificate" "frontend" {
  domain_name       = var.domain_name
  validation_method = "DNS"

  subject_alternative_names = [
    "*.${var.domain_name}"
  ]

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${var.project_name}-frontend-cert"
  }
}

resource "aws_acm_certificate" "api" {
  domain_name       = var.api_domain_name
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${var.project_name}-api-cert"
  }
}

resource "aws_acm_certificate" "cdn" {
  provider = aws.us-east-1  # CloudFront requires certs in us-east-1

  domain_name       = "cdn.${var.domain_name}"
  validation_method = "DNS"

  lifecycle {
    create_before_destroy = true
  }

  tags = {
    Name = "${var.project_name}-cdn-cert"
  }
}

# ============================================================================
# CloudWatch Alarms and Monitoring
# ============================================================================

module "monitoring" {
  source = "./modules/monitoring"

  project_name = var.project_name
  environment  = var.environment

  # ECS monitoring
  ecs_cluster_name = module.ecs_cluster.cluster_name
  ecs_service_name = module.ecs_cluster.service_name

  # RDS monitoring
  rds_instance_id = module.rds.instance_id

  # ALB monitoring
  alb_arn_suffix = module.ecs_cluster.alb_arn_suffix
  target_group_arn_suffix = module.ecs_cluster.target_group_arn_suffix

  # Alarm notification SNS topic
  alarm_email = "alerts@aipostgenerator.com"
}

# ============================================================================
# Outputs
# ============================================================================

output "alb_dns_name" {
  description = "Application Load Balancer DNS name"
  value       = module.ecs_cluster.alb_dns_name
}

output "cloudfront_frontend_domain" {
  description = "CloudFront distribution domain for frontend"
  value       = module.cloudfront_frontend.domain_name
}

output "cloudfront_cdn_domain" {
  description = "CloudFront distribution domain for uploads CDN"
  value       = module.cloudfront_uploads.domain_name
}

output "rds_endpoint" {
  description = "RDS database endpoint"
  value       = module.rds.endpoint
  sensitive   = true
}

output "redis_endpoint" {
  description = "Redis cache endpoint"
  value       = module.redis.endpoint
  sensitive   = true
}

output "ecr_repository_url" {
  description = "ECR repository URL for Docker images"
  value       = aws_ecr_repository.backend.repository_url
}

output "s3_frontend_bucket" {
  description = "S3 bucket for frontend static assets"
  value       = module.s3_frontend.bucket_name
}

output "s3_uploads_bucket" {
  description = "S3 bucket for user uploads"
  value       = module.s3_uploads.bucket_name
}
