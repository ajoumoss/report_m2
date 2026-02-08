import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

class LLMProcessor:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        # 의원님께서 결제 설정을 완료하셨으므로 가용한 가장 강력한 Pro 모델을 유지합니다.
        self.model_name = 'gemini-2.5-pro' 

    def generate_report(self, news_data, previous_reports=None):
        import glob
        import time
        
        # 1. 회의록 PDF 업로드 및 처리
        # minutes/회의록 및 minutes/국정감사 폴더 내의 PDF 파일 탐색
        pdf_files = glob.glob("minutes/회의록/*.pdf") + glob.glob("minutes/회의록/*.PDF") + \
                    glob.glob("minutes/국정감사/*.pdf") + glob.glob("minutes/국정감사/*.PDF")
        uploaded_files = []
        
        if pdf_files:
            # 날짜 기준 정렬 (파일명 끝의 (YYYY.MM.DD.) 추출)
            try:
                pdf_files.sort(key=lambda x: x.split('(')[-1].split(')')[0], reverse=True)
            except:
                pdf_files.sort(reverse=True) # 날짜 파싱 실패 시 이름 역순

            # 최근 10개만 선택
            target_files = pdf_files[:10]
            print(f"📄 전체 {len(pdf_files)}개 중 최근 {len(target_files)}개 회의록을 분석합니다.")
            
            for pdf in target_files:
                try:
                    # 파일 업로드 (한글 파일명 오류 방지를 위해 바이너리 모드로 읽기, MIME 타입 명시)
                    with open(pdf, 'rb') as f:
                        file_ref = self.client.files.upload(file=f, config={'mime_type': 'application/pdf', 'display_name': os.path.basename(pdf)})
                    print(f"   - 업로드 완료: {os.path.basename(pdf)}")
                    uploaded_files.append(file_ref)
                except Exception as e:
                    print(f"   - 업로드 실패 ({pdf}): {e}")

            # 파일 처리 대기 (ACTIVE 상태 확인)
            # Gemini 1.5 Pro는 문서 처리 시간이 필요할 수 있음
            print("⏳ 파일 처리 대기 중...")
            for f in uploaded_files:
                while f.state.name == "PROCESSING":
                    time.sleep(2)
                    f = self.client.files.get(name=f.name)
            print("✅ 모든 회의록 파일 준비 완료!")

        prompt = self._build_prompt(news_data, has_minutes=len(uploaded_files) > 0, previous_reports=previous_reports)
        
        # 프롬프트 + 파일(있다면) 함께 전송
        contents = [prompt]
        if uploaded_files:
            contents.extend(uploaded_files)

        response = self.client.models.generate_content(
            model=self.model_name,
            contents=contents
        )
        return response.text

    def create_chat_session(self, news_data):
        # 채팅 기능은 현재 사용하지 않으므로 그대로 유지하거나 필요 시 업데이트
        from google.genai import types
        system_msg = self._build_prompt(news_data)
        
        chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=system_msg
            )
        )
        return chat

    def _build_prompt(self, news_data, has_minutes=False, previous_reports=None):
        news_summary = ""
        link_index = 1
        for cat, items in news_data.items():
            news_summary += f"\n### 섹션: {cat}\n"
            # 중복 방지를 위해 더 많은 뉴스 제공 (50 -> 100)
            for item in items[:100]:
                news_summary += f"- 기사[{link_index}]: {item['title']}\n  요약: {item['description']}\n  링크: {item['link']}\n"
                link_index += 1
        
        minutes_instruction = ""
        if has_minutes:
            minutes_instruction = """
[회의록 및 국정감사 교차 검증 지침] (매우 중요 - 2026년 2월 기준)
- 첨부된 PDF(국회 회의록 및 국정감사 결과보고서) 내용을 **반드시** 정밀 분석하십시오.
- **분석 핵심 목표**:
  1. **[미해결 이슈 추적]**: 지난 국정감사(2024년, 2025년)나 상임위 회의에서 지적되었으나, **여전히 개선되지 않았거나 이행이 지지부진한 사안**을 발굴하십시오.
  2. **[거짓 해명 포착]**: 현 장관/차관의 최근 발언이나 뉴스가 과거 회의록의 발언과 모순되는 점을 찾으십시오.
- **작성 요건**:
  - 미해결 이슈 발견 시, **[회의록 팩트체크]** 섹션에 **정확한 근거(회의명, 날짜, 페이지, 발언자, 발언 원문)**를 명시해야 합니다.
  - "과거에 지적되었다"라고 뭉뚱그리지 말고, **"2024년 국정감사 (p.150)에서 OOO 의원이 지적했으나..."**와 같이 구체적으로 적시하십시오.
"""

    
        history_instruction = ""
        if previous_reports:
            history_instruction = f"""
[🚫 중복 방지 및 연속성 관리 지침 (Critical)]
1. **[1번 ~ 5번 이슈 (오늘의 핵심 쟁점 - Impact First)]**:
   - **[선정 기준]**: 과거에 다뤘냐 아니냐는 중요하지 않습니다. **"지금 이 시점에 가장 심각하고, 장관을 가장 아프게 찌를 수 있는 이슈"** 5개를 선정하십시오.
   - **[유연성]**: 지난 보고서의 핵심 이슈가 여전히 가장 중요하다면 **연속해서 추적(중복 허용)**하십시오. 하지만, 만약 더 크고 새로운 대형 악재가 터졌다면 과감히 그것을 1~5번에 배치하십시오.
   - **[작성 요건]**: 만약 중복된 주제라면, 반드시 **업데이트된 현황**과 **심화된 논리**를 담아야 합니다.


2. **[6번 ~ 10번 이슈 (중량감 있는 다양성 확보)]**:
   - **[성격]**: 단순한 단신이나 홍보성 기사가 아닙니다. 1~5번만큼은 아니더라도, **국감에서 지적될 만한 "체급 있는" 이슈**를 선정하십시오.
   - **[다양성 필수]**: 1~5번이 특정 주제(예: 게임, 영화)에 쏠렸다면, 여기서는 **체육, 관광, 예술, 출판, 저작권** 등 소외된 분야의 굵직한 문제를 다뤄야 합니다.
   - **[선정 기준]**: "예산 삭감", "낙하산 인사", "제도 미비", "지역 차별" 등 **구조적인 문제**를 다루는 기사를 우선 배치하십시오.

3. **[11번 ~ 20번 이슈 (완전 신규 발굴 - Zero Tolerance)]**:
   - **[성격]**: 지난 72시간 내 발생한 새로운 소식, 단신, 지역 축제 등 **참신함** 위주.
   - **[절대 금지]**: 아래 [최근 보고서 이슈 목록]에 언급된 단어나 주제가 **조금이라도 섞여 있다면 무조건 제외**하십시오.
   - **목표**: 의원님이 "이런 일도 있었어?"라고 할 만한 **완벽하게 새로운 정보**를 제공하십시오.

[최근 보고서 이슈 목록 (이 주제들은 11~20번에서 절대 사용 금지!)]
{"="*30}
{chr(10).join(previous_reports[:3])} 
{"="*30}
"""

        prompt = f"""
[기본 정보 및 맥락]
- **현재 시점**: 2026년 2월
- **분석 대상 기간**: 지난 72시간 (3일)
- **정치 상황**: 2025년 8월, 문체부 장관을 포함한 주요 보직 개편이 있었습니다.
- **🛡️ [시스템 팩트체크 및 시점 보정 지침] (Systemic Fact-Checking)**: 
  1. **정보의 유효기간 검증**: 기사에 언급된 직함(장관, 차관 등)이 **'현재 시점(2026년 2월)'**과 일치하는지 반드시 교차 검증하십시오.
  2. **과거 정보 필터링**: 만약 기사가 과거(2025년 이전) 사건을 다루거나, 단순 검색 유사도로 인해 수집된 '구버전 정보'라면, 이를 '현재 사실'로 기술해서는 안 됩니다.
  3. **충돌 해결**: [내부 지식] vs [검색된 기사 내용]이 충돌할 경우, **기사의 '발행일(Date)'이 최신인 것을 신뢰**하되, 명백히 시점이 지난 기사(예: 2024년 기사)가 섞여 있다면 해당 내용은 **'과거 사례'**로 분류하거나 과감히 제외하십시오.
  4. **인물 호칭 원칙**: 퇴임한 인물이 언급될 경우 반드시 '전(Ex-) 장관', '당시 장관' 등으로 호칭을 명확히 구분하여 현직자와 혼동되지 않도록 하십시오.
- **목표**: 의원님을 위한 '현안 질의용 날카로운 내부 보고서' 작성

{history_instruction}
{minutes_instruction}

[기사 선별 및 분석 지침]
1. **[데이터 활용 가이드 (Basket Mapping)]**:
   - **Basket A(거버넌스/감사)** & **Basket C(체육계 비리)**: 이곳의 기사들은 **1~5번(핵심 타격)** 이슈로 우선 채택하십시오. 장관/기관장이 가장 아파할 내용들입니다.
   - **Basket B(산업)** & **Basket D(관광/민원)**: **6~10번(구조적 문제)** 및 **11~20번(신규 발굴)** 재료로 폭넓게 활용하십시오.
   - **Recall(포괄 이슈)**: 놓친 이슈가 없는지 보완하는 용도로 쓰십시오.

2. **TOP 20 선정 전략**: 
   - **1~5번 (핵심 타격)**: **중복/신규 불문.** 현재 가장 논란이 뜨겁고 파급력이 큰 **"최고 존엄" 이슈** 선정.
   - **6~10번 (중량급 확산)**: **체급 있는 이슈.** 1~5번 이외의 분야에서 **구조적/정책적 문제**를 비중 있게 다루기. (단순 단신 X)
   - **11~20번 (신규 발굴)**: **중복 제로(0%).** 가볍더라도 **완전히 새로운** 소식/사건 발굴.

3. **[유사/중복 이슈 통합 원칙 (매우 중요)]**:
   - 동일한 사건(예: "문체부 예산 삭감 발표")에 대해 여러 언론사가 보도한 경우, 이를 **하나의 이슈( [N]. 문체부 예산 삭감 논란 )로 통합**하여 기술하십시오.
   - 절대 같은 사건을 제목만 바꿔서 [N]번과 [N+1]번에 나누어 싣지 마십시오. (적발 시 감점)

2. **작성 태도**:
   - 1~5번은 **"저격수"**처럼 급소를 찌르고, 6~10번은 **"평론가"**처럼 구조를 분석하고, 11~20번은 **"탐정"**처럼 새로운 사실을 발굴하십시오.

[보고서 작성 포맷 (엄수)]

**시작 멘트**:
"지난 24시간 동안의 주요 현안 및 지난 국정감사 이후의 핵심 쟁점을 심층 분석하여 보고드립니다.
본 보고서에 포함된 [질의 포인트 및 제언]은 정책 참고용으로 제안된 것이며, 구체적인 실행 및 세부 내용은 실무진과의 협의가 필요함을 안내드립니다."

**(1번부터 20번까지 아래 포맷 동일 적용)**

### [N]. [이슈 제목]

**[현안 개요 및 국민적 관심사]**
[내용 서술] <sup><a href="기사링크" target="_blank">[기사번호]</a></sup>

**[정부 대응의 문제점 및 쟁점] (🚨 근거 표시 필수 구간)**
- **모든 문장** 끝에 근거(기사번호/회의록) 필수.
- *예시: "문체부는 '검토 중'이라는 답변만 반복...(중략)... <sup><a href='...' target='_blank'>[5]</a></sup>"*

**[질의 포인트 및 제언]**
- 포인트 1: ...
- 포인트 2: ...

**[예상 반박 및 재반박 논리]** (특히 1~5번 필수 작성)
- *측 답변 예상: [장관의 예상되는 구체적 변명. 예: "예산 부족으로 어쩔 수 없었다"]*
- *재반박 논리: [이를 반박할 팩트. 예: "작년 불용 예산이 OO억 원임을 들어 예산 타령이 거짓임을 지적"]*

**[회의록 팩트체크]** (관련 내용 있을 시 필수)
...

[수집된 데이터 (기사 목록)]
{news_summary}

위 데이터를 바탕으로 **핵심 추적(1~5)과 신규 발굴(6~20)이 조화된** 최상의 보고서를 작성하십시오.
**특히 1~5번은 중복이더라도 더 깊이 있게, 업데이트된 내용으로 작성해야 합니다.**
"""
        return prompt
        return prompt