terraform {
  required_version = ">= 1.5.0"

  required_providers {
    docker = {
      source  = "kreuzwerker/docker"
      version = "~> 3.0"
    }
  }
}

provider "docker" {
  host = var.docker_host
}

resource "docker_volume" "weaviate_data" {
  name = var.weaviate_volume_name
}

resource "docker_image" "weaviate" {
  name         = var.weaviate_image
  keep_locally = true
}

resource "docker_container" "weaviate" {
  name  = var.weaviate_container_name
  image = docker_image.weaviate.image_id

  restart = "unless-stopped"

  ports {
    internal = 8080
    external = var.weaviate_http_port
  }

  ports {
    internal = 50051
    external = var.weaviate_grpc_port
  }

  env = [
    "QUERY_DEFAULTS_LIMIT=25",
    "AUTHENTICATION_ANONYMOUS_ACCESS_ENABLED=true",
    "PERSISTENCE_DATA_PATH=/var/lib/weaviate",
    "DEFAULT_VECTORIZER_MODULE=none",
    "CLUSTER_HOSTNAME=node1"
  ]

  volumes {
    volume_name    = docker_volume.weaviate_data.name
    container_path = "/var/lib/weaviate"
  }
}