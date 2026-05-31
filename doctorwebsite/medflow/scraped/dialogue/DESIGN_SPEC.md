# Dialogue.co — Full Design & Feature Blueprint

**Source:** https://www.dialogue.co/en/  
**Scraped with:** Scrapling `DynamicFetcher` (headless browser, network idle)  
**Platform:** HubSpot CMS (module-based layout)

Use this document as the single reference to replicate the Dialogue homepage in Claude Design or any frontend stack.

---

## 1. Brand & Positioning

| Attribute | Value |
|-----------|-------|
| Product | Virtual care & employee well-being platform (B2B) |
| Audience | HR leaders, organizational buyers, benefits managers |
| Tone | Empathetic, trustworthy, data-driven, premium healthcare |
| Tagline pattern | "Your people are fine. Until they're not." |
| Value prop | Safe, timely virtual care when employees finally ask for help |

---

## 2. Typography

| Role | Font |
|------|------|
| Display / Headlines | **Poynter Oldstyle Disp Semi Bd** (`PoynterOSDisp`) |
| Body / UI | **Roboto**, fallback `Helvetica Neue, Arial, sans-serif` |
| Icons | Font Awesome 4.7 |

Headlines use a serif editorial feel; body copy stays clean sans-serif. Large H1/H2 with generous line-height.

---

## 3. Color & Visual Language

Dialogue uses a warm, healthcare-trust palette (extracted from inline styles):

| Token | Hex | Usage |
|-------|-----|-------|
| Help/soft background | `#FFEFE2` | Help Centre dropdown, warm accent panels |
| Dark text | `#212020` | Primary body text, nav links |
| White | `#FFFFFF` | Hero backgrounds, cards |
| Brand accent | Teal/green tones | CTAs, logo, trust signals (from brand CSS modules) |

**Visual style:**
- Soft peach/cream warm accents
- High whitespace, editorial layout
- Rounded pill buttons for primary CTAs
- App screenshots in phone mockups for product sections
- AOS scroll animations (`aos-init` classes)
- Swiper carousels for benefits + testimonials

---

## 4. Global Header (Sticky)

```
[Logo]  Integrated Health Platform ▾  |  Why Dialogue ▾  |  Resources ▾  |  Get Pricing  |  Help Centre ▾  |  Login ▾  |  [Book a demo]
                                                                                                    [EN (CA) ▾]
```

### Mega-menu: Integrated Health Platform
**Overview**
- Dialogue IHP — single modern platform for org health
- How we're different — Humanized Healthcare outcomes
- Our clients — productivity, absenteeism, culture

**Programs**
- Employee Assistance Program (EAP)
- Mental Health+
- Primary Care
- Wellness

**Features**
- Women's and Family Health
- EAP cost savings calculator
- Well-Being Score / business case reports

### Mega-menu: Why Dialogue
**Dialogue Experience:** Organizational leaders, Partners, Members, Healthiest Workplace Awards  
**Why Dialogue:** Discover savings, Why virtual care?, Ultimate Guide to EAP, About us  
**Work with us:** Careers, Culture/diversity

### Mega-menu: Resources
**Learn:** Resource Centre, Blog, Case studies, Newsletter  
**Support:** How to use Dialogue, Help centre, Contact sales  
**Featured cards:** 13x ROI report, 2026 Healthiest Workplace Awards, Women's health campaign

### Utility nav
- **Get Pricing** — standalone link
- **Help Centre** — dropdown with warm `#FFEFE2` background
- **Login** — Member login + Admin login (user/lock icons)
- **Book a demo** — primary header CTA button
- **Language/region switcher** — Canada EN, Canada FR, Global EN (flag icons)

---

## 5. Page Sections (Top → Bottom)

### Section A — Hero (`ooh-hero`)
**Headline (H1):** Your people are fine. Until they're not.

**Animated concern cards** (floating icons + short labels):
- Haven't slept in weeks (sleep icon)
- Stressed about budget cuts (cash icon)
- Worried about aging parents (account-child icon)
- Center quote bubble: "I'm fine."

