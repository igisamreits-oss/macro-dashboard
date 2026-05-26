# Global REIT Macro Dashboard

격주 글로벌 리츠 운용미팅용 매크로 지표 대시보드.

## 구성

- **캘린더**: T-7 ~ T+28 (5주), 6개국 (US / EU·UK / SG / AU / JP / CA)
- **카테고리 (v1)**: 물가 + 중앙은행 정책결정
- **데이터 소스**: Bloomberg (xbbg) primary + FRED/investing.com fallback
- **호스팅**: GitHub Pages + GitHub Actions

## 디렉토리

```
macro-dashboard/
├── scripts/
│   ├── config.py             # 지표 마스터 정의
│   ├── fetch_bloomberg.py    # 회사 PC에서 매일 7:30am 실행
│   ├── fetch_fred.py         # GitHub Actions cron (US 백업)
│   ├── fetch_calendar.py     # GitHub Actions cron (캘린더)
│   └── build_dashboard.py    # JSON → HTML
├── templates/
│   └── index.html.j2         # Jinja2 템플릿
├── data/                     # fetcher 출력 (JSON)
│   ├── bloomberg/
│   ├── fred/
│   └── calendar/
├── docs/                     # GitHub Pages 루트 (자동 생성)
├── .github/workflows/
│   └── build.yml             # CI/CD
└── requirements.txt
```

## 실행

```bash
pip install -r requirements.txt
python scripts/build_dashboard.py
# docs/index.html 생성됨
```

## 일일 자동화

- **블룸버그 PC (Windows Task Scheduler, 매일 07:30 KST)**
  - `python scripts/fetch_bloomberg.py`
  - `git add data/bloomberg && git commit && git push`
- **GitHub Actions (매일 01:00 UTC = 10:00 KST)**
  - `fetch_fred.py` + `fetch_calendar.py` + `build_dashboard.py`
  - `docs/` 자동 푸시 → Pages 갱신
