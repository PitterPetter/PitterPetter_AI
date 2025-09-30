# sequence_llm_node.py
import json
from typing import Dict, Any, List
from langsmith import Client
import re
from app.models.lg_schemas import State

# config와 llm 임포트
from config import llm

# LangSmith 클라이언트 초기화
try:
    client = Client()
except Exception as e:
    print(f"⚠️ LangSmith Client 초기화 실패. 오류: {e}")
    client = None

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
            response_text = llm_raw_result.content.strip()
        else:
            response_text = str(llm_raw_result).strip()
        
        # ```json ... ``` 제거
        if response_text.startswith("```"):
            response_text = response_text.strip("`").strip()
            if response_text.lower().startswith("json"):
                response_text = response_text[4:].strip()

        # 대괄호 블록만 추출
        match = re.search(r"\[.*\]", response_text, re.S)
        if match:
            response_text = match.group()

        try:
            recommended_sequence: List[str] = json.loads(response_text)
            if not isinstance(recommended_sequence, list):
                recommended_sequence = []
                print(f"⚠️ LLM 응답이 예상한 리스트 형식이 아닙니다: {response_text}")
        except json.JSONDecodeError:
            recommended_sequence = []
            print(f"⚠️ LLM 응답 JSON 파싱 실패: {response_text}")

        state["recommended_sequence"] = recommended_sequence
        print(f"✔️ 추천 카테고리 시퀀스: {state['recommended_sequence']}")

        return {"recommended_sequence": state['recommended_sequence']}

    except Exception as e:
        print(f"⛔️ LLM 호출 또는 프롬프트 처리 중 오류 발생: {e}")
        state["recommended_sequence"] = []
        return {"recommended_sequence": state['recommended_sequence'], "status": "failed"}
    
    