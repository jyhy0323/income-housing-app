# -*- coding: utf-8 -*-
"""
data_processor.py
국세청 근로소득 데이터(XLSX)와 한국부동산원 매매가격지수(CSV)를 통합 분석하는 전국 시·군·구 엔진
"""

import os
import glob
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

PROVINCES = [
    '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
    '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'
]

def get_data_files():
    xlsx_files = glob.glob(os.path.join(DATA_DIR, '*.xlsx'))
    csv_files = glob.glob(os.path.join(DATA_DIR, '*.csv'))
    
    if not xlsx_files or not csv_files:
        raise FileNotFoundError("data 폴더에 .xlsx 또는 .csv 파일이 존재하지 않습니다.")
        
    return xlsx_files[0], csv_files[0]

def parse_income_data(xlsx_path):
    """
    국세청 전국 시·군·구 근로소득 데이터 파싱
    전국 평균 연봉(100 기준점) 및 각 시군구별 1인당 평균 연봉 산출
    """
    df_raw = pd.read_excel(xlsx_path, header=None)
    
    # 3번 행: 전국 전체 합계
    nat_workers = float(str(df_raw.iloc[3, 1]).replace(',', ''))
    nat_amount = float(str(df_raw.iloc[3, 2]).replace(',', '')) # 백만원
    nat_avg_won = (nat_amount * 1_000_000) / nat_workers
    nat_avg_manwon = round(nat_avg_won / 10_000, 1)
    
    income_map = {}
    current_sido = '서울'
    
    for i in range(4, len(df_raw)):
        name = str(df_raw.iloc[i, 0]).strip()
        try:
            w_str = str(df_raw.iloc[i, 1]).replace(',', '')
            a_str = str(df_raw.iloc[i, 2]).replace(',', '')
            w = float(w_str)
            a = float(a_str)
        except (ValueError, TypeError):
            continue
            
        avg_won = (a * 1_000_000) / w
        avg_manwon = round(avg_won / 10_000, 1)
        income_index = round((avg_won / nat_avg_won) * 100, 2)
        
        if name in PROVINCES:
            current_sido = name
        else:
            income_map[(current_sido, name)] = {
                'sido': current_sido,
                'name': name,
                'workers': int(w),
                'total_amount_mil': int(a),
                'avg_income_won': round(avg_won),
                'avg_income_manwon': avg_manwon,
                'income_index': income_index # 전국 100 기준
            }
            
    return {
        'nat_avg_manwon': nat_avg_manwon,
        'nat_workers': int(nat_workers),
        'income_map': income_map
    }

