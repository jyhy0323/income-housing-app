# -*- coding: utf-8 -*-
"""
app.py
대한민국 전국 시·군·구별 소득 수준 vs 부동산 가격 통계 분석 웹 애플리케이션
+ 이용자 자유 자연어 질문(Q&A) & AI 맞춤형 표 생성 기능 탑재
"""

import os
import json
import logging
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import google.generativeai as genai
from data_processor import load_and_analyze

# 환경변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

app = Flask(__name__)

# Gemini API 초기화
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
GEMINI_MODEL_NAME = os.getenv('GEMINI_MODEL', 'gemini-3.5-flash-lite')

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    logging.info(f"[INIT] Gemini API 설정 완료 (Model: {GEMINI_MODEL_NAME})")
else:
    logging.warning("[WARN] GEMINI_API_KEY가 설정되지 않았습니다.")

@app.route('/')
def index():
    """메인 대시보드 페이지"""
    return render_template('index.html')

@app.route('/api/data', methods=['GET'])
def get_data():
    """전국 시·군·구 및 시도별 통계 데이터 조회 API"""
    housing_type = request.args.get('type', '아파트')
    sido = request.args.get('sido', '전체')
    try:
        data = load_and_analyze(housing_type, sido)
        return jsonify({
            'status': 'success',
            'data': data
        })
    except Exception as e:
        logging.error(f"[ERROR] 데이터 분석 실패: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/ai-analyze', methods=['POST'])
def ai_analyze():
    """Gemini AI를 통한 특정 시·군·구 심층 경제 진단 리포트 생성"""
    if not GEMINI_API_KEY:
        return jsonify({
            'status': 'error',
            'message': 'Gemini API 키가 설정되지 않았습니다.'
        }), 500

    req_data = request.get_json() or {}
    full_name = req_data.get('full_name', '서울 강남구')
    housing_type = req_data.get('type', '아파트')

    try:
        analysis_data = load_and_analyze(housing_type, '전체')
        nat_summary = analysis_data['nat_summary']
        districts = analysis_data['districts']
        
        target = next((d for d in districts if d['full_name'] == full_name or d['name'] == full_name), None)
        if not target:
            return jsonify({'status': 'error', 'message': f'{full_name} 데이터를 찾을 수 없습니다.'}), 404

        # Gemini 3.5 모델 호출
        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL_NAME,
            generation_config={"response_mime_type": "application/json"}
        )

        prompt = f"""
당신은 대한민국 거시경제 및 국토/부동산 통계 전문가입니다.
국세청 연말정산 공식 근로소득 데이터와 한국부동산원 공식 주택 매매가격지수 통계를 바탕으로,
전국 시·군·구 단위에서 '{target['full_name']}'의 소득 수준과 부동산 가격의 상관관계 및 주거부담 괴리율을 심층 진단해 주세요.

[공식 통계 지표]
1. 분석 대상: {target['full_name']} (주택유형: {housing_type})
2. 근로소득 지표:
   - 1인당 평균 연봉: {target['avg_income_manwon']:,}만 원
   - 대한민국 전국 평균 대비 소득 지수: {target['income_index']} (전국 평균 100 기준, 전국 평균연봉: {nat_summary['avg_income_manwon']:,}만 원)
   - 전국 시·군·구 중 소득 순위: {target['nat_income_rank']}위 / {nat_summary['total_nationwide']}개
3. 부동산 가격지표:
   - 최신 가격지수(2026.09): {target['price_index_latest']}
   - 최근 6개월 가격 상승률: {target['growth_rate']}% (전국 전체 평균 상승률: {nat_summary['price_growth_rate']}%)
4. 융합 진단 지표:
   - 소득 대비 가격지수 괴리율(Mismatch Ratio): {target['mismatch_ratio']}% (100 초과 시 소득 대비 집값 부담/상승 가중)
   - 4분면 특성 분류: {target['quadrant_label']}

반드시 아래 JSON 포맷 규격에 맞춰 한국어로 답변해 주세요:
{{
  "headline": "전국적 관점에서 해당 시·군·구의 경제·부동산 특성을 관통하는 명확하고 학술적인 한 줄 헤드라인",
  "income_summary": "{target['full_name']}의 소득 수준(전국 {target['nat_income_rank']}위)과 수도권/지방 간 소득 격차에 대한 객관적 해석 (2~3문장)",
  "housing_summary": "{housing_type} 가격지수 및 최근 상승률 흐름에 대한 전국 시장 대비 해석 (2~3문장)",
  "mismatch_analysis": "소득 지표와 부동산 지표를 결합했을 때 나타나는 주거부담 및 불균형 괴리율 진단 (2~3문장)",
  "policy_implication": "조별 과제 보고서 및 논문에 바로 인용할 수 있는 학술적/정책적 시사점 (2~3문장)"
}}
"""

        response = model.generate_content(prompt)
        report = json.loads(response.text)

        return jsonify({
            'status': 'success',
            'report': report,
            'stats': target,
            'nat_summary': nat_summary
        })

    except Exception as e:
        logging.error(f"[ERROR] AI 분석 생성 중 오류: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"AI 분석 실패: {str(e)}"
        }), 500

