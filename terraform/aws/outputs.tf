output "instance_id" {
  description = "EC2 instance ID for Session Manager."
  value       = aws_instance.server.id
}

output "aws_account_id" {
  value = var.aws_account_id
}

output "aws_region" {
  value = var.aws_region
}

output "tunnel_token_parameter_name" {
  description = "Store the token here with scripts/configure-tunnel.py; the token is not managed by Terraform."
  value       = local.token_path
}

output "container_platform" {
  description = "Required platform for application images."
  value       = var.instance_type == "t4g.small" ? "linux/arm64" : "linux/amd64"
}
