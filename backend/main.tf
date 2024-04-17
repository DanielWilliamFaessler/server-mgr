provider "hcloud" {
  token = var.hcloud_token
}

variable "hcloud_token" {
  type      = string
  sensitive = true
}

variable "server_image" {
  type    = string
  default = "ubuntu-22.04"
}

variable "server_type" {
  type    = string
  default = "cx11"
}

variable "server_name" {
  type    = string
}

variable "server_location" {
  type    = string
  default = "nbg1"
}

variable "server_labels" {
  type    = map(string)
  default = {}
}

variable "server_password" {
  type      = string
  sensitive = true
  validation {
    condition     = length(var.server_password) >= 8
    error_message = "The password must be at least 8 characters long."
  }
}

variable "server_action" {
  type    = string
  default = ""
  validation {
    condition     = var.server_action == "" || contains(["poweroff", "poweron", "reboot", "reset", "shutdown"], var.server_action)
    error_message = "Invalid server action defined. Valid actions are: ${join(", ", ["poweroff", "poweron", "reboot", "reset", "shutdown"])}."
  }
}

variable "server_password_reset" {
  type    = bool
  default = false
}

data "hcloud_ssh_key" "dominic_yubikey" {
  name = "Dominic @ Yubikey"
}

resource "hcloud_server" "instance" {
  server_type = var.server_type
  name        = var.server_name
  labels      = var.server_labels
  image       = var.server_image
  location    = var.server_location
  user_data   = <<EOT
#cloud-config
chpasswd:
  expire: false
  list: root:${var.server_password}
ssh_pwauth: true
ssh_authorized_keys:
  - ${data.hcloud_ssh_key.dominic_yubikey.public_key}
EOT
  lifecycle {
    ignore_changes = [user_data]
  }
}

data "http" "server_action" {
  count = var.server_action != "" ? 1 : 0

  depends_on = [hcloud_server.instance]

  request_headers = {
    Authorization : "Bearer ${var.hcloud_token}"
  }


  url    = "https://api.hetzner.cloud/v1/servers/${hcloud_server.instance.id}/actions/${var.server_action}"
  method = "POST"
}

data "http" "server_password_reset" {
  count = var.server_password_reset ? 1 : 0

  depends_on = [hcloud_server.instance]

  request_headers = {
    Authorization : "Bearer ${var.hcloud_token}"
  }

  url    = "https://api.hetzner.cloud/v1/servers/${hcloud_server.instance.id}/actions/reset_password"
  method = "POST"
}

output "server_id" {
  value = hcloud_server.instance.id
}

output "server_name" {
  value = hcloud_server.instance.name
}

output "server_state" {
  value = hcloud_server.instance.status
}

output "server_address" {
  value = hcloud_server.instance.ipv4_address
}

output "server_labels" {
  value = jsonencode(hcloud_server.instance.labels)
}

output "server_action_output" {
  value = var.server_action != "" ? jsondecode(data.http.server_action[0].response_body) : null
}

output "server_password_reset_output" {
  value = var.server_password_reset ? jsondecode(data.http.server_password_reset[0].response_body)["root_password"] : null
  sensitive = true
}
