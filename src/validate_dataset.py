import argparse  # 명령행 인자를 처리하기 위한 표준 라이브러리이다.
import json  # 검증 결과를 JSON 파일로 저장하기 위한 표준 라이브러리이다.
from pathlib import Path  # 파일 경로를 다루기 위한 표준 라이브러리이다.

import pandas as pd  # CSV 데이터 검증을 위한 표 처리 라이브러리이다.

try:  # 패키지 형태로 실행될 때 사용하는 import 경로이다.
    from .click_reaction_config import (  # 프로젝트 설정값을 불러온다.
        NUMERIC_COLUMNS,  # 숫자형이어야 하는 열 목록이다.
        PROCESSED_DATA,  # 검증 요약 파일을 저장할 기본 폴더이다.
        REQUIRED_COLUMNS,  # 반드시 존재해야 하는 열 목록이다.
        VALID_VERIFICATION_STATUSES,  # 허용되는 검증 상태 값 목록이다.
        resolve_project_path,  # 프로젝트 기준 경로 해석 함수이다.
    )
except ImportError:  # 파일을 직접 실행할 때 사용하는 import 경로이다.
    from click_reaction_config import (  # 직접 실행용 프로젝트 설정값을 불러온다.
        NUMERIC_COLUMNS,  # 숫자형이어야 하는 열 목록이다.
        PROCESSED_DATA,  # 검증 요약 파일을 저장할 기본 폴더이다.
        REQUIRED_COLUMNS,  # 반드시 존재해야 하는 열 목록이다.
        VALID_VERIFICATION_STATUSES,  # 허용되는 검증 상태 값 목록이다.
        resolve_project_path,  # 프로젝트 기준 경로 해석 함수이다.
    )


def _non_empty(series: pd.Series) -> pd.Series:
    return series.notna() & (series.astype(str).str.strip() != "")  # NaN이 아니고 공백 문자열도 아닌 값을 True로 표시한다.


def validate_dataframe(df: pd.DataFrame) -> tuple[list[str], list[str]]:
    # 이 함수는 cleaned dataset이 분석 가능한 형식인지 검사한다.
    # 오류는 실행을 막는 문제이고, 경고는 분석은 가능하지만 해석에 주의해야 하는 문제이다.
    errors: list[str] = []  # 치명적인 검증 오류를 담는 리스트이다.
    warnings: list[str] = []  # 분석은 가능하지만 주의가 필요한 경고를 담는 리스트이다.

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]  # 필수 열 중 누락된 열을 찾는다.
    if missing_columns:  # 필수 열이 하나라도 없으면 분석을 진행할 수 없다.
        errors.append(f"Missing required columns: {', '.join(missing_columns)}")  # 누락된 열 이름을 오류에 기록한다.
        return errors, warnings  # 필수 열이 없으면 이후 검사는 의미가 없으므로 바로 반환한다.

    duplicate_ids = df["record_id"][df["record_id"].duplicated()].tolist()  # 중복 record_id 값을 찾는다.
    if duplicate_ids:  # 중복 ID가 있으면 행 구분이 불가능해진다.
        errors.append(f"Duplicate record_id values: {', '.join(map(str, duplicate_ids))}")  # 중복 ID를 오류에 기록한다.

    for column in REQUIRED_COLUMNS:  # 필수 열을 하나씩 검사한다.
        empty_mask = ~_non_empty(df[column])  # 해당 열에서 빈 값을 가진 행을 찾는다.
        if empty_mask.any():  # 빈 필수값이 하나라도 있으면 오류이다.
            row_numbers = (df.index[empty_mask] + 2).tolist()  # CSV 행 번호는 header 때문에 index보다 2 크다.
            errors.append(f"Empty required value in {column} at CSV rows {row_numbers}")  # 빈 값 위치를 오류에 기록한다.

    for column in NUMERIC_COLUMNS:  # 숫자형이어야 하는 열을 하나씩 검사한다.
        if column in df.columns:  # 데이터에 해당 열이 존재하는 경우에만 검사한다.
            numeric = pd.to_numeric(df[column], errors="coerce")  # 숫자로 변환하고 실패한 값은 NaN으로 만든다.
            bad_mask = _non_empty(df[column]) & numeric.isna()  # 원래 값은 있는데 숫자로 바뀌지 않은 행을 찾는다.
            if bad_mask.any():  # 숫자 변환 실패가 있으면 오류이다.
                row_numbers = (df.index[bad_mask] + 2).tolist()  # 문제가 있는 CSV 행 번호를 계산한다.
                errors.append(f"Non-numeric value in {column} at CSV rows {row_numbers}")  # 숫자 오류 위치를 기록한다.

    if "k_value" in df.columns:  # 속도상수 열이 있으면 값 범위를 검사한다.
        k_values = pd.to_numeric(df["k_value"], errors="coerce")  # k_value를 숫자로 변환한다.
        bad_k = k_values.notna() & (k_values <= 0)  # k는 양수여야 하므로 0 이하 값을 찾는다.
        if bad_k.any():  # 잘못된 k 값이 있으면 오류이다.
            row_numbers = (df.index[bad_k] + 2).tolist()  # 문제가 있는 CSV 행 번호를 계산한다.
            errors.append(f"k_value must be positive at CSV rows {row_numbers}")  # k 값 오류를 기록한다.

    if "temperature_K" in df.columns:  # 온도 열이 있으면 값 범위를 검사한다.
        temperature = pd.to_numeric(df["temperature_K"], errors="coerce")  # 온도를 숫자로 변환한다.
        bad_temperature = temperature.notna() & (temperature <= 0)  # 절대온도는 0보다 커야 한다.
        if bad_temperature.any():  # 잘못된 온도 값이 있으면 오류이다.
            row_numbers = (df.index[bad_temperature] + 2).tolist()  # 문제가 있는 CSV 행 번호를 계산한다.
            errors.append(f"temperature_K must be positive at CSV rows {row_numbers}")  # 온도 오류를 기록한다.

    if "pH" in df.columns:  # pH 열이 있으면 범위를 검사한다.
        ph = pd.to_numeric(df["pH"], errors="coerce")  # pH를 숫자로 변환한다.
        bad_ph = ph.notna() & ((ph < 0) | (ph > 14))  # pH의 일반 범위인 0-14 밖 값을 찾는다.
        if bad_ph.any():  # 잘못된 pH가 있으면 오류이다.
            row_numbers = (df.index[bad_ph] + 2).tolist()  # 문제가 있는 CSV 행 번호를 계산한다.
            errors.append(f"pH must be between 0 and 14 at CSV rows {row_numbers}")  # pH 오류를 기록한다.

    if "yield_percent" in df.columns:  # 수율 열이 있으면 범위를 검사한다.
        yield_percent = pd.to_numeric(df["yield_percent"], errors="coerce")  # 수율을 숫자로 변환한다.
        bad_yield = yield_percent.notna() & ((yield_percent < 0) | (yield_percent > 100))  # 수율은 0-100 범위여야 한다.
        if bad_yield.any():  # 잘못된 수율이 있으면 오류이다.
            row_numbers = (df.index[bad_yield] + 2).tolist()  # 문제가 있는 CSV 행 번호를 계산한다.
            errors.append(f"yield_percent must be between 0 and 100 at CSV rows {row_numbers}")  # 수율 오류를 기록한다.

    statuses = set(df["verification_status"].dropna().astype(str))  # 데이터에 실제로 등장한 검증 상태 값을 모은다.
    invalid_statuses = sorted(statuses - VALID_VERIFICATION_STATUSES)  # 허용되지 않은 검증 상태 값을 찾는다.
    if invalid_statuses:  # 허용되지 않은 상태 값이 있으면 오류이다.
        errors.append(f"Invalid verification_status values: {', '.join(invalid_statuses)}")  # 잘못된 상태 값을 오류에 기록한다.

    if "k_unit" in df.columns and "k_value" in df.columns:  # k 값과 단위 열이 모두 있으면 단위 누락을 검사한다.
        has_k = pd.to_numeric(df["k_value"], errors="coerce").notna()  # 숫자형 k 값이 있는 행을 찾는다.
        missing_units = has_k & ~_non_empty(df["k_unit"])  # k는 있는데 단위가 비어 있는 행을 찾는다.
        if missing_units.any():  # 속도상수 단위가 빠진 행이 있으면 오류이다.
            row_numbers = (df.index[missing_units] + 2).tolist()  # 문제가 있는 CSV 행 번호를 계산한다.
            errors.append(f"Rows with k_value must include k_unit at CSV rows {row_numbers}")  # 단위 누락 오류를 기록한다.

    not_primary = df["verification_status"].astype(str) != "primary_checked"  # 원문 확인이 끝나지 않은 행을 찾는다.
    if not_primary.any():  # 확인 필요 행이 있으면 경고를 남긴다.
        warnings.append(  # 분석은 가능하지만 보고서 해석에 주의가 필요하다.
            f"{int(not_primary.sum())} row(s) are not primary_checked. Treat analysis as exploratory."  # 확인 필요 행 수를 경고한다.
        )

    return errors, warnings  # 검증 오류와 경고를 반환한다.


