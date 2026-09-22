import streamlit as st
import google.generativeai as genai
import os
from dotenv import load_dotenv
import pandas as pd
from PIL import Image

# 환경 변수 로드 (.env 파일에서 API 키 읽기)
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# 페이지 설정
st.set_page_config(
    page_title="가지 영농후계자 AI 비서",
    page_icon="🍆",
    layout="wide"
)

# API 키 입력 확인 (UI에서도 입력 가능하도록)
if not api_key:
    st.sidebar.warning("API 키가 설정되지 않았습니다.")
    api_key_input = st.sidebar.text_input("Gemini API Key를 입력하세요", type="password")
    if api_key_input:
        api_key = api_key_input
        genai.configure(api_key=api_key)
else:
    genai.configure(api_key=api_key)

# 세션 상태 초기화
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# 프롬프트 템플릿 정의
PROMPTS = {
    "비료/농약 상담": """[역할(Role)]
당신은 대한민국 농촌진흥청 소속의 시설 채소(가지) 재배 및 병해충 방제 최고 전문가입니다.

[상황(Context) 및 작업(Task)]
저는 영농후계자로 선정되어 비닐하우스 5동에서 가지 농사를 짓고 있습니다. 질문에 대해 과학적이고 검증된 사실에 기반하여 원인과 해결책(비료/농약 처방)을 제시해 주세요.

[제약 조건(Constraint)]
1. 반드시 대한민국의 '농사로(농촌진흥청)' 및 '농약안전정보시스템'의 가이드라인을 검색하여 기반으로 답변할 것.
2. 정확한 성분명이나 희석 비율을 모를 경우, 절대 유추하거나 지어내지 말고 전문 기관의 진단이 필요하다고 밝힐 것.
3. 전문가의 조언이되, 초보 농업인도 이해하기 쉽게 단계별(Step-by-step)로 설명할 것.""",

    "지원 정책 검색": """[역할(Role)]
당신은 대한민국 농림축산식품부 및 지자체 농정과의 청년창업농/영농후계자 지원 사업을 담당하는 정책 자문관입니다.

[상황(Context) 및 작업(Task)]
저는 비닐하우스에서 가지를 재배하는 신규 영농후계자입니다. 저의 상황에 맞는 최신 정부/지자체 지원 정책을 찾아 요약해 주세요.

[제약 조건(Constraint)]
1. 2026년 기준 최신 정보를 기반으로 답변할 것.
2. 정보의 출처를 반드시 명시할 것.
3. 지원 대상, 내용, 신청 방법, 문의처를 표(Table) 형태로 정리할 것.
4. 모호한 정보는 안내하지 말고 1332(농업콜센터)로 문의하라고 할 것.""",

    "병해충 이미지 진단": """[역할(Role)]
당신은 식물 병리학자이자 해충 방제 전문가입니다.

[상황(Context) 및 작업(Task)]
첨부된 가지 잎/열매 사진을 분석하여 의심되는 병이나 해충을 진단하고, 초기 방제법을 안내해 주세요.

[제약 조건(Constraint)]
1. 시각적 증상(반점 색상, 모양, 벌레 유무 등)을 구체적으로 묘사하고 분석할 것.
2. 단정짓지 말고 "의심됩니다" 수준으로 표현하며, 농업기술센터 등 전문가의 2차 확인을 권장할 것.
3. 친환경적 방제법과 화학적 방제법(농약)을 나누어 설명할 것.""",

    "영농 데이터 분석": """[역할(Role)]
당신은 스마트팜 데이터 분석 전문가입니다.

[상황(Context) 및 작업(Task)]
제공된 영농 일지 데이터(온도, 습도, 수확량 등)를 분석하여 가지 생육 패턴과 환경의 상관관계를 도출하고 관리 인사이트를 제공해 주세요.

[제약 조건(Constraint)]
1. 수치 데이터에 기반하여 객관적으로 분석할 것.
2. 최적의 온습도 관리 범위를 제안할 것.
3. 발견된 이상치나 주의할 패턴이 있다면 강조할 것.""",

    "마케팅 콘텐츠 생성": """[역할(Role)]
당신은 농산물 직거래 전문 마케터 및 카피라이터입니다.

[상황(Context) 및 작업(Task)]
당일 수확한 신선한 무농약 가지를 B2C(직거래)로 판매하기 위한 매력적인 홍보 콘텐츠를 작성해 주세요. 타겟은 건강에 관심이 많은 20~40대 주부입니다.

[제약 조건(Constraint)]
1. 인스타그램 게시글 포맷(이모지 활용, 줄바꿈)으로 작성할 것.
2. 추천 해시태그를 5개 이상 포함할 것.
3. 가지의 영양학적 장점(안토시아닌 등)과 요리 활용법(가지 솥밥 등)을 살짝 언급할 것."""
}

# 사이드바 설정
with st.sidebar:
    st.title("🍆 영농후계자 AI 비서")
    selected_mode = st.radio(
        "사용할 모드를 선택하세요",
        list(PROMPTS.keys())
    )
    
    st.markdown("---")
    st.markdown("### 설정")
    temperature = st.slider("창의성 지수 (Temperature)", 0.0, 1.0, 0.1, 0.1, help="낮을수록 사실 기반, 높을수록 창의적인 답변을 합니다.")
    
    if st.button("대화 내용 초기화"):
        st.session_state.chat_history = []
        st.rerun()

