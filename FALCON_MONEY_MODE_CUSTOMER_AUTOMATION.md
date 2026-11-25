# Falcon Money Mode — Fiverr and customer automation product plan

Date: 2026-11-24. Status: **roadmap only**. No customer-service or Fiverr integration has been released in the Windows app.

## User goal

Turn Falcon into a free local assistant that **helps earn income by producing client-ready websites, original AI artwork, and customer-service automation projects**, and reduces the work of running the seller's Fiverr business. Falcon retains the existing single purple chat, STOP, Ollama, local project storage, gaming-safe model handling, and trusted release updater.

## Two distinct types of customer automation

### A. Assistant for the owner's Fiverr business

1. The seller provides customer requirements in-chat by entering/pasting them or via a user-chosen, limited screenshot. Do not scrape Fiverr inboxes, customers, files, orders or account pages.
2. Falcon structures the order into a local project brief: requested deliverables, exact specs, agreed scope, buyer questions, due date, revision count, progress and acceptance checks.
3. Falcon drafts personalized replies, questions and status updates for the seller to review and manually send using Fiverr's built-in messaging. Fiverr native quick responses and first-contact auto-reply are permitted ways to reduce effort.
4. Falcon produces website/art files in a controlled workspace, checks outputs, and assembles a delivery folder and message for the seller to review.
5. For the first release, **no autonomous sending, Fiverr login automation, scraping, mass contact, unilateral delivery or account operations.** Sensitive data is not copied to public GitHub, logs or model training.

### B. Sell customer-service automations to clients

Possible Fiverr Gig: "I will build a custom FAQ chatbot and customer inquiry workflow for your business."

- Starter package: FAQ chatbot embedded in an approved website, grounded in the client's supplied business FAQ, clear AI disclosure and human handoff.
- Optional scope: lead/contact intake to a client-owned approved destination with explicit opt-in, appointment request collection (not falsely confirmed reservations), draft ticket summaries, local dashboard and notification routing.
- Project output: source code, setup guide, tests, dependency/license list, privacy policy notes, a clear handoff path and honest maintenance scope.
- Demonstrate with synthetic test data first. Client authorizes their own accounts/services; don't collect or store credentials in Falcon prompts.
- No promises of continuous 24/7 zero-cost hosted availability: free local inference needs an always-on client-owned machine or separate infrastructure. Some integrations, email/SMS and hosting may have charges.
- Respect destination platform terms, permission policies, customer consent and data retention requirements. No spam, unsolicited mass outreach, impersonation or scraping prohibited sites.

## Fiverr policy check (as of Nov 24, 2026)

- Fiverr allows responsible AI-assisted services and automation offerings: https://help.fiverr.com/hc/en-us/articles/37554976380177-Using-AI-on-Fiverr-Guidelines-for-freelancers-and-clients
- Built-in quick responses and first-message auto-replies: https://help.fiverr.com/hc/en-us/articles/10092069817617-Quick-responses-and-auto-replies
- Fiverr Terms of Service restrict unauthorized automation and extracting data from the marketplace: https://www.fiverr.com/legal-portal/legal-terms/terms-of-service
- Community standards prohibit mass automated messages: https://help.fiverr.com/hc/en-us/articles/37554441398929-Our-Community-Standards
- These platform restrictions must be evaluated again before any integrated on-platform automation ships. Native auto-reply does not replace a seller's actual response.

## Proposed first three Fiverr Gigs

1. AI-assisted custom static websites (starter test pricing $100–$250), includes responsive design, functional navigation, client-specific content, revisions, honest hosting limitations.
2. Original custom AI graphics for YouTube/social/brand visuals (starter test pricing $15–$50), subject to image-generation model/license and platform rights.
3. Custom customer-service FAQ/lead-intake chatbot setup (starter test pricing $75–$250), exact boundaries and recurring hosting disclosed.

Prices are **experiments**, not estimates of actual demand or guaranteed income. Income requires customers and manual review; Falcon cannot autonomously ensure sales.

## Milestones and acceptance tests

**M1: Seller assistant (local, no third-party account access)**
- Input is a manually supplied sanitized order brief; return structured, validated task card with milestones, work checklist, due dates and missing details.
- Draft an accurate, customized response from supplied facts and ask clarifying questions instead of hallucinating price or commitments.
- Flag deadlines and revisions; forget/remove per-client local records upon request.
- No outbound messages/uploads, external account access, or paid API calls.

**M2: Client deliverable production**
- Build/test a small static website and produce image assets from a licensed free local generator when available.
- Screenshot at desktop/mobile viewport and inspect navigation/console errors in an isolated browser.
- Keep evidence, truthful "not tested" states, backups and correction loop. Protect secrets and client files.
- Require seller signoff before delivering or publishing.

**M3: Automation product**
- Build an FAQ chatbot using a client's approved facts and an explicit unknown/hand-off response.
- Add bounded intake workflow with explicit visitor consent, validated fields, a tested retention/deletion policy, human escalation.
- Test prompt injection, untrusted webpage instructions, wrong-business questions, PII handling, and duplicate events.
- A client can run the build on their own Windows/Linux or explicitly funded hosting with license/maintenance terms documented.

**M4: Optional platform integration**
- Only integrate with Fiverr account workflows if there is an authorized API/integration explicitly permitting the required operation.
- Avoid browser bots and extracting marketplace data in violation of Fiverr Terms; use native Fiverr auto-replies/quick responses instead.
- Preserve STOP, audit logs and revocable authorizations for other client-approved services.

## Desired customer interaction

User: "Falcon, this person wants a three-page landscaping site with an online contact form, budget $220, delivery in 5 days. Draft my reply and build a plan."
Expected: an order card, realistic implementation checklist, requested missing information, a response **draft** and milestone dates. No Fiverr login, sending, payment or contract commitments without the user.

User: "Falcon, make a FAQ chatbot for this shop that answers opening hours and directs unusual questions to the owner."
Expected: build an original small project from supplied FAQs, test handling of unknown answers, review privacy/hosting implications and produce install instructions.

## First decision

Focus implementation on a local seller-assistant order card + reply drafting, then website quality, then a demonstrably working client FAQ chatbot. Treat account integrations and generalized autonomous browser control as separately verified, permission-scoped capabilities. Document dependencies and benchmark each workflow with local models.