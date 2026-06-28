import argparse  # 명령행 인자를 처리하기 위한 표준 라이브러리이다.
import json  # 클리닝 요약 보고서를 JSON으로 저장하기 위한 표준 라이브러리이다.
import re  # 논문에서 추출된 숫자 문자열을 정규표현식으로 파싱하기 위한 라이브러리이다.
from pathlib import Path  # 파일 경로를 안전하게 다루기 위한 표준 라이브러리이다.

import pandas as pd  # CSV 데이터 전처리와 표 생성을 위한 핵심 라이브러리이다.

try:  # 패키지 형태로 import될 때 사용하는 경로이다.
    from .click_reaction_config import PROCESSED_DATA, resolve_project_path  # 출력 경로와 경로 해석 함수를 불러온다.
    from .validate_dataset import validate_dataframe  # 전처리 후 데이터 검증 함수를 불러온다.
except ImportError:  # 파일을 직접 실행할 때 사용하는 경로이다.
    from click_reaction_config import PROCESSED_DATA, resolve_project_path  # 직접 실행용 경로 설정을 불러온다.
    from validate_dataset import validate_dataframe  # 직접 실행용 검증 함수를 불러온다.


# LLM 또는 사람이 입력한 CSV에서 실제 결측값으로 취급할 표현들이다.
PLACEHOLDER_VALUES = {
    "",  # 빈 문자열은 결측값으로 본다.
    "nan",  # 문자열 nan도 결측값으로 본다.
    "none",  # none 표기도 결측값으로 본다.
    "na",  # na 표기도 결측값으로 본다.
    "n/a",  # n/a 표기도 결측값으로 본다.
    "not reported",  # 논문에 보고되지 않았다는 표현은 결측값으로 본다.
    "확인 필요",  # 아직 확인되지 않은 값은 분석값으로 쓰지 않는다.
    "unknown value",  # unknown value도 결측값으로 본다.
}

# 알카인 구조군 이름을 통일하기 위한 사전이다.
ALKYNE_FAMILY_NORMALIZATION = {
    "bcn": "bicyclononyne",  # BCN 약어를 표준 구조군 이름으로 바꾼다.
    "bicyclononyne": "bicyclononyne",  # 이미 표준 이름이면 그대로 둔다.
    "cyclooctyne": "cyclooctyne",  # 일반 cyclooctyne 계열이다.
    "cyclooctyne uaa": "cyclooctyne",  # UAA로 적힌 cyclooctyne도 같은 계열로 묶는다.
    "strained cyclooctyne": "cyclooctyne",  # strained cyclooctyne 표기를 일반 계열로 통일한다.
    "difluorinated cyclooctyne": "fluorinated_cyclooctyne",  # DIFO 계열을 fluorinated cyclooctyne으로 통일한다.
    "fluorinated cyclooctyne": "fluorinated_cyclooctyne",  # fluorinated 표기를 표준 이름으로 바꾼다.
    "azacyclooctyne": "azacyclooctyne",  # aza-cyclooctyne 계열이다.
    "biarylazacyclooctynone": "biarylazacyclooctynone",  # BARAC 계열 구조군이다.
    "strained biarylazacyclooctynone": "biarylazacyclooctynone",  # strained 표현을 제거해 같은 계열로 묶는다.
    "dibo": "dibenzocyclooctyne",  # DIBO 약어를 표준 구조군으로 바꾼다.
    "dibo derivative": "dibenzocyclooctyne",  # DIBO 유도체를 같은 계열로 묶는다.
    "dibo carbamate": "dibenzocyclooctyne",  # DIBO carbamate도 같은 계열로 묶는다.
    "dibo ketone": "dibenzocyclooctyne",  # DIBO ketone도 같은 계열로 묶는다.
    "dibo oxime": "dibenzocyclooctyne",  # DIBO oxime도 같은 계열로 묶는다.
    "dibenzocyclooctyne": "dibenzocyclooctyne",  # 이미 표준 이름이면 그대로 둔다.
    "terminal alkyne": "terminal_alkyne",  # terminal alkyne 표기를 모델용 이름으로 바꾼다.
}


