"""
지표 마스터 정의 — 모든 fetcher와 builder가 이 파일을 참조한다.

각 indicator는 다음 정보를 가진다:
- id           : 내부 식별자 (예: us_cpi_yoy)
- country      : US / EU / UK / SG / AU / JP / CA
- category     : inflation / central_bank
- name         : 표시명
- name_ko      : 한글 표시명
- bbg          : Bloomberg ticker (xbbg용, None이면 Bloomberg fetch 스킵)
- fred         : FRED series ID (None이면 FRED fetch 스킵)
- frequency    : M (월) / Q (분기) / E (이벤트)
- importance   : 1 (★) / 2 (★★) / 3 (★★★)
"""

COUNTRIES = {
    "US": {"name": "United States", "flag": "🇺🇸", "tz": "America/New_York"},
    "EU": {"name": "Eurozone",      "flag": "🇪🇺", "tz": "Europe/Frankfurt"},
    "UK": {"name": "United Kingdom","flag": "🇬🇧", "tz": "Europe/London"},
    "SG": {"name": "Singapore",     "flag": "🇸🇬", "tz": "Asia/Singapore"},
    "AU": {"name": "Australia",     "flag": "🇦🇺", "tz": "Australia/Sydney"},
    "JP": {"name": "Japan",         "flag": "🇯🇵", "tz": "Asia/Tokyo"},
    "CA": {"name": "Canada",        "flag": "🇨🇦", "tz": "America/Toronto"},
}

CATEGORIES = {
    "inflation":     {"name_ko": "물가",       "order": 1},
    "central_bank":  {"name_ko": "중앙은행",   "order": 2},
}

