variable "linode_token" {
  type      = string
  sensitive = true
}

variable "label" {
  type    = string
  default = "ms-edge-01"
}

variable "region" {
  type    = string
  default = "us-east"
}

variable "type" {
  type    = string
  default = "g6-nanode-1"
}

variable "image" {
  type    = string
  default = "linode/ubuntu24.04"
}

variable "ssh_pub_key" {
  type      = string
  sensitive = true
}

variable "root_pass" {
  type      = string
  sensitive = true
}

variable "domain" {
  type = string
}

variable "repo_url" {
  type    = string
  default = "https://github.com/Machine-Saver-Inc/AirVibe_Edge"
}

# Optional (only needed for Let's Encrypt DNS-01)
variable "cloudflare_api_token" {
  type      = string
  sensitive = true
  default   = ""
}

variable "acme_email" {
  type    = string
  default = ""
}

# Admin token for the API issuance endpoints
variable "admin_token" {
  type = string
}

# Mosquitto server cert mode: "private" or "letsencrypt"
variable "cert_mode" {
  type    = string
  default = "private"
}
