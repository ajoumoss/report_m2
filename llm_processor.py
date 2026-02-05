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
[🚫 중복 방지 절대 원칙 (Critical)]
- 아래 [최근 보고서 이슈 목록]에 포함된 주제는 **이번 보고서에서 절대 다루지 마십시오.**
- **'중요하니까 또 써야지' 금지.** 이미 보고된 내용은 의원님이 알고 계십니다.
- **무조건 새로운 기사, 새로운 소식**을 찾아내십시오. 메인 이슈가 고갈되었다면, 다소 지엽적인 이슈나 지역 문화 이슈라도 발굴하여 **20개를 채우되, 중복은 피하십시오.**
- 만약 완전히 동일한 사건을 다시 다뤄야 한다면, **반드시 '새로운 팩트(New Fact)'가 추가된 경우에만 허용**하며, 제목에 `[업데이트]`를 붙이고 **무엇이 달라졌는지**를 명시해야 합니다.

[최근 보고서 이슈 목록 (제외 대상)]
{"="*30}
{chr(10).join(previous_reports[:3])} 
{"="*30}
"""

        prompt = f"""
[기본 정보 및 맥락]
- **현재 시점**: 2026년 2월
- **분석 대상 기간**: 지난 72시간 (3일)
- **정치 상황**: 2025년 8월부로 정권 및 문체부 장관이 교체되었습니다.
- **목표**: 의원님을 위한 '현안 질의용 날카로운 내부 보고서' 작성

{history_instruction}
{minutes_instruction}

[기사 선별 및 분석 지침]
1. **TOP 20 선정**: 
   - 1~10번: 구조적/장기적 문제 (국감 지적 사항 등 연계)
   - 11~20번: 최신 발생 단신 및 현안 (지난 72시간 내 뉴스)
   - **다양성 확보**: 특정 주제에만 몰리지 않도록 문화/체육/관광 분야를 골고루 배분하십시오.
   - **중복 회피**: 위 '제외 대상'에 있는 내용은 쓰지 마십시오.

2. **작성 태도**:
   - 단순히 "문제가 있다"고 말하는 것은 누구나 할 수 있습니다. **"어떤 규정 위반인지", "과거 어떤 약속을 어겼는지", "어떤 구체적 피해가 발생했는지"**를 짚어내야 의원님이 질의할 수 있습니다.

[보고서 작성 포맷 (엄수)]

**시작 멘트**:
"지난 24시간 동안의 주요 현안 및 지난 국정감사 이후의 핵심 쟁점을 심층 분석하여 보고드립니다.
본 보고서에 포함된 [질의 포인트 및 제언]은 정책 참고용으로 제안된 것이며, 구체적인 실행 및 세부 내용은 실무진과의 협의가 필요함을 안내드립니다."

**(1번부터 20번까지 아래 포맷 동일 적용)**

### [N]. [이슈 제목]

**[현안 개요 및 국민적 관심사]**
[내용 서술] <sup><a href="기사링크" target="_blank">[기사번호]</a></sup>

**[정부 대응의 문제점 및 쟁점] (🚨 근거 표시 필수 구간)**
- 이 섹션의 **모든 문장** 끝에는 반드시 근거가 되는 **기사 번호 `[N]`** 또는 **회의록 출처**가 붙어야 합니다.
- **작성 규칙**:
  1. 문체부의 대응이 미흡하다면, **그 미흡함을 보여주는 기사나 자료**가 있어야 합니다.
  2. 근거 기사가 없다면 비판하지 마십시오. "구체적 대응 자료가 확인되지 않음"이라고 사실대로 적으십시오.
  3. **잘못된 예**: "정부는 소극적 태도로 일관하고 있다." (근거 없음)
  4. **올바른 예**: "문체부는 '검토 중'이라는 답변만 반복하며 1년째 결론을 내지 못하고 있다. <sup><a href='...' target='_blank'>[5]</a></sup>"
- **이 규칙을 1번부터 20번까지 끝까지 지키십시오.** 뒷부분으로 갈수록 흐지부지하지 마십시오.

**[질의 포인트 및 제언]**
- 포인트 1: ...
- 포인트 2: ...

**[예상 반박 및 재반박 논리]** (선택)
...

**[회의록 팩트체크]** (관련 내용 있을 시 필수)
...

[수집된 데이터 (기사 목록)]
{news_summary}

위 데이터를 바탕으로 **중복 없는** 최상의 보고서를 작성하십시오.
**20번까지 [정부 대응의 문제점] 섹션에 근거 `[N]`이 달려있는지 마지막으로 확인하십시오.**
"""
        return prompt
        return prompt