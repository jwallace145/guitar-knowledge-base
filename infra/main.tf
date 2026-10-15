# The site stack: production distribution for guitar.jwall.engineering served
# from <bucket>/prod, and the pr-<n>.preview.guitar.jwall.engineering
# distribution served from <bucket>/previews/pr-<n>.
#
# The bucket and the three CI roles are owned by jwallace145/jwall-engineering-infra
# and only referenced here by name. No dev environment: the apply role may only
# change the production and preview record names in the zone.
module "site" {
  source  = "jwallace145/jwall-engineering/aws"
  version = "0.4.0"

  bucket_name                 = module.context.bucket_name
  bucket_regional_domain_name = "${module.context.bucket_name}.s3.us-east-1.amazonaws.com"
  domain_name                 = var.domain_name
  zone_id                     = var.zone_id
  dev_domain_name             = null
  enable_preview              = true
}
