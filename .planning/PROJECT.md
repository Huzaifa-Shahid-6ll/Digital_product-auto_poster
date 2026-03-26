# Digital Product Auto-Poster

## What This Is

An end-to-end automation tool that automates the entire digital product validation workflow - from niche research and product idea generation to creating, listing, and promoting digital products on platforms like Etsy and Gumroad.

## Core Value

Enable entrepreneurs to validate and launch digital products with minimal manual effort - a "set and forget" system that researches niches, generates product ideas, creates deliverables, lists them on marketplaces, and drives traffic automatically.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Niche research automation - AI-powered market analysis to find profitable niches
- [ ] Product idea generation - Generate digital product ideas based on niche research
- [ ] Product creation - Auto-generate digital products (planners, templates, guides)
- [ ] Marketplace listing - Auto-create listings on Etsy, Gumroad, etc.
- [ ] Traffic generation - Automated promotion via social media, communities, influencers

### Out of Scope

- [Physical products] — Playbook is digital-product focused
- [Payment processing] — Use existing marketplace payment systems
- [Customer support] — Marketplaces handle this

## Context

**Playbook foundation:** The VISION.md file contains a "Digital Product Validation Playbook" - a step-by-step guide for validating digital product ideas. This automation tool will implement all 10 steps of that playbook:

1. Pick a niche
2. Check market demand on Etsy
3. Decide angle/competitor to beat
4. Define product in plain language
5. Build smallest version
6. Make it look credible
7. Price for validation
8. Create listing
9. Get traffic
10. Check results like a scientist

**Existing codebase:** The project already has some infrastructure. Run `/gsd-map-codebase` to understand current state.

## Constraints

- **[Timeline]**: MVP should ship fast enough to validate demand
- **[Tech]**: Use existing stack patterns from codebase mapping
- **[Scope]**: Focus on one marketplace first (Etsy), expand later

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Full automation | User wants entire Playbook implemented | — Pending |
| Both use cases | Build for personal use + potential sale | — Pending |
| Etsy first | Largest digital product marketplace | — Pending |

---

*Last updated: 2026-03-26 after initialization*

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state