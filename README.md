# AI 개인탐구: 클릭반응 데이터 기반 군집 분석과 속도 예측

이 프로젝트는 `Azide-alkyne` 계열 클릭반응을 독립적인 AI 개인탐구 주제로 다룬다. 이전 화학 수행평가나 이후 생물직교화학 대주제를 전제로 하지 않고, 반응 조건과 구조적 특징이 반응속도 또는 활성화에너지와 어떤 관계를 갖는지 데이터 기반으로 분석한다.

## 1. 최종 목표

최종 산출물은 다음 네 가지다.

- 문헌에서 정리한 클릭반응 데이터셋
- PubChem 등 공개 DB에서 확인한 구조명, SMILES, 기본 구조 정보
- 군집 분석과 기초 예측 모델 결과
- 탐구 보고서 초안과 분석 요약

탐구 질문은 다음처럼 잡는다.

- 어떤 조건과 구조 descriptor가 `Azide-alkyne` 클릭반응의 속도 차이와 관련되는가?
- 반응 데이터를 빠른/중간/느린 반응군으로 군집화할 수 있는가?
- 제한된 데이터에서도 반응속도상수 `k` 또는 속도 등급을 기초적으로 예측할 수 있는가?

## 2. 프로젝트 구조

```text
data/
  raw/                 원자료, 수동 정리 CSV, PubChem 조회어
  processed/           검증 결과, feature table, 분석 결과
  schema/              데이터 열 정의
notebooks/             탐구용 Jupyter Notebook
references/            후보 논문과 추출 기록
reports/               보고서 초안과 분석 요약
src/                   검증, 전처리, 분석, PubChem 조회 코드
tests/                 파이프라인 테스트
```

경로 문제를 줄이기 위해 `src` 모듈들은 프로젝트 루트를 자동 탐색한다. 즉 `project-aipersonal` 폴더, `notebooks` 폴더, 또는 다른 하위 폴더에서 실행해도 `data/raw/...` 같은 경로를 프로젝트 루트 기준으로 찾도록 구성했다.

## 3. 설치해야 하는 것

기본 분석에는 Python이 필요하다. 권장 패키지는 `requirements.txt`에 있다.

```bash
python -m pip install -r requirements.txt
```

필수 패키지:

- `pandas`: CSV 데이터 읽기와 정리
- `numpy`: 수치 계산
- `scikit-learn`: PCA, spectral clustering, 회귀 모델
- `matplotlib`, `seaborn`: 그래프 생성
- `jupyter`: notebook 실행

선택 패키지:

- `rdkit`: SMILES에서 분자 descriptor를 자동 계산할 때 사용

RDKit이 없어도 프로젝트는 진행 가능하다. 초기에는 `ring_strain_level`, `fluorine_count`, `fused_aromatic_count`, `heteroatom_in_ring`처럼 수동 descriptor를 사용한다.

현재 환경에 `scikit-learn`이나 `matplotlib`이 없으면 `src/run_analysis.py`는 fallback 방식으로 실행된다. 이 경우 spectral clustering과 그래프 저장은 건너뛰지만, feature 생성, 속도 기반 군집, ridge 회귀 검증, 분석 요약은 생성된다.

## 4. 사용자가 수동으로 해야 할 일

가장 중요한 일은 논문에서 데이터를 정확히 뽑아 CSV로 정리하는 것이다. 

진행 순서:

1. `references/literature_sources.md`에서 후보 논문을 고른다.
2. 특히 단위, 온도, 용매, 반응물 이름, figure/table 위치를 확인한다.
6. 확인된 행을 `data/raw/click_reaction_seed.csv`의 형식에 맞춰 새 CSV에 추가한다. 권장 파일명은 `data/raw/click_reaction_literature.csv`이다.
7. `verification_status`를 처음에는 `needs_primary_check`로 두고, 원논문 표/그림/본문에서 직접 확인한 뒤 `primary_checked`로 바꾼다.
8. 검증, feature 생성, 분석 스크립트를 순서대로 돌린다.

