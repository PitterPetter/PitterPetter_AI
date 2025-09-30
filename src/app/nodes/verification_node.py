import json
import re
from typing import Dict, Any
from langsmith import Client
from app.models.schemas import State
from config import llm

# LangSmith 클라이언트 초기화
try:
    client = Client()
except Exception as e:
    print(f"⚠️ LangSmith Client 초기화 실패. 오류: {e}")
    client = None


def verification_node(state: State) -> Dict[str, Any]:
    """
    생성된 추천 결과의 합리성을 검증하는 노드.
    LangSmith에서 'gh_check' 프롬프트를 불러와 LLM의 판단을 요청합니다.
    """
    print("✅ 검증 노드 실행")

    # 1. 클라이언트 유효성 체크
    if not client:
        print("⛔️ LangSmith 클라이언트 없음 → 검증 불가 처리")
        state["current_judge"] = None
        state["judgement_reason"] = "LangSmith Client 없음 → 검증 불가"
        return {
            "current_judge": state.get("current_judge"),
            "judgement_reason": state.get("judgement_reason"),
        }

    # 2. 입력 데이터 구성
    input_data = {
        "user_data": json.dumps(state.get("user_data", {}), ensure_ascii=False),
        "recommended_sequence": json.dumps(state.get("recommended_sequence", []), ensure_ascii=False),
        "recommendations": json.dumps(state.get("recommendations", []), ensure_ascii=False),
    }

    # 3. 재시도 카운트 관리
    if "check_count" not in state:
        state["check_count"] = 0

    MAX_RETRY = 2
    if state["check_count"] >= MAX_RETRY:
        print("⚠️ 검증 재시도 횟수 초과 → 강제 종료")
        state["current_judge"] = False
        state["judgement_reason"] = f"검증 {MAX_RETRY}회 실패 → 강제 종료"
        state["check_count"] = 0
        return {
            "current_judge": state.get("current_judge"),
            "judgement_reason": state.get("judgement_reason"),
        }

    try:
        # 4. 프롬프트 실행 시도
        try:
            check_prompt = client.pull_prompt("gh_check")
        except Exception as e:
            print(f"⛔️ 검증 프롬프트 불러오기 실패: {e}")
            state["current_judge"] = False
            state["judgement_reason"] = "검증 프롬프트 없음"
            return {
                "current_judge": state.get("current_judge"),
                "judgement_reason": state.get("judgement_reason"),
            }

        messages = check_prompt.format_prompt(**input_data).to_messages()
        llm_raw_result = llm.invoke(messages)

        raw_content = getattr(llm_raw_result, "content", "").strip()
    
        # 5. LLM 응답 파싱
        parsed_args = {}
        try:
            parsed_args = json.loads(raw_content)  # JSON 전체 파싱
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_content, re.DOTALL)
            if match:
                try:
                    parsed_args = json.loads(match.group(0))
                except Exception:
                    parsed_args = {}

        # 6. 결과 반영
        judge_val = parsed_args.get("judge")
        reason_val = parsed_args.get("reason")

        if isinstance(judge_val, bool):
            state["current_judge"] = judge_val
            state["judgement_reason"] = reason_val or "판단 근거 없음"
        else:
            state["current_judge"] = None
            state["judgement_reason"] = f"LLM 응답 파싱 실패: {raw_content[:100]}..."

        # 7. 재시도 관리
        if state["current_judge"] is True:
            state["check_count"] = 0
        elif state["current_judge"] is False:
            state["check_count"] += 1

        print(f"✔️ 검증 결과 → Judge={state['current_judge']}, Reason={state['judgement_reason']}")
        return {
            "current_judge": state.get("current_judge"),
            "judgement_reason": state.get("judgement_reason"),
        }

    except Exception as e:
        print(f"⛔️ 검증 중 오류 발생: {e}")
        state["current_judge"] = None
        state["judgement_reason"] = f"검증 오류 발생: {e}"
        return {
            "current_judge": state.get("current_judge"),
            "judgement_reason": state.get("judgement_reason"),
        }
