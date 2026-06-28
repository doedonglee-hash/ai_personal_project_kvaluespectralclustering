from pathlib import Path  # 파일과 폴더 경로를 운영체제에 맞게 다루기 위한 표준 라이브러리이다.

# 프로젝트 루트 판별에 사용할 대표 폴더 이름 목록이다.
PROJECT_DIR_NAMES = {
    "data",  # 원본 데이터와 처리된 데이터가 들어 있는 폴더이다.
    "notebooks",  # Jupyter Notebook 실행 파일이 들어 있는 폴더이다.
    "references",  # 참고 문헌과 조사 기록이 들어 있는 폴더이다.
    "reports",  # 분석 요약과 그래프 결과물이 저장되는 폴더이다.
    "src",  # 실제 Python 실행 코드가 들어 있는 폴더이다.
    "tests",  # 코드가 정상 동작하는지 확인하는 테스트 폴더이다.
}


def find_project_root(start: Path | None = None) -> Path:
    """Locate the project root from a script, notebook, or child directory."""
    module_root = Path(__file__).resolve().parents[1]  # 현재 설정 파일 기준으로 프로젝트 루트를 우선 추정한다.
    candidates = [module_root]  # 탐색 후보 목록에 모듈 기준 루트를 먼저 넣는다.
    if start is not None:  # 외부에서 시작 경로를 넘긴 경우 그 경로도 함께 검사한다.
        start = start.resolve()  # 상대 경로를 절대 경로로 변환한다.
        candidates.extend([start, *start.parents])  # 시작 경로와 모든 상위 폴더를 후보로 추가한다.
    else:  # 시작 경로가 없으면 현재 작업 폴더를 기준으로 탐색한다.
        cwd = Path.cwd().resolve()  # 현재 실행 위치를 절대 경로로 얻는다.
        candidates.extend([cwd, *cwd.parents])  # 현재 폴더와 상위 폴더들을 후보로 추가한다.

    seen: set[Path] = set()  # 같은 경로를 중복 검사하지 않기 위한 집합이다.
    for candidate in candidates:  # 후보 경로를 하나씩 확인한다.
        if candidate in seen:  # 이미 검사한 경로이면 건너뛴다.
            continue  # 중복 검사를 피한다.
        seen.add(candidate)  # 현재 후보를 검사 완료 목록에 추가한다.
        if (candidate / "src").is_dir() and (candidate / "data").is_dir():  # src와 data가 모두 있으면 프로젝트 루트로 본다.
            return candidate  # 찾은 프로젝트 루트를 반환한다.
    return module_root  # 탐색에 실패하면 모듈 기준 루트를 기본값으로 사용한다.


PROJECT_ROOT = find_project_root()  # 프로젝트 전체의 기준 경로를 계산한다.
RAW_DATA = PROJECT_ROOT / "data" / "raw"  # 원본 CSV 데이터 폴더 경로이다.
PROCESSED_DATA = PROJECT_ROOT / "data" / "processed"  # 전처리/분석 결과 데이터 폴더 경로이다.
REPORTS = PROJECT_ROOT / "reports"  # 보고서와 분석 요약 폴더 경로이다.
FIGURES = REPORTS / "figures"  # 그래프 이미지 저장 폴더 경로이다.


def resolve_project_path(path: str | Path, must_exist: bool = False) -> Path:
    """Resolve relative project paths consistently from notebooks and scripts."""
    path = Path(path)  # 문자열로 들어온 경로를 Path 객체로 변환한다.
    if path.is_absolute():  # 이미 절대 경로이면 추가 변환이 필요 없다.
        return path  # 절대 경로를 그대로 반환한다.

    cwd_candidate = (Path.cwd() / path).resolve()  # 현재 실행 위치 기준 후보 경로이다.
    project_candidate = (PROJECT_ROOT / path).resolve()  # 프로젝트 루트 기준 후보 경로이다.

    if must_exist:  # 실제 존재하는 입력 파일을 찾는 경우이다.
        if cwd_candidate.exists():  # 현재 작업 폴더 기준 파일이 존재하면 우선 사용한다.
            return cwd_candidate  # 현재 작업 폴더 기준 경로를 반환한다.
        return project_candidate  # 아니면 프로젝트 루트 기준 경로를 반환한다.

    if path.parts and path.parts[0] in PROJECT_DIR_NAMES:  # data/src/reports처럼 프로젝트 폴더로 시작하는 경로인지 확인한다.
        return project_candidate  # 프로젝트 내부 경로로 해석한다.
    return cwd_candidate  # 그 외에는 현재 작업 폴더 기준 경로로 해석한다.


