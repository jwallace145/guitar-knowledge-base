provider "aws" {
  region = "us-east-1"

  # Every resource this stack creates carries the organisation-wide tag set.
  # The `Project` tag is what the apply role's IAM policy keys on, so this
  # block is load-bearing, not cosmetic.
  default_tags {
    tags = module.context.tags
  }
}
