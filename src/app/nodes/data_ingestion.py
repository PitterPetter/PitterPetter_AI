import json
from typing import Dict, Any
from app.models.schemas import State
from langsmith import Client
from config import llm
import re

# LangSmith 클라이언트 초기화
try:
    client = Client()
except Exception as e:
    print(f"⚠️ LangSmith Client 초기화 실패. 오류: {e}")
    client = None
    
# 1. 데이터 수집 및 정제 노드 (미구현)
def data_ingestion_node(state: State) -> Dict[str, Any]:
    # TODO: Google Place API 호출 및 데이터 정제 로직 구현
    # LLM 보정 Agent는 별도의 노드 또는 함수로 분리 가능
    print("✅ 데이터 수집 및 정제 노드 실행")
    # ... 데이터 수집 및 정제 로직 ...
    # 예시: state.poi_data = {"restaurants": [...], "cafes": [...]}
    return {"status": "data_ingested"}
# -------------------------------------------------------------------------------------------------

#post man

# 날씨 데이터 - > 시작 지점의 하루 날씨가 어떻게 되는가 - [ ]

# place 데이터 불러와서 값 전달 잘 되는지 확인하고 - 1.
# 시퀀스 에서 카테고리 노드로 이어지게 세팅하고 - 2.
# 정제-> types -> 알아서 카테고리 12가지중으로 분리하게끔 이 정제는 각 카테고리별로 api를 쏘고 가져와서 정제하는게 필요하겟죠
# 각 카테고리별로 프롬프트 정리하고(날씨 데이터, 유저데이터 (무드) 등 적절한 값 뽑아서 합리적인 추천 유도) -[프롬프팅 다시 짜고 , 인풋 데이터 형식 정확하게 맞추기]

# 각 카테고리 노드에서 반환된 추천json 을 묶어서 검증하고 -> output (json 형태로 출력되게)