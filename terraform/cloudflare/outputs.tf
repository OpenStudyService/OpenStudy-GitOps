output "account_id" {
  value = var.account_id
}

output "tunnel_id" {
  value = cloudflare_zero_trust_tunnel_cloudflared.main.id
}

output "hostname" {
  value = var.hostname
}
