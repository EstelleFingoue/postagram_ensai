## NE RIEN TOUCHER DANS CE FICHIER !!!!!!!!

terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  required_version = ">= 1.5.0"
}

provider "aws" {
  region = "us-east-1" # Change selon ta région (ex: eu-west-1, us-east-1, etc.)
}
# Récupération du VPC et des sous-réseaux par défaut
data "aws_vpc" "default" {
  default = true
}

data "aws_caller_identity" "current" {}


data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}

resource "aws_security_group" "web_sg" {
  name        = "tp-note"
  description = "Autorise SSH et HTTP  en entree, tout en sortie"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "HTTP 8080 webservice et health-check ALB"
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    security_groups = [aws_security_group.web_sg.id]
  }
# Notes: port 8080 ajouté pour que le webservice (app.py) et le health-check du Target Group ALB soient accessibles depuis l’ALB.

  egress {
    description = "Tout trafic sortant"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "web-sg"
  }
}