def _is_placeholder(value: object) -> bool:
    if pd.isna(value):  # pandas가 인식하는 NaN이면 결측값이다.
        return True  # 결측값으로 판단한다.
    return str(value).strip().lower() in PLACEHOLDER_VALUES  # 문자열을 정리해 결측 표현 목록과 비교한다.


def _blank_placeholders(value: object) -> object:
    return pd.NA if _is_placeholder(value) else value  # 결측 표현은 pd.NA로 통일하고, 나머지는 그대로 둔다.


def parse_numeric_like(value: object) -> object:
    # 이 함수는 논문/LLM 추출값의 다양한 숫자 표현을 실제 float 값으로 바꾼다.
    # 예: "4.3 × 10-3"은 0.0043, "(9.0 ± 0.3) × 10-2"는 0.09로 변환된다.
    if _is_placeholder(value):  # 결측값이면 숫자로 변환하지 않는다.
        return pd.NA  # 분석에서 결측값으로 처리한다.
    text = str(value).strip()  # 입력값을 문자열로 바꾸고 양끝 공백을 제거한다.
    text = (  # 논문 PDF에서 자주 생기는 특수문자를 일반 문자로 통일한다.
        text.replace("−", "-")  # 수학용 minus를 ASCII 하이픈으로 바꾼다.
        .replace("–", "-")  # en dash를 ASCII 하이픈으로 바꾼다.
        .replace("—", "-")  # em dash를 ASCII 하이픈으로 바꾼다.
        .replace("×", "x")  # 곱셈 기호를 x로 바꾼다.
        .replace("·", "")  # 가운데점을 제거한다.
    )
    text = re.sub(r"\([^)]*±[^)]*\)", lambda match: match.group(0).split("±")[0].lstrip("(").strip(), text)  # 괄호 안 오차 표기에서 중심값만 남긴다.
    text = re.sub(r"±\s*[-+]?\d*\.?\d+", "", text)  # 괄호 밖 오차 표기를 제거한다.
    text = text.replace(">", "").replace("<", "").replace("~", "")  # 부등호와 근사 기호를 제거해 대표값만 사용한다.

    sci_match = re.search(  # 과학적 표기법 형태를 찾는다.
        r"([-+]?\d*\.?\d+)\s*x\s*10\s*\^?\s*([-+]?\d+)",  # 예: 4.3 x 10-3 또는 4.3 x 10^-3 형식이다.
        text,  # 검색 대상 문자열이다.
        flags=re.IGNORECASE,  # x 대소문자 차이를 무시한다.
    )
    if sci_match:  # 과학적 표기법이 발견된 경우이다.
        return float(sci_match.group(1)) * (10 ** int(sci_match.group(2)))  # 계수와 지수를 계산해 실제 숫자로 반환한다.

    simple_match = re.search(r"[-+]?\d*\.?\d+", text)  # 일반 소수 또는 정수 형태의 숫자를 찾는다.
    if simple_match:  # 일반 숫자가 발견된 경우이다.
        return float(simple_match.group(0))  # 찾은 숫자를 float로 반환한다.
    return pd.NA  # 어떤 숫자도 찾지 못하면 결측값으로 처리한다.


