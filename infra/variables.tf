variable "domain_name" {
  description = "Production FQDN the site is served on. Previews are served from `pr-<n>.preview.<domain_name>`."
  type        = string

  validation {
    condition     = can(regex("^([a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,63}$", var.domain_name))
    error_message = "domain_name must be a lowercase FQDN without a trailing dot (e.g. `guitar.jwall.engineering`)."
  }
}

variable "zone_id" {
  description = "Route 53 hosted zone ID for jwall.engineering, owned by jwallace145/jwall-engineering-infra (`terraform output hosted_zone_id` there). Hardcoded because the CI roles may not list hosted zones."
  type        = string

  validation {
    condition     = can(regex("^Z[A-Z0-9]{5,31}$", var.zone_id))
    error_message = "zone_id must be a Route 53 hosted zone ID (e.g. `Z0123456789ABCDEFGHIJ`)."
  }
}