# 데이터 검증 단계에서 반드시 있어야 하는 핵심 열 목록이다.
REQUIRED_COLUMNS = [
    "record_id",  # 각 반응 행을 구분하는 고유 ID이다.
    "reaction_type",  # SPAAC, CuAAC 등 반응 종류를 나타낸다.
    "azide",  # 아자이드 반응물 이름이다.
    "alkyne",  # 알카인 반응물 또는 구조군 이름이다.
    "catalyst",  # 촉매 이름이며 촉매가 없으면 none으로 기록한다.
    "catalyst_present",  # 촉매 존재 여부를 0 또는 1로 기록한다.
    "source",  # 데이터가 나온 논문 또는 출처이다.
    "source_type",  # 원논문, 리뷰, 템플릿 등 출처 종류이다.
    "verification_status",  # 원문 확인 여부를 나타낸다.
]

# 숫자로 변환되어야 하는 열 목록이다.
NUMERIC_COLUMNS = [
    "catalyst_present",  # 촉매 존재 여부는 숫자형 0/1로 다룬다.
    "temperature_K",  # 온도는 K 단위 숫자로 다룬다.
    "pH",  # pH는 0에서 14 사이 숫자로 다룬다.
    "k_value",  # 반응속도상수 값이다.
    "Ea_kJ_mol",  # 활성화에너지 값이다.
    "yield_percent",  # 수율 또는 전환율 값이다.
    "ring_strain_level",  # 고리 strain 수준을 수동 descriptor로 표현한다.
    "fluorine_count",  # fluorine 치환 개수이다.
    "fused_aromatic_count",  # fused aromatic ring 개수이다.
    "heteroatom_in_ring",  # 고리 내 heteroatom 존재 여부이다.
]

# AI feature table에 직접 넣을 숫자형 변수 목록이다.
FEATURE_NUMERIC_COLUMNS = [
    "catalyst_present",  # 촉매 여부를 모델 feature로 사용한다.
    "temperature_K",  # 온도를 모델 feature로 사용한다.
    "pH",  # pH를 모델 feature로 사용한다.
    "Ea_kJ_mol",  # 활성화에너지 값을 feature 후보로 둔다.
    "yield_percent",  # 수율 정보를 feature 후보로 둔다.
    "ring_strain_level",  # 구조적 strain descriptor를 feature로 사용한다.
    "fluorine_count",  # 전자효과와 관련된 fluorine 개수를 feature로 사용한다.
    "fused_aromatic_count",  # fused aromatic 구조 정보를 feature로 사용한다.
    "heteroatom_in_ring",  # heteroatom 포함 여부를 feature로 사용한다.
]

# one-hot encoding으로 숫자화할 범주형 변수 목록이다.
CATEGORICAL_FEATURE_COLUMNS = [
    "reaction_type",  # 반응 종류를 범주형 feature로 사용한다.
    "catalyst",  # 촉매 종류를 범주형 feature로 사용한다.
    "solvent_class",  # 용매 종류를 범주형 feature로 사용한다.
    "alkyne_family",  # 알카인 구조군을 범주형 feature로 사용한다.
]

# 검증 상태 열에 허용되는 값 목록이다.
VALID_VERIFICATION_STATUSES = {
    "primary_checked",  # 원문을 확인한 데이터이다.
    "needs_primary_check",  # 원문 재확인이 필요한 데이터이다.
    "template",  # 입력 예시나 템플릿 행이다.
}
