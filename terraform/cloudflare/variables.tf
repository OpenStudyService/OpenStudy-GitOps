variable "account_id" {
  description = "Cloudflare account that owns the existing zone."
  type        = string

  validation {
    condition     = can(regex("^[a-f0-9]{32}$", var.account_id))
    error_message = "Use a 32-character Cloudflare account ID."
  }
}

variable "zone_id" {
  description = "Existing Cloudflare zone; register the domain and delegate nameservers first."
  type        = string

  validation {
    condition     = can(regex("^[a-f0-9]{32}$", var.zone_id))
    error_message = "Use a 32-character Cloudflare zone ID."
  }
}

variable "hostname" {
  description = "Public fully-qualified hostname, such as api.example.com."
  type        = string

  validation {
    condition     = length(var.hostname) <= 253 && can(regex("^([a-z0-9]([a-z0-9-]*[a-z0-9])?\\.)+[a-z]{2,}$", var.hostname))
    error_message = "Use a lowercase hostname without a URL scheme or path."
  }
}

variable "tunnel_name" {
  description = "Name of the remotely managed Cloudflare Tunnel."
  type        = string
  default     = "openstudy-prod"
}

variable "origin_service" {
  description = "Loopback Gateway listener. Zone Full(strict) does not change this local protocol."
  type        = string
  default     = "http://127.0.0.1:8080"

  validation {
    condition     = can(regex("^http://127\\.0\\.0\\.1:[0-9]{1,5}$", var.origin_service)) && try(tonumber(split(":", var.origin_service)[2]) >= 1 && tonumber(split(":", var.origin_service)[2]) <= 65535, false)
    error_message = "Use a loopback HTTP origin with a valid port, such as http://127.0.0.1:8080."
  }
}

variable "enable_api_rate_limit" {
  description = "Enable only after reviewing existing zone rules and actual API paths."
  type        = bool
  default     = false
}

variable "api_path_prefix" {
  description = "Zone-wide path prefix protected by the optional Free-plan rule. Host matching is unavailable on Free."
  type        = string
  default     = "/api/"

  validation {
    condition     = can(regex("^/[A-Za-z0-9/_-]*$", var.api_path_prefix))
    error_message = "Use a path prefix containing letters, digits, slash, underscore or hyphen."
  }
}

variable "requests_per_10_seconds" {
  description = "Maximum requests per client IP and Cloudflare data center in a 10-second window."
  type        = number
  default     = 100

  validation {
    condition     = var.requests_per_10_seconds >= 1 && floor(var.requests_per_10_seconds) == var.requests_per_10_seconds
    error_message = "Use a positive integer request limit."
  }
}
