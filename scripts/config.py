"""
지표 마스터 정의 — 모든 fetcher와 builder가 이 파일을 참조한다.

INDICATOR 필드:
  id           : 내부 식별자
  country      : COUNTRIES 코드
  category     : CATEGORIES 키 (스냅샷형 vs 이벤트형 구분은 CATEGORIES.is_snapshot)
  name / name_ko : 표시명
  bbg          : Bloomberg ticker (None이면 Bloomberg fetch 스킵)
  fred         : FRED series ID (None이면 FRED 스킵)
  frequency    : D(Daily) / W(Weekly) / M(Monthly) / Q(Quarterly) / E(Event)
  importance   : 1(★) / 2(★★) / 3(★★★)
  unit         : "%" / "index" / "bp" 등 표시 단위
  decimals     : 표시 소수점 자릿수
  note         : 보충 설명 (옵션)
"""

COUNTRIES = {
    "US": {"name": "United States", "flag": "🇺🇸", "tz": "America/New_York"},
    "EU": {"name": "Eurozone",      "flag": "🇪🇺", "tz": "Europe/Frankfurt"},
    "UK": {"name": "United Kingdom","flag": "🇬🇧", "tz": "Europe/London"},
    "DE": {"name": "Germany",       "flag": "🇩🇪", "tz": "Europe/Berlin"},
    "FR": {"name": "France",        "flag": "🇫🇷", "tz": "Europe/Paris"},
    "SE": {"name": "Sweden",        "flag": "🇸🇪", "tz": "Europe/Stockholm"},
    "SG": {"name": "Singapore",     "flag": "🇸🇬", "tz": "Asia/Singapore"},
    "HK": {"name": "Hong Kong",     "flag": "🇭🇰", "tz": "Asia/Hong_Kong"},
    "AU": {"name": "Australia",     "flag": "🇦🇺", "tz": "Australia/Sydney"},
    "JP": {"name": "Japan",         "flag": "🇯🇵", "tz": "Asia/Tokyo"},
    "KR": {"name": "Korea",         "flag": "🇰🇷", "tz": "Asia/Seoul"},
    "CA": {"name": "Canada",        "flag": "🇨🇦", "tz": "America/Toronto"},
}

# is_snapshot=True → "Markets Snapshot" 섹션 (캘린더 X)
# is_snapshot=False → 카테고리별 패널 + 캘린더 (이벤트형)
CATEGORIES = {
    "policy_rate":         {"name_ko": "단기 정책금리",       "is_snapshot": True,  "order": 1, "emoji": "💵"},
    "breakeven":           {"name_ko": "Breakeven 10Y",      "is_snapshot": True,  "order": 3, "emoji": "📈"},
    "mortgage_rate":       {"name_ko": "모기지금리",          "is_snapshot": True,  "order": 4, "emoji": "🏠"},
    "inflation":           {"name_ko": "물가",               "is_snapshot": False, "order": 5, "emoji": "📊"},
    "central_bank":        {"name_ko": "중앙은행",            "is_snapshot": False, "order": 6, "emoji": "🏦"},
    "unemployment":        {"name_ko": "실업률",              "is_snapshot": False, "order": 7, "emoji": "👥"},
    "housing":             {"name_ko": "주택지표",            "is_snapshot": False, "order": 8, "emoji": "🏘️"},
    "consumer_confidence": {"name_ko": "소비자심리",          "is_snapshot": False, "order": 9, "emoji": "💭"},
    "retail_sales":        {"name_ko": "소매판매",            "is_snapshot": False, "order": 10, "emoji": "🛒"},
}


# 각 indicator 디폴트: decimals=1, unit="%"
def _ind(**kwargs):
    defaults = {"unit": "%", "decimals": 1, "fred": None, "ois_1y_bbg": None, "note": ""}
    defaults.update(kwargs)
    return defaults


