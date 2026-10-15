output "bucket_name" {
  description = "Site bucket the deploy and preview workflows sync into."
  value       = module.context.bucket_name
}

output "prod_url" {
  description = "Production URL."
  value       = module.site.prod_url
}

output "prod_distribution_id" {
  description = "CloudFront distribution ID for production; the deploy workflow invalidates it after each sync."
  value       = module.site.prod_distribution_id
}

output "preview_url_pattern" {
  description = "Preview URL pattern (`https://pr-<n>.preview.<domain_name>`)."
  value       = module.site.preview_url_pattern
}

output "preview_distribution_id" {
  description = "CloudFront distribution ID serving `*.preview.<domain_name>`."
  value       = module.site.preview_distribution_id
}
