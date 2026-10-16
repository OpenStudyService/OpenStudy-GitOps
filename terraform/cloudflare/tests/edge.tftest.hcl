mock_provider "cloudflare" {
  mock_data "cloudflare_zone" {
    defaults = {
      id      = "11111111111111111111111111111111"
      name    = "example.com"
      account = { id = "00000000000000000000000000000000" }
      status  = "active"
      paused  = false
    }
  }
}

variables {
  account_id = "00000000000000000000000000000000"
  zone_id    = "11111111111111111111111111111111"
  hostname   = "api.example.com"
}

run "encrypted_edge" {
  command = plan

  assert {
    condition     = cloudflare_dns_record.api.proxied && cloudflare_dns_record.api.type == "CNAME" && cloudflare_dns_record.api.ttl == 1
    error_message = "Public DNS must use Cloudflare's proxy and automatic TTL."
  }

  assert {
    condition     = cloudflare_zone_setting.ssl.value == "strict" && cloudflare_zone_setting.https.value == "on"
    error_message = "Use Full(strict) and redirect HTTP to HTTPS."
  }

  assert {
    condition     = cloudflare_zero_trust_tunnel_cloudflared_config.main.config.ingress[0].service == "http://127.0.0.1:8080" && cloudflare_zero_trust_tunnel_cloudflared_config.main.config.ingress[1].service == "http_status:404"
    error_message = "Route only the configured hostname to the loopback Gateway and reject unmatched routes."
  }

  assert {
    condition     = length(cloudflare_ruleset.api_rate_limit) == 0
    error_message = "Do not replace an existing zone's rate-limit rules without enabling the option."
  }
}

run "free_plan_rate_limit" {
  command = plan

  variables {
    enable_api_rate_limit = true
  }

  assert {
    condition     = length(cloudflare_ruleset.api_rate_limit[0].rules) == 1 && cloudflare_ruleset.api_rate_limit[0].rules[0].ratelimit.period == 10 && cloudflare_ruleset.api_rate_limit[0].rules[0].ratelimit.mitigation_timeout == 10
    error_message = "Keep the optional rule within the Free plan's rule count and timing limits."
  }

  assert {
    condition     = !strcontains(cloudflare_ruleset.api_rate_limit[0].rules[0].expression, "http.host")
    error_message = "The Free plan does not support host matching for rate limiting."
  }
}

run "reject_public_origin" {
  command = plan

  variables {
    origin_service = "http://0.0.0.0:8080"
  }

  expect_failures = [var.origin_service]
}

run "reject_foreign_hostname" {
  command = plan

  variables {
    hostname = "api.other-domain.com"
  }

  expect_failures = [data.cloudflare_zone.target]
}

run "reject_wrong_cloudflare_account" {
  command = plan

  variables {
    account_id = "22222222222222222222222222222222"
  }

  expect_failures = [data.cloudflare_zone.target]
}