**Subcopy:** Health is everything. Don't settle  
**Supporting text:** Give them access to safe, timely care that meets them when they finally find the courage to ask for help.

**CTAs:**
- Primary: **See it in action**
- Secondary: **Book a call**

**Layout:** Split hero — copy left, animated visual cards right. Mobile has dedicated `mobile-section` variant.

---

### Section B — Social Proof Logos (`cstm-sprtng-orgs`)
**Headline:** Trusted by 52,000+ Canadian organizations.

**Logo strip:** Via Rail, SunLife, National Bank, Lightspeed, Samsung (grayscale, horizontal scroll or row)

**Link:** Discover our client stories

---

### Section C — Benefits Carousel (`home-benefits`)
**Headline:** Experience the Dialogue difference

**Intro:** Satisfaction, utilization, and member wait time guarantees.

**3 Swiper slides** (prev/next arrows):

| Slide | Before → After headline | Metrics |
|-------|-------------------------|---------|
| 1 | Members giving up → navigating with clarity | 4.7/5 appointment satisfaction, 4.6/5 overall satisfaction |
| 2 | Fast but unreliable → safest care on time | 98%+ triage accuracy (3M+ consults), 1,000+ monthly audits, 700+ criteria compliance |
| 3 | Feeling unsupported → white-glove success | 9.4/10 onboarding satisfaction, 1hr support response, reporting dashboards |

Each slide: H4 title, bullet metrics, lifestyle photo (woman on phone).

---

### Section D — Integrated Health Platform (`hp-main`)
**Headline:** Dialogue's Integrated Health Platform

**Intro:** One-stop care hub, 24/7/365, programs stronger together.

**Tab/icon navigation** (4 programs):

#### Employee Assistance Program (EAP)
- Outdated EAP → employee-designed, digital-first work-life support
- App screenshot: EAP services screen
- CTA: Learn more

#### Mental Health+
- Leading disability driver → tools + professional guidance
- Screenshots: Start consultation, Monitor stress, Self-Care Toolkits
- CTA: Learn more

#### Primary Care
- Virtual resolution for common workplace/clinic issues
- Screenshot: reason-for-consult picker (skin, urology, sexual health, heart/lung, eye)
- CTA: Learn more

#### Wellness
- Daily healthy habits, challenges, content
- Screenshots: abs/core training, habits tracking
- CTA: Learn more

**Section CTA:** Discover our platform

---

### Section E — Impact Stats (`cstm-vrtl-hlthcr`)
**Headline:** Having real impact.

| Stat | Label |
|------|-------|
| **40%** | Average improvement in mental health scores (PHQ-9) within ~30 days |
| **30 days** | Average LOA duration vs industry avg 65 days |
| **4+** | Hours saved per consultation on average |

Large numeric H2s with small H6 captions. 3-column layout.

---

### Section F — Testimonials (`cstm-review-testi`)
**Headline:** Over 26,000 five-star app ratings

**Swiper carousel** with pagination bullets. Sample quotes:
- Moon K. — "phenomenal... biggest changes I've ever made"
- Anne C. — "10 stars... Fast, Accommodating, polite"
- Patsy R. — middle-of-the-night support, felt safe
- Laura J. — prescription renewals, BC doctor shortage
- Alex A. — outstanding service, genuine follow-up

Each card: quote, author name, star rating implied.

---

### Section G — Lead Magnet Banner (`textBanner`)
**Headline:** This is the cost-benefit analysis your leadership team needs to see.  
**Sub:** Discover **13x the ROI**: The business case for virtual mental health care.

**CTA:** Download the report  
**Visual:** HR leader image + report thumbnail  
**Animation:** AOS fade-in

---

### Section H — Demo Modal (overlay)
**Title:** Schedule a live demo  
**Copy:** Fill out form; existing customers → support@dialogue.co  
**Fields:** Standard HubSpot demo form (name, company, email, etc.)

