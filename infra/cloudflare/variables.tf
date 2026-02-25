variable "zone_id" {
  description = "Cloudflare zone ID for refactorum.com."
  type        = string
}

variable "account_id" {
  description = "Cloudflare account ID."
  type        = string
}

variable "email_destination" {
  description = "Real email that receives forwards (e.g. thomas.r.decloedt@gmail.com). Must verify once."
  type        = string
  sensitive   = true
}

variable "resend_dkim_name" {
  description = "Resend DKIM record name (e.g. resend._domainkey). Empty to skip."
  type        = string
  default     = ""
}

variable "resend_dkim_target" {
  description = "Resend DKIM CNAME target. Required when resend_dkim_name is set."
  type        = string
  default     = ""
}

variable "firebase_hosting_target" {
  description = "Firebase Hosting A/CNAME target. Empty to skip."
  type        = string
  default     = ""
}

variable "firebase_hosting_type" {
  description = "Firebase Hosting record type: A or CNAME."
  type        = string
  default     = "CNAME"
}

variable "firebase_hosting_name" {
  description = "DNS record name for Firebase: @ for root, www for www subdomain."
  type        = string
  default     = "www"
}
