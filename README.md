# Stock Filter & Recommendation (PyQt 데스크톱 프로토타입)

이 저장소는 요청하신 로직을 바탕으로 한 데스크톱 프로토타입입니다. PyQt6 기반으로 실시간(주기적) 시세 조회, 필터 적용, DeMark 목표 계산, 간단한 추천 문구 출력을 제공합니다. 실제 거래 연동은 포함되어 있지 않습니다.

주요 기능
- VIX(\^VIX) 체크: 공포지수 30 이상이면 모든 매매 중단 조건 노출
- 필터: PEG, 매출성장률(연간), MA200, RSI(14), 섹터 대비 Gap(간단 평균 기반)
- 등급 부여: S / A / F
- DeMark 목표(전일 기준) 계산: Pivot/Support/Resistance 및 오늘의 '권장 매수가(디마크 저가)'
- 간단한 백테스터 골격 포함 (app/backtester.py)
- PyQt UI: 다크 테마, 실시간 갱신(기본 60초)

간단 실행 방법
1. 가상환경 생성 (권장)
   python -m venv .venv
   source .venv/bin/activate
2. 의존성 설치
   pip install -r requirements.txt
3. 실행
   python main.py

설계/가정(간단)
- PEG 및 재무 데이터는 yfinance의 `Ticker.info`와 `Ticker.financials`를 사용합니다. 일부 종목은 데이터가 누락될 수 있습니다.
- DeMark 계산: 전일 High/Low/Close를 이용해 X = High + Low + Close, Pivot = X/4, Support = X/2 - High, Resistance = X/2 - Low 방식(요청하신 방식에 기반, 상세 튜닝은 추후)

제한사항
- yfinance는 레이트리밋 및 일부 재무 필드 누락 가능. 프로덕션에서는 유료 API(Finnhub, AlphaVantage, IEX 등)를 권장합니다.

더 진행할 것
- 유저 티커 업로드 UI, 상세 백테스트 리포트(그래프), 실거래 연동(별도 구현)