---

## 6. Footer

**Columns:**
- **Partners** — Partner with us
- **Company** — About Us, Careers, Press, Culture, Brand guidelines
- **Platform** — IHP, EAP, Mental Health+, Primary Care, Wellness, EAP calculator
- **Contact** — Blog, iOS app, Android app, Help Centre, Status, Contact Us

**Bottom bar:** © 2026 Dialogue | Privacy | Terms | AODA | Cookie Policy | Rights  
**Social:** Follow us icons

---

## 7. Interactive Components Checklist

- [ ] Sticky header with mega-menus (3 top-level dropdowns)
- [ ] Region/language switcher with flags
- [ ] Dual login dropdown (Member / Admin)
- [ ] Hero animated floating cards (3 concerns + "I'm fine")
- [ ] Dual CTA button pair in hero
- [ ] Client logo marquee/strip
- [ ] Swiper benefits carousel (3 slides, arrows)
- [ ] Tabbed program showcase with phone mockups
- [ ] 3-column impact statistics
- [ ] Testimonial Swiper with pagination dots
- [ ] AOS scroll animations on sections
- [ ] Bottom text banner CTA
- [ ] HubSpot demo booking modal
- [ ] Fancybox (lightbox) — loaded but optional
- [ ] Slick slider CSS — legacy support

---

## 8. Tech Stack (Original Site)

| Layer | Technology |
|-------|------------|
| CMS | HubSpot |
| CSS modules | Per-section minified HubSpot modules |
| Carousels | Swiper.js |
| Animations | AOS 2.3.1 |
| Sliders | Slick 1.8 |
| Lightbox | Fancybox 3.5.6 |
| Forms/CTA | HubSpot CTAs + embedded scripts |
| Grid | Bootstrap-style span12 cells |

**Key CSS module files:**
- `module_Hero_Animated_Objects_OOH.min.css`
- `module_Home_Benefits.min.css`
- `module_Integrated_Health_Platform_Module.min.css`
- `module_Home_3_columns_data.min.css`
- `module_Home_Bottom_Text_Banner.min.css`
- `template_Dialogue_May2020-style.css`

---

## 9. Replication Notes for Claude Design

When rebuilding, prioritize these **visual signatures**:

1. **Editorial serif headlines** (Poynter-style) paired with clean Roboto body
2. **Empathetic hero** — not a typical SaaS gradient; warm, human, concern cards
3. **Trust density** — logos, stats, accreditation badges, star ratings stacked vertically
4. **Product tabs with real app UI** — phone screenshots are central to conversion
5. **Carousel-heavy mid-page** — benefits + testimonials both use Swiper
6. **Soft peach accents** (`#FFEFE2`) for help/warmth, dark `#212020` text
7. **B2B conversion path** — Book a demo (header) + Download report (footer banner)

### Suggested component map (React/Next.js)

```
<Header megaMenus login regionSwitcher cta="Book a demo" />
<Hero animatedCards ctas={["See it in action", "Book a call"]} />
<LogoStrip count="52,000+" logos={[...]} />
<BenefitsCarousel slides={3} metrics={[...]} />
<PlatformTabs programs={[EAP, MentalHealth, PrimaryCare, Wellness]} />
<ImpactStats stats={[40%, 30days, 4+hrs]} />
<TestimonialCarousel count="26,000+" reviews={[...]} />
<ReportBanner roi="13x" cta="Download the report" />
<Footer columns={4} />
<DemoModal />
```

---

## 10. Raw Scrape Outputs

| File | Contents |
|------|----------|
| `page.html` | Full rendered DOM |
| `design-data.json` | Structured headings, sections, images, stylesheets |
| `page-content.md` | Flattened text content |
| `DESIGN_SPEC.md` | This file |

Re-run scraper:
```bash
cd medflow && source .venv/bin/activate && python scripts/scrape_dialogue_design.py
```
