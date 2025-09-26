# sequence_llm_node.py
import json
from typing import Dict, Any, List
from langsmith import Client
import re
from app.models.schemas import State
#from ..tests.test_data import initial_state 

# config와 llm 임포트
from config import llm

# LangSmith 클라이언트 초기화
try:
    client = Client()
except Exception as e:
    print(f"⚠️ LangSmith Client 초기화 실패. 오류: {e}")
    client = None

def sequence_llm_node(state: State) -> Dict[str, Any]:
    # ... (기존과 동일한 코드) ...
    print("✅ 카테고리 시퀀스 LLM 노드 실행")
    if not client:
        print("⛔️ LangSmith 클라이언트가 없어 노드를 건너뜁니다.")
        return {"recommended_sequence": [], "status": "failed"}

    input_data = {
        "var2": json.dumps(state["available_categories"], ensure_ascii=False, indent=2),
        "user1": json.dumps(state["user_data"], ensure_ascii=False, indent=2),
        "user2": json.dumps(state.get("partner_data", state.get("user_partner_data", {})),
                        ensure_ascii=False, indent=2),  # 테스트 단계에서는 비워두거나 다른 dummy 데이터 넣기
        "couple": json.dumps(state["couple_data"], ensure_ascii=False, indent=2),  # 마찬가지
        "trigger": json.dumps(state["trigger_data"], ensure_ascii=False, indent=2),
        "question": state["query"],
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
    
# 파일 맨 아래에 추가
if __name__ == "__main__":
    from ..tests.test_data import initial_state  # <-- 이 부분도 수정되었습니다.
    import asyncio

    print("--- sequence_llm_node 테스트 시작 ---")
    
    async def test_node():
        result = sequence_llm_node(initial_state)
        print("\n--- 테스트 결과 ---")
        print(f"반환 값: {result}")
        print(f"업데이트된 상태: {initial_state}")
        
    asyncio.run(test_node())