INDICATORS = [
    # ═══════════════════════════════════════════════════════════════════
    # 스냅샷형 — 단기 정책금리 / 오버나이트
    # ═══════════════════════════════════════════════════════════════════
    _ind(id="us_pol_sofr",     country="US", category="policy_rate", name="SOFR",        name_ko="SOFR",       bbg="SOFRRATE Index",  fred="SOFR", frequency="D", importance=2, decimals=2),
    _ind(id="ca_pol_corra",    country="CA", category="policy_rate", name="CORRA",       name_ko="CORRA",      bbg="CAONREPO Index",  frequency="D", importance=2, decimals=2),
    _ind(id="uk_pol_sonia",    country="UK", category="policy_rate", name="SONIA",       name_ko="SONIA",      bbg="SONIO/N Index",   frequency="D", importance=2, decimals=2),
    _ind(id="eu_pol_estr",     country="EU", category="policy_rate", name="€STR",        name_ko="€STR",       bbg="ESTRON Index",    frequency="D", importance=2, decimals=2),
    _ind(id="kr_pol_cd91",     country="KR", category="policy_rate", name="KRW 91D CD",  name_ko="CD91",       bbg="KWCDC Curncy",    frequency="D", importance=2, decimals=2),
    _ind(id="sg_pol_sora",     country="SG", category="policy_rate", name="SORA",        name_ko="SORA",       bbg="SIBCSORA Index",  frequency="D", importance=2, decimals=2),
    _ind(id="hk_pol_hibor3m",  country="HK", category="policy_rate", name="HIBOR 3M",    name_ko="HIBOR 3M",   bbg="HIHD03M Index",   frequency="D", importance=2, decimals=2),
    _ind(id="se_pol_stib3m",   country="SE", category="policy_rate", name="STIBOR 3M",   name_ko="STIBOR 3M",  bbg="STIB3M Index",    frequency="D", importance=1, decimals=2),

    # (크레딧 스프레드 카테고리 제거 — FICV 티커 분리되어 통일 어려움)

    # ═══════════════════════════════════════════════════════════════════
    # 스냅샷형 — Breakeven Inflation 10Y
    # ═══════════════════════════════════════════════════════════════════
    _ind(id="us_be_10y", country="US", category="breakeven", name="US 10Y Breakeven", name_ko="US 10Y",  bbg="USGGBE10 Index", frequency="D", importance=2, decimals=2),
    _ind(id="uk_be_10y", country="UK", category="breakeven", name="UK 10Y Breakeven", name_ko="UK 10Y",  bbg="UKGGBE10 Index", frequency="D", importance=2, decimals=2),
    _ind(id="eu_be_10y", country="EU", category="breakeven", name="EU 10Y Swap BE",   name_ko="EU 10Y",  bbg="EUSWSB10 Index", frequency="D", importance=2, decimals=2, note="Swap-based"),
    _ind(id="de_be_10y", country="DE", category="breakeven", name="DE 10Y Breakeven", name_ko="DE 10Y",  bbg="DEGGBE10 Index", frequency="D", importance=1, decimals=2),
    _ind(id="fr_be_10y", country="FR", category="breakeven", name="FR 10Y Breakeven", name_ko="FR 10Y",  bbg="FRGG10EB Index", frequency="D", importance=1, decimals=2),
    _ind(id="au_be_10y", country="AU", category="breakeven", name="AU 10Y Breakeven", name_ko="AU 10Y",  bbg="ADGGBE10 Index", frequency="D", importance=1, decimals=2),
    _ind(id="jp_be_10y", country="JP", category="breakeven", name="JP 10Y Breakeven", name_ko="JP 10Y",  bbg="JYGGBE10 Index", frequency="D", importance=1, decimals=2),
    _ind(id="se_be_10y", country="SE", category="breakeven", name="SE 10Y Breakeven", name_ko="SE 10Y",  bbg="SKGGBE10 Index", frequency="D", importance=1, decimals=2),

    # ═══════════════════════════════════════════════════════════════════
    # 스냅샷형 — 모기지금리
    # ═══════════════════════════════════════════════════════════════════
    _ind(id="us_mort_30y", country="US", category="mortgage_rate", name="US 30Y Fixed Mortgage", name_ko="US 30Y 모기지", bbg="NMCMFR30 Index", fred="MORTGAGE30US", frequency="W", importance=3, decimals=2),

    # ═══════════════════════════════════════════════════════════════════
    # 이벤트형 — 물가 (기존 유지)
    # ═══════════════════════════════════════════════════════════════════
    _ind(id="us_cpi_yoy",       country="US", category="inflation", name="CPI YoY",         name_ko="CPI",          bbg="CPI YOY Index",   fred="CPIAUCSL",  frequency="M", importance=3),
    _ind(id="us_core_cpi_yoy",  country="US", category="inflation", name="Core CPI YoY",    name_ko="Core CPI",     bbg="CPI XYOY Index",  fred="CPILFESL",  frequency="M", importance=3),
    _ind(id="us_pce_yoy",       country="US", category="inflation", name="PCE YoY",         name_ko="PCE",          bbg="PCE DEFY Index",  fred="PCEPI",     frequency="M", importance=3),
    _ind(id="us_core_pce_yoy",  country="US", category="inflation", name="Core PCE YoY",    name_ko="Core PCE",     bbg="PCE CYOY Index",  fred="PCEPILFE",  frequency="M", importance=3),
    _ind(id="eu_hicp_yoy",      country="EU", category="inflation", name="HICP YoY",        name_ko="HICP",         bbg="ECCPEMUY Index",  frequency="M", importance=3),
    _ind(id="eu_core_hicp_yoy", country="EU", category="inflation", name="Core HICP YoY",   name_ko="Core HICP",    bbg="CPEXEMUY Index",  frequency="M", importance=3),
    _ind(id="uk_cpi_yoy",       country="UK", category="inflation", name="CPI YoY",         name_ko="CPI",          bbg="UKRPCJYR Index",  frequency="M", importance=3),
    _ind(id="uk_core_cpi_yoy",  country="UK", category="inflation", name="Core CPI YoY",    name_ko="Core CPI",     bbg="UKHCA9IY Index",  frequency="M", importance=2),
    _ind(id="sg_cpi_yoy",       country="SG", category="inflation", name="CPI YoY",             name_ko="CPI",          bbg="SICPIYOY Index",  frequency="M", importance=2),
    _ind(id="sg_core_cpi",      country="SG", category="inflation", name="MAS Core CPI",        name_ko="MAS Core",     bbg="SMASCORE Index",  frequency="M", importance=2),
    _ind(id="au_cpi_yoy_q",     country="AU", category="inflation", name="CPI YoY (Q)",         name_ko="CPI 분기",     bbg="AUCPIYOY Index",  frequency="Q", importance=3),
    _ind(id="au_core_yoy",      country="AU", category="inflation", name="Underlying Core CPI", name_ko="Core CPI",     bbg="AUUIR Index",     frequency="Q", importance=3),
    _ind(id="jp_cpi_yoy",       country="JP", category="inflation", name="National CPI YoY",    name_ko="전국 CPI",     bbg="JNCPIYOY Index",  frequency="M", importance=3),
    _ind(id="jp_core_cpi",      country="JP", category="inflation", name="Core CPI ex Fresh",   name_ko="Core CPI",     bbg="JNCPIXFF Index",  frequency="M", importance=3),
    _ind(id="jp_core_core",     country="JP", category="inflation", name="Core-Core (ex F&E)",  name_ko="Core-Core",    bbg="JCPNEFFE Index",  frequency="M", importance=2),
    _ind(id="ca_cpi_yoy",       country="CA", category="inflation", name="CPI YoY",             name_ko="CPI",          bbg="CACPIYOY Index",  frequency="M", importance=3),
    _ind(id="ca_core_trim",     country="CA", category="inflation", name="BoC Core Trim",       name_ko="Core Trim",    bbg="CACPTYOY Index",  frequency="M", importance=2),

    # ═══════════════════════════════════════════════════════════════════
    # 이벤트형 — 중앙은행 정책결정 (기존 유지)
    # ═══════════════════════════════════════════════════════════════════
    _ind(id="fomc", country="US", category="central_bank", name="FOMC Rate Decision",   name_ko="FOMC", bbg="FDTR Index",     fred="DFEDTARU", ois_1y_bbg="USSO1 Curncy",  frequency="E", importance=3, decimals=2),
    _ind(id="ecb",  country="EU", category="central_bank", name="ECB Deposit Rate",     name_ko="ECB",  bbg="EUORDEPO Index", ois_1y_bbg="EESWE1 Curncy", frequency="E", importance=3, decimals=2),
    _ind(id="boe",  country="UK", category="central_bank", name="BoE Bank Rate",        name_ko="BoE",  bbg="UKBRBASE Index", ois_1y_bbg="BPSWS1 Curncy", frequency="E", importance=3, decimals=2),
    _ind(id="mas",  country="SG", category="central_bank", name="MAS Policy Statement", name_ko="MAS",  bbg=None,             frequency="E", importance=2, decimals=2),
    _ind(id="rba",  country="AU", category="central_bank", name="RBA Cash Rate",        name_ko="RBA",  bbg="RBATCTR Index",  ois_1y_bbg="ADSO1 Curncy",  frequency="E", importance=3, decimals=2),
    _ind(id="boj",  country="JP", category="central_bank", name="BoJ Policy Rate",      name_ko="BoJ",  bbg="BOJDPBAL Index", ois_1y_bbg="JYSO1 Curncy",  frequency="E", importance=3, decimals=2),
    _ind(id="boc",  country="CA", category="central_bank", name="BoC Overnight Rate",   name_ko="BoC",  bbg="CABROVER Index", ois_1y_bbg="CDSO1 Curncy",  frequency="E", importance=3, decimals=2),

    # ═══════════════════════════════════════════════════════════════════
    # 이벤트형 — 실업률
    # ═══════════════════════════════════════════════════════════════════
    _ind(id="us_unemp",     country="US", category="unemployment", name="Unemployment Rate",       name_ko="실업률",                  bbg="USURTOT Index",  fred="UNRATE", frequency="M", importance=3),
    _ind(id="ca_unemp",     country="CA", category="unemployment", name="Unemployment Rate",       name_ko="실업률",                  bbg="CANLXEMR Index", frequency="M", importance=3),
    _ind(id="uk_unemp_ilo", country="UK", category="unemployment", name="ILO Unemployment Rate",   name_ko="실업률 (3M MA)",          bbg="UKUEILOR Index", frequency="M", importance=2),
    _ind(id="eu_unemp",     country="EU", category="unemployment", name="Unemployment Rate",       name_ko="유로존 실업률",            bbg="UMRTEMU Index",  frequency="M", importance=2),
    _ind(id="au_unemp",     country="AU", category="unemployment", name="Unemployment Rate",       name_ko="실업률",                  bbg="AULFUNEM Index", frequency="M", importance=2),
    _ind(id="jp_unemp",     country="JP", category="unemployment", name="Unemployment Rate",       name_ko="실업률",                  bbg="JNUE Index",     frequency="M", importance=2),
    _ind(id="kr_unemp",     country="KR", category="unemployment", name="Unemployment Rate",       name_ko="실업률",                  bbg="KOEAUERS Index", frequency="M", importance=2),
    _ind(id="hk_unemp",     country="HK", category="unemployment", name="Unemployment Rate (3MMA)",name_ko="실업률 (3M MA)",          bbg="HKUERATE Index", frequency="M", importance=2),
    _ind(id="sg_unemp",     country="SG", category="unemployment", name="Unemployment Rate Overall SA", name_ko="실업률 SA",          bbg="SIQUTOTA Index", frequency="Q", importance=2),
    _ind(id="se_unemp",     country="SE", category="unemployment", name="Unemployment Rate",       name_ko="실업률",                  bbg="SWUERATE Index", frequency="M", importance=1),

    # ═══════════════════════════════════════════════════════════════════
    # 이벤트형 — 주택지표
    # ═══════════════════════════════════════════════════════════════════
    _ind(id="us_nahb",                  country="US", category="housing", name="NAHB Housing Market Index",        name_ko="NAHB (50 기준)",             bbg="USHBMIDX Index", fred="HOUST", frequency="M", importance=3, unit="index", decimals=0),
    _ind(id="us_housing_starts",        country="US", category="housing", name="Housing Starts (k)",               name_ko="주택착공 (천호)",            bbg="NHSPSTOT Index", fred="HOUST", frequency="M", importance=3, unit="k", decimals=0),
    _ind(id="us_existing_home_sales",   country="US", category="housing", name="Existing Home Sales (M)",          name_ko="기존주택매매 (백만호)",      bbg="ETSLTOTL Index", fred="EXHOSLUSM495S", frequency="M", importance=3, unit="M", decimals=2),
    _ind(id="us_case_shiller_yoy",     country="US", category="housing", name="Case-Shiller 20-City YoY",         name_ko="Case-Shiller 20",            bbg="SPCS20Y% Index", fred="SPCS20RSA", frequency="M", importance=3, note="2개월 시차"),
    _ind(id="ca_housing_starts",        country="CA", category="housing", name="Housing Starts",                   name_ko="주택착공",                   bbg="EHHUCA Index",   frequency="M", importance=2, unit="k", decimals=0),
    _ind(id="uk_nationwide_mom",        country="UK", category="housing", name="Nationwide House Price MoM",       name_ko="Nationwide HPI MoM",         bbg="UKNBAAMM Index", frequency="M", importance=2),
    _ind(id="de_construction_pmi",      country="DE", category="housing", name="Construction PMI SA",              name_ko="건설 PMI (50)",              bbg="MPMIDEXA Index", frequency="M", importance=2, unit="index", decimals=1),
    _ind(id="fr_construction_pmi",      country="FR", category="housing", name="Construction PMI SA",              name_ko="건설 PMI (50)",              bbg="MPMIFRXA Index", frequency="M", importance=2, unit="index", decimals=1),
    _ind(id="jp_housing_starts_yoy",    country="JP", category="housing", name="Housing Starts YoY",               name_ko="주택착공 YoY",               bbg="JNHSYOY Index",  frequency="M", importance=2),
    _ind(id="kr_kb_hpi_yoy",            country="KR", category="housing", name="KB House Price Index YoY",         name_ko="KB 전국 YoY",                bbg="KOHPTYOY Index", frequency="M", importance=3),
    _ind(id="kr_kb_hpi_seoul_yoy",      country="KR", category="housing", name="KB Seoul Price YoY",               name_ko="KB 서울 YoY",                bbg="KOHPSYOY Index", frequency="M", importance=3),
    _ind(id="hk_rvd_hpi",               country="HK", category="housing", name="RVD HK Property Price Index",      name_ko="RVD 주택가격지수",           bbg="HKRLPDAP Index", frequency="W", importance=2, unit="index", decimals=1),
    _ind(id="hk_property_transactions", country="HK", category="housing", name="HK Property Transactions",         name_ko="부동산 거래량",              bbg="HKLRTRBU Index", frequency="M", importance=2, unit="cnt", decimals=0),
    _ind(id="sg_ura_ppi",               country="SG", category="housing", name="URA Private Residential PPI",      name_ko="URA 주택가격지수",           bbg=None,             frequency="Q", importance=3, unit="index", decimals=1, note="티커 확인 필요"),

    # ═══════════════════════════════════════════════════════════════════
    # 이벤트형 — 소비자심리
    # ═══════════════════════════════════════════════════════════════════
    _ind(id="us_michigan",        country="US", category="consumer_confidence", name="U-Michigan Sentiment",        name_ko="미시간 (월2회)", bbg="CONSSENT Index", fred="UMCSENT", frequency="M", importance=3, unit="index", decimals=1),
    _ind(id="us_cb_confidence",   country="US", category="consumer_confidence", name="Conference Board Confidence", name_ko="Conf Board",     bbg="CONCCONF Index", frequency="M", importance=3, unit="index", decimals=1),
    _ind(id="ca_nanos",           country="CA", category="consumer_confidence", name="Bloomberg Nanos BNCCI",       name_ko="Nanos 신뢰",     bbg="BNCCINDX Index", frequency="W", importance=2, unit="index", decimals=1),
    _ind(id="uk_gfk",             country="UK", category="consumer_confidence", name="GfK Consumer Confidence",     name_ko="GfK",            bbg="UKCCI Index",    frequency="M", importance=2, unit="net", decimals=0),
    _ind(id="eu_consumer_conf",   country="EU", category="consumer_confidence", name="EC Consumer Confidence",      name_ko="EU 소비자신뢰",  bbg="EUCCEMU Index",  frequency="M", importance=2, unit="net", decimals=1),
    _ind(id="jp_consumer_conf",   country="JP", category="consumer_confidence", name="Consumer Confidence",         name_ko="소비자신뢰",     bbg="JCONSENT Index", frequency="M", importance=2, unit="index", decimals=1),
    _ind(id="se_consumer_conf",   country="SE", category="consumer_confidence", name="Consumer Confidence SA",      name_ko="소비자신뢰",     bbg="SWETCI Index",   frequency="M", importance=1, unit="index", decimals=1),

    # ═══════════════════════════════════════════════════════════════════
    # 이벤트형 — 소매판매
    # ═══════════════════════════════════════════════════════════════════
    _ind(id="us_retail_mom",          country="US", category="retail_sales", name="Retail Sales MoM SA",         name_ko="소매판매 MoM",         bbg="RSTAMOM Index",  fred="RSAFS", frequency="M", importance=3),
    _ind(id="ca_retail_mom",          country="CA", category="retail_sales", name="Retail Sales MoM SA",         name_ko="소매판매 MoM",         bbg="CARSCHNG Index", frequency="M", importance=2),
    _ind(id="uk_retail_ex_fuel_mom",  country="UK", category="retail_sales", name="Retail Sales ex Fuel MoM",    name_ko="소매판매(연료제외) MoM", bbg="UKRVAMOM Index", frequency="M", importance=2),
    _ind(id="eu_retail_mom",          country="EU", category="retail_sales", name="Retail Sales Vol MoM SA",     name_ko="소매판매 MoM",         bbg="RSSAEMUM Index", frequency="M", importance=2),
    _ind(id="au_retail_mom",          country="AU", category="retail_sales", name="Retail Sales MoM SA",         name_ko="소매판매 MoM",         bbg="AURSTSA Index",  frequency="M", importance=2),
    _ind(id="jp_retail_mom",          country="JP", category="retail_sales", name="Large-Scale Retail MoM SA",   name_ko="대형소매 MoM",         bbg="JNRSMOM Index",  frequency="M", importance=2),
    _ind(id="kr_retail_mom",          country="KR", category="retail_sales", name="Retail Sales MoM SA",         name_ko="소매판매 MoM",         bbg="KOCGCGSM Index", frequency="M", importance=2),
    _ind(id="hk_retail_yoy",          country="HK", category="retail_sales", name="Retail Sales Value YoY",      name_ko="소매판매 YoY",         bbg="HKRSVANY Index", frequency="M", importance=2, note="YoY only"),
    _ind(id="sg_retail_mom",          country="SG", category="retail_sales", name="Retail Sales Total MoM SA",   name_ko="소매판매 MoM",         bbg="SRSATM Index",   frequency="M", importance=2),
    _ind(id="se_retail_ex_fuel_mom",  country="SE", category="retail_sales", name="Retail Sales ex Fuel MoM",    name_ko="소매판매 MoM",         bbg="SWRSAMM Index",  frequency="M", importance=1),
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


def snapshot_categories() -> list[str]:
    return [k for k, v in CATEGORIES.items() if v["is_snapshot"]]


def event_categories() -> list[str]:
    return [k for k, v in CATEGORIES.items() if not v["is_snapshot"]]
