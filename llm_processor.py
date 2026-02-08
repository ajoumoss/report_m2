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
[🚫 중복 및 연속성 관리 지침 (Modified)]
1. **[1번 ~ 5번 이슈 (핵심 추적)]**:
   - **중복 허용 (조건부)**: 직전 보고서에 나왔던 이슈라도, **"현재 시점에서 가장 중요하고 시급한 국정 현안"**이라면 1~5번에 다시 포함시키십시오.
   - **작성 지침**: 단순 반복은 지양하고, **심층 분석**이나 **새로운 쟁점/업데이트된 현황**을 반드시 추가하여 '연속성 있는 보고'가 되도록 하십시오.

2. **[6번 ~ 20번 이슈 (다양성 확보)]**:
   - **절대 중복 금지**: 6번부터 20번까지는 아래 [최근 보고서 이슈 목록]에 포함된 내용과 겹치는 기사를 **무조건 제외**하십시오.
   - **완전 신규 발굴**: 이 구간은 아직 다루지 않은 **새로운 이슈(New Topics)**로만 채워야 합니다.

[최근 보고서 이슈 목록 (6~20번 중복 배제용)]
{"="*30}
{chr(10).join(previous_reports[:3])} 
{"="*30}
"""

        prompt = f"""
[기본 정보 및 맥락]
- **현재 시점**: 2026년 2월
- **분석 대상 기간**: 지난 72시간 (3일)
- **정치 상황**: 
   1. **현재 여야 구도**: **여당(더불어민주당)**, **야당(국민의힘)**.
   2. **[정당-인물-직책 논리 검증 (중요도 1순위)]**:
      - **인물 소속 고정**: **황희 = 더불어민주당 (여당)** / **유인촌 = 국민의힘 (야당)**. 이 연결은 절대 변하지 않습니다.
      - **직책 소속 일치**: 뉴스에 "민주당 전략공천관리위원장"이라고 나오면 이는 반드시 **"여당(더불어민주당)의 직책"**입니다. 이를 "야당(국민의힘)의 직책"으로 기술하는 것은 치명적 허위사실입니다.
      - **명칭 교정 원칙**: 뉴스 기사(과거 데이터 기반)에 "야당인 민주당"이라고 적혀 있더라도, 시스템 설정에 따라 반드시 **"여당인 민주당"**으로 고쳐 써야 합니다. 정당 명칭은 유지하되 '여/야' 지칭만 시스템 설정에 맞추십시오.
   3. **[시스템 팩트체크 및 환각 방지 지침]**: 
      - **논리적 모순 금지**: "여당 소속 인물이 야당의 위원장으로 발탁"과 같은 비논리적 서술은 뉴스에 그런 특수 상황이 명시되지 않는 한 절대 금지입니다.
      - **야당 정부 표현 금지**: 정부는 무조건 **"여당(현 정부)"**입니다.
      - **최휘영**: 현 문화체육관광부 장관 (여당 정부 인사)
   4. **인사 현황**: 2025년 8월, 문체부 주요 보직 개편이 있었습니다.
   5. **정보 유효성**: 2026년 2월 시점의 직함을 사용하고, 퇴직자는 '전 장관'으로 표기하십시오.
   6. **오류 무관용**: 여야 구도를 잘못 서술하는 순간 보고서 전체의 설득력이 사라집니다. 최종 출력 전 반드시 "인물-정당-여야" 삼각 관계를 재검증하십시오.

{history_instruction}
{minutes_instruction}

[기사 선별 및 분석 지침]
1. **[데이터 활용 가이드 (Basket Mapping)]**:
   - **Basket A(거버넌스/감사)** & **Basket C(체육계 비리)**: 1~5번 핵심 이슈로 우선 채택.
   - **Basket B(산업)** & **Basket D(관광/민원)**: 6~20번 이슈로 활용.

2. **[유사/중복 이슈 통합 원칙]**: 동일 사건은 하나의 이슈로 통합하십시오. 절대 같은 사건을 쪼개서 번호를 늘리지 마십시오.

3. **[이슈 선정 근거 작성 지침]**:
   - 각 이슈마다 해당 이슈를 선정한 이유를 **[이슈 선정 근거]** 섹션에 명확히 기술하십시오.
   - **1~5번**: 국가적 중대성, 국정감사 핵심 쟁점, 연속적인 추적 필요성 등을 강조하십시오.
   - **6~10번**: 정책적 다양성(체육, 관광, 예술 등), 최신 동향의 중요성, 기존 이슈의 새로운 전개 등을 기술하십시오.
   - **11~20번**: 최근 72시간 내의 시의성, 민생 직결성, 새로운 정책 발표 등을 근거로 제시하십시오.

4. **🚨 [인용 및 근거 표기 지침 (중요도 1순위)]**:
   - **[현안 개요 및 국민적 관심사]** 섹션과 **[정부 대응의 문제점 및 쟁점]** 섹션의 **모든 문장** 끝에는 반드시 근거 기사 번호([N])와 링크를 달아야 합니다.
   - **단 하나의 문장도 근거 없이 기술하지 마십시오.** (신뢰도와 직결되는 사항임)
   - 예시: "문체부의 예산 집행률은 40%에 불과합니다.<sup><a href='...' target='_blank'>[5]</a></sup>"

[보고서 작성 포맷 (엄수)]

**시작 멘트**:
"지난 72시간 동안의 주요 현안 및 지난 국정감사 이후의 핵심 쟁점을 심층 분석하여 보고드립니다.
(만약 1~5번 중복 가능성 공지가 필요하다면 여기에 굵게 삽입)"

**(1번부터 20번까지 아래 포맷 적용)**

### [N]. [이슈 제목] (6-10번 중복 시 [업데이트] 태그 추가)

**[이슈 선정 근거]**
[해당 이슈를 선정한 구체적인 이유 서술]

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