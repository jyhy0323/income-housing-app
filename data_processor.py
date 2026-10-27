# -*- coding: utf-8 -*-
"""
data_processor.py
국세청 근로소득 데이터(XLSX)와 한국부동산원 매매가격지수(CSV)를 통합 분석하는 전국 시·군·구 엔진
+ 소득 5분위 계층 분석, 6대 권역별 주거부담 비교, 주택 유형별 자산 양극화 모듈 통합
"""

import os
import glob
import pandas as pd
import numpy as np

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')

PROVINCES = [
    '서울', '부산', '대구', '인천', '광주', '대전', '울산', '세종',
    '경기', '강원', '충북', '충남', '전북', '전남', '경북', '경남', '제주'
]

MACRO_REGION_MAP = {
    '수도권': ['서울', '경기', '인천'],
    '동남권 (부·울·경)': ['부산', '울산', '경남'],
    '대경권 (대구·경북)': ['대구', '경북'],
    '충청권 (대전·세종·충청)': ['대전', '세종', '충북', '충남'],
    '호남권 (광주·전라)': ['광주', '전북', '전남'],
    '강원·제주권': ['강원', '제주']
}

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
    전국 시·군·구 소득, 가격지수, 5분위 분석, 권역별 분석, 주택유형 분석 통합 연산
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
                
                mismatch_ratio = round((p_latest / match_found['income_index']) * 100, 2)
                full_name = f"{match_found['sido']} {match_found['name']}"
                
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

    # 중복 제거
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

    # 1. 🔥 소득 5분위(Quintile) 심층 계층 분석
    df_all = pd.DataFrame(unique_list)
    df_asc = df_all.sort_values(by='avg_income_manwon', ascending=True).reset_index(drop=True)
    q_size = len(df_asc) // 5
    quintiles = []
    
    for i in range(5):
        start = i * q_size
        end = (i + 1) * q_size if i < 4 else len(df_asc)
        q_slice = df_asc.iloc[start:end]
        
        q_name_map = {
            0: ("1분위 (소득 하위 20%)", "저소득 취약 계층"),
            1: ("2분위 (소득 하위 20~40%)", "중하위 서민 계층"),
            2: ("3분위 (중위 40~60%)", "전국 중간 계층"),
            3: ("4분위 (상위 20~40%)", "중상위 소득 계층"),
            4: ("5분위 (소득 상위 20%)", "최상위 고소득 계층")
        }
        q_title, q_desc = q_name_map[i]
        
        quintiles.append({
            'tier': i + 1,
            'title': q_title,
            'desc': q_desc,
            'count': len(q_slice),
            'min_income': float(q_slice['avg_income_manwon'].min()),
            'max_income': float(q_slice['avg_income_manwon'].max()),
            'income_min': float(q_slice['avg_income_manwon'].min()),
            'income_max': float(q_slice['avg_income_manwon'].max()),
            'avg_income': round(float(q_slice['avg_income_manwon'].mean()), 1),
            'avg_income_manwon': round(float(q_slice['avg_income_manwon'].mean()), 1),
            'avg_income_index': round(float(q_slice['income_index'].mean()), 2),
            'avg_price_index': round(float(q_slice['price_index_latest'].mean()), 2),
            'avg_growth_rate': round(float(q_slice['growth_rate'].mean()), 2),
            'avg_mismatch_ratio': round(float(q_slice['mismatch_ratio'].mean()), 2),
            'sample_districts': q_slice['full_name'].head(4).tolist()
        })
        
    # 5분위 배율 (Q5 / Q1)
    q5_inc = quintiles[4]['avg_income']
    q1_inc = quintiles[0]['avg_income']
    income_gap_ratio = round(q5_inc / q1_inc, 2)
    mismatch_gap_ratio = round(quintiles[0]['avg_mismatch_ratio'] / quintiles[4]['avg_mismatch_ratio'], 2)

    # 2. 🔥 전국 6대 권역별(Macro Region) 주거 부담 비교
    macro_regions = []
    for reg_name, sidos in MACRO_REGION_MAP.items():
        r_slice = df_all[df_all['sido'].isin(sidos)]
        if not r_slice.empty:
            top_inc = r_slice.sort_values('avg_income_manwon', ascending=False).iloc[0]
            top_mismatch = r_slice.sort_values('mismatch_ratio', ascending=False).iloc[0]
            
            macro_regions.append({
                'region_name': reg_name,
                'count': len(r_slice),
                'sidos': sidos,
                'avg_income_manwon': round(float(r_slice['avg_income_manwon'].mean()), 1),
                'avg_income_index': round(float(r_slice['income_index'].mean()), 2),
                'avg_price_index': round(float(r_slice['price_index_latest'].mean()), 2),
                'avg_growth_rate': round(float(r_slice['growth_rate'].mean()), 2),
                'avg_mismatch_ratio': round(float(r_slice['mismatch_ratio'].mean()), 2),
                'top_income_gu': f"{top_inc['full_name']} ({top_inc['avg_income_manwon']:,}만)",
                'top_mismatch_gu': f"{top_mismatch['full_name']} ({top_mismatch['mismatch_ratio']}%)"
            })
            
    # 권역별 소득 순위 정렬
    macro_regions.sort(key=lambda x: x['avg_income_manwon'], reverse=True)

    # 3. 🔥 주택 유형별(아파트, 연립다세대, 단독주택, 종합) 전국 비교
    housing_types_summary = []
    for h_type in available_types:
        h_df = df_price[df_price['주택유형별(1)'] == h_type]
        h_nat = h_df[(h_df['지역별(1)'] == '전국') & (h_df['지역별(2)'] == '소계')]
        h_seoul = h_df[(h_df['지역별(1)'] == '서울') & (h_df['지역별(2)'] == '소계')]
        
        if not h_nat.empty:
            nat_base = float(h_nat['2026.04'].values[0])
            nat_latest = float(h_nat['2026.09'].values[0])
            nat_growth = round(((nat_latest - nat_base) / nat_base) * 100, 2)
        else:
            nat_latest, nat_growth = 100.0, 0.0
            
        if not h_seoul.empty:
            seoul_base = float(h_seoul['2026.04'].values[0])
            seoul_latest = float(h_seoul['2026.09'].values[0])
            seoul_growth = round(((seoul_latest - seoul_base) / seoul_base) * 100, 2)
        else:
            seoul_latest, seoul_growth = 100.0, 0.0
            
        type_desc_map = {
            '아파트': '자산 형성 및 선호도가 가장 높은 대표 주거 유형',
            '종합': '아파트, 연립, 단독주택을 총망라한 전 주택 시장 지표',
            '연립다세대': '서민·청년층의 주거 진입 사다리 및 다세대 빌라',
            '단독주택': '단독·다가구 및 전통적 단독 주거 유형'
        }
        
        housing_types_summary.append({
            'type': h_type,
            'desc': type_desc_map.get(h_type, '주택 유형'),
            'nat_latest_index': nat_latest,
            'nat_growth_rate': nat_growth,
            'seoul_latest_index': seoul_latest,
            'seoul_growth_rate': seoul_growth
        })

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
            'total_nationwide': len(unique_list),
            'income_gap_ratio': income_gap_ratio,
            'mismatch_gap_ratio': mismatch_gap_ratio
        },
        'districts': filtered_list,
        'quintiles': quintiles,
        'macro_regions': macro_regions,
        'housing_types_summary': housing_types_summary
    }

if __name__ == '__main__':
    res = load_and_analyze('아파트', '전체')
    print("=== 다차원 분석 데이터 엔진 가동 테스트 ===")
    print(f"5분위 수: {len(res['quintiles'])}개")
    print(f"권역 수: {len(res['macro_regions'])}개")
    print(f"주택유형 수: {len(res['housing_types_summary'])}개")
    print("소득 5분위 배율:", res['nat_summary']['income_gap_ratio'])
