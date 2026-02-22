---
title: List refactor-agent on Google Cloud AI Agent Marketplace
labels: `enhancement`, `infrastructure`, `business`
---

### Goal

Publish our A2A refactoring agent on the [Google Cloud AI Agent Marketplace](https://cloud.google.com/marketplace/docs/partners/ai-agents) for monetization via usage-based or subscription pricing.

### Why

The marketplace provides enterprise distribution, Google-managed billing, and co-selling with Google Cloud — without exposing our internal tools or engine logic (A2A is opaque by default).

### Steps

#### 1. Vendor onboarding
- [ ] [Sign up as a Cloud Marketplace vendor](https://cloud.google.com/marketplace/docs/partners/offer-products#initiate-onboarding)
- [ ] Complete the Cloud Marketplace Project Info Form to access [Producer Portal](https://console.cloud.google.com/producer-portal)
- [ ] Accept the Marketplace Partner Agreement

#### 2. Agent Card
- [ ] Create an Agent Card JSON per the [A2A Agent Card spec](https://a2a-protocol.org/dev/specification/)
- [ ] Store it in a Cloud Storage bucket
- [ ] Reference: our existing A2A adapter in `src/refactor_agent/a2a/` already defines capabilities implicitly — formalize into the card

#### 3. Hosting
- [ ] Deploy the agent to a stable HTTPS endpoint (Cloud Run, GKE, or similar)
- [ ] Ensure the A2A endpoint is publicly reachable

#### 4. Auth & multi-tenancy
- [ ] Implement Google OAuth sign-in ([technical integration docs](https://cloud.google.com/marketplace/docs/partners/ai-agents/technical-integration))
- [ ] Account creation and Google account linking
- [ ] Tenant isolation for concurrent customers

#### 5. Billing integration
- [ ] Choose pricing model ([options](https://cloud.google.com/marketplace/docs/partners/ai-agents/pricing-models)): free, subscription, usage-based, or combined
- [ ] If usage-based: implement metric reporting via the [Cloud Commerce Partner Procurement API](https://cloud.google.com/marketplace/docs/partners/commerce-api)
- [ ] Define metric (e.g., refactoring operations, files processed)

#### 6. Listing & review
- [ ] Add product details in Producer Portal ([docs](https://cloud.google.com/marketplace/docs/partners/ai-agents/add-product))
- [ ] Upload Agent Card in Producer Portal ([docs](https://cloud.google.com/marketplace/docs/partners/ai-agents/agent-card))
- [ ] Submit pricing for review (~4 business days)
- [ ] Submit technical integration for review
- [ ] [Publish](https://cloud.google.com/marketplace/docs/partners/ai-agents/publish) (~2 days after approval)

### Key references
- [Marketplace AI agent overview](https://cloud.google.com/marketplace/docs/partners/ai-agents)
- [A2A protocol docs](https://a2a-protocol.org/latest/)
- [Marketplace blog announcement](https://cloud.google.com/blog/topics/partners/google-cloud-ai-agent-marketplace)
- [Pricing models](https://cloud.google.com/marketplace/docs/partners/ai-agents/pricing-models)