import argparse  # 명령행 인자를 처리하기 위한 표준 라이브러리이다.
import json  # PubChem API 응답 JSON을 읽기 위한 표준 라이브러리이다.
import time  # PubChem 요청 사이에 지연 시간을 넣기 위한 표준 라이브러리이다.
from pathlib import Path  # 파일 경로를 다루기 위한 표준 라이브러리이다.
from urllib.error import HTTPError, URLError  # 웹 요청 실패 유형을 구분하기 위한 예외 클래스이다.
from urllib.parse import quote  # 검색어를 URL에 넣을 수 있게 인코딩하기 위한 함수이다.
from urllib.request import urlopen  # PubChem REST API에 요청을 보내기 위한 함수이다.

import pandas as pd  # CSV 파일을 읽고 결과 테이블을 저장하기 위한 라이브러리이다.

try:  # 패키지 형태로 실행될 때 사용하는 import 경로이다.
    from .click_reaction_config import PROCESSED_DATA, RAW_DATA, resolve_project_path  # 프로젝트 경로 설정을 불러온다.
except ImportError:  # 파일을 직접 실행할 때 사용하는 import 경로이다.
    from click_reaction_config import PROCESSED_DATA, RAW_DATA, resolve_project_path  # 직접 실행용 경로 설정을 불러온다.


PUBCHEM_PROPERTIES = "CanonicalSMILES,IsomericSMILES,MolecularFormula,MolecularWeight"  # PubChem에서 받을 구조 정보 목록이다.


def fetch_pubchem_properties(query_term: str, timeout: int = 20) -> dict:
    # 이 함수는 PubChem에서 한 검색어에 대한 SMILES, 분자식, 분자량을 가져온다.
    encoded = quote(query_term)  # 검색어를 URL 안전 문자열로 변환한다.
    url = (  # PubChem PUG REST API 주소를 만든다.
        "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/"  # 이름 기반 compound 검색 엔드포인트이다.
        f"{encoded}/property/{PUBCHEM_PROPERTIES}/JSON"  # 요청할 property 목록과 JSON 형식을 지정한다.
    )
    try:  # 네트워크 요청은 실패 가능성이 있으므로 예외 처리를 한다.
        with urlopen(url, timeout=timeout) as response:  # PubChem API에 실제 요청을 보낸다.
            payload = json.loads(response.read().decode("utf-8"))  # 응답 바이트를 JSON 객체로 변환한다.
    except HTTPError as exc:  # PubChem이 404 등 HTTP 오류를 반환한 경우이다.
        return {"query_term": query_term, "status": f"http_error_{exc.code}", "url": url}  # 실패 상태를 기록한다.
    except URLError as exc:  # 네트워크 연결 자체가 실패한 경우이다.
        return {"query_term": query_term, "status": f"url_error_{exc.reason}", "url": url}  # 연결 오류 상태를 기록한다.
    except TimeoutError:  # 지정 시간 안에 응답이 오지 않은 경우이다.
        return {"query_term": query_term, "status": "timeout", "url": url}  # 시간 초과 상태를 기록한다.

    properties = payload.get("PropertyTable", {}).get("Properties", [])  # PubChem property 결과 리스트를 꺼낸다.
    if not properties:  # 검색 결과가 비어 있으면 구조 정보를 찾지 못한 것이다.
        return {"query_term": query_term, "status": "not_found", "url": url}  # 미발견 상태를 반환한다.

    first = properties[0]  # 여러 결과가 있을 때 첫 번째 결과를 대표값으로 사용한다.
    return {  # 검색 성공 결과를 표 형태로 저장할 수 있게 dict로 만든다.
        "query_term": query_term,  # 원래 검색어를 기록한다.
        "status": "found",  # 검색 성공 상태를 기록한다.
        "cid": first.get("CID"),  # PubChem compound ID를 기록한다.
        "canonical_smiles": first.get("CanonicalSMILES"),  # canonical SMILES를 기록한다.
        "isomeric_smiles": first.get("IsomericSMILES"),  # 입체화학 포함 SMILES를 기록한다.
        "molecular_formula": first.get("MolecularFormula"),  # 분자식을 기록한다.
        "molecular_weight": first.get("MolecularWeight"),  # 분자량을 기록한다.
        "url": url,  # 재확인을 위한 요청 URL을 기록한다.
    }


