# Data Analyst Portfolio | OVERDARE

오버데어(OVERDARE) 데이터 분석가 지원을 위한 주요 프로젝트 저장소입니다.  
가설 수립, 통계적 검정, 시뮬레이션 모델링, 실측 데이터 파이프라인 구축 및 검증 전 과정을 다룬 5개 프로젝트로 구성되어 있습니다.

---

## 핵심 역량 및 기술 스택

* **Methodologies:** 데이터 검증 및 스크리닝(Data Validation & Screening), 비모수 검정(Non-Parametric Testing), 대기열 이론(M/M/1 Queuing Model), 몬테카를로 시뮬레이션(Monte Carlo Simulation), 통계적 가설 검정, 텍스트 마이닝
* **Languages & Tools:** Python (Pandas, NumPy, SciPy, Statsmodels, BeautifulSoup4, Matplotlib), SQL (SQLite), Git

---

## 주요 프로젝트 목록

### 1. 서브노티카2 유저 행동 가설 검증 및 리뷰 데이터 분석
* **내용:** 플레이어 이탈 가설 시뮬레이션 설계 및 실제 Steam 리뷰 데이터(n=150) 기반 검증
* **기술 스택:** Python (Pandas, SciPy), SQLite (Dual Pipeline), Chi-Square Test, Mann-Whitney U Test
* **주요 성과:**
  * 조우 유형별 이탈률(카이제곱 검정) 및 파밍 시도 횟수(Mann-Whitney U 검정) 기반 UX 시뮬레이션 구축
  * Steam 리뷰 수집 파이프라인 구축 후 원문 직접 대조를 통해 오탐 가능성이 높은 키워드(예: PC)를 정화하는 데이터 전처리 프로세스 적용
  * 1.1 패치 비살상 설계 관련 유저 불만("대응 수단 부재")과 습성 도입 가설의 배경을 분리하여 정직한 데이터 해석 도출


### 2. 리그 오브 레전드 사망 위치 기반 이상 패턴 탐지 및 오탐 감소 분석
* **내용:** 적진 사망 좌표 데이터 기반 포지션별 기준선 검증 및 제재 시스템 오탐 위험 완화
* **기술 스택:** Python (Pandas, SciPy, Statsmodels), SQL, Kruskal-Wallis, Mann-Whitney U, Riot Match-V5 API
* **주요 성과:**
  * 20경기(1,141건 사망 이벤트) 실데이터 기반 좌표 산출 및 팀/포지션/라인전 단계별 그룹화
  * 단일 절대 기준 대비 포지션 기반 Z-score 적용 시 정상 유저의 트롤 오탐 플래그 29건에서 1건으로 감소 수치 검증


### 3. AI NPC 아키텍처 비동기 처리 및 대기열 최적화 시뮬레이션
* **내용:** 카디널(중앙집중형) vs 대지인(개별지능형) AI NPC 구조의 부하, 지연시간, 유저 경험 다양성 비교
* **기술 스택:** Python (NumPy, SciPy), Queueing Theory (M/M/1 Model), KS Test
* **주요 성과:**
  * 가동률 $u$ 기반 M/M/1 대기열 공식을 적용하여 시스템 붕괴 원인이 처리 속도가 아닌 서버 비용의 선형 증가임을 수치적 교차 검증
  * 독립된 지수분포 간 무기억성을 활용한 KS 검정($p=0.955$)으로 탐지 로직 비노출 유저 경험 모델링 설계


### 4. 슬레이 더 스파이어 2 드로우 확률 모델과 유저 체감 간 괴리 정량화
* **내용:** 덱 빌딩 게임 내 드로우 확률 수식화 및 유저 체감의 수학적 재정의
* **기술 스택:** Python (NumPy, Counter), Monte Carlo Simulation, Hypergeometric Distribution
* **주요 성과:**
  * 물리적 카드 복원 모델 기각 후 '동일 카드명 겹침'으로 문제 재정의하여 유저 체감 수치(80%)와 수학적 결과(73%) 대조 성공
  * 단순 연산 재정의를 통해 계산 복잡성을 제거한 경량화 시뮬레이션 구현


### 5. 팰월드 패치 및 플레이 동기 감쇠 곡선 시뮬레이션
* **내용:** 게임 밸런스 재설계가 유저 Retention에 미치는 영향 모델링 및 커뮤니티 데이터 검증
* **기술 스택:** Python (NumPy, Pandas, BeautifulSoup4), Z-Test, Web Scraping Pipeline
* **주요 성과:**
  * EA 대비 1.0 패치노트 이정표 반영 및 동기 감쇠 곡선 시뮬레이션(`np.trapezoid` 적용)을 통한 라이브 케어 가설 입증
  * 커뮤니티(디시인사이드 840건) 스크래핑을 통한 특정 아이템/레벨 장벽 불만 정성 분석 및 가설 교차 검증


---

## Contact
* **Email:** kurogensi@naver.com
* **GitHub:** [https://github.com/Xikuro01/Data-Projects-Archive]
