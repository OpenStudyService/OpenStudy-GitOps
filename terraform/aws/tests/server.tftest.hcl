mock_provider "aws" {
  mock_data "aws_availability_zones" {
    defaults = {
      names = ["ap-northeast-2a"]
    }
  }

  mock_data "aws_ssm_parameter" {
    defaults = {
      value = "ami-0123456789abcdef0"
    }
  }
}

variables {
  aws_account_id      = "123456789012"
  free_tier_confirmed = true
}

run "server_security" {
  command = plan

  assert {
    condition     = length(aws_security_group.server.ingress) == 0
    error_message = "The server must not expose any inbound ports."
  }

  assert {
    condition     = aws_instance.server.metadata_options[0].http_tokens == "required" && aws_instance.server.metadata_options[0].http_put_response_hop_limit == 1
    error_message = "Require IMDSv2 and keep metadata responses to one network hop."
  }

  assert {
    condition     = aws_instance.server.disable_api_termination && !aws_instance.server.root_block_device[0].delete_on_termination && aws_instance.server.root_block_device[0].encrypted
    error_message = "Protect the instance from termination and retain the encrypted root volume."
  }

  assert {
    condition     = aws_instance.server.credit_specification[0].cpu_credits == "standard"
    error_message = "Use standard CPU credits to avoid unlimited-mode surplus charges."
  }

  assert {
    condition     = jsondecode(aws_iam_role_policy.tunnel_token.policy).Statement[0].Resource == "arn:aws:ssm:ap-northeast-2:123456789012:parameter/openstudy-prod/cloudflared/token" && !contains(jsondecode(aws_iam_role_policy.session_manager.policy).Statement[0].Action, "ssm:GetParameter")
    error_message = "Token access must remain limited to the dedicated SSM parameter."
  }

  assert {
    condition     = output.container_platform == "linux/arm64" && strcontains(data.aws_ssm_parameter.al2023.name, "arm64") && strcontains(local.user_data, "cloudflared-linux-aarch64.rpm")
    error_message = "The AMI, cloudflared RPM and application images must match Graviton."
  }
}

run "legacy_x86" {
  command = plan

  variables {
    instance_type = "t3.micro"
  }

  assert {
    condition     = output.container_platform == "linux/amd64" && strcontains(data.aws_ssm_parameter.al2023.name, "x86_64") && strcontains(local.user_data, "cloudflared-linux-x86_64.rpm")
    error_message = "The t3.micro alternative must use x86 AMIs and binaries."
  }
}

run "require_free_tier_review" {
  command = plan

  variables {
    free_tier_confirmed = false
  }

  expect_failures = [aws_instance.server]
}