최소 데이터 목표:

- 8행 이상: 파이프라인 테스트와 탐색적 군집 가능
- 15행 이상: 군집 결과를 보고서에 조심스럽게 해석 가능
- 25행 이상: 기초 예측 모델과 변수 중요도 해석이 조금 더 안정적
- 40행 이상: 반응 유형별 비교와 교차검증 결과를 더 설득력 있게 제시 가능

## 5. 데이터셋에 넣을 값

기본 열 정의는 `data/schema/reaction_dataset_columns.csv`에 있다. 중요한 열은 다음과 같다.

| 열 | 의미 |
| --- | --- |
| `record_id` | 각 행의 고유 ID |
| `reaction_type` | `SPAAC`, `CuAAC`, `thermal_Huisgen` 등 |
| `azide` | 아자이드 반응물 |
| `alkyne` | 알카인 반응물 또는 scaffold |
| `catalyst` | 촉매명, 없으면 `none` |
| `catalyst_present` | 촉매 있으면 `1`, 없으면 `0` |
| `solvent`, `solvent_class` | 용매와 큰 분류 |
| `temperature_K` | 절대온도 K |
| `pH` | pH, 없으면 빈칸 |
| `k_value`, `k_unit` | 속도상수와 단위 |
| `Ea_kJ_mol` | 활성화에너지 |
| `yield_percent` | 수율 |
| `SMILES` | 대표 구조의 SMILES |
| `alkyne_family` | `cyclooctyne`, `fluorinated_cyclooctyne` 등 |
| `ring_strain_level` | 수동 strain 등급, 보통 0-3 |
| `fluorine_count` | fluorine 치환 수 |
| `fused_aromatic_count` | fused aromatic ring 수 |
| `heteroatom_in_ring` | 핵심 고리 내 heteroatom 있으면 `1` |
| `rate_label` | `slow`, `medium`, `fast` |
| `source`, `source_doi` | 논문 제목/출처와 DOI |
| `source_type` | `primary_article`, `review`, `public_db`, `secondary_summary` |
| `verification_status` | `primary_checked`, `needs_primary_check`, `template` |
| `notes` | 비교 한계, 표/그림 위치 |

주의할 점:

- `k_value`가 있으면 `k_unit`도 반드시 적는다.
- 서로 다른 단위의 `k`를 섞지 않는다. 가능하면 `M^-1 s^-1`인 second-order rate constant 위주로 모은다.
- 온도는 섭씨가 아니라 K로 넣는다. 예: 25°C = 298.15 K.
- 조건이 다른 값을 직접 비교할 때는 `notes`에 한계를 적는다.


## 6. 공개 DB 탐색

PubChem 조회어는 `data/raw/pubchem_query_terms.csv`에 있다. 네트워크가 가능한 환경에서 다음 명령을 실행하면 구조명, SMILES, 분자식, 분자량 조회 결과가 `data/processed/pubchem_lookup.csv`에 저장된다.

```bash
python src/fetch_pubchem_smiles.py --terms data/raw/pubchem_query_terms.csv
```

PubChem 결과는 자동으로 믿지 말고, 논문에서 사용한 정확한 derivative와 일치하는지 확인해야 한다. 특히 `DIBO`, `DBCO`, `DIBAC`, `ADIBO`, `BARAC`처럼 약어가 여러 형태로 쓰이는 경우 주의한다.

## 7. 분석 프로그램 실행

먼저 seed 데이터로 전체 흐름이 작동하는지 확인한다.

```bash
python src/validate_dataset.py --input data/raw/click_reaction_seed.csv
python src/build_features.py --input data/raw/click_reaction_seed.csv
python src/run_analysis.py --input data/raw/click_reaction_seed.csv
```

문헌 데이터를 새 파일에 모았다면 다음처럼 입력 파일만 바꾼다.

```bash
python src/validate_dataset.py --input data/raw/click_reaction_literature.csv
python src/build_features.py --input data/raw/click_reaction_literature.csv
python src/run_analysis.py --input data/raw/click_reaction_literature.csv
```

