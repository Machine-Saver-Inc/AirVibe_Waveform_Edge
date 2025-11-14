terraform {
  required_providers {
    linode     = { source = "linode/linode", version = "~> 2.20" }
    cloudflare = { source = "cloudflare/cloudflare", version = "~> 4.41" }
  }
}

provider "linode" {
  token = var.linode_token
}

provider "cloudflare" {}  # reads CLOUDFLARE_API_TOKEN from env if present

data "cloudflare_zone" "zone" {
  name = var.domain
}

resource "linode_instance" "edge" {
  label           = var.label
  region          = var.region
  type            = var.type
  image           = var.image
  authorized_keys = [var.ssh_pub_key]
  root_pass       = var.root_pass
  booted          = true

  metadata {
    user_data = base64encode(
      templatefile("${path.module}/../cloud-init/cloud-init.yaml.tmpl", {
        domain                 = var.domain
        repo_url               = var.repo_url
        acme_email             = var.acme_email
        cloudflare_api_token   = var.cloudflare_api_token
        admin_token            = var.admin_token
        cert_mode              = var.cert_mode
      })
    )
  }
}

resource "cloudflare_record" "edge_a" {
  zone_id = data.cloudflare_zone.zone.id
  name    = "edge"
  type    = "A"
  value   = linode_instance.edge.ip_address
  proxied = false
  ttl     = 300
}
