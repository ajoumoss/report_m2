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
[🚫 중복 및 연속성 관리 지침 (Critical Update)]
1. **[1번 ~ 5번 이슈 (핵심 추적)]**:
   - **중복 허용**: 과거에 다뤘더라도 **"지금 이 시점에 가장 중요하고 큰 이슈"**라면 다시 다루십시오. 중복 여부보다 중요도가 최우선입니다.
   - **작성 문구**: 보고서 시작 부분에 아래 문구를 **주요 공지**로 크게 삽입하십시오:
     > **"※ 1~5번 현안은 국정의 핵심 지표로서, 연속적인 추적이 필요할 경우 이전 보고서와 중복된 내용을 포함할 수 있습니다."**

2. **[6번 ~ 10번 이슈 (주요 및 다양성)]**:
   - **중복 허용 및 태그**: 이전 보고서와 같은 이슈를 다뤄도 괜찮습니다. 다만, 이 경우 제목이나 본문 시작 부분에 반드시 **[업데이트]**라는 문구를 명시하십시오.
   - **다양성**: 1~5번에서 다루지 않은 체육, 관광, 예술 등 다양한 분야의 주요 소식을 포함하십시오.

3. **[11번 ~ 20번 이슈 (완전 신규)]**:
   - **중복 배제**: 아래 [최근 보고서 이슈 목록]을 참고하여, 최대한 중복되지 않는 새로운 이슈를 발굴하여 제공하십시오.

[최근 보고서 이슈 목록 (중복 관리 참고용)]
{"="*30}
{chr(10).join(previous_reports[:3])} 
{"="*30}
"""

        prompt = f"""
[기본 정보 및 맥락]
- **현재 시점**: 2026년 2월
- **분석 대상 기간**: 지난 72시간 (3일)
- **정치 상황**: 2025년 8월, 문체부 장관을 포함한 주요 보직 개편이 있었습니다.
- **🛡️ [시스템 팩트체크 및 시점 보정 지침]**: 
  1. **정보 유효성**: 2026년 2월 시점의 직함(현 장관: 최휘영)을 사용하고, 퇴임자(유인촌, 황희 등)는 반드시 '전 장관'으로 표기하십시오.
  2. **최신성 우선**: 갈등 정보 발생 시 최신 발행일 기사를 신뢰하십시오.

{history_instruction}
{minutes_instruction}

[기사 선별 및 분석 지침]
1. **[데이터 활용 가이드 (Basket Mapping)]**:
   - **Basket A(거버넌스/감사)** & **Basket C(체육계 비리)**: 1~5번 핵심 이슈로 우선 채택.
   - **Basket B(산업)** & **Basket D(관광/민원)**: 6~20번 이슈로 활용.

2. **[유사/중복 이슈 통합 원칙]**: 동일 사건은 하나의 이슈로 통합하십시오. 절대 같은 사건을 쪼개서 번호를 늘리지 마십시오.

3. **🚨 [인용 및 근거 표기 지침 (중요도 1순위)]**:
   - **[현안 개요 및 국민적 관심사]** 섹션과 **[정부 대응의 문제점 및 쟁점]** 섹션의 **모든 문장** 끝에는 반드시 근거 기사 번호([N])와 링크를 달아야 합니다.
   - **단 하나의 문장도 근거 없이 기술하지 마십시오.** (신뢰도와 직결되는 사항임)
   - 예시: "문체부의 예산 집행률은 40%에 불과합니다.<sup><a href='...' target='_blank'>[5]</a></sup>"

[보고서 작성 포맷 (엄수)]

**시작 멘트**:
"지난 72시간 동안의 주요 현안 및 지난 국정감사 이후의 핵심 쟁점을 심층 분석하여 보고드립니다.
(만약 1~5번 중복 가능성 공지가 필요하다면 여기에 굵게 삽입)"

**(1번부터 20번까지 아래 포맷 적용)**

### [N]. [이슈 제목] (6-10번 중복 시 [업데이트] 태그 추가)

**[현안 개요 및 국민적 관심사]** (🚨 **모든 문장에 근거 링크 필수**)
[내용 서술] <sup><a href="링크" target="_blank">[기사번호]</a></sup> ...

**[정부 대응의 문제점 및 쟁점]** (🚨 **모든 문장에 근거 링크 필수**)
[내용 서술] <sup><a href="링크" target="_blank">[기사번호]</a></sup> ...

**[질의 포인트 및 제언]**
...

**[예상 반박 및 재반박 논리]**
...

**[회의록 팩트체크]**
...

[수집된 데이터 (기사 목록)]
{news_summary}

위 데이터를 바탕으로 의원실의 신뢰도를 높일 수 있는 **완벽하게 근거가 뒷받침된** 심층 보고서를 작성하십시오.
"""
        return prompt