def fetch_terms(terms_path: Path, output_path: Path, delay_seconds: float = 0.2) -> pd.DataFrame:
    # 이 함수는 검색어 CSV 전체를 읽고 PubChem 조회 결과 CSV를 만든다.
    terms_path = resolve_project_path(terms_path, must_exist=True)  # 입력 CSV 경로를 프로젝트 기준으로 해석한다.
    output_path = resolve_project_path(output_path)  # 출력 CSV 경로를 프로젝트 기준으로 해석한다.
    terms = pd.read_csv(terms_path)  # PubChem 검색어 목록 CSV를 읽는다.
    rows = []  # 각 검색어의 조회 결과를 담을 리스트이다.
    for _, row in terms.iterrows():  # 검색어 CSV의 각 행을 순회한다.
        result = fetch_pubchem_properties(str(row["query_term"]))  # 현재 검색어로 PubChem 구조 정보를 조회한다.
        result["alkyne"] = row.get("alkyne", "")  # 어떤 알카인 후보에 대한 검색인지 기록한다.
        result["notes"] = row.get("notes", "")  # 검색어에 대한 주의사항을 함께 보존한다.
        rows.append(result)  # 조회 결과를 결과 리스트에 추가한다.
        time.sleep(delay_seconds)  # PubChem 서버에 과도한 요청을 보내지 않도록 잠시 쉰다.

    output = pd.DataFrame(rows)  # 조회 결과 리스트를 표 형태로 바꾼다.
    output_path.parent.mkdir(parents=True, exist_ok=True)  # 출력 폴더가 없으면 만든다.
    output.to_csv(output_path, index=False)  # PubChem 조회 결과를 CSV로 저장한다.
    return output  # 후속 확인을 위해 결과 DataFrame을 반환한다.


def main() -> int:
    # 명령행에서 PubChem 조회 스크립트를 실행할 때 사용되는 진입점이다.
    parser = argparse.ArgumentParser(description="Fetch PubChem SMILES/property lookup for alkyne query terms.")  # CLI 설명을 만든다.
    parser.add_argument(  # 검색어 CSV 파일 경로 인자를 추가한다.
        "--terms",  # 검색어 파일을 지정하는 옵션 이름이다.
        default=RAW_DATA / "pubchem_query_terms.csv",  # 기본 검색어 파일 위치이다.
        type=Path,  # 인자를 Path 객체로 받는다.
    )
    parser.add_argument(  # 출력 CSV 파일 경로 인자를 추가한다.
        "--output",  # 출력 파일을 지정하는 옵션 이름이다.
        default=PROCESSED_DATA / "pubchem_lookup.csv",  # 기본 출력 파일 위치이다.
        type=Path,  # 인자를 Path 객체로 받는다.
    )
    parser.add_argument("--delay-seconds", default=0.2, type=float)  # 요청 사이 대기 시간을 설정한다.
    args = parser.parse_args()  # 사용자가 입력한 명령행 인자를 읽는다.

    output = fetch_terms(args.terms, args.output, args.delay_seconds)  # PubChem 검색어 전체를 조회한다.
    print(output.to_string(index=False))  # 콘솔에서 결과를 바로 확인할 수 있게 출력한다.
    return 0  # 정상 종료 코드를 반환한다.


if __name__ == "__main__":  # 이 파일을 직접 실행했을 때만 main을 호출한다.
    raise SystemExit(main())  # main의 반환값을 프로그램 종료 코드로 사용한다.
