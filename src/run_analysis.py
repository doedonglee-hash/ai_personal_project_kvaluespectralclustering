import argparse  # 명령행 인자를 처리하기 위한 표준 라이브러리이다.
import json  # 분석 메트릭을 JSON 파일로 저장하기 위한 표준 라이브러리이다.
from pathlib import Path  # 파일 경로를 다루기 위한 표준 라이브러리이다.

import numpy as np  # 표준화, PCA fallback, ridge 회귀 계산에 사용하는 수치 계산 라이브러리이다.
import pandas as pd  # feature table과 분석 결과 CSV를 다루기 위한 표 처리 라이브러리이다.

try:  # 패키지 형태로 실행될 때 사용하는 import 경로이다.
    from .build_features import build_feature_table  # cleaned dataset을 모델 feature로 바꾸는 함수를 불러온다.
    from .click_reaction_config import FIGURES, PROCESSED_DATA, REPORTS, resolve_project_path  # 출력 경로 설정을 불러온다.
except ImportError:  # 파일을 직접 실행할 때 사용하는 import 경로이다.
    from build_features import build_feature_table  # 직접 실행용 feature 생성 함수를 불러온다.
    from click_reaction_config import FIGURES, PROCESSED_DATA, REPORTS, resolve_project_path  # 직접 실행용 경로 설정을 불러온다.


