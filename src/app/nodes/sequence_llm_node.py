# sequence_llm_node.py
import json
import re
from typing import Dict, Any, List, Optional, Tuple

from langsmith import Client

from app.models.lg_schemas import State

# config와 llm 임포트
from config import llm

# LangSmith 클라이언트 초기화
try:
    client = Client()
except Exception as e:
    print(f"⚠️ LangSmith Client 초기화 실패. 오류: {e}")
    client = None

def _strip_code_fence(text: str) -> str:
    if text.startswith("```") and text.endswith("```"):
        stripped = text.strip("`").strip()
        if stripped.lower().startswith("json"):
            return stripped[4:].strip()
        return stripped
    return text


def _extract_json_payload(raw_text: str) -> Tuple[Optional[Dict[str, Any]], Optional[List[str]]]:
    cleaned = _strip_code_fence(raw_text.strip())

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        obj_match = re.search(r"\{.*\}", cleaned, re.S)
        if obj_match:
            try:
                parsed = json.loads(obj_match.group())
            except json.JSONDecodeError:
                parsed = None
        else:
            parsed = None

        if parsed is None:
            list_match = re.search(r"\[.*\]", cleaned, re.S)
            if list_match:
                try:
                    list_payload = json.loads(list_match.group())
                    if isinstance(list_payload, list):
                        return None, list_payload
                except json.JSONDecodeError:
                    pass
            print(f"⚠️ LLM 응답 JSON 파싱 실패: {raw_text}")
            return None, None

    if isinstance(parsed, list):
        return None, parsed

    if isinstance(parsed, dict):
        categories = parsed.get("categories")
        if isinstance(categories, list):
            return parsed, categories
        print("⚠️ LLM 응답의 categories 필드가 리스트가 아닙니다")
        return parsed, None

    print("⚠️ LLM 응답이 dict/list 형식이 아닙니다")
    return None, None


def _parse_structured_text(raw_text: str) -> Optional[Dict[str, Any]]:
    """JSON 파싱이 실패했을 때 단순 텍스트 포맷에서 정보 추출."""

    lines = [line.strip() for line in raw_text.splitlines()]
    title: Optional[str] = None
    explain: Optional[str] = None
    categories: List[str] = []
    capturing_categories = False

    for line in lines:
        if not line:
            if capturing_categories:
                capturing_categories = False
            continue

        title_match = re.match(r"(?i)^course\s*title[:\-\s]*(.+)$", line)
        if title_match:
            title = title_match.group(1).strip()
            capturing_categories = False
            continue

        explain_match = re.match(r"(?i)^sequence\s*explain[:\-\s]*(.+)$", line)
        if explain_match:
            explain = explain_match.group(1).strip()
            capturing_categories = False
            continue

        if re.match(r"(?i)^available\s+categories", line):
            capturing_categories = True
            continue

        if capturing_categories:
            cat_match = re.match(r"^\d+\s+([A-Za-z0-9_\-\s]+)$", line)
            if cat_match:
                category = cat_match.group(1).strip().lower().replace(" ", "_")
                if category:
                    categories.append(category)
                continue
            else:
                capturing_categories = False

    if not title and not explain and not categories:
        return None

    payload: Dict[str, Any] = {}
    if title:
        payload["title"] = title
    if explain:
        payload["explain"] = explain
    if categories:
        payload["categories"] = categories

    return payload or None


def sequence_llm_node(state: State) -> Dict[str, Any]:
    print("✅ 카테고리 시퀀스 LLM 노드 실행")
    if not client:
        print("⛔️ LangSmith 클라이언트가 없어 노드를 건너뜁니다.")
        return {"recommended_sequence": [], "status": "failed"}

    input_data = {
        "var2": json.dumps(state.get("available_categories", []), ensure_ascii=False, indent=2),
        "user1": json.dumps(state.get("user", {}), ensure_ascii=False, indent=2),
        "user2": json.dumps(state.get("partner", {}), ensure_ascii=False, indent=2),
        "couple": json.dumps(state.get("couple", {}), ensure_ascii=False, indent=2),
        "trigger": json.dumps(state.get("user_choice", {}), ensure_ascii=False, indent=2),
        "question": state.get("query", ""),
    }
    try:
        prompt_template = client.pull_prompt("gh_sequence")
        formatted_messages = prompt_template.format_prompt(**input_data).to_messages()
        llm_raw_result = llm.invoke(formatted_messages)

        response_text = ""
        if hasattr(llm_raw_result, "content"):
            response_text = llm_raw_result.content or ""
        else:
            response_text = str(llm_raw_result)
        print(f"📝 LLM 응답: {response_text}")
        parsed_payload, recommended_sequence = _extract_json_payload(response_text)

        if not parsed_payload or not recommended_sequence:
            fallback_payload = _parse_structured_text(response_text)
            if fallback_payload:
                if not parsed_payload:
                    parsed_payload = fallback_payload
                else:
                    if fallback_payload.get("title") and "title" not in parsed_payload:
                        parsed_payload["title"] = fallback_payload["title"]
                    if fallback_payload.get("explain") and "explain" not in parsed_payload:
                        parsed_payload["explain"] = fallback_payload["explain"]
                    if fallback_payload.get("categories") and "categories" not in parsed_payload:
                        parsed_payload["categories"] = fallback_payload["categories"]
                if not recommended_sequence:
                    recommended_sequence = fallback_payload.get("categories") or []

        if not isinstance(recommended_sequence, list):
            recommended_sequence = []
            print("⚠️ 추천 카테고리 시퀀스를 찾지 못했습니다")

        state["recommended_sequence"] = recommended_sequence

        result: Dict[str, Any] = {"recommended_sequence": state["recommended_sequence"]}

        if parsed_payload:
            course_title = parsed_payload.get("title")
            sequence_explain = parsed_payload.get("explain")

            if course_title:
                state["course_title"] = course_title
                result["course_title"] = course_title
            if sequence_explain:
                state["sequence_explain"] = sequence_explain
                result["sequence_explain"] = sequence_explain

        print(f"✔️ 추천 카테고리 시퀀스: {state['recommended_sequence']}")

        return result

    except Exception as e:
        print(f"⛔️ LLM 호출 또는 프롬프트 처리 중 오류 발생: {e}")
        state["recommended_sequence"] = []
        return {"recommended_sequence": state['recommended_sequence'], "status": "failed"}
