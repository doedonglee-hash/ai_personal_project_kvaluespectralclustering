import argparse  # 명령행 인자를 처리하기 위한 표준 라이브러리이다.
from pathlib import Path  # 파일 경로를 다루기 위한 표준 라이브러리이다.

import numpy as np  # 로그 변환과 결측값 계산 등 수치 계산에 사용한다.
import pandas as pd  # CSV 데이터와 feature table을 다루기 위한 라이브러리이다.

try:  # 패키지 형태로 import될 때 사용하는 경로이다.
    from .click_reaction_config import (  # feature 생성에 필요한 설정값을 불러온다.
        CATEGORICAL_FEATURE_COLUMNS,  # one-hot encoding할 범주형 열 목록이다.
        FEATURE_NUMERIC_COLUMNS,  # 모델에 넣을 숫자형 열 목록이다.
        PROCESSED_DATA,  # feature table을 저장할 기본 폴더이다.
        resolve_project_path,  # 프로젝트 기준 경로 해석 함수이다.
    )
    from .validate_dataset import validate_dataframe  # feature 생성 전 데이터 검증 함수를 불러온다.
except ImportError:  # 파일을 직접 실행할 때 사용하는 경로이다.
    from click_reaction_config import (  # 직접 실행용 설정값을 불러온다.
        CATEGORICAL_FEATURE_COLUMNS,  # one-hot encoding할 범주형 열 목록이다.
        FEATURE_NUMERIC_COLUMNS,  # 모델에 넣을 숫자형 열 목록이다.
        PROCESSED_DATA,  # feature table을 저장할 기본 폴더이다.
        resolve_project_path,  # 프로젝트 기준 경로 해석 함수이다.
    )
    from validate_dataset import validate_dataframe  # 직접 실행용 검증 함수를 불러온다.


def build_feature_table(df: pd.DataFrame) -> pd.DataFrame:
    # 이 함수는 cleaned dataset을 AI 모델이 읽을 수 있는 feature table로 변환한다.
    # 핵심 목표는 속도상수 k가 있는 행만 남기고, 구조/조건 정보를 숫자 feature로 바꾸는 것이다.
    errors, warnings = validate_dataframe(df)  # feature 생성 전에 데이터 형식을 검증한다.
    if errors:  # 검증 오류가 있으면 feature table을 만들면 안 된다.
        raise ValueError("; ".join(errors))  # 오류 내용을 예외로 발생시켜 실행을 중단한다.
    for warning in warnings:  # 경고는 실행을 막지 않고 사용자에게 알려준다.
        print(f"WARNING: {warning}")  # 원문 확인 필요 등의 경고를 출력한다.

    model_df = df.copy()  # 원본 DataFrame을 바꾸지 않기 위해 복사한다.
    model_df["k_value"] = pd.to_numeric(model_df["k_value"], errors="coerce")  # k_value를 숫자로 변환한다.
    model_df = model_df[model_df["k_value"].notna()].reset_index(drop=True)  # k_value가 있는 행만 AI 분석 대상으로 남긴다.
    if model_df.empty:  # 속도상수 행이 하나도 없으면 분석할 수 없다.
        raise ValueError("No rows with numeric k_value are available for feature building.")  # 분석 불가 오류를 발생시킨다.

    features = pd.DataFrame({"record_id": model_df["record_id"]})  # feature table의 첫 열로 record_id를 보존한다.
    for column in FEATURE_NUMERIC_COLUMNS:  # 숫자형 feature 열을 하나씩 처리한다.
        if column in model_df.columns:  # 데이터에 해당 열이 존재하면 사용한다.
            numeric = pd.to_numeric(model_df[column], errors="coerce")  # 숫자로 변환하고 실패한 값은 NaN으로 둔다.
        else:  # 데이터에 해당 열이 없으면 전체를 결측으로 만든다.
            numeric = pd.Series(np.nan, index=model_df.index)  # 같은 길이의 NaN Series를 만든다.
        fill_value = numeric.median(skipna=True)  # 결측값 대체에 사용할 중앙값을 계산한다.
        if pd.isna(fill_value):  # 모든 값이 결측이면 중앙값도 NaN이다.
            fill_value = 0  # 모든 값이 비어 있는 열은 0으로 채운다.
        features[column] = numeric.fillna(fill_value)  # 결측값을 중앙값 또는 0으로 채운 숫자 feature를 저장한다.
        features[f"{column}_missing"] = numeric.isna().astype(int)  # 원래 결측이었는지 여부를 별도 feature로 남긴다.

    for column in CATEGORICAL_FEATURE_COLUMNS:  # 범주형 feature 열을 하나씩 처리한다.
        values = model_df[column] if column in model_df.columns else "unknown"  # 열이 없으면 unknown 범주로 처리한다.
        dummies = pd.get_dummies(values.fillna("unknown").astype(str), prefix=column)  # 범주형 값을 one-hot encoding한다.
        features = pd.concat([features, dummies], axis=1)  # 생성된 더미 변수를 feature table에 붙인다.

    features["log10_k"] = np.log10(model_df["k_value"])  # 속도상수 범위가 넓으므로 log10 변환한 목표값을 만든다.
    features["k_value"] = model_df["k_value"]  # 원래 k_value도 해석용으로 보존한다.
    features["alkyne"] = model_df["alkyne"]  # 그래프 라벨과 결과 해석을 위해 알카인 이름을 보존한다.
    features["rate_label"] = model_df.get("rate_label", pd.Series([""] * len(model_df))).fillna("")  # 수동 속도 라벨이 있으면 보존한다.
    features["verification_status"] = model_df["verification_status"]  # 원문 검증 상태를 결과 해석용으로 보존한다.
    return features  # 완성된 feature table을 반환한다.


def main() -> int:
    parser = argparse.ArgumentParser(description="Build model-ready features.")  # feature 생성 스크립트의 CLI 설명이다.
    parser.add_argument("--input", required=True, type=Path)  # cleaned CSV 입력 경로 인자이다.
    parser.add_argument(  # feature table 출력 경로 인자이다.
        "--output",  # 출력 파일 옵션 이름이다.
        default=PROCESSED_DATA / "model_features.csv",  # 기본 feature table 저장 위치이다.
        type=Path,  # Path 객체로 받는다.
    )
    args = parser.parse_args()  # 명령행 인자를 해석한다.

    input_path = resolve_project_path(args.input, must_exist=True)  # 입력 파일 경로를 프로젝트 기준으로 해석한다.
    output_path = resolve_project_path(args.output)  # 출력 파일 경로를 프로젝트 기준으로 해석한다.
    df = pd.read_csv(input_path)  # cleaned CSV를 읽는다.
    features = build_feature_table(df)  # AI 분석용 feature table을 생성한다.
    output_path.parent.mkdir(parents=True, exist_ok=True)  # 출력 폴더가 없으면 만든다.
    features.to_csv(output_path, index=False)  # feature table을 CSV로 저장한다.
    print(f"Wrote {len(features)} rows and {len(features.columns)} columns to {output_path}")  # 생성 결과를 콘솔에 출력한다.
    return 0  # 정상 종료 코드를 반환한다.


if __name__ == "__main__":  # 파일을 직접 실행했을 때만 main을 호출한다.
    raise SystemExit(main())  # main의 반환값을 프로그램 종료 코드로 사용한다.