def _standardize(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = matrix.mean(axis=0)  # 각 feature 열의 평균을 계산한다.
    std = matrix.std(axis=0)  # 각 feature 열의 표준편차를 계산한다.
    std[std == 0] = 1  # 표준편차가 0인 열은 0으로 나누지 않도록 1로 바꾼다.
    return (matrix - mean) / std, mean, std  # 표준화된 행렬과 평균/표준편차를 반환한다.


def _fallback_pca(matrix: np.ndarray, n_components: int = 2) -> np.ndarray:
    # sklearn이 없을 때 사용하는 PCA 대체 구현이다.
    # SVD를 사용해 고차원 feature를 2차원 좌표로 줄인다.
    centered = matrix - matrix.mean(axis=0)  # PCA 전에 각 feature의 평균을 0으로 맞춘다.
    _, _, vt = np.linalg.svd(centered, full_matrices=False)  # SVD로 주성분 방향을 계산한다.
    components = vt[:n_components].T  # 사용할 주성분 개수만큼 방향 벡터를 선택한다.
    return centered @ components  # 원본 데이터를 주성분 방향에 투영해 좌표를 만든다.


def _fallback_rate_clusters(log10_k: pd.Series) -> pd.Series:
    # sklearn clustering이 실패할 때 사용하는 대체 군집 방식이다.
    # log10(k)를 분위수로 나누어 느림/중간/빠름 cluster를 만든다.
    ranks = log10_k.rank(method="first")  # 같은 값이 있어도 순위를 고유하게 부여한다.
    labels = pd.qcut(ranks, q=3, labels=["slow_cluster", "medium_cluster", "fast_cluster"])  # 순위를 3개 분위수로 나눈다.
    return labels.astype(str)  # cluster label을 문자열로 반환한다.


def _ridge_leave_one_out_rmse(x: np.ndarray, y: np.ndarray, alpha: float = 1.0) -> float:
    # ridge regression을 직접 계산해 leave-one-out RMSE를 구한다.
    # 데이터 수가 26행으로 작기 때문에 한 행씩 빼고 예측하는 방식이 적절하다.
    predictions = []  # 각 held-out 행의 예측값을 저장할 리스트이다.
    for held_out in range(len(y)):  # 각 행을 한 번씩 테스트 데이터로 사용한다.
        train_mask = np.ones(len(y), dtype=bool)  # 모든 행을 일단 학습 데이터로 표시한다.
        train_mask[held_out] = False  # 현재 held-out 행만 학습에서 제외한다.
        x_train = x[train_mask]  # 학습용 feature 행렬이다.
        y_train = y[train_mask]  # 학습용 log10(k) 값이다.
        x_test = x[held_out : held_out + 1]  # 테스트용 feature 한 행이다.

        x_train_i = np.column_stack([np.ones(len(x_train)), x_train])  # 절편항 1을 feature 앞에 추가한다.
        x_test_i = np.column_stack([np.ones(len(x_test)), x_test])  # 테스트 데이터에도 절편항을 추가한다.
        penalty = np.eye(x_train_i.shape[1]) * alpha  # ridge 회귀의 L2 패널티 행렬을 만든다.
        penalty[0, 0] = 0  # 절편항에는 패널티를 적용하지 않는다.
        beta = np.linalg.pinv(x_train_i.T @ x_train_i + penalty) @ x_train_i.T @ y_train  # ridge 회귀 계수를 계산한다.
        predictions.append(float((x_test_i @ beta).item()))  # held-out 행의 예측값을 저장한다.
    return float(np.sqrt(np.mean((np.array(predictions) - y) ** 2)))  # 실제값과 예측값의 RMSE를 반환한다.


def _feature_correlations(features: pd.DataFrame, feature_columns: list[str]) -> pd.DataFrame:
    # 각 feature와 log10(k)의 절대 상관계수를 계산한다.
    # 이는 인과관계가 아니라 어떤 feature가 속도상수와 함께 움직이는지 보는 탐색 지표이다.
    rows = []  # feature별 상관 결과를 저장할 리스트이다.
    target = features["log10_k"].to_numpy()  # 목표값인 log10(k)를 numpy 배열로 가져온다.
    for column in feature_columns:  # feature 열을 하나씩 순회한다.
        values = features[column].to_numpy(dtype=float)  # 현재 feature 값을 숫자 배열로 변환한다.
        if np.std(values) == 0:  # 값이 모두 같으면 상관계수를 계산할 수 없다.
            score = 0.0  # 변동이 없는 feature의 상관 점수는 0으로 둔다.
        else:  # 값에 변동이 있으면 상관계수를 계산한다.
            score = float(abs(np.corrcoef(values, target)[0, 1]))  # log10(k)와의 절대 상관계수를 계산한다.
            if np.isnan(score):  # 계산 결과가 NaN이면 안전하게 0으로 처리한다.
                score = 0.0  # NaN 상관값을 0으로 바꾼다.
        rows.append({"feature": column, "abs_corr_with_log10_k": score})  # feature 이름과 점수를 기록한다.
    return pd.DataFrame(rows).sort_values("abs_corr_with_log10_k", ascending=False)  # 상관이 큰 순서로 정렬해 반환한다.


def _markdown_table(df: pd.DataFrame) -> str:
    if df.empty:  # 출력할 행이 없으면 빈 표 문구를 반환한다.
        return "_No rows._"  # Markdown용 빈 결과 문구이다.
    columns = list(df.columns)  # 표에 사용할 열 이름 목록이다.
    lines = [  # Markdown 표의 헤더와 구분선을 만든다.
        "| " + " | ".join(columns) + " |",  # 표 헤더 행이다.
        "| " + " | ".join(["---"] * len(columns)) + " |",  # Markdown 구분선 행이다.
    ]
    for _, row in df.iterrows():  # DataFrame의 각 행을 순회한다.
        values = [str(row[column]) for column in columns]  # 각 셀 값을 문자열로 바꾼다.
        lines.append("| " + " | ".join(values) + " |")  # Markdown 표 행을 추가한다.
    return "\n".join(lines)  # 전체 표 문자열을 반환한다.


def _try_sklearn_analysis(x_scaled: np.ndarray) -> tuple[np.ndarray, np.ndarray | None, str]:
    # PCA와 spectral clustering을 sklearn으로 실행한다.
    # sklearn이 없거나 실패하면 fallback PCA를 사용해 최소한의 분석 결과를 만든다.
    try:  # sklearn 설치 여부와 실행 가능 여부를 확인한다.
        from sklearn.cluster import SpectralClustering  # spectral clustering 모델을 불러온다.
        from sklearn.decomposition import PCA  # PCA 차원 축소 모델을 불러온다.

        coordinates = PCA(n_components=2, random_state=42).fit_transform(x_scaled)  # feature를 2차원 PCA 좌표로 변환한다.
        n_clusters = min(3, len(x_scaled))  # 데이터 수보다 많은 cluster를 만들지 않도록 cluster 수를 정한다.
        if n_clusters >= 2:  # cluster가 2개 이상일 때만 clustering을 수행한다.
            n_neighbors = min(10, len(x_scaled) - 1)  # 작은 데이터에서도 그래프가 끊기지 않도록 이웃 수를 정한다.
            clusters = SpectralClustering(  # spectral clustering 모델을 만든다.
                n_clusters=n_clusters,  # 만들 cluster 수이다.
                affinity="nearest_neighbors",  # 가까운 이웃 그래프를 기반으로 유사도를 계산한다.
                n_neighbors=n_neighbors,  # 각 점을 몇 개의 이웃과 연결할지 지정한다.
                random_state=42,  # 재현 가능한 결과를 위해 난수 시드를 고정한다.
                assign_labels="kmeans",  # spectral embedding 이후 k-means로 label을 배정한다.
            ).fit_predict(x_scaled)  # 표준화된 feature로 cluster label을 예측한다.
        else:  # 데이터가 너무 적어 cluster를 만들 수 없는 경우이다.
            clusters = None  # clustering 결과를 None으로 둔다.
        return coordinates, clusters, "sklearn"  # PCA 좌표, cluster label, 사용 방법 이름을 반환한다.
    except Exception as exc:  # sklearn 사용이 불가능하거나 오류가 발생한 경우이다.
        print(f"WARNING: sklearn analysis unavailable, using fallback methods: {exc}")  # fallback 사용 사실을 출력한다.
        coordinates = _fallback_pca(x_scaled, n_components=2)  # numpy 기반 PCA 대체 좌표를 계산한다.
        return coordinates, None, "fallback"  # fallback 좌표와 clustering 없음 상태를 반환한다.


def _write_optional_plot(coordinates: pd.DataFrame) -> str | None:
    # PCA 좌표와 cluster label을 이용해 시각화 이미지를 저장한다.
    # 보고서에는 이 이미지가 "프로그램 동작화면 및 분석 결과" 자료로 들어갈 수 있다.
    try:  # matplotlib/seaborn이 설치되어 있을 때만 그림을 저장한다.
        import matplotlib.pyplot as plt  # 그래프 생성 라이브러리이다.
        import seaborn as sns  # 보기 좋은 scatter plot을 만들기 위한 라이브러리이다.

        FIGURES.mkdir(parents=True, exist_ok=True)  # 그림 저장 폴더를 만든다.
        output = FIGURES / "pca_clusters.png"  # 저장할 그림 파일 경로이다.
        plt.figure(figsize=(8, 5))  # 그림 크기를 설정한다.
        sns.scatterplot(  # PCA 좌표를 산점도로 그린다.
            data=coordinates,  # 그릴 데이터는 PCA 좌표와 cluster 정보이다.
            x="component_1",  # x축은 첫 번째 PCA 성분이다.
            y="component_2",  # y축은 두 번째 PCA 성분이다.
            hue="cluster",  # 점 색은 spectral clustering 결과로 구분한다.
            style="rate_label",  # 수동 rate label이 있으면 점 모양으로 표시한다.
            s=120,  # 점 크기이다.
        )
        for _, row in coordinates.iterrows():  # 각 점에 알카인 이름 라벨을 붙인다.
            plt.text(row["component_1"], row["component_2"], str(row["alkyne"]), fontsize=8)  # 점 옆에 알카인 이름을 표시한다.
        plt.title("Click reaction feature map")  # 그래프 제목을 설정한다.
        plt.tight_layout()  # 요소가 잘리지 않도록 레이아웃을 조정한다.
        plt.savefig(output, dpi=180)  # 그래프를 PNG 파일로 저장한다.
        plt.close()  # 메모리 관리를 위해 figure를 닫는다.
        return str(output)  # 저장된 그림 경로를 반환한다.
    except Exception as exc:  # 그래프 라이브러리가 없거나 저장에 실패한 경우이다.
        print(f"WARNING: plot skipped: {exc}")  # 그림 생성을 건너뛰었음을 출력한다.
        return None  # 그림 경로가 없음을 반환한다.


def run_analysis(input_path: Path) -> dict:
    # 이 함수는 AI 분석 전체를 실행한다.
    # cleaned CSV를 읽고 feature table을 만든 뒤 PCA, spectral clustering, ridge regression, 결과 저장을 수행한다.
    input_path = resolve_project_path(input_path, must_exist=True)  # 입력 cleaned CSV 경로를 프로젝트 기준으로 해석한다.
    df = pd.read_csv(input_path)  # cleaned dataset을 읽는다.
    features = build_feature_table(df)  # 모델이 사용할 feature table을 생성한다.

    excluded = {"record_id", "log10_k", "k_value", "alkyne", "rate_label", "verification_status"}  # 모델 입력에서 제외할 해석용 열 목록이다.
    feature_columns = [column for column in features.columns if column not in excluded]  # 실제 모델 입력 feature 열 목록을 만든다.
    x = features[feature_columns].to_numpy(dtype=float)  # feature table을 numpy 행렬로 변환한다.
    y = features["log10_k"].to_numpy(dtype=float)  # 목표값 log10(k)를 numpy 배열로 변환한다.
    x_scaled, _, _ = _standardize(x)  # feature별 스케일 차이를 없애기 위해 표준화한다.

    coordinates, spectral_clusters, method = _try_sklearn_analysis(x_scaled)  # PCA와 spectral clustering을 수행한다.
    if spectral_clusters is None:  # spectral clustering 결과가 없으면 fallback cluster를 사용한다.
        cluster_labels = _fallback_rate_clusters(features["log10_k"])  # log10(k) 분위수 기반 cluster를 만든다.
        cluster_method = "fallback_log10_k_quantiles"  # 사용한 cluster 방법 이름을 기록한다.
    else:  # spectral clustering 결과가 있으면 그 label을 사용한다.
        cluster_labels = pd.Series([f"spectral_cluster_{value}" for value in spectral_clusters])  # 숫자 cluster label을 문자열로 바꾼다.
        cluster_method = "spectral_clustering"  # 사용한 cluster 방법 이름을 기록한다.

    coordinates_df = pd.DataFrame(  # PCA 좌표와 cluster 결과를 표로 만든다.
        {
            "record_id": features["record_id"],  # 각 점의 원본 record_id이다.
            "alkyne": features["alkyne"],  # 그래프와 표에서 볼 알카인 이름이다.
            "component_1": coordinates[:, 0],  # PCA 첫 번째 성분 좌표이다.
            "component_2": coordinates[:, 1] if coordinates.shape[1] > 1 else 0,  # PCA 두 번째 성분 좌표이다.
            "cluster": cluster_labels,  # spectral clustering 또는 fallback cluster 결과이다.
            "rate_label": features["rate_label"],  # 수동 속도 라벨이 있으면 보존한다.
            "log10_k": features["log10_k"],  # 로그 변환된 속도상수이다.
            "verification_status": features["verification_status"],  # 원문 검증 상태이다.
        }
    )

    feature_importance = _feature_correlations(features, feature_columns)  # feature와 log10(k)의 절대 상관계수를 계산한다.
    rmse = _ridge_leave_one_out_rmse(x_scaled, y) if len(y) >= 4 else None  # 데이터가 충분하면 leave-one-out RMSE를 계산한다.

    PROCESSED_DATA.mkdir(parents=True, exist_ok=True)  # 분석 결과 CSV 저장 폴더를 만든다.
    REPORTS.mkdir(parents=True, exist_ok=True)  # 보고서 요약 저장 폴더를 만든다.
    coordinates_path = PROCESSED_DATA / "analysis_coordinates.csv"  # PCA 좌표와 cluster 결과 CSV 경로이다.
    importance_path = PROCESSED_DATA / "feature_importance.csv"  # feature correlation 결과 CSV 경로이다.
    metrics_path = PROCESSED_DATA / "model_metrics.json"  # 모델 성능과 분석 메트릭 JSON 경로이다.
    summary_path = REPORTS / "analysis_summary.md"  # 보고서용 Markdown 요약 파일 경로이다.

    coordinates_df.to_csv(coordinates_path, index=False)  # PCA 좌표와 cluster 결과를 CSV로 저장한다.
    feature_importance.to_csv(importance_path, index=False)  # feature correlation 결과를 CSV로 저장한다.
    figure_path = _write_optional_plot(coordinates_df)  # PCA cluster plot을 PNG로 저장한다.

    metrics = {  # 분석 실행 결과를 JSON으로 저장하기 위한 dict이다.
        "input": str(input_path),  # 분석에 사용한 입력 파일 경로이다.
        "rows_used": int(len(features)),  # 실제 분석에 사용된 k_value 행 수이다.
        "feature_count": int(len(feature_columns)),  # 모델 입력 feature 개수이다.
        "projection_method": method,  # PCA 구현 방식이다.
        "cluster_method": cluster_method,  # cluster 생성 방식이다.
        "ridge_leave_one_out_rmse_log10_k": rmse,  # ridge regression의 leave-one-out RMSE이다.
        "figure_path": figure_path,  # 저장된 그래프 파일 경로이다.
        "warning": "Treat results as exploratory until all analysis rows are primary_checked and comparable.",  # 결과 해석 주의 문구이다.
    }
    metrics_path.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")  # 분석 메트릭을 JSON 파일로 저장한다.

    top_features = feature_importance.head(5)  # 상관계수가 가장 큰 feature 5개만 요약에 넣는다.
    summary_lines = [  # 보고서용 Markdown 요약 내용을 줄 단위로 만든다.
        "# Analysis Summary",  # 요약 제목이다.
        "",  # Markdown 빈 줄이다.
        f"- Rows used: {len(features)}",  # 분석에 사용된 행 수를 기록한다.
        f"- Projection method: {method}",  # PCA 방법을 기록한다.
        f"- Cluster method: {cluster_method}",  # clustering 방법을 기록한다.
        f"- Ridge leave-one-out RMSE on log10(k): {rmse:.3f}" if rmse is not None else "- Ridge model skipped: not enough rows.",  # RMSE 또는 생략 이유를 기록한다.
        "- Data warning: results are exploratory until analysis rows are primary-checked and measured under comparable conditions.",  # 데이터 해석 주의 문구이다.
        "",  # Markdown 빈 줄이다.
        "## Top feature correlations",  # feature correlation 섹션 제목이다.
        "",  # Markdown 빈 줄이다.
        _markdown_table(top_features),  # 상위 feature correlation 표를 Markdown으로 넣는다.
        "",  # Markdown 빈 줄이다.
        "## Cluster assignments",  # cluster 배정 결과 섹션 제목이다.
        "",  # Markdown 빈 줄이다.
        _markdown_table(coordinates_df[["record_id", "alkyne", "cluster", "rate_label", "log10_k"]]),  # 주요 cluster 결과 표를 넣는다.
    ]
    summary_path.write_text("\n".join(summary_lines), encoding="utf-8")  # Markdown 분석 요약 파일을 저장한다.

    return metrics  # 분석 메트릭 dict를 반환한다.


def main() -> int:
    parser = argparse.ArgumentParser(description="Run click reaction clustering and prediction analysis.")  # 분석 스크립트의 CLI 설명이다.
    parser.add_argument("--input", required=True, type=Path)  # cleaned CSV 입력 경로 인자이다.
    args = parser.parse_args()  # 명령행 인자를 해석한다.

    metrics = run_analysis(args.input)  # 전체 분석 파이프라인을 실행한다.
    print(json.dumps(metrics, indent=2, ensure_ascii=False))  # 분석 메트릭을 콘솔에 출력한다.
    return 0  # 정상 종료 코드를 반환한다.


if __name__ == "__main__":  # 파일을 직접 실행했을 때만 main을 호출한다.
    raise SystemExit(main())  # main의 반환값을 프로그램 종료 코드로 사용한다.