def load_and_analyze(housing_type='아파트', target_sido='전체'):
    """
    전국 시·군·구 소득과 부동산 가격지수 매칭 및 분석
    """
    xlsx_path, csv_path = get_data_files()
    inc_res = parse_income_data(xlsx_path)
    income_map = inc_res['income_map']
    nat_avg_manwon = inc_res['nat_avg_manwon']
    
    # 부동산 가격지수 CSV 로드
    df_price = pd.read_csv(csv_path, encoding='cp949')
    available_types = df_price['주택유형별(1)'].unique().tolist()
    if housing_type not in available_types:
        housing_type = available_types[0] if available_types else '아파트'
        
    df_filtered = df_price[df_price['주택유형별(1)'] == housing_type]
    
    # 전국 전체 가격지수 벤치마크
    nat_row = df_filtered[(df_filtered['지역별(1)'] == '전국') & (df_filtered['지역별(2)'] == '소계')]
    nat_p_latest = float(nat_row['2026.09'].values[0]) if not nat_row.empty else 100.98
    nat_p_base = float(nat_row['2026.04'].values[0]) if not nat_row.empty else 99.46
    nat_growth = round(((nat_p_latest - nat_p_base) / nat_p_base) * 100, 2)
    
    matched_list = []
    
    for _, row in df_filtered.iterrows():
        sido_p = str(row['지역별(1)']).strip()
        r2 = str(row['지역별(2)']).strip()
        r3 = str(row['지역별(3)']).strip()
        r4 = str(row['지역별(4)']).strip()
        
        # 권역 총계 제외
        if sido_p in ['전국', '수도권', '지방', '(구)6대광역시', '(구)5대광역시', '5대광역시', '4대광역시', '(구)9개도', '(구)8개도', '8개도', '7개도']:
            continue
            
        # 시도명 통일
        sido = sido_p
        if sido == '전남광주':
            sido = '광주' if '광주' in r2 else '전남'
            
        candidates = []
        if r4 not in ['소계', '-', 'nan']:
            candidates.append(r4)
        if r3 not in ['소계', '-', 'nan']:
            candidates.append(r3)
        if r2 not in ['소계', '-', 'nan'] and '권역' not in r2 and '권' not in r2:
            candidates.append(r2)
            
        match_found = None
        for cand in candidates:
            for (i_sido, i_name), val in income_map.items():
                if (sido == i_sido or sido in i_sido or i_sido in sido):
                    # 명칭 대조 (예: 과천 == 과천시, 강남 == 강남구, 중 == 중구)
                    if cand == i_name or cand in i_name or i_name in cand or cand + '구' == i_name or cand + '시' == i_name or cand + '군' == i_name:
                        match_found = val
                        break
            if match_found:
                break
                
        if match_found:
            try:
                p_base = float(row['2026.04'])
                p_latest = float(row['2026.09'])
                growth_rate = round(((p_latest - p_base) / p_base) * 100, 2)
                
                # 주거부담 괴리율 (소득지수 대비 가격지수 비율, 전국=100)
                mismatch_ratio = round((p_latest / match_found['income_index']) * 100, 2)
                full_name = f"{match_found['sido']} {match_found['name']}"
                
                # 4분면 분류 (전국 소득 100 기준, 전국 가격상승률 기준)
                is_high_income = match_found['income_index'] >= 100
                is_high_growth = growth_rate >= nat_growth
                
                if is_high_income and not is_high_growth:
                    quadrant = "Q1_프리미엄안정"
                    quadrant_label = "자산집중·지수안정 (초고소득 거주지)"
                elif not is_high_income and is_high_growth:
                    quadrant = "Q2_주거부담경보"
                    quadrant_label = "소득대비 지수급등 (서민 주거부담 과중)"
                elif not is_high_income and not is_high_growth:
                    quadrant = "Q3_서민안정"
                    quadrant_label = "소득·가격 동반안정 (외곽 실속 주거지)"
                else:
                    quadrant = "Q4_신흥성장"
                    quadrant_label = "소득·가격 동반성장 (신흥 가치 상승지)"
                    
                matched_list.append({
                    'full_name': full_name,
                    'sido': match_found['sido'],
                    'name': match_found['name'],
                    'avg_income_manwon': match_found['avg_income_manwon'],
                    'income_index': match_found['income_index'],
                    'price_index_base': p_base,
                    'price_index_latest': p_latest,
                    'growth_rate': growth_rate,
                    'mismatch_ratio': mismatch_ratio,
                    'quadrant': quadrant,
                    'quadrant_label': quadrant_label,
                    'workers': match_found['workers']
                })
            except Exception:
                continue

    # 중복 제거 (단일 지역 최적값 유지)
    seen = set()
    unique_list = []
    for item in matched_list:
        if item['full_name'] not in seen:
            seen.add(item['full_name'])
            unique_list.append(item)
            
    # 전국 전체 소득 순위 부여
    unique_list.sort(key=lambda x: x['avg_income_manwon'], reverse=True)
    for rank, item in enumerate(unique_list, 1):
        item['nat_income_rank'] = rank
        
    # 시도 필터링
    available_sidos = ['전체'] + [s for s in PROVINCES if any(d['sido'] == s for d in unique_list)]
    
    filtered_list = unique_list
    if target_sido and target_sido != '전체':
        filtered_list = [d for d in unique_list if d['sido'] == target_sido]
        
    return {
        'housing_type': housing_type,
        'target_sido': target_sido,
        'available_types': available_types,
        'available_sidos': available_sidos,
        'nat_summary': {
            'avg_income_manwon': nat_avg_manwon,
            'price_index_latest': nat_p_latest,
            'price_growth_rate': nat_growth,
            'total_districts': len(filtered_list),
            'total_nationwide': len(unique_list)
        },
        'districts': filtered_list
    }

if __name__ == '__main__':
    res = load_and_analyze('아파트', '전체')
    print("=== 전국 시군구 데이터 처리 엔진 테스트 ===")
    print(f"전국 평균 연봉: {res['nat_summary']['avg_income_manwon']} 만원")
    print(f"전국 아파트 최근 상승률: {res['nat_summary']['price_growth_rate']}%")
    print(f"매칭된 전국 시군구: {res['nat_summary']['total_nationwide']}개")
    print(f"지원 시도 목록: {res['available_sidos']}")