def normalize_k_unit(value: object) -> object:
    # 이 함수는 속도상수 단위 표기를 M^-1 s^-1 형태로 통일한다.
    if _is_placeholder(value):  # 단위가 비어 있거나 보고되지 않은 경우이다.
        return pd.NA  # 결측값으로 둔다.
    text = str(value).strip()  # 단위 값을 문자열로 바꾸고 공백을 제거한다.
    normalized = (  # 다양한 유니코드 단위 표기를 ASCII 기반 문자열로 정리한다.
        text.replace("−", "-")  # 수학용 minus를 하이픈으로 바꾼다.
        .replace("–", "-")  # en dash를 하이픈으로 바꾼다.
        .replace("—", "-")  # em dash를 하이픈으로 바꾼다.
        .replace("⁻", "-")  # 위첨자 minus를 하이픈으로 바꾼다.
        .replace("¹", "1")  # 위첨자 1을 일반 숫자로 바꾼다.
        .replace(" ", "")  # 단위 비교를 쉽게 하기 위해 공백을 제거한다.
    )
    lowered = normalized.lower()  # 대소문자 차이를 없앤다.
    if lowered in {"m-1s-1", "m^-1s^-1", "m−1s−1"}:  # 대표적인 2차 속도상수 단위 표기인지 확인한다.
        return "M^-1 s^-1"  # 표준 단위 표기로 반환한다.
    if "m" in lowered and "s" in lowered and "-1" in lowered:  # 유사한 2차 속도상수 단위인지 넓게 확인한다.
        return "M^-1 s^-1"  # 표준 단위 표기로 반환한다.
    return text  # 알 수 없는 단위는 원문 표기를 유지한다.


def normalize_alkyne_family(value: object) -> object:
    # 이 함수는 구조군 이름을 표준화해 one-hot encoding이 불필요하게 쪼개지는 것을 막는다.
    if _is_placeholder(value):  # 구조군 정보가 없으면 결측값으로 둔다.
        return pd.NA  # 결측값을 반환한다.
    key = re.sub(r"\s+", " ", str(value).strip().lower().replace("_", " "))  # 공백/대소문자/밑줄 차이를 정리한다.
    return ALKYNE_FAMILY_NORMALIZATION.get(key, str(value).strip())  # 사전에 있으면 표준명으로, 없으면 원래 값을 유지한다.


