import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

class LLMProcessor:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
        # 의원님께서 결제 설정을 완료하셨으므로 가용한 가장 강력한 Pro 모델을 유지합니다.
        self.model_name = 'gemini-2.5-pro' 

    def generate_report(self, news_data):
        import glob
        import time
        
        # 1. 회의록 PDF 업로드 및 처리
        pdf_files = glob.glob("minutes/*.pdf")
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

        prompt = self._build_prompt(news_data, has_minutes=len(uploaded_files) > 0)
        
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

    def _build_prompt(self, news_data, has_minutes=False):
        news_summary = ""
        link_index = 1
        for cat, items in news_data.items():
            news_summary += f"\n### 섹션: {cat}\n"
            for item in items[:50]:  # 섹션별 50개로 확장하여 더 많은 이슈 발굴
                news_summary += f"- 기사[{link_index}]: {item['title']}\n  요약: {item['description']}\n  링크: {item['link']}\n"
                link_index += 1
        
        minutes_instruction = ""
        if has_minutes:
            minutes_instruction = """
[회의록 교차 검증 지침] (중요 - 2026년 2월 기준)
- 첨부된 PDF(국회 회의록) 내용을 정밀 분석하십시오.
- **시점 구분**: 2025년 8월 이전 회의록은 '전임 정부(유인촌 전 장관)' 시기이고, 2025년 8월 이후는 '현 정부' 시기입니다.
- **분석 포인트**:
  1. **현 정부(2025.08~) 회의록**: 현 장관이나 차관의 발언이 최근 뉴스(2026년 2월)와 모순되는지 즉각 팩트체크하십시오. (거짓 해명, 말 바꾸기 포착)
  2. **전임 정부(~2025.07) 회의록**: 과거의 지적 사항이 여전히 해결되지 않고 반복되는지 확인하십시오. (전임 장관의 실명을 거론하며 비난하지 말고, **'반복되는 고질적 문제'**나 **'정부 차원의 약속 불이행'** 관점에서 접근)
- 만약 관련된 내용이 회의록에 있다면, **[회의록 팩트체크]** 섹션에 구체적인 발언 날짜나 내용을 인용하여 적시하십시오.
"""

        prompt = f"""
[기본 정보 및 맥락]
- **현재 시점**: 2026년 2월
- **정치 상황**: 2025년 8월부로 정권 및 문체부 장관이 교체되었습니다. (유인촌 전 장관은 2025년 7월 사임)
- **주의 사항**: 
  1. **유인촌 전 장관**에 대한 비판이나 언급은 현 시점에서 부적절하므로 지양하십시오. (단, 과거 약속과 현재의 불일치를 비교할 때는 건조하게 사실만 인용)
  2. 비판의 대상은 **'현직 문체부 장관'** 및 **'현 정부의 문체부'**여야 합니다.
  3. 이미 해결되었거나 철 지난 이슈는 배제하고, **새롭게 부상하는 이슈**나 **해결되지 않은 고질적 문제**를 발굴하십시오.

[역할 및 페르소나]
- 당신은 **'문체위(문화체육관광위원회) 의원의 현안질의 전문 입법 보좌관'**입니다. ('~입니까?' 같은 질문형이 아닌, '~점을 지적해야 함' 식의 **보고서체** 사용)
- 단순한 사실 전달을 넘어, **현재 국회 문화체육관광 분야에서 시급히 다뤄져야 할 문제**, **국민들이 궁금해하거나 공분하는 사안**, 그리고 **정부 정책의 미흡한 점**을 날카롭게 포착해야 합니다.
- 국정감사나 상임위 현안질의에서 의원님이 바로 사용할 수 있도록, **'정곡을 찌르는 비판적 시각'**과 **'논리적인 대안'**을 제시하십시오.
{minutes_instruction}

[기사 선별 기준]
- 단순 행사 홍보나 동정 기사는 배제하십시오.
- **체육계 비리, 문화 예술계 불공정 관행, 관광 산업의 구조적 문제, K-컬처 관련 정부 지원의 허와 실** 등 정부의 실책이나 국민적 관심이 높은 사안을 최우선으로 다룹니다.
- 정부나 관련 기관의 해명보다는, **문제의 본질과 현장의 비판적인 목소리**에 집중하십시오.

[보고서 작성 지침]
- **시작 멘트**: 보고서의 최상단(제목 아래, 본문 시작 전)에 별도의 인사말 없이 반드시 아래 문구로 시작하십시오.
  "지난 7일간의 주요 현안을 심층 분석하여 보고드립니다.
  본 보고서에 포함된 [질의 포인트 및 제언]은 정책 참고용으로 제안된 것이며, 구체적인 실행 및 세부 내용은 실무진과의 협의가 필요함을 안내드립니다."
- **TOP 20 심층 분석**: 가장 시급하고 중요한 문체위 현안 20가지를 선정하여 분석합니다.
- **어조**: 진중하고 분석적이며, 정부의 책임을 묻는 날카로운 시각을 유지하십시오. (보고용 경어체)
- **출처 표시**: 모든 사실 정보나 주장은 문장 끝에 반드시 `<sup><a href="URL" target="_blank">[기사번호]</a></sup>`를 달아 근거를 명시해야 합니다.

[작성 포맷]

1. **Ⅰ. 주간 문체위 현안 브리핑**
   - 지난 7일간 문화/체육/관광 분야에서 가장 뜨거웠던 이슈와 여론의 흐름을 3~4문장으로 요약 보고합니다.
   
2. **Ⅱ. 심층 이슈 포커스 (TOP 20)**
   - 의원님이 현안질의에서 다뤄야 할 핵심 이슈 20개를 분석합니다.
   
   ### [N]. [이슈 제목]
   (주의: 이슈 제목은 반드시 `###` (H3) 헤더를 사용해야 크게 표시됩니다.)
   
   **[현안 개요 및 국민적 관심사]**
   [사건의 핵심 내용과 왜 이 문제가 국민들의 관심을 받고 있는지, 혹은 왜 공분을 사고 있는지 서술. `<sup><a href="URL" target="_blank">[N]</a></sup>`]
   
   **[정부 대응의 문제점 및 쟁점]**
   [해당 사안에 대한 문체부(현 정부) 및 유관 기관의 대응이 왜 미흡한지, 예산 낭비나 행정 편의주의적 요소는 없는지 비판적으로 분석. `<sup><a href="URL" target="_blank">[N]</a></sup>`]
   
   **[질의 포인트 및 제안]**
   [대사체("장관님, ~입니까?") 대신 **제안형 보고체**로 서술하십시오.]
   - *포인트 1: [구체적인 문제점]에 대해 [구체적인 근거]를 들어 장관의 책임을 추궁할 것을 제안함.*
   - *포인트 2: [정부의 미온적 태도]를 비판하고, [구체적인 대안]을 마련하여 [언제까지] 보고하라고 요구할 것을 권고함.*
   
   **[예상 반박 및 재반박 논리]** (예측 가능한 경우에만 작성)
   - *측 답변 예상: [장관이나 부처가 내세울 것으로 예상되는 방어 논리나 핑계]*
   - *재반박 논리: [이에 대해 구체적인 수치나 과거 발언, 회의록 등을 근거로 반박할 논리]*

   **[회의록 팩트체크]** (회의록에 관련 내용이 있을 경우에만 작성)
   [첨부된 회의록 내용을 바탕으로, 과거 발언과 현재 상황의 모순점이나 약속 불이행 여부를 지적합니다.]
   - **필수 포함 항목**: 해당 발언이 나온 **구체적인 파일명 및 페이지 번호**, 그리고 **발언 내용 원문**을 인용하십시오.
   - *예시: "2025년 11월 17일 회의록 (p. 23)에서 김철수 차관은 '예산 100억 원 증액을 기재부와 합의했다'고 발언했으나, 현재 예산안에는 반영되지 않음"*
   - *예시: "2024년 국정감사 회의록 (p. 105)에서 장관은 '즉각적인 감사 착수'를 약속했으나, 1년이 지난 지금까지 결과 보고가 없음"*

3. **Ⅲ. 단신 및 일정 보고**
   - 주요 정책 발표, 놓쳐선 안 될 행사나 공모 일정 등을 간략히 정리합니다.
   - 각 항목 끝에 링크 `<sup><a href="URL" target="_blank">[N]</a></sup>` 첨부.

[수집된 데이터]
{news_summary}

위 데이터를 바탕으로 최고의 문체위 현안 질의 참고용 심층 보고서를 작성해주십시오.
"""
        return prompt