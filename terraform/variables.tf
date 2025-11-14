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

variable "cloudflare_api_token" {
  type      = string
  sensitive = true
}

variable "acme_email" {
  type = string
}

variable "cloudflare_zone_id" {
  type = string
}

# Public Issuing CA cert (PEM) injected into mosquitto
variable "issuing_ca_cert_pem" {
  type = string
}