def normalize_dataset(df: pd.DataFrame) -> pd.DataFrame:
    # 이 함수가 전체 전처리의 핵심이다.
    # 원본 문헌 CSV를 복사한 뒤 결측값, 단위, 구조군, 숫자 표현을 분석 가능한 형태로 정리한다.
    cleaned = df.copy()  # 원본 DataFrame을 직접 수정하지 않기 위해 복사본을 만든다.

    for column in cleaned.columns:  # 모든 열을 순회한다.
        cleaned[column] = cleaned[column].map(_blank_placeholders)  # 결측 표현을 pd.NA로 통일한다.

    cleaned = cleaned.dropna(how="all").reset_index(drop=True)  # 완전히 빈 행을 제거하고 인덱스를 다시 매긴다.
    if "record_id" in cleaned.columns:  # record_id 열이 있는 경우이다.
        cleaned = cleaned[cleaned["record_id"].notna()].reset_index(drop=True)  # record_id가 없는 깨진 행은 분석에서 제외한다.

    for column in ["azide", "alkyne"]:  # 필수 반응물 이름 열을 순회한다.
        if column in cleaned.columns:  # 해당 열이 실제 데이터에 존재하는지 확인한다.
            cleaned[column] = cleaned[column].fillna("unknown_needs_check")  # 비어 있으면 확인 필요 값을 넣어 필수 열 오류를 막는다.

    if "catalyst" in cleaned.columns and "catalyst_present" in cleaned.columns:  # 촉매명과 촉매 여부 열이 모두 있는지 확인한다.
        catalyst_present = pd.to_numeric(cleaned["catalyst_present"], errors="coerce").fillna(0)  # 촉매 여부를 숫자 0/1로 변환한다.
        missing_catalyst = cleaned["catalyst"].isna() & (catalyst_present == 0)  # 촉매가 없다고 표시된 행 중 촉매명이 빈 행을 찾는다.
        cleaned.loc[missing_catalyst, "catalyst"] = "none"  # 촉매가 없는 행의 catalyst 값을 none으로 채운다.

    if "k_unit" in cleaned.columns:  # 속도상수 단위 열이 있으면 표준화한다.
        cleaned["k_unit_original"] = df["k_unit"]  # 원래 단위 표기를 별도 열에 보존한다.
        cleaned["k_unit"] = cleaned["k_unit"].map(normalize_k_unit)  # 분석용 단위 표기를 표준화한다.

    if "alkyne_family" in cleaned.columns:  # 알카인 구조군 열이 있으면 표준화한다.
        cleaned["alkyne_family_original"] = df["alkyne_family"]  # 원래 구조군 표기를 별도 열에 보존한다.
        cleaned["alkyne_family"] = cleaned["alkyne_family"].map(normalize_alkyne_family)  # 분석용 구조군 이름을 통일한다.

    for column in ["k_value", "temperature_K", "pH", "Ea_kJ_mol", "yield_percent", "ring_strain_level", "fluorine_count", "fused_aromatic_count"]:  # 숫자 변환 대상 열 목록이다.
        if column in cleaned.columns:  # 해당 숫자 열이 실제 데이터에 있으면 처리한다.
            cleaned[f"{column}_original"] = df[column]  # 원본 값을 보존해 추후 검증할 수 있게 한다.
            cleaned[column] = cleaned[column].map(parse_numeric_like)  # 사람이 읽는 숫자 표현을 실제 숫자로 변환한다.

    if "heteroatom_in_ring" in cleaned.columns:  # 고리 내 heteroatom 열이 있으면 처리한다.
        cleaned["heteroatom_in_ring_original"] = df["heteroatom_in_ring"]  # 원본 heteroatom 표기를 보존한다.
        cleaned["heteroatom_in_ring"] = cleaned["heteroatom_in_ring"].map(  # N/O/S/YES 등은 1로, 숫자는 숫자로 변환한다.
            lambda value: 1 if str(value).strip().upper() in {"N", "O", "S", "YES", "TRUE", "1"} else parse_numeric_like(value)  # heteroatom 존재 여부를 모델용 숫자로 만든다.
        )

    if "verification_status" in cleaned.columns:  # 검증 상태 열이 있으면 확인 필요 표시를 갱신한다.
        review_columns = [column for column in ["azide", "alkyne", "temperature_K_original", "pH_original"] if column in cleaned.columns]  # 확인 필요 문구를 검사할 열 목록이다.
        needs_review = pd.Series(False, index=cleaned.index)  # 각 행의 재확인 필요 여부를 False로 초기화한다.
        for column in review_columns:  # 검사 대상 열을 하나씩 확인한다.
            needs_review = needs_review | df[column.replace("_original", "")].astype(str).str.contains("확인 필요|near neutral", na=False)  # 확인 필요 문구가 있으면 True로 표시한다.
        cleaned.loc[needs_review, "verification_status"] = "needs_primary_check"  # 확인 필요 행의 상태를 needs_primary_check로 바꾼다.

    return cleaned  # 전처리된 DataFrame을 반환한다.


def summarize_dataset(df: pd.DataFrame, errors: list[str], warnings: list[str]) -> dict:
    numeric_k = pd.to_numeric(df.get("k_value"), errors="coerce") if "k_value" in df else pd.Series(dtype=float)  # 숫자형 k 행 수를 세기 위한 Series이다.
    numeric_yield = pd.to_numeric(df.get("yield_percent"), errors="coerce") if "yield_percent" in df else pd.Series(dtype=float)  # 숫자형 수율 행 수를 세기 위한 Series이다.
    numeric_ea = pd.to_numeric(df.get("Ea_kJ_mol"), errors="coerce") if "Ea_kJ_mol" in df else pd.Series(dtype=float)  # 숫자형 활성화에너지 행 수를 세기 위한 Series이다.
    return {  # 전처리 결과를 요약한 dict를 반환한다.
        "rows": int(len(df)),  # 전체 행 수이다.
        "valid_after_cleaning": not errors,  # 검증 오류가 없으면 True이다.
        "errors": errors,  # 검증 오류 목록이다.
        "warnings": warnings,  # 검증 경고 목록이다.
        "rows_with_numeric_k": int(numeric_k.notna().sum()),  # 속도상수 k가 있는 행 수이다.
        "rows_with_numeric_yield": int(numeric_yield.notna().sum()),  # 수율/전환율이 있는 행 수이다.
        "rows_with_numeric_Ea": int(numeric_ea.notna().sum()),  # 활성화에너지가 있는 행 수이다.
        "reaction_type_counts": df.get("reaction_type", pd.Series(dtype=str)).fillna("<NA>").astype(str).value_counts().to_dict(),  # 반응 종류별 행 수이다.
        "verification_status_counts": df.get("verification_status", pd.Series(dtype=str)).fillna("<NA>").astype(str).value_counts().to_dict(),  # 검증 상태별 행 수이다.
        "recommendation": (  # 현재 데이터 품질에 대한 자동 요약 문장이다.
            "Good for exploratory workflow and yield/condition summaries; add more primary-checked k_value rows "  # 탐색적 분석에는 충분하다는 메시지이다.
            "before making strong claims about reaction-rate prediction."  # 강한 예측 주장은 주의해야 한다는 메시지이다.
        ),
    }