# 메인 화면
st.title(f"{selected_mode} 모드")

# 모드별 사용법 예시 안내 (초보자용)
with st.expander("💡 처음이신가요? 이렇게 질문해 보세요!"):
    if selected_mode == "비료/농약 상담":
        st.info("예시: 가지 잎 가장자리가 노랗게 변하고 열매가 잘 안 자라는데, 원인이 뭘까? 추천하는 비료나 농약 알려줘.")
    elif selected_mode == "지원 정책 검색":
        st.info("예시: 나는 경기도 용인시에서 농사짓는 30대 1년 차 영농후계자야. 비닐하우스 스마트팜 장비 도입을 위한 보조금이나 저리 대출 지원 정책 찾아줘.")
    elif selected_mode == "병해충 이미지 진단":
        st.info("예시: (사진 업로드 후) 이 잎사귀에 생긴 하얀 가루 같은 게 뭔지 진단해주고, 어떻게 방제해야 하는지 알려줘.")
    elif selected_mode == "영농 데이터 분석":
        st.info("예시: (데이터 업로드 후) 이번 달 데이터에서 가지 생육이 가장 좋았던 날들의 온습도 조건을 분석하고, 다음 달 관리 포인트를 요약해 줘.")
    elif selected_mode == "마케팅 콘텐츠 생성":
        st.info("예시: 30대 주부를 타겟으로, 당일 수확해 신선하고 무농약으로 키운 가지의 장점을 강조하는 인스타그램 홍보 게시글과 해시태그를 작성해 줘.")

st.markdown("---")

# 제미나이 모델 설정
def get_model(temperature_val):
    generation_config = genai.types.GenerationConfig(
        temperature=temperature_val,
    )
    # 이미지나 일반 텍스트 모두 대응 가능한 모델 (최신 2.5 Flash 버전 적용)
    return genai.GenerativeModel('gemini-2.5-flash', generation_config=generation_config)

# 채팅 기록 표시
for role, text in st.session_state.chat_history:
    with st.chat_message(role):
        st.markdown(text)

# 사용자 입력 처리
if selected_mode == "병해충 이미지 진단":
    uploaded_file = st.file_uploader("가지 잎이나 열매의 사진을 업로드해주세요.", type=["jpg", "jpeg", "png"])
    user_input = st.chat_input("추가적인 증상 설명이나 궁금한 점을 입력하세요.")
    
    if uploaded_file and user_input and api_key:
        image = Image.open(uploaded_file)
        st.image(image, caption="업로드된 이미지", use_column_width=True)
        
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("이미지를 분석하고 있습니다..."):
                try:
                    model = get_model(temperature)
                    system_prompt = PROMPTS[selected_mode]
                    prompt = f"시스템 설정: {system_prompt}\n\n사용자 질문: {user_input}"
                    
                    response = model.generate_content([image, prompt])
                    st.markdown(response.text)
                    
                    st.session_state.chat_history.append(("user", f"[이미지 업로드됨] {user_input}"))
                    st.session_state.chat_history.append(("assistant", response.text))
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

elif selected_mode == "영농 데이터 분석":
    uploaded_data = st.file_uploader("영농 일지 데이터(CSV 형식)를 업로드해주세요.", type=["csv"])
    user_input = st.chat_input("분석을 원하는 구체적인 내용을 입력하세요.")
    
    if uploaded_data and user_input and api_key:
        df = pd.read_csv(uploaded_data)
        st.write("업로드된 데이터 미리보기:")
        st.dataframe(df.head())
        
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("데이터를 분석하고 있습니다..."):
                try:
                    model = get_model(temperature)
                    system_prompt = PROMPTS[selected_mode]
                    data_string = df.to_string()
                    prompt = f"시스템 설정: {system_prompt}\n\n제공된 데이터:\n{data_string}\n\n사용자 질문: {user_input}"
                    
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                    
                    st.session_state.chat_history.append(("user", f"[데이터 업로드됨] {user_input}"))
                    st.session_state.chat_history.append(("assistant", response.text))
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

else:
    # 텍스트 기반 모드 (비료/농약, 지원정책, 마케팅)
    user_input = st.chat_input("질문을 입력하세요.")
    
    if user_input and api_key:
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("답변을 생성하고 있습니다..."):
                try:
                    model = get_model(temperature)
                    system_prompt = PROMPTS[selected_mode]
                    prompt = f"시스템 설정: {system_prompt}\n\n사용자 질문: {user_input}"
                    
                    response = model.generate_content(prompt)
                    st.markdown(response.text)
                    
                    st.session_state.chat_history.append(("user", user_input))
                    st.session_state.chat_history.append(("assistant", response.text))
                except Exception as e:
                    st.error(f"오류가 발생했습니다: {e}")

if not api_key:
    st.info("좌측 사이드바에 Gemini API Key를 입력해야 챗봇을 사용할 수 있습니다.")
