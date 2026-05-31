#!/usr/bin/env python3
"""Scrape Dialogue.co homepage design and features using Scrapling."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from urllib.parse import urljoin, urlparse

from scrapling.fetchers import DynamicFetcher

URL = "https://www.dialogue.co/en/"
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "scraped" / "dialogue"


def unique(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        cleaned = re.sub(r"\s+", " ", item).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            out.append(cleaned)
    return out


def extract_nav(page) -> dict:
    nav_links: list[dict] = []
    for a in page.css("header a, nav a, [role='navigation'] a"):
        href = a.attrib.get("href", "")
        text = a.css("::text").getall()
        label = " ".join(t.strip() for t in text if t.strip())
        if label and href and not href.startswith("#"):
            nav_links.append({"label": label, "href": urljoin(URL, href)})
    deduped: list[dict] = []
    seen: set[str] = set()
    for item in nav_links:
        key = f"{item['label']}|{item['href']}"
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    return {"links": deduped}


def extract_headings(page) -> list[dict]:
    headings = []
    for level in range(1, 7):
        for el in page.css(f"h{level}"):
            text = el.css("::text").getall()
            label = " ".join(t.strip() for t in text if t.strip())
            if label:
                headings.append({"level": level, "text": label})
    return headings


def extract_buttons(page) -> list[str]:
    buttons: list[str] = []
    for sel in ["button", "a.btn", "a[class*='button']", "[class*='cta'] a", "[class*='btn']"]:
        for el in page.css(sel):
            text = el.css("::text").getall()
            label = " ".join(t.strip() for t in text if t.strip())
            if label:
                buttons.append(label)
    return unique(buttons)


def extract_stylesheets(page) -> list[str]:
    return unique([link.attrib.get("href", "") for link in page.css("link[rel='stylesheet']")])


def extract_fonts(page) -> list[str]:
    fonts: list[str] = []
    for link in page.css("link[href*='font'], link[rel='preload'][as='font']"):
        href = link.attrib.get("href", "")
        if href:
            fonts.append(href)
    for style in page.css("style"):
        content = style.css("::text").get() or ""
        fonts.extend(re.findall(r"font-family:\s*([^;}{]+)", content, re.I))
    return unique(fonts)


def extract_colors_from_css(css_text: str) -> list[str]:
    hex_colors = re.findall(r"#[0-9a-fA-F]{3,8}\b", css_text)
    rgb_colors = re.findall(r"rgba?\([^)]+\)", css_text)
    return unique(hex_colors + rgb_colors)


def extract_sections(page) -> list[dict]:
    sections: list[dict] = []
    for section in page.css("section, [class*='section'], main > div"):
        text_nodes = section.css("h1::text, h2::text, h3::text, h4::text").getall()
        heading = " ".join(t.strip() for t in text_nodes if t.strip())
        body = section.css("p::text").getall()
        body_text = " ".join(t.strip() for t in body[:3] if t.strip())
        if heading or len(body_text) > 40:
            sections.append(
                {
                    "heading": heading[:200] if heading else None,
                    "preview": body_text[:300] if body_text else None,
                    "class": section.attrib.get("class", "")[:120],
                    "id": section.attrib.get("id", ""),
                }
            )
    return sections[:40]


def extract_stats(page) -> list[str]:
    stats: list[str] = []
    for el in page.css("[class*='stat'], [class*='metric'], [class*='number'], strong, b"):
        text = el.css("::text").get() or ""
        text = text.strip()
        if text and re.search(r"\d", text) and len(text) < 80:
            stats.append(text)
    return unique(stats)[:30]


def extract_testimonials(page) -> list[dict]:
    testimonials: list[dict] = []
    for block in page.css("[class*='testimonial'], [class*='review'], [class*='quote'], blockquote"):
        quote = " ".join(t.strip() for t in block.css("p::text, ::text").getall() if t.strip())
        author = block.css("[class*='author'], [class*='name'], cite::text, footer::text").get() or ""
        if quote and len(quote) > 30:
            testimonials.append({"quote": quote[:500], "author": author.strip()[:80]})
    return testimonials[:15]


def extract_images(page) -> list[dict]:
    images: list[dict] = []
    for img in page.css("img"):
        src = img.attrib.get("src") or img.attrib.get("data-src") or ""
        alt = img.attrib.get("alt", "")
        if src:
            images.append({"src": urljoin(URL, src), "alt": alt[:120]})
    return images[:50]


def extract_meta(page) -> dict:
    return {
        "title": page.css("title::text").get() or "",
        "description": page.css("meta[name='description']::attr(content)").get() or "",
        "og_title": page.css("meta[property='og:title']::attr(content)").get() or "",
        "og_description": page.css("meta[property='og:description']::attr(content)").get() or "",
        "og_image": page.css("meta[property='og:image']::attr(content)").get() or "",
        "theme_color": page.css("meta[name='theme-color']::attr(content)").get() or "",
    }


def extract_programs(page) -> list[dict]:
    programs: list[dict] = []
    keywords = ["EAP", "Mental Health", "Primary Care", "Wellness", "Integrated Health"]
    for heading in page.css("h2, h3, h4"):
        text = " ".join(t.strip() for t in heading.css("::text").getall() if t.strip())
        if any(k.lower() in text.lower() for k in keywords):
            parent = heading.parent
            desc = ""
            if parent:
                p = parent.css("p::text").get()
                if p:
                    desc = p.strip()
            programs.append({"title": text, "description": desc[:400]})
    return programs


def extract_footer(page) -> dict:
    footer_links: list[dict] = []
    for a in page.css("footer a"):
        href = a.attrib.get("href", "")
        text = " ".join(t.strip() for t in a.css("::text").getall() if t.strip())
        if text:
            footer_links.append({"label": text, "href": urljoin(URL, href)})
    return {"links": footer_links}


def extract_carousel_indicators(page) -> list[str]:
    indicators: list[str] = []
    for el in page.css("[class*='carousel'], [class*='slider'], [class*='swiper']"):
        cls = el.attrib.get("class", "")
        if cls:
            indicators.append(cls[:100])
    return unique(indicators)


def build_design_spec(data: dict) -> str:
    lines = [
        "# Dialogue.co Design & Feature Specification",
        "",
        f"**Source:** {URL}",
        "",
        "## Page Meta",
        f"- **Title:** {data['meta']['title']}",
        f"- **Description:** {data['meta']['description']}",
        f"- **Theme color:** {data['meta'].get('theme_color') or 'N/A'}",
        "",
        "## Site Architecture & Navigation",
        "",
        "### Primary Navigation",
    ]
    for link in data.get("nav_sample", [])[:20]:
        lines.append(f"- {link.get('label', '')} ? `{link.get('href', '')}`")

    lines.extend(["", "## Page Sections (Top to Bottom)", ""])
    for i, section in enumerate(data.get("sections", []), 1):
        if section.get("heading"):
            lines.append(f"### {i}. {section['heading']}")
        else:
            lines.append(f"### {i}. Section")
        if section.get("preview"):
            lines.append(f"> {section['preview']}")
        lines.append("")

    lines.extend(["## Hero & Messaging", ""])
    for h in data.get("headings", [])[:8]:
        lines.append(f"- **H{h['level']}:** {h['text']}")

    lines.extend(["", "## Call-to-Action Buttons", ""])
    for btn in data.get("buttons", []):
        lines.append(f"- {btn}")

    lines.extend(["", "## Programs / Product Features", ""])
    for prog in data.get("programs", []):
        lines.append(f"### {prog['title']}")
        if prog.get("description"):
            lines.append(prog["description"])
        lines.append("")

    lines.extend(["", "## Stats & Social Proof", ""])
    for stat in data.get("stats", []):
        lines.append(f"- {stat}")

    lines.extend(["", "## Testimonials", ""])
    for t in data.get("testimonials", [])[:8]:
        lines.append(f"> \"{t['quote'][:200]}...\"")
        if t.get("author"):
            lines.append(f"> - {t['author']}")
        lines.append("")

    lines.extend(["", "## Design System Notes", ""])
    lines.append("### Typography & Fonts")
    for font in data.get("fonts", [])[:15]:
        lines.append(f"- {font}")

    lines.append("")
    lines.append("### Color Palette (from CSS)")
    for color in data.get("colors", [])[:25]:
        lines.append(f"- `{color}`")

    lines.extend(["", "## Interactive Components", ""])
    lines.append("- Mega-menu navigation with dropdown columns (Integrated Health Platform, Why Dialogue, Resources)")
    lines.append("- Hero with animated concern cards (sleep, stress, aging parents)")
    lines.append("- Dual CTA buttons: 'See it in action' + 'Book a call'")
    lines.append("- Client logo trust bar (Via Rail, SunLife, National Bank, etc.)")
    lines.append("- Feature carousel with prev/next arrows")
    lines.append("- Tabbed program showcase (EAP, Mental Health+, Primary Care, Wellness)")
    lines.append("- Stats counter section with large numbers")
    lines.append("- Testimonial carousel/slider")
    lines.append("- Lead magnet CTA (Download the report)")
    lines.append("- Demo booking modal/form")
    lines.append("- Language selector (EN/FR, CA/Global)")
    lines.append("- Login dropdown (Member / Admin)")

    lines.extend(["", "## Footer Structure", ""])
    for link in data.get("footer", {}).get("links", [])[:20]:
        lines.append(f"- {link['label']}")

    lines.extend(["", "## Replication Checklist for Claude Design", ""])
    checklist = [
        "Sticky header with logo, mega-menus, Get Pricing, Help Centre, Login, Book a demo",
        "Full-width hero with emotional headline and subcopy",
        "Floating/animated pain-point cards in hero",
        "Primary + secondary CTA button pair",
        "Logo strip with 'Trusted by 52,000+ organizations'",
        "3-column feature cards with metrics (satisfaction scores, compliance stats)",
        "Horizontal carousel for feature deep-dives",
        "Platform overview with icon tabs and app screenshots",
        "Impact metrics section (40%, 30 days, 4+ hours)",
        "Star ratings social proof block",
        "Testimonial slider with quotes and names",
        "Dark/contrast CTA banner for report download",
        "Multi-column footer with Partners, Company, Platform, Contact",
        "Schedule demo modal with form fields",
    ]
    for item in checklist:
        lines.append(f"- [ ] {item}")

    return "\n".join(lines)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching {URL} with DynamicFetcher...")
    page = DynamicFetcher.fetch(
        URL,
        headless=True,
        network_idle=True,
        disable_resources=False,
        block_ads=True,
    )

    html_path = OUTPUT_DIR / "page.html"
    html_path.write_text(str(page), encoding="utf-8")
    print(f"Saved HTML to {html_path}")

    css_text = " ".join(
        (page.css("style::text").get() or "")
        for _ in [None]
    )
    for link in page.css("link[rel='stylesheet']"):
        href = link.attrib.get("href", "")
        if href:
            css_text += f" {href}"

    nav_raw = []
    for a in page.css("header a, nav a"):
        href = a.attrib.get("href", "")
        text = " ".join(t.strip() for t in a.css("::text").getall() if t.strip())
        if text and href:
            nav_raw.append({"label": text, "href": urljoin(URL, href)})

    data = {
        "url": URL,
        "meta": extract_meta(page),
        "headings": extract_headings(page),
        "buttons": extract_buttons(page),
        "sections": extract_sections(page),
        "stats": extract_stats(page),
        "testimonials": extract_testimonials(page),
        "programs": extract_programs(page),
        "images": extract_images(page),
        "fonts": extract_fonts(page),
        "stylesheets": extract_stylesheets(page),
        "colors": extract_colors_from_css(str(page)),
        "footer": extract_footer(page),
        "carousel_classes": extract_carousel_indicators(page),
        "nav_sample": nav_raw[:30],
    }

    json_path = OUTPUT_DIR / "design-data.json"
    json_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved JSON to {json_path}")

    spec_path = OUTPUT_DIR / "DESIGN_SPEC.md"
    spec_path.write_text(build_design_spec(data), encoding="utf-8")
    print(f"Saved design spec to {spec_path}")

    md_path = OUTPUT_DIR / "page-content.md"
    text_content = page.css("body ::text").getall()
    clean_text = "\n".join(unique([t.strip() for t in text_content if t.strip() and len(t.strip()) > 2]))
    md_path.write_text(f"# Dialogue.co Page Content\n\n{clean_text}", encoding="utf-8")
    print(f"Saved text content to {md_path}")


if __name__ == "__main__":
    main()