추출한 CSV에는 `4.3 × 10-3`, `>95`, `확인 필요`, `near neutral`처럼 사람이 읽는 표현이 들어갈 수 있다. 이 경우 원본은 그대로 두고 cleaned CSV를 만든 뒤 분석한다.

```bash
python src/clean_literature_dataset.py --input data/raw/click_reaction_literature.csv
python src/validate_dataset.py --input data/processed/click_reaction_literature_cleaned.csv
python src/build_features.py --input data/processed/click_reaction_literature_cleaned.csv
python src/run_analysis.py --input data/processed/click_reaction_literature_cleaned.csv
```

현재 파일명이 `click_reaction_literature.csv.csv`처럼 저장되어 있다면 명령의 입력 파일명만 그 이름으로 바꿔 쓰면 된다.

생성되는 주요 파일:

- `data/processed/validation_summary.json`: 필수 열, 단위, 숫자 오류 검증 결과
- `data/processed/literature_cleaning_report.json`: 추출 CSV를 분석용으로 정리한 결과와 데이터 충분성 요약
- `data/processed/model_features.csv`: 모델 입력용 feature table
- `data/processed/analysis_coordinates.csv`: PCA 또는 fallback 좌표와 군집 결과
- `data/processed/feature_importance.csv`: `log10(k)`와 feature의 관련성
- `data/processed/model_metrics.json`: 모델과 분석 메트릭
- `reports/analysis_summary.md`: 보고서에 옮길 수 있는 분석 요약
- `reports/figures/pca_clusters.png`: `matplotlib`, `seaborn` 설치 시 생성되는 시각화

테스트는 다음으로 실행한다.

```bash
python -m unittest tests/test_pipeline.py
```

## 8. 분석 원리

`src/validate_dataset.py`는 데이터가 분석 가능한 형식인지 확인한다. 필수 열 누락, 빈 값, 숫자가 아닌 값, `k_unit` 누락, pH 범위, 수율 범위 등을 검사한다. `verification_status`가 `primary_checked`가 아니면 경고를 띄운다.

`src/build_features.py`는 모델용 feature를 만든다. 숫자형 열은 결측값을 중앙값으로 채우고, 범주형 열은 one-hot encoding으로 바꾼다. 반응속도상수는 범위가 넓기 때문에 `log10_k = log10(k_value)`를 예측/해석 대상값으로 만든다.

`src/run_analysis.py`는 세 가지 분석을 한다.

- 차원 축소: `scikit-learn`이 있으면 PCA, 없으면 NumPy SVD fallback을 사용한다.
- 군집 분석: `scikit-learn`이 있으면 spectral clustering, 없으면 `log10(k)` 분위수로 slow/medium/fast cluster를 만든다.
- 기초 예측: ridge regression의 leave-one-out RMSE를 계산한다. 데이터가 적기 때문에 정확도보다 과적합 위험과 해석 가능성을 보는 용도다.

`feature_importance.csv`는 엄밀한 인과 분석이 아니라 `log10(k)`와 각 feature의 절대 상관을 정리한 탐색 지표다. 보고서에서는 "이 feature가 반응속도를 결정한다"가 아니라 "이 데이터셋에서는 이 feature가 속도 차이와 함께 변하는 경향을 보였다"라고 해석한다.


```

## 9. 좋은 데이터의 기준

보고서에 넣을 최종 데이터는 다음 조건을 만족해야 한다.

- `verification_status`가 가능한 한 `primary_checked`이다.
- `source_doi` 또는 원문 링크가 있다.
- 같은 논문에서 가져온 값이라도 조건이 다르면 행이 분리되어 있다.
- `k_value`의 단위가 명확하다.
- `temperature_K`, `solvent`, `catalyst`가 비어 있지 않다.
- `notes`에 표/그림/본문 위치와 비교 한계가 적혀 있다.

가장 중요한 원칙은 간단하다. 데이터의 근거는 반드시 논문이다.
