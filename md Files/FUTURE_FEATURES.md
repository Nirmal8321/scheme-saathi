# Scheme Saathi: Future Features and Roadmap

Status of this file: a to-do list for after the hackathon. Nothing here is built yet unless it says "done".

Legend: **P1** = do first, **P2** = next, **P3** = later. Effort: S (hours), M (a day or two), L (a week or more).

---

## 1. Your requested upgrades

### 1.1 Much bigger scheme database (P1, L)

**Goal:** go from 13 schemes to hundreds, central and state.

**Where the data can come from (check each source's terms of use before copying):**
- myScheme.gov.in (the national scheme portal). First check whether it offers an official API or data export. Do not assume it does.
- data.gov.in (Open Government Data platform): official datasets, some need a free API key.
- Ministry and department sites (agriculture, health, education, rural development).
- State portals (Maharashtra and others), the MahaDBT portal for Maharashtra schemes.
- India Code (laws and notifications).

**How to build it safely:**
1. Define one **scheme schema** (see section 4) and store every scheme in the same shape.
2. Write an **ingestion script** (not manual copying): fetch, clean, and convert to the schema.
3. Use the AI **only as a helper** to turn official text into draft rules, then a **human reviews** each rule. A wrong rule is a wrong answer for a real person.
4. Every scheme keeps `source_url`, `last_verified`, and a `status` (draft, reviewed, expired).
5. Add a **monthly refresh job** that re-fetches official pages and flags changes.

**Storage change:** move from one `schemes.json` file to a small database (SQLite first, Postgres later) with indexes on category, state and tags. A single JSON file will get slow and hard to edit at hundreds of schemes.

### 1.2 Load first 25, then "Load more" (P1, M)

**Goal:** fast first screen, with the rest on demand.

**Key idea:** the rule engine is plain Python and cheap, so run it on **all** schemes. The expensive parts (AI explanation, audio) are done **only for the schemes the user can see**.

**Design:**
1. `/api/analyze` runs rules on all schemes and sorts them (yes, then maybe, boosted by topic).
2. It returns the **top 25** with a `next_cursor` (or `offset`) and a `total_count`.
3. A new route `/api/schemes/page` takes the same profile and the cursor, and returns the next 25.
4. The UI shows a "Load more schemes (X remaining)" button.
5. AI explanations are generated **per page** (one AI call per page) or **on demand** when a card is opened. This saves free-tier quota.
6. Cache the sorted result in `st.session_state` so the user can page without redoing the rules.

### 1.3 Filters by type of scheme (P1, M)

**Filters to add:**
- **Category:** agriculture, health, education, housing, women and child, business and loans, energy (LPG, solar), social security (pension), skill development.
- **Level:** central or state.
- **State:** Maharashtra and others.
- **Beneficiary group:** farmer, woman, student, senior citizen, disabled, SC/ST/OBC, minority, street vendor, entrepreneur.
- **Benefit type:** cash transfer, loan, subsidy, insurance, free service, scholarship.
- **Eligibility result:** Eligible only, Eligible + Maybe, all.
- **Has deadline soon.**

**How:** store `category`, `benefit_type`, `beneficiary_tags` and `level` for every scheme. The filters are applied to the rule results **before** paging. The UI uses a sidebar or a row of chips, and the chosen filters are sent to the API.

### 1.4 Profile JSON upgrade (P1, M)

**Today's profile:** occupation, age, gender, state, district, annual income, income note, land acres, caste category, family members, `has_lpg`.

**Proposed profile v2** (versioned, so old data still works):

```json
{
  "schema_version": 2,
  "person": {
    "age": 45, "gender": "male", "marital_status": "married",
    "disability": {"has": false, "percent": null},
    "education_level": "10th", "is_student": false
  },
  "location": {
    "state": "Maharashtra", "district": "Wardha",
    "area_type": "rural", "pincode": null
  },
  "household": {
    "members": 5, "annual_income": 80000, "income_source": "farming",
    "income_per_month": null, "ration_card": "yellow",
    "bpl_status": null, "owns_pucca_house": null, "has_lpg": false,
    "category": "General", "minority": false,
    "has_bank_account": true, "aadhaar_linked_bank": null
  },
  "farming": {
    "land_acres": 2, "owner_or_tenant": "owner",
    "crops": ["cotton", "soybean"], "irrigated": null,
    "has_kcc": null, "has_crop_insurance": null
  },
  "business": {
    "type": null, "udyam_registered": null, "is_street_vendor": false,
    "has_vending_certificate": null
  },
  "family_members": [
    {"relation": "wife", "age": 40, "gender": "female"},
    {"relation": "daughter", "age": 15, "gender": "female"}
  ],
  "unknown_fields": ["bpl_status", "owns_pucca_house"],
  "sources": {"age": "user_said", "income": "user_said"}
}
```

**Why this is better:**
- Groups related facts, so rules are easier to write.
- **Family members** unlock schemes for the wife, children and parents (girl-child schemes, scholarships, pensions).
- `unknown_fields` and `sources` tell the app exactly what to ask and what was guessed.
- Farmer and business details support specific schemes (crop insurance, KCC, Udyam).
- Keep a **migration function** from v1 to v2.

**Privacy for the new profile:** sensitive facts (disability, income, caste) must stay in the browser session only, with no storage unless the user opts in (see section 3).

---

## 2. Features from the original plan that are not built

| Feature | Priority | Effort | Notes |
|---|---|---|---|
| **WhatsApp / Telegram bot** | P1 | M | Rural users already use WhatsApp. Reuse the same backend routes. Telegram is easier to start. |
| **Application checklist PDF** (documents + steps + link, in the user's language) | P1 | S | Downloadable and printable |
| **Family mode** (find schemes for wife, children and parents from one profile) | P1 | M | Needs profile v2 |
| **"Why not eligible" plus how to become eligible** | P1 | S | Example: "get an income certificate" |
| **Nearest CSC / Seva Kendra finder** | P2 | M | Map link, needs a location dataset |
| **Deadline alerts** (scheme closing soon) | P2 | S | Needs a `deadline` field in the data |
| **Photo input** (photo of a notice, then OCR and explain) | P2 | M | Gemini vision, or Tesseract |
| **Low-literacy mode** (icons, big audio button, almost no text) | P2 | M | Voice-first screen |
| **More languages** (Tamil, Bengali, Telugu, Gujarati, Kannada) | P2 | M | Add question text, test STT and TTS for each |
| **Better Marathi speech recognition** | P1 | M | Use a larger Whisper model, a hosted speech API, or Bhashini (the government's language API) |
| **Better voice quality** | P3 | M | Bhashini TTS or another natural voice |
| **Follow-up chat in the UI** (backend route exists) | P2 | S | Make sure it is visible and works |
| **PDF notice explainer in the UI** (backend route exists) | P2 | S | Upload tab with summary, key points and deadlines |
| **Missing-info form for all unknown fields** | P1 | S | Friendly inputs in the user's language |
| **Browser-use agent** that fills application forms on gov portals | P3 | L | Hardest feature, portals change often, high risk |

---

## 3. Product and trust features

- **User accounts and saved profile (opt-in):** return later and see new schemes. Needs consent, encryption and a clear delete option.
- **"New scheme for you" alerts:** needs saved profiles, so build accounts first.
- **Share results:** WhatsApp share button with a short summary and links.
- **Feedback button on every card:** "Was this correct?" This is how you find wrong rules.
- **Source freshness badge:** "Verified 12 days ago".
- **Scheme comparison:** two schemes side by side.
- **Accessibility:** screen-reader labels, high contrast, large fonts.
- **Privacy page:** what is stored, for how long, and why.

---

## 4. Data model for the big database

**Scheme record (target shape):**

```json
{
  "id": "pm_kisan",
  "name": {"en": "PM-KISAN", "hi": "पीएम-किसान", "mr": "पीएम-किसान"},
  "level": "central",
  "state": null,
  "category": "agriculture",
  "benefit_type": "cash_transfer",
  "beneficiary_tags": ["farmer", "landholder"],
  "benefit": "Rs 6,000 per year in 3 installments",
  "documents": ["Aadhaar", "7/12 land record", "Bank passbook"],
  "how_to_apply": "...",
  "official_link": "https://pmkisan.gov.in",
  "source_url": "...",
  "deadline": null,
  "status": "reviewed",
  "last_verified": "2026-11-05",
  "reviewed_by": "name",
  "rules": {
    "all_of": [
      {"field": "household.annual_income", "op": "<=", "value": 250000}
    ],
    "any_of": [],
    "none_of": []
  },
  "requires_verification": ["bpl_status"],
  "raw_text": "..."
}
```

**Why a richer rules format (`all_of`, `any_of`, `none_of`):** real schemes have conditions like "A and (B or C) but not D". The current flat rules cannot express that. The new format can, and the rule engine stays plain, testable Python.

**Multi-language names and text:** store translations in the data (reviewed once), so the AI is not needed to translate fixed facts every time.

---

## 5. Performance and cost optimization

| Item | Priority | Idea |
|---|---|---|
| Rule engine on all, AI on visible only | P1 | Described in 1.2 |
| Per-card explanations on demand | P1 | One small AI call when the card opens |
| Cache AI answers (done, disk) | done | Move to Redis or SQLite when hosted |
| Cache audio (done, disk) | done | Pre-generate audio for common phrases |
| Incremental index updates | P2 | Do not rebuild all embeddings when one scheme changes |
| Lighter models for hosting | P1 | Gemini embeddings and hosted speech, to drop torch and big downloads |
| Rate-limit and queue requests | P2 | Prevent "AI is busy" for many users |
| Paid tier or multiple providers | P2 | Fallback: if one model is over quota, use another |
| Streaming responses | P3 | Show the profile first, then cards as they arrive |
| Async calls and parallel fetch | P2 | Faster official-page checks |

---

## 6. Quality, testing and safety

- **Evaluation set:** grow from 5 to 50+ sample people, and track an accuracy score for profile extraction and verdicts.
- **Rule review workflow:** a second person approves every new scheme's rules.
- **Automated rule tests** per scheme (a pass case and a fail case).
- **Monitoring:** log errors, slow requests and AI quota usage (without logging personal data).
- **Regression tests in CI** (GitHub Actions) that run the no-AI tests on every push.
- **Prompt-injection protection** for the "check official source" and PDF features (web pages and PDFs can contain hostile text).
- **Rate limiting and abuse protection** on public routes.
- **Disclaimer and legal review:** the app gives guidance, not legal advice.

---

## 7. Deployment and operations

- **Permanent hosting:** Hugging Face Space (Docker) now, then a paid or cloud host (Render, Railway, Cloud Run) when traffic grows.
- **Secrets only in the host's secret store.**
- **Custom domain** for the final product.
- **Health checks and uptime alerts.**
- **Persistent storage** for caches and the vector index, instead of rebuilding at every start.
- **CI/CD:** push to GitHub and auto-deploy.

---

## 8. Known issues to fix first

1. Irrelevant "maybe" schemes can appear when occupation is unknown (for example a street-vendor scheme for an elderly widow).
2. Marathi speech recognition is only fair with small Whisper models.
3. Free AI quota is tiny, so many users cause "AI is busy".
4. Data covers only 13 schemes, and rules are simplified.
5. Some schemes were marked UNVERIFIED during the build. Re-verify all of them.
6. gTTS needs internet and has basic Marathi voice quality.
7. The `schemes.json` single-file approach will not scale.

---

## 9. Suggested roadmap

**Phase 1 (first 2 weeks): make it permanent and stable**
- Deploy on Hugging Face (permanent link).
- Add GitHub Actions for the no-AI tests.
- Re-verify all 13 schemes by hand.
- Show the follow-up chat and the PDF tab properly in the UI.

**Phase 2 (weeks 3 to 6): scale the data**
- Profile v2 and the new scheme schema.
- Move data to SQLite, and write the ingestion script.
- Grow to 100 reviewed schemes.
- Add filters and "Load more" (first 25, then more).

**Phase 3 (weeks 7 to 12): reach and quality**
- Telegram or WhatsApp bot.
- Application checklist PDF.
- Better Marathi speech (Bhashini or a hosted model).
- Family mode and "why not eligible".
- Feedback buttons, an evaluation set and monitoring.

**Phase 4 (later):**
- Accounts and alerts, more states and languages, a CSC finder, and (carefully) a form-filling agent.
