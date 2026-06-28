import os
import json
from dotenv import load_dotenv
from anthropic import Anthropic

load_dotenv()

# ── paths ──────────────────────────────────────────────────────────────────
PROCESSED_DIR = "data/processed"
OUTPUT_PATH   = "data/kpis.json"

FILES = {
    2022: "msft_10k_2022.txt",
    2023: "msft_10k_2023.txt",
    2024: "msft_10k_2024.txt",
}

# exact character positions where the numbers table starts in each file
# we found these by searching for the total revenue figure in each file
KNOWN_POSITIONS = {
    2022: 309315,
    2023: 303182,
    2024: None,  # keyword search works fine for 2024
}

client = Anthropic()


# ── prompt ─────────────────────────────────────────────────────────────────
def build_prompt(text, year):
    return f"""
You are a financial data extractor analyzing Microsoft's {year} 10-K filing.

Extract ONLY these exact metrics from the text below.
Return ONLY a valid JSON object — no explanation, no markdown, no preamble.

Keys to extract:
- total_revenue (integer, in millions USD)
- intelligent_cloud_revenue (integer, in millions USD)
- productivity_and_business_processes_revenue (integer, in millions USD)
- more_personal_computing_revenue (integer, in millions USD)
- operating_income (integer, in millions USD)
- net_income (integer, in millions USD)
- microsoft_cloud_revenue (integer, in millions USD)
- azure_growth_yoy_pct (float, e.g. 29.0 for 29%)
- gross_margin (integer, in millions USD)
- diluted_eps (float, in USD)

Rules:
- All revenue/income values must be integers in MILLIONS (e.g. 245,122 = 245122)
- If a value is genuinely not found, use null
- Do not guess or hallucinate numbers
- Return only the JSON object, nothing else

Filing text:
{text}
"""


# ── find relevant section ──────────────────────────────────────────────────
def get_relevant_text(text, year):
    # section 1 — the numbers table (revenue, income, EPS)
    known_pos = KNOWN_POSITIONS.get(year)
    if known_pos is not None:
        start = max(0, known_pos - 500)
        print(f"  Using known position: {known_pos:,}")
    else:
        keywords = ["245,122", "SEGMENT RESULTS OF OPERATIONS", "Gross margin"]
        start = 0
        for keyword in keywords:
            idx = text.find(keyword)
            if idx != -1:
                start = max(0, idx - 500)
                print(f"  Found via keyword at: {idx:,}")
                break

    numbers_section = text[start:start + 20000]

    # section 2 — the highlights section (azure growth, cloud revenue)
    highlights_idx = text.find("Highlights from fiscal year")
    if highlights_idx == -1:
        highlights_idx = text.find("Microsoft Cloud revenue increased")
    
    highlights_section = ""
    if highlights_idx != -1:
        highlights_section = text[highlights_idx:highlights_idx + 3000]
        print(f"  Found highlights at: {highlights_idx:,}")

    # combine both sections
    return highlights_section + "\n\n" + numbers_section


# ── extraction function ────────────────────────────────────────────────────
def extract_kpis(year, filename):
    filepath = os.path.join(PROCESSED_DIR, filename)

    print(f"\nExtracting KPIs for FY{year}...")

    with open(filepath, "r", encoding="utf-8") as f:
        text = f.read()

    relevant_text = get_relevant_text(text, year)

    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1000,
        messages=[
            {
                "role": "user",
                "content": build_prompt(relevant_text, year)
            }
        ]
    )

    raw = response.content[0].text.strip()

    # clean up if Claude wrapped in markdown code block
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    kpis = json.loads(raw)

    # print results
    print(f"  FY{year} extracted successfully")
    print(f"  Total Revenue:      {kpis.get('total_revenue')}M")
    print(f"  Intelligent Cloud:  {kpis.get('intelligent_cloud_revenue')}M")
    print(f"  Operating Income:   {kpis.get('operating_income')}M")
    print(f"  Net Income:         {kpis.get('net_income')}M")
    print(f"  Azure Growth:       {kpis.get('azure_growth_yoy_pct')}%")
    print(f"  Diluted EPS:        {kpis.get('diluted_eps')}")

    return kpis


# ── main ───────────────────────────────────────────────────────────────────
def run():
    os.makedirs("data", exist_ok=True)
    all_kpis = {}

    for year, filename in FILES.items():
        kpis = extract_kpis(year, filename)
        all_kpis[str(year)] = kpis

    with open(OUTPUT_PATH, "w") as f:
        json.dump(all_kpis, f, indent=2)

    print(f"\nAll KPIs saved to {OUTPUT_PATH}")
    print("\nFull summary:")
    for year, kpis in all_kpis.items():
        print(f"\n  FY{year}:")
        for key, value in kpis.items():
            print(f"    {key}: {value}")


if __name__ == "__main__":
    run()