@app.route('/api/chat-query', methods=['POST'])
def chat_query():
    """
    이용자가 입력한 임의의 자연어 질문을 받아 전체 통계 데이터를 분석한 뒤
    서술형 답변 및 맞춤형 결과 표(Table)를 JSON으로 생성
    """
    if not GEMINI_API_KEY:
        return jsonify({
            'status': 'error',
            'message': 'Gemini API 키가 설정되지 않았습니다.'
        }), 500

    req_data = request.get_json() or {}
    question = req_data.get('question', '').strip()
    housing_type = req_data.get('type', '아파트')
    history = req_data.get('history', [])

    if not question:
        return jsonify({'status': 'error', 'message': '질문을 입력해 주세요.'}), 400

    try:
        # 전체 148개 시군구 데이터 로드
        analysis_data = load_and_analyze(housing_type, '전체')
        nat_summary = analysis_data['nat_summary']
        districts = analysis_data['districts']

        # AI에게 전달할 경량 데이터셋 구성
        compact_rows = []
        for d in districts:
            compact_rows.append({
                "rank": d['nat_income_rank'],
                "sido": d['sido'],
                "gu": d['name'],
                "income": d['avg_income_manwon'],
                "income_idx": d['income_index'],
                "price_idx": d['price_index_latest'],
                "growth": d['growth_rate'],
                "mismatch": d['mismatch_ratio'],
                "quad": d['quadrant_label'].split(' ')[0]
            })

        # 이전 대화 맥락 포맷팅
        history_text = ""
        if history and isinstance(history, list):
            history_text = "\n[이전 대화 맥락 (가지 질문 맥락)]\n"
            for h in history[-3:]: # 최근 3회 대화 참조
                history_text += f"- 사용자: {h.get('question', '')}\n"
                history_text += f"- AI 답변 요약: {h.get('answer_snippet', '')}\n"

        model = genai.GenerativeModel(
            model_name=GEMINI_MODEL_NAME,
            generation_config={"response_mime_type": "application/json"}
        )

        prompt = f"""
당신은 대한민국 거시경제 및 국토 통계 전문 AI입니다.
아래 제공된 대한민국 전국 148개 시·군·구의 공식 통계 데이터(국세청 연말정산 1인당 평균 근로소득 및 한국부동산원 주택 가격지수, 괴리율)를 읽고,
사용자의 질문에 데이터 기반으로 정확히 답변하며, 질문과 관련된 데이터들을 추출하여 [맞춤형 결과 표]를 구성해 주세요.
사용자가 답변에 대해 추가적인 '가지 질문(꼬리 질문)'을 던졌다면, 이전 대화 맥락을 충분히 반영하여 심층적으로 답변해 주세요.

[대한민국 전국 공식 통계 데이터 요약]
- 전국 평균 연봉: {nat_summary['avg_income_manwon']:,}만 원 (전국 소득지수 100 기준점)
- 전국 평균 가격지수: {nat_summary['price_index_latest']} (최근 6개월 상승률: +{nat_summary['price_growth_rate']}%)
- 전체 자치구 수: {len(compact_rows)}개
{history_text}
[전체 자치구 148개 데이터셋]
{json.dumps(compact_rows, ensure_ascii=False)}

[사용자의 질문]
"{question}"

[작성 지침]
1. 반드시 실제 데이터셋에 존재하는 수치만을 정확히 인용하세요. 왜곡이나 추정치는 금지합니다.
2. 답변(answer): 질문자의 의도를 정확히 해결하는 명쾌하고 친절한 경제 통계적 해설 (3~5문장).
   - 강남 등 고가 지역의 괴리율이 낮게 나오는 이유에 대해 묻는다면: "부동산원 가격지수(Index, 2021=100)는 실거래 매매가(20~30억)가 아닌 시계열 지표(강남 98.5)이고, 소득지수는 198.9(전국의 약 2배)이므로 수학적으로 (98.5/198.9)*100 = 49.5%로 낮게 계산되는 지표의 통계적 특성"을 친절히 설명해 주세요.
3. 핵심 요약(key_points): 질문과 직결된 핵심 수치 요약 2~3개.
4. 결과 표(table): 질문에 해당하는 지역들을 선별하거나 비교하여 [제목(title)], [열 목록(headers)], [행 데이터(rows)]로 구성하세요.
5. 가지 질문 추천(follow_up_questions): 사용자가 이 답변을 읽고 더 깊이 파고들 수 있는 날카롭고 흥미로운 후속 '가지 질문' 3가지를 제시하세요.

반드시 아래 JSON 스키마 규격으로만 응답해 주세요:
{{
  "answer": "질문에 대한 정확한 데이터 기반 해설 (줄바꿈 가능, 3~5문장)",
  "key_points": [
    "핵심 수치 요약 1",
    "핵심 수치 요약 2"
  ],
  "table": {{
    "title": "추출 및 분석 결과 표 제목 (예: 전국 연봉 5,000만 원 이상 자치구 비교 표)",
    "headers": ["전국순위", "시·도", "시·군·구", "1인당 평균연봉(만원)", "전국대비 소득지수", "가격지수", "최근 상승률", "소득대비 괴리율", "4분면 분류"],
    "rows": [
      ["#1", "서울", "강남구", "8,419.6", "198.89", "98.50", "+0.33%", "49.52%", "자산집중"]
    ]
  }},
  "follow_up_questions": [
    "추천 후속 가지 질문 1 (예: 강남과 부산 중구의 공식 지표 대조 표 보여줘)",
    "추천 후속 가지 질문 2",
    "추천 후속 가지 질문 3"
  ]
}}
"""

        response = model.generate_content(prompt)
        chat_report = json.loads(response.text)

        return jsonify({
            'status': 'success',
            'question': question,
            'result': chat_report,
            'nat_summary': nat_summary
        })

    except Exception as e:
        logging.error(f"[ERROR] AI 질의응답 실패: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': f"AI 질의응답 실패: {str(e)}"
        }), 500

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5002))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    logging.info(f"Starting Income & Housing Analyzer on http://127.0.0.1:{port} (debug={debug})...")
    app.run(host='127.0.0.1', port=port, debug=debug)
