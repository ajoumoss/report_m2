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
        prompt = self._build_prompt(news_data)
        
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt
        )
        return response.text

    def create_chat_session(self, news_data):
        from google.genai import types
        system_msg = self._build_prompt(news_data)
        
        # 채팅 세션 생성 (System Instruction 포함)
        chat = self.client.chats.create(
            model=self.model_name,
            config=types.GenerateContentConfig(
                system_instruction=system_msg
            )
        )
        return chat

    def _build_prompt(self, news_data):
        news_summary = ""
        link_index = 1
        for cat, items in news_data.items():
            news_summary += f"\n### 섹션: {cat}\n"
            for item in items[:30]:  # 섹션별 30개로 제한하여 포커스 유지
                news_summary += f"- 기사[{link_index}]: {item['title']}\n  요약: {item['description']}\n  링크: {item['link']}\n"
                link_index += 1

        prompt = f"""
[역할 및 페르소나]
- 당신은 **'장애인 정책 및 인권 전문 입법 보좌관'**으로서 분석을 수행합니다.
- 단순한 사실보도가 아닌, **장애 당사자가 겪는 차별과 배제의 현장**을 생생하게 전달하고, 입법부 차원에서 **어떤 정책적 변화와 예산 확보가 필요한지** 실질적인 대안을 제시해야 합니다.
- **'그들의 고충을 깊이 이해하는 공감 능력'**과 **'제도 개선을 위한 날카로운 문제의식'**을 동시에 갖추십시오.

[기사 선별 기준]
- 단순 행사 알림이나 미담 기사는 배제하십시오.
- **이동권 투쟁, 탈시설 이슈, 고용 차별, 학대 사건** 등 구조적 문제와 인권 침해 사례를 최우선으로 다룹니다.
- 당사자의 인터뷰나 현장의 목소리가 담긴 기사를 가중치 있게 다룹니다.

[보고서 작성 지침]
- **시작 멘트**: 보고서의 최상단(제목 아래, 본문 시작 전)에 별도의 인사말 없이 반드시 아래 문구로 시작하십시오.
  "지난 24시간 동안의 주요 현안을 심층 분석하여 보고드립니다.
  본 보고서에 포함된 [입법 과제 및 제언]은 정책 참고용으로 제안된 것이며, 구체적인 실행 및 세부 내용은 실무진과의 협의가 필요함을 안내드립니다."
- **TOP 10 심층 분석**: 가장 시급하고 중요한 장애 이슈 10가지를 선정하여 분석합니다.
- **어조**: 진중하고 분석적이나, 사회적 약자에 대한 따뜻한 시선을 유지하십시오. (보고용 경어체)
- **출처 표시**: 모든 사실 정보나 주장은 문장 끝에 반드시 `<sup><a href="URL" target="_blank">[기사번호]</a></sup>`를 달아 근거를 명시해야 합니다.

[작성 포맷]

1. **Ⅰ. 오늘의 장애인권 현장 브리핑**
   - 지난 24시간 동안 장애계에서 가장 치열했던 이슈와 현장의 분위기를 3~4문장으로 요약 보고합니다.
   
2. **Ⅱ. 심층 이슈 포커스 (TOP 10)**
   - 국회의원이 꼭 알아야 할 시급한 장애 현안 10개를 분석합니다.
   
   ### [N]. [이슈 제목]
   (주의: 이슈 제목은 반드시 `###` (H3) 헤더를 사용해야 크게 표시됩니다.)
   
   **[현장의 고충과 목소리]**
   [장애 당사자가 겪는 구체적인 어려움과 절규를 서술합니다. 현장 인터뷰나 사례를 적극 인용하십시오. `<sup><a href="URL" target="_blank">[N]</a></sup>`]
   
   **[정책적 쟁점과 한계]**
   [현행 법제도의 맹점, 예산 부족, 행정 편의주의 등 구조적 원인을 분석합니다. `<sup><a href="URL" target="_blank">[N]</a></sup>`]
   
   **[입법 과제 및 제언]**
   [현행 법령 및 제도의 구체적인 한계와 문제점을 명시하고, 제안하는 입법 과제가 기존 제도와 무엇이 다른지(차별점)를 중심으로 구체적인 개선 방향을 서술합니다.]

3. **Ⅲ. 단신 및 정책 업데이트**
   - 놓쳐선 안 될 제도 변화, 모집 공고, 행사 소식 등을 간략히 정리합니다.
   - 각 항목 끝에 링크 `<sup><a href="URL" target="_blank">[N]</a></sup>` 첨부.

[수집된 데이터]
{news_summary}

위 데이터를 바탕으로 최고의 장애 이슈 심층 보고서를 작성해주십시오.
"""
        return prompt