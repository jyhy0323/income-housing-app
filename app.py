# -*- coding: utf-8 -*-
"""
app.py
대한민국 전국 시·군·구별 소득 수준 vs 부동산 가격 통계 분석 웹 애플리케이션
Flask 백엔드 + Gemini 3.5 Flash Lite 연동 (전국 시·군·구 지원)
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
    """Gemini AI를 통한 전국 특정 시·군·구 심층 경제 진단 리포트 생성"""
    if not GEMINI_API_KEY:
        return jsonify({
            'status': 'error',
            'message': 'Gemini API 키가 설정되지 않았습니다.'
        }), 500

    req_data = request.get_json() or {}
    full_name = req_data.get('full_name', '서울 강남구')
    housing_type = req_data.get('type', '아파트')
    sido = req_data.get('sido', '전체')

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

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5002))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    logging.info(f"Starting Income & Housing Analyzer on http://127.0.0.1:{port} (debug={debug})...")
    app.run(host='127.0.0.1', port=port, debug=debug)
