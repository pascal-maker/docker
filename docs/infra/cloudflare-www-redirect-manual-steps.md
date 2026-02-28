# Cloudflare WWW-to-Apex Redirect: Manual Steps

Steps that cannot be done in Terraform. Do these **before** running `make infra-apply` for the www redirect.

---

## 1. Add Redirect Permission to Cloudflare API Token

**Why:** Terraform cannot create or modify API tokens. Permissions are set only in the Cloudflare Dashboard.

**Note:** You cannot add permissions to an existing token. Create a new token with all required permissions, then replace the value in `secrets.tfvars`.

### Steps

1. Go to: https://dash.cloudflare.com/profile/api-tokens
2. Click **Create Token**
3. Click **Create Custom Token**
4. **Token name:** `refactor-agent-terraform`
5. **Permissions** — add each row:

   | Permission type | Resource | Permission |
   |-----------------|----------|------------|
   | Zone | DNS | Edit |
   | Zone | Email Routing Rules | Edit |
   | Zone | Single Redirect | Edit |
   | Zone | Zone Settings | Edit |
   | Account | Email Routing Addresses | Edit |

6. **Zone resources:** For each Zone permission (DNS, Email Routing Rules, Single Redirect, Zone Settings), click **Include** → **Specific zone** → select `refactorum.com`
7. **Account resources:** For Email Routing Addresses, set **Include** → **Your account**
8. Click **Continue to summary**
9. Click **Create Token**
10. Copy the token immediately (it is shown only once)
11. Open `infra/secrets.tfvars` and set `cloudflare_api_token = "<paste token here>"`
12. If migrating from Cloudflare provider v4, run the state migration (see below)
13. Run `make infra-apply`

---

## 2. State Migration (v4 → v5 only)

`terraform state mv` cannot move between resource types (`cloudflare_record` → `cloudflare_dns_record`). Use remove + import.

### Step A: Get zone ID and record IDs

`terraform state show` fails with v5 (schema mismatch). Use one of these:

**Option 1 — From raw state** (if `state pull` works):

```bash
cd infra
terraform state pull | jq -r '
  .resources[] | select(.type == "cloudflare_record") | 
  .instances[] | .attributes | "\(.zone_id) \(.id)"
'
```

**Option 2 — From Cloudflare API** (replace `YOUR_TOKEN` and `ZONE_ID`):

```bash
# Get zone ID: https://dash.cloudflare.com → refactorum.com → Overview → Zone ID (right sidebar)
curl -s "https://api.cloudflare.com/client/v4/zones/ZONE_ID/dns_records" \
  -H "Authorization: Bearer YOUR_TOKEN" | jq '.result[] | select(.name | test("refactorum.com|resend")) | {name, type, id}'
```

Note the **zone_id** (one value for the zone) and **id** (one per record: SPF and DKIM).

### Step B: Remove old resources from state

```bash
cd infra
terraform state rm 'module.cloudflare[0].cloudflare_record.resend_spf'
terraform state rm 'module.cloudflare[0].cloudflare_record.resend_dkim[0]'
```

### Step C: Import into new resource type

Import format is `zone_id/record_id`. Replace placeholders with values from Step A:

```bash
cd infra
terraform import 'module.cloudflare[0].cloudflare_dns_record.resend_spf' 'ZONE_ID/SPF_RECORD_ID'
terraform import 'module.cloudflare[0].cloudflare_dns_record.resend_dkim[0]' 'ZONE_ID/DKIM_RECORD_ID'
```

### Step D: Remove old zone settings (if still in state)

```bash
terraform state rm 'module.cloudflare[0].cloudflare_zone_settings_override.refactorum'
```

### Step E: Fix email routing address (if RFC3339 error)

If plan fails with "Invalid RFC3339 String Value" on `cloudflare_email_routing_address.destination`:

1. Remove from state: `terraform state rm 'module.cloudflare[0].cloudflare_email_routing_address.destination'`
2. Get the address UUID:
   ```bash
   TOKEN=$(grep cloudflare_api_token secrets.tfvars | cut -d'"' -f2)
   curl -s "https://api.cloudflare.com/client/v4/accounts/ACCOUNT_ID/email/routing/addresses" \
     -H "Authorization: Bearer $TOKEN" | jq '.result[] | select(.email=="YOUR_EMAIL") | .tag'
   ```
3. Import with `account_id/address_uuid` (not email):
   ```bash
   terraform import -var-file=dev.tfvars -var-file=secrets.tfvars \
     'module.cloudflare[0].cloudflare_email_routing_address.destination' \
     'ACCOUNT_ID/ADDRESS_UUID'
   ```

### Step F: Apply

```bash
terraform plan -var-file=dev.tfvars -var-file=secrets.tfvars
make infra-apply
```
