output "s3_memory_bucket" {
  value = aws_s3_bucket.memory.bucket
}

output "s3_memory_bucket_arn" {
  value = aws_s3_bucket.memory.arn
}

output "s3_frontend_bucket" {
  value = aws_s3_bucket.frontend.bucket
}

output "s3_frontend_bucket_arn" {
  value = aws_s3_bucket.frontend.arn
}

output "s3_frontend_website_endpoint" {
  value = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

output "lambda_function_name" {
  description = "Name of the Lambda function"
  value       = aws_lambda_function.twin.function_name
}

output "api_gateway_url" {
  description = "URL of the API Gateway"
  value       = aws_apigatewayv2_api.main.api_endpoint
}

output "cloudfront_domain_url" {
  value       = aws_cloudfront_distribution.s3_distribution.domain_name
  description = "URL of the CloudFront distribution"
}

output "cloudfront_url" {
  description = "URL of the CloudFront distribution"
  value       = "https://${aws_cloudfront_distribution.s3_distribution.domain_name}"
}
