terraform {
  required_version = ">=1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "6.40.0"
    }
    aap = {
      source  = "ansible/aap"
      version = "1.3.0"
    }
  }

  backend "s3" {
    bucket       = "kodegaapp-twin-terraform-state"
    key          = "twin-app.tfstate"
    use_lockfile = true
    region       = "us-east-1"
  }
}


provider "aws" {}


provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}