def validate_file(input_path: Path) -> dict:
    input_path = resolve_project_path(input_path, must_exist=True)  # 입력 CSV 경로를 프로젝트 기준으로 해석한다.
    df = pd.read_csv(input_path)  # 검증할 CSV 파일을 읽는다.
    errors, warnings = validate_dataframe(df)  # DataFrame 단위 검증을 수행한다.
    return {  # 검증 결과를 dict로 정리한다.
        "input": str(input_path),  # 검증한 입력 파일 경로이다.
        "rows": int(len(df)),  # 데이터 행 수이다.
        "columns": list(df.columns),  # 데이터 열 목록이다.
        "errors": errors,  # 검증 오류 목록이다.
        "warnings": warnings,  # 검증 경고 목록이다.
        "valid": not errors,  # 오류가 없으면 True이다.
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate click reaction dataset CSV.")  # 검증 스크립트의 CLI 설명이다.
    parser.add_argument("--input", required=True, type=Path)  # 검증할 입력 CSV 경로 인자이다.
    parser.add_argument(  # 검증 요약 JSON 출력 경로 인자이다.
        "--summary",  # 요약 파일 옵션 이름이다.
        default=PROCESSED_DATA / "validation_summary.json",  # 기본 요약 파일 경로이다.
        type=Path,  # Path 객체로 받는다.
    )
    args = parser.parse_args()  # 명령행 인자를 해석한다.

    summary_path = resolve_project_path(args.summary)  # 요약 파일 경로를 프로젝트 기준으로 해석한다.
    result = validate_file(args.input)  # 입력 CSV 검증을 실행한다.
    summary_path.parent.mkdir(parents=True, exist_ok=True)  # 요약 파일 저장 폴더를 만든다.
    summary_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")  # 검증 결과를 JSON으로 저장한다.

    print(json.dumps(result, indent=2, ensure_ascii=False))  # 검증 결과를 콘솔에 출력한다.
    return 0 if result["valid"] else 1  # 검증 성공 여부에 따라 종료 코드를 반환한다.


if __name__ == "__main__":  # 파일을 직접 실행했을 때만 main을 호출한다.
    raise SystemExit(main())  # main의 반환값을 프로그램 종료 코드로 사용한다.
