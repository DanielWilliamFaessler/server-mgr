terraform {
  required_providers {
    hcloud = {
      source  = "hetznercloud/hcloud"
      version = "1.45.0"
    }
    null = {
      source  = "hashicorp/null"
      version = "3.2.2"
    }
    http = {
      source  = "hashicorp/http"
      version = "3.4.2"
    }
  }
}
