variable "project_name" {
  type        = string
  description = "Name prefix for all the resources"
  validation {
    condition     = can(regex("^[a-z0-9-]+$", var.project_name))
    error_message = "Project name must contain only lowercase letters, numbers, and hyphens."
  }
}

variable "environment" {
  type        = string
  description = "Environment name (dev, test, prod)"

  validation {
    condition     = contains(["dev", "test", "prod"], var.environment)
    error_message = "Environment must be one of:dev,test,prod."
  }
}

variable "bedrock_model_id" {
  type        = string
  description = "Bedrock model ID"
  default     = "amazon.nova-micro-v1:0"
}

variable "lamda_timeout" {
  type        = number
  description = "Lambda function timeout in seconds"
  default     = 60
}

variable "api_throttle_burst_limit" {
  type        = number
  description = "API Gateway throttle burst limit"
  default     = 10
}
variable "api_throttle_rate_limit" {
  type        = number
  description = "API Gateway throttle rate limit"
  default     = 5
}

variable "use_custom_domain" {
  type        = bool
  description = "Attach a custom domain to CloudFront"
  default     = false
}

variable "root_domain" {
  type        = string
  description = "Apex domain name, e.g. mydomain.com"
  default     = ""
}

