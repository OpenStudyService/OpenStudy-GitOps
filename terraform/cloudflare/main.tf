data "cloudflare_zone" "target" {
  zone_id = var.zone_id

  lifecycle {
    postcondition {
      condition     = self.account.id == var.account_id
      error_message = "The zone must belong to the specified Cloudflare account."
    }

    postcondition {
      condition     = self.status == "active" && !self.paused
      error_message = "Activate the zone and enable Cloudflare's proxy before applying."
    }

    postcondition {
      condition     = var.hostname == self.name || endswith(var.hostname, ".${self.name}")
      error_message = "The public hostname must belong to the selected zone."
    }
  }
}

resource "cloudflare_zero_trust_tunnel_cloudflared" "main" {
  account_id = data.cloudflare_zone.target.account.id
  name       = var.tunnel_name
  config_src = "cloudflare"
}

resource "cloudflare_zero_trust_tunnel_cloudflared_config" "main" {
  account_id = data.cloudflare_zone.target.account.id
  tunnel_id  = cloudflare_zero_trust_tunnel_cloudflared.main.id

  config = {
    ingress = [
      {
        hostname = var.hostname
        service  = var.origin_service
      },
      {
        service = "http_status:404"
      }
    ]
  }
}

resource "cloudflare_dns_record" "api" {
  zone_id = data.cloudflare_zone.target.id
  name    = var.hostname
  type    = "CNAME"
  content = "${cloudflare_zero_trust_tunnel_cloudflared.main.id}.cfargotunnel.com"
  proxied = true
  ttl     = 1
}

resource "cloudflare_zone_setting" "ssl" {
  zone_id    = data.cloudflare_zone.target.id
  setting_id = "ssl"
  value      = "strict"
}

resource "cloudflare_zone_setting" "https" {
  zone_id    = data.cloudflare_zone.target.id
  setting_id = "always_use_https"
  value      = "on"
}

# Free Managed Ruleset is enabled by Cloudflare. Do not replace its managed rules.
# Free supports one rate-limit rule with a path expression and 10-second windows.
resource "cloudflare_ruleset" "api_rate_limit" {
  count   = var.enable_api_rate_limit ? 1 : 0
  zone_id = data.cloudflare_zone.target.id
  name    = "OpenStudy API rate limit"
  kind    = "zone"
  phase   = "http_ratelimit"

  rules = [{
    ref         = "openstudy_api_rate_limit"
    description = "Limit API requests by client IP."
    expression  = "starts_with(http.request.uri.path, \"${var.api_path_prefix}\")"
    action      = "block"
    enabled     = true
    ratelimit = {
      characteristics     = ["cf.colo.id", "ip.src"]
      period              = 10
      requests_per_period = var.requests_per_10_seconds
      mitigation_timeout  = 10
    }
  }]
}
