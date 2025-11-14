output "edge_ipv4"   { value = linode_instance.edge.ip_address }
output "edge_domain" { value = "edge.${var.domain}" }
