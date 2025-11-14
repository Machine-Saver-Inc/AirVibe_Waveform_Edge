variable "linode_token"      { type = string, sensitive = true }
variable "label"             { type = string, default = "ms-edge-01" }
variable "region"            { type = string, default = "us-east" }
variable "type"              { type = string, default = "g6-nanode-1" }
variable "image"             { type = string, default = "linode/ubuntu24.04" }
variable "ssh_pub_key"       { type = string, sensitive = true }
variable "root_pass"         { type = string, sensitive = true }

variable "domain"            { type = string }            # e.g., "machinesaver.com"
variable "repo_url"          { type = string, default = "https://github.com/Machine-Saver-Inc/AirVibe_Waveform_Edge" }

# For acme.sh DNS-01 on the VPS
variable "cloudflare_api_token" { type = string, sensitive = true }
variable "acme_email"           { type = string }

# For creating the DNS A record via Terraform
variable "cloudflare_zone_id" { type = string }           # zone id for domain

# Public Issuing CA cert (client-auth) injected into mosquitto
variable "issuing_ca_cert_pem" { type = string }