def clean_file(input_path: Path, output_path: Path, report_path: Path) -> dict:
    # 이 함수는 파일 단위 전처리를 수행한다.
    # raw CSV를 읽고, cleaned CSV와 전처리 보고서 JSON을 생성한다.
    input_path = resolve_project_path(input_path, must_exist=True)  # 입력 파일 경로를 프로젝트 기준으로 해석한다.
    output_path = resolve_project_path(output_path)  # cleaned CSV 출력 경로를 해석한다.
    report_path = resolve_project_path(report_path)  # JSON 보고서 출력 경로를 해석한다.

    raw = pd.read_csv(input_path)  # 원본 문헌 CSV를 읽는다.
    cleaned = normalize_dataset(raw)  # 원본 데이터를 분석 가능한 형태로 전처리한다.
    errors, warnings = validate_dataframe(cleaned)  # 전처리된 데이터가 스키마를 만족하는지 검증한다.

    output_path.parent.mkdir(parents=True, exist_ok=True)  # cleaned CSV 저장 폴더를 만든다.
    report_path.parent.mkdir(parents=True, exist_ok=True)  # JSON 보고서 저장 폴더를 만든다.
    cleaned.to_csv(output_path, index=False)  # 전처리된 데이터를 CSV로 저장한다.

    report = summarize_dataset(cleaned, errors, warnings)  # 전처리 결과 요약 정보를 만든다.
    report["input"] = str(input_path)  # 보고서에 입력 파일 경로를 기록한다.
    report["output"] = str(output_path)  # 보고서에 출력 파일 경로를 기록한다.
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")  # 요약 보고서를 JSON 파일로 저장한다.
    return report  # 실행 결과를 호출자에게 반환한다.


def main() -> int:
    parser = argparse.ArgumentParser(description="Clean LLM-extracted literature CSV for analysis.")  # 전처리 스크립트의 CLI 설명이다.
    parser.add_argument("--input", required=True, type=Path)  # 원본 CSV 입력 경로 인자를 정의한다.
    parser.add_argument(  # cleaned CSV 출력 경로 인자를 정의한다.
        "--output",  # 출력 파일 옵션 이름이다.
        default=PROCESSED_DATA / "click_reaction_literature_cleaned.csv",  # 기본 출력 파일 경로이다.
        type=Path,  # Path 객체로 받는다.
    )
    parser.add_argument(  # 전처리 요약 보고서 출력 경로 인자를 정의한다.
        "--report",  # 보고서 파일 옵션 이름이다.
        default=PROCESSED_DATA / "literature_cleaning_report.json",  # 기본 보고서 파일 경로이다.
        type=Path,  # Path 객체로 받는다.
    )
    args = parser.parse_args()  # 명령행 인자를 해석한다.

    report = clean_file(args.input, args.output, args.report)  # 실제 전처리를 실행한다.
    print(json.dumps(report, indent=2, ensure_ascii=False))  # 전처리 결과를 콘솔에 출력한다.
    return 0 if report["valid_after_cleaning"] else 1  # 검증 성공 여부에 따라 종료 코드를 반환한다.


if __name__ == "__main__":  # 파일을 직접 실행했을 때만 main을 호출한다.
    raise SystemExit(main())  # main의 반환값을 프로그램 종료 코드로 사용한다.