INDICATORS = [
    # ── 물가 ──────────────────────────────────────────────────────────
    {"id": "us_cpi_yoy",      "country": "US", "category": "inflation",
     "name": "CPI YoY",       "name_ko": "CPI",
     "bbg": "CPI YOY Index",  "fred": "CPIAUCSL", "frequency": "M", "importance": 3},
    {"id": "us_core_cpi_yoy", "country": "US", "category": "inflation",
     "name": "Core CPI YoY",  "name_ko": "Core CPI",
     "bbg": "CPI XYOY Index", "fred": "CPILFESL", "frequency": "M", "importance": 3},
    {"id": "us_pce_yoy",      "country": "US", "category": "inflation",
     "name": "PCE YoY",       "name_ko": "PCE",
     "bbg": "PCE DEFY Index", "fred": "PCEPI",    "frequency": "M", "importance": 3},
    {"id": "us_core_pce_yoy", "country": "US", "category": "inflation",
     "name": "Core PCE YoY",  "name_ko": "Core PCE",
     "bbg": "PCE CYOY Index", "fred": "PCEPILFE", "frequency": "M", "importance": 3},

    {"id": "eu_hicp_yoy",     "country": "EU", "category": "inflation",
     "name": "HICP YoY",      "name_ko": "HICP",
     "bbg": "ECCPEMUY Index", "fred": None,      "frequency": "M", "importance": 3},
    {"id": "eu_core_hicp_yoy","country": "EU", "category": "inflation",
     "name": "Core HICP YoY", "name_ko": "Core HICP",
     "bbg": "CPEXEMUY Index", "fred": None,      "frequency": "M", "importance": 3},

    {"id": "uk_cpi_yoy",      "country": "UK", "category": "inflation",
     "name": "CPI YoY",       "name_ko": "CPI",
     "bbg": "UKRPCJYR Index", "fred": None,      "frequency": "M", "importance": 3},
    {"id": "uk_core_cpi_yoy", "country": "UK", "category": "inflation",
     "name": "Core CPI YoY",  "name_ko": "Core CPI",
     "bbg": "UKHCA9IY Index", "fred": None,      "frequency": "M", "importance": 2},

    {"id": "sg_cpi_yoy",      "country": "SG", "category": "inflation",
     "name": "CPI YoY",       "name_ko": "CPI",
     "bbg": "SICPIYY Index",  "fred": None,      "frequency": "M", "importance": 2},
    {"id": "sg_core_cpi",     "country": "SG", "category": "inflation",
     "name": "MAS Core CPI",  "name_ko": "Core CPI",
     "bbg": "SICCYOY Index",  "fred": None,      "frequency": "M", "importance": 2},

    {"id": "au_cpi_yoy_q",    "country": "AU", "category": "inflation",
     "name": "CPI YoY (Q)",   "name_ko": "CPI 분기",
     "bbg": "AUCPIYOY Index", "fred": None,      "frequency": "Q", "importance": 3},
    {"id": "au_cpi_yoy_m",    "country": "AU", "category": "inflation",
     "name": "Monthly CPI YoY","name_ko":"월간 CPI",
     "bbg": "AUCPMYOY Index", "fred": None,      "frequency": "M", "importance": 2},
    {"id": "au_trimmed_mean", "country": "AU", "category": "inflation",
     "name": "Trimmed Mean",  "name_ko": "Trimmed Mean",
     "bbg": "AUCPTMYY Index", "fred": None,      "frequency": "Q", "importance": 3},

    {"id": "jp_cpi_yoy",      "country": "JP", "category": "inflation",
     "name": "National CPI YoY", "name_ko": "전국 CPI",
     "bbg": "JNCPIYOY Index", "fred": None,      "frequency": "M", "importance": 3},
    {"id": "jp_core_cpi",     "country": "JP", "category": "inflation",
     "name": "Core CPI (ex-fresh food)", "name_ko": "Core CPI",
     "bbg": "JNCPIXFF Index", "fred": None,      "frequency": "M", "importance": 3},
    {"id": "jp_tokyo_cpi",    "country": "JP", "category": "inflation",
     "name": "Tokyo CPI YoY", "name_ko": "도쿄 CPI",
     "bbg": "JCPNTOKY Index", "fred": None,      "frequency": "M", "importance": 2},

    {"id": "ca_cpi_yoy",      "country": "CA", "category": "inflation",
     "name": "CPI YoY",       "name_ko": "CPI",
     "bbg": "CACPIYOY Index", "fred": None,      "frequency": "M", "importance": 3},
    {"id": "ca_core_trim",    "country": "CA", "category": "inflation",
     "name": "BoC Core Trim", "name_ko": "Core Trim",
     "bbg": "CPTRYOY Index",  "fred": None,      "frequency": "M", "importance": 2},

    # ── 중앙은행 정책결정 (이벤트) ────────────────────────────────────
    {"id": "fomc",  "country": "US", "category": "central_bank",
     "name": "FOMC Rate Decision", "name_ko": "FOMC",
     "bbg": "FDTR Index",     "fred": "DFEDTARU","frequency": "E", "importance": 3},
    {"id": "ecb",   "country": "EU", "category": "central_bank",
     "name": "ECB Deposit Rate",   "name_ko": "ECB",
     "bbg": "EUORDEPO Index", "fred": None,      "frequency": "E", "importance": 3},
    {"id": "boe",   "country": "UK", "category": "central_bank",
     "name": "BoE Bank Rate",      "name_ko": "BoE",
     "bbg": "UKBRBASE Index", "fred": None,      "frequency": "E", "importance": 3},
    {"id": "mas",   "country": "SG", "category": "central_bank",
     "name": "MAS Policy Statement","name_ko":"MAS",
     "bbg": None,             "fred": None,      "frequency": "E", "importance": 2},
    {"id": "rba",   "country": "AU", "category": "central_bank",
     "name": "RBA Cash Rate",      "name_ko": "RBA",
     "bbg": "RBATCTR Index",  "fred": None,      "frequency": "E", "importance": 3},
    {"id": "boj",   "country": "JP", "category": "central_bank",
     "name": "BoJ Policy Rate",    "name_ko": "BoJ",
     "bbg": "BOJDPBAL Index", "fred": None,      "frequency": "E", "importance": 3},
    {"id": "boc",   "country": "CA", "category": "central_bank",
     "name": "BoC Overnight Rate", "name_ko": "BoC",
     "bbg": "CABROVER Index", "fred": None,      "frequency": "E", "importance": 3},
]


def get_indicator(id_: str) -> dict | None:
    for ind in INDICATORS:
        if ind["id"] == id_:
            return ind
    return None


def by_country(country: str) -> list[dict]:
    return [i for i in INDICATORS if i["country"] == country]


def by_category(category: str) -> list[dict]:
    return [i for i in INDICATORS if i["category"] == category]
