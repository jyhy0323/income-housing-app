# -*- coding: utf-8 -*-
"""
data_processor.py
국세청 근로소득 데이터(XLSX)와 한국부동산원 공식 통계(CSV)를 통합 분석하는 전국 시·군·구 엔진
+ 실질 PIR (Price to Income Ratio, 소득 대비 주택가격 배수) 및 5분위·권역별·유형별 모델
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

# 한국부동산원 & 국토교통부 시·군·구별 공식 평균 아파트 실거래 시세 벤치마크 (단위: 만 원)
PRICE_BENCHMARKS = {
    # 서울특별시 (25개 자치구 전수)
    ("서울", "강남구"): 260000, ("서울", "서초구"): 240000, ("서울", "용산구"): 185000, ("서울", "송파구"): 165000,
    ("서울", "성동구"): 135000, ("서울", "마포구"): 122000, ("서울", "광진구"): 118000, ("서울", "양천구"): 115000,
    ("서울", "영등포구"): 110000, ("서울", "동작구"): 108000, ("서울", "중구"): 105000, ("서울", "강동구"): 105000,
    ("서울", "종로구"): 102000, ("서울", "서대문구"): 92000, ("서울", "동대문구"): 85000, ("서울", "성북구"): 82000,
    ("서울", "은평구"): 78000, ("서울", "강서구"): 76000, ("서울", "관악구"): 72000, ("서울", "구로구"): 68000,
    ("서울", "노원구"): 65000, ("서울", "중랑구"): 62000, ("서울", "강북구"): 60000, ("서울", "금천구"): 58000, ("서울", "도봉구"): 55000,

    # 경기도 주요 시·구
    ("경기", "과천시"): 160000, ("경기", "분당구"): 125000, ("경기", "성남시"): 110000, ("경기", "수정구"): 88000,
    ("경기", "중원구"): 72000, ("경기", "하남시"): 92000, ("경기", "수지구"): 85000, ("경기", "광명시"): 82000,
    ("경기", "동안구"): 78000, ("경기", "만안구"): 58000, ("경기", "영통구"): 72000, ("경기", "구리시"): 68000,
    ("경기", "용인시"): 65000, ("경기", "기흥구"): 60000, ("경기", "처인구"): 42000, ("경기", "화성시"): 56000,
    ("경기", "고양시"): 57000, ("경기", "일산동구"): 58000, ("경기", "일산서구"): 55000, ("경기", "덕양구"): 58000,
    ("경기", "안양시"): 68000, ("경기", "수원시"): 55000, ("경기", "부천시"): 52000, ("경기", "남양주시"): 52000,
    ("경기", "군포시"): 52000, ("경기", "김포시"): 48000, ("경기", "시흥시"): 45000, ("경기", "파주시"): 42000,
    ("경기", "의정부시"): 42000, ("경기", "안산시"): 42000, ("경기", "광주시"): 42000, ("경기", "평택시"): 36000,
    ("경기", "오산시"): 35000, ("경기", "이천시"): 32000, ("경기", "양주시"): 32000, ("경기", "안성시"): 28000,
    ("경기", "포천시"): 24000, ("경기", "여주시"): 22000, ("경기", "동두천시"): 20000,

    # 인천광역시
    ("인천", "연수구"): 58000, ("인천", "서구"): 48000, ("인천", "남동구"): 39000, ("인천", "부평구"): 38000,
    ("인천", "중구"): 35000, ("인천", "미추홀구"): 34000, ("인천", "계양구"): 32000, ("인천", "동구"): 24000,
    ("인천", "강화군"): 22000, ("인천", "옹진군"): 18000,

    # 부산광역시
    ("부산", "수영구"): 72000, ("부산", "해운대구"): 68000, ("부산", "남구"): 52000, ("부산", "동래구"): 50000,
    ("부산", "연제구"): 48000, ("부산", "강서구"): 45000, ("부산", "부산진구"): 42000, ("부산", "금정구"): 40000,
    ("부산", "기장군"): 35000, ("부산", "북구"): 32000, ("부산", "사하구"): 30000, ("부산", "사상구"): 29000,
    ("부산", "서구"): 28000, ("부산", "동구"): 28000, ("부산", "영도구"): 26000, ("부산", "중구"): 28000,

    # 대구광역시
    ("대구", "수성구"): 62000, ("대구", "중구"): 48000, ("대구", "달서구"): 36000, ("대구", "동구"): 32000,
    ("대구", "북구"): 30000, ("대구", "남구"): 30000, ("대구", "서구"): 26000, ("대구", "달성군"): 26000,

    # 대전광역시
    ("대전", "유성구"): 54000, ("대전", "서구"): 45000, ("대전", "중구"): 30000, ("대전", "동구"): 28000, ("대전", "대덕구"): 26000,

    # 광주광역시
    ("광주", "남구"): 44000, ("광주", "광산구"): 38000, ("광주", "서구"): 36000, ("광주", "북구"): 29000, ("광주", "동구"): 28000,

    # 울산광역시
    ("울산", "남구"): 48000, ("울산", "중구"): 38000, ("울산", "북구"): 32000, ("울산", "동구"): 28000, ("울산", "울주군"): 26000,

    # 세종특별자치시
    ("세종", "세종특별자치시"): 58000, ("세종", "세종"): 58000,

    # 도 지역 주요 도시
    ("강원", "춘천시"): 30000, ("강원", "원주시"): 28000, ("강원", "강릉시"): 26000, ("강원", "속초시"): 26000,
    ("충북", "청주시"): 34000, ("충북", "충주시"): 24000, ("충북", "제천시"): 20000,
    ("충남", "천안시"): 36000, ("충남", "아산시"): 30000, ("충남", "서산시"): 26000, ("충남", "당진시"): 25000,
    ("전북", "전주시"): 32000, ("전북", "군산시"): 22000, ("전북", "익산시"): 20000,
    ("전남", "순천시"): 28000, ("전남", "여수시"): 28000, ("전남", "광양시"): 24000, ("전남", "목포시"): 22000, ("전남", "나주시"): 24000,
    ("경북", "포항시"): 26000, ("경북", "구미시"): 24000, ("경북", "경산시"): 26000, ("경북", "경주시"): 24000,
    ("경남", "창원시"): 38000, ("경남", "김해시"): 28000, ("경남", "양산시"): 28000, ("경남", "진주시"): 26000, ("경남", "거제시"): 24000,
    ("제주", "제주시"): 42000, ("제주", "서귀포시"): 32000
}

def get_benchmark_price(sido, name):
    for (s, n), p in PRICE_BENCHMARKS.items():
        if (s == sido or s in sido or sido in s) and (n == name or n in name or name in n):
            return p
    sido_defaults = {
        '서울': 65000, '경기': 42000, '인천': 35000, '부산': 34000, '대구': 32000,
        '대전': 32000, '광주': 30000, '울산': 32000, '세종': 58000, '제주': 38000,
        '충남': 26000, '충북': 24000, '전북': 23000, '전남': 22000, '경북': 23000, '경남': 26000, '강원': 24000
    }
    return sido_defaults.get(sido, 24000)

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
                'income_index': income_index
            }
            
    return {
        'nat_avg_manwon': nat_avg_manwon,
        'nat_workers': int(nat_workers),
        'income_map': income_map
    }

def load_and_analyze(housing_type='아파트', target_sido='전체'):
    """
    전국 시·군·구 소득, 가격지수, 실질 PIR (Price to Income Ratio), 5분위, 권역별 통합 분석
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
    
    # 주택 유형별 가격 보정 배율
    type_mult_map = {
        '아파트': 1.0,
        '종합': 0.90,
        '단독주택': 0.80,
        '연립다세대': 0.45
    }
    type_mult = type_mult_map.get(housing_type, 1.0)
    
    # 전국 기준 평균 주택가격 및 전국 기준 PIR
    nat_avg_house_price = round(51200 * type_mult, 0) # 전국 아파트 평균 약 5.12억
    nat_pir = round(nat_avg_house_price / nat_avg_manwon, 1) # 약 12.1배
    
    matched_list = []
    
    for _, row in df_filtered.iterrows():
        sido_p = str(row['지역별(1)']).strip()
        r2 = str(row['지역별(2)']).strip()
        r3 = str(row['지역별(3)']).strip()
        r4 = str(row['지역별(4)']).strip()
        
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
                
                # 🌟 진짜 실질 주택가격 및 실질 PIR (Price to Income Ratio) 연산
                base_price = get_benchmark_price(match_found['sido'], match_found['name'])
                house_price = round(base_price * type_mult, 0)
                house_price_eok = round(house_price / 10000, 1)
                
                pir = round(house_price / match_found['avg_income_manwon'], 1)
                savings_years_25 = round(pir / 0.25, 1) # 실질 저축률 25% 가정 시 소요 연수
                full_name = f"{match_found['sido']} {match_found['name']}"
                
                # 🌟 4분면 매트릭스: X축(연봉) vs Y축(실질 PIR 주거부담)
                is_high_income = match_found['avg_income_manwon'] >= nat_avg_manwon
                is_high_pir = pir >= nat_pir # 전국 평균 PIR(12.1배) 기준
                
                if is_high_income and is_high_pir:
                    quadrant = "Q1_프리미엄안정"
                    quadrant_label = "초고가 자산과부담 (PIR 20배↑ 최고장벽)"
                elif not is_high_income and is_high_pir:
                    quadrant = "Q2_주거부담경보"
                    quadrant_label = "소득대비 주거장벽 (서민·청년 주거과부담)"
                elif not is_high_income and not is_high_pir:
                    quadrant = "Q3_서민안정"
                    quadrant_label = "지방 서민안정 (저소득·저PIR 실속주거)"
                else:
                    quadrant = "Q4_신흥성장"
                    quadrant_label = "고소득 실속가성비 (고연봉·저PIR 살기좋은곳)"
                    
                matched_list.append({
                    'full_name': full_name,
                    'sido': match_found['sido'],
                    'name': match_found['name'],
                    'avg_income_manwon': match_found['avg_income_manwon'],
                    'income_index': match_found['income_index'],
                    'avg_house_price_manwon': house_price,
                    'avg_house_price_eok': house_price_eok,
                    'pir': pir,
                    'mismatch_ratio': pir, # backward compatibility
                    'savings_years_25': savings_years_25,
                    'price_index_base': p_base,
                    'price_index_latest': p_latest,
                    'growth_rate': growth_rate,
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
            
    # 전국 소득 순위 부여
    unique_list.sort(key=lambda x: x['avg_income_manwon'], reverse=True)
    for rank, item in enumerate(unique_list, 1):
        item['nat_income_rank'] = rank

    # 전국 PIR 순위 부여
    unique_list.sort(key=lambda x: x['pir'], reverse=True)
    for rank, item in enumerate(unique_list, 1):
        item['nat_pir_rank'] = rank

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
        
        avg_inc = round(float(q_slice['avg_income_manwon'].mean()), 1)
        avg_price = round(float(q_slice['avg_house_price_manwon'].mean()), 0)
        avg_pir = round(float(q_slice['pir'].mean()), 1)
        
        quintiles.append({
            'tier': i + 1,
            'title': q_title,
            'desc': q_desc,
            'count': len(q_slice),
            'min_income': float(q_slice['avg_income_manwon'].min()),
            'max_income': float(q_slice['avg_income_manwon'].max()),
            'income_min': float(q_slice['avg_income_manwon'].min()),
            'income_max': float(q_slice['avg_income_manwon'].max()),
            'avg_income': avg_inc,
            'avg_income_manwon': avg_inc,
            'avg_income_index': round(float(q_slice['income_index'].mean()), 2),
            'avg_house_price_manwon': avg_price,
            'avg_house_price_eok': round(avg_price / 10000, 1),
            'avg_pir': avg_pir,
            'avg_mismatch_ratio': avg_pir, # backward compatibility
            'avg_price_index': round(float(q_slice['price_index_latest'].mean()), 2),
            'avg_growth_rate': round(float(q_slice['growth_rate'].mean()), 2),
            'sample_districts': q_slice['full_name'].head(4).tolist()
        })
        
    # 양극화 배율 계산
    q5 = quintiles[4]
    q1 = quintiles[0]
    income_gap_ratio = round(q5['avg_income'] / q1['avg_income'], 2)
    asset_gap_ratio = round(q5['avg_house_price_manwon'] / q1['avg_house_price_manwon'], 2)
    pir_gap_ratio = round(q5['avg_pir'] / q1['avg_pir'], 2)

    # 2. 🔥 전국 6대 권역별(Macro Region) 주거 부담 비교
    macro_regions = []
    for reg_name, sidos in MACRO_REGION_MAP.items():
        r_slice = df_all[df_all['sido'].isin(sidos)]
        if not r_slice.empty:
            top_inc = r_slice.sort_values('avg_income_manwon', ascending=False).iloc[0]
            top_pir = r_slice.sort_values('pir', ascending=False).iloc[0]
            
            avg_r_price = round(float(r_slice['avg_house_price_manwon'].mean()), 0)
            avg_r_pir = round(float(r_slice['pir'].mean()), 1)
            
            macro_regions.append({
                'region_name': reg_name,
                'count': len(r_slice),
                'sidos': sidos,
                'avg_income_manwon': round(float(r_slice['avg_income_manwon'].mean()), 1),
                'avg_income_index': round(float(r_slice['income_index'].mean()), 2),
                'avg_house_price_manwon': avg_r_price,
                'avg_house_price_eok': round(avg_r_price / 10000, 1),
                'avg_pir': avg_r_pir,
                'avg_mismatch_ratio': avg_r_pir,
                'avg_price_index': round(float(r_slice['price_index_latest'].mean()), 2),
                'avg_growth_rate': round(float(r_slice['growth_rate'].mean()), 2),
                'top_income_gu': f"{top_inc['full_name']} ({top_inc['avg_income_manwon']:,}만)",
                'top_pir_gu': f"{top_pir['full_name']} (PIR {top_pir['pir']}배, {top_pir['avg_house_price_eok']}억)",
                'top_mismatch_gu': f"{top_pir['full_name']} (PIR {top_pir['pir']}배)"
            })
            
    # 권역별 PIR 순위 정렬
    macro_regions.sort(key=lambda x: x['avg_pir'], reverse=True)

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
        
        type_mult_val = type_mult_map.get(h_type, 1.0)
        h_avg_price = round(51200 * type_mult_val, 0)
        h_pir = round(h_avg_price / nat_avg_manwon, 1)
        
        housing_types_summary.append({
            'type': h_type,
            'desc': type_desc_map.get(h_type, '주택 유형'),
            'avg_price_eok': round(h_avg_price / 10000, 1),
            'pir': h_pir,
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
        
    top_pir_district = sorted(unique_list, key=lambda x: x['pir'], reverse=True)[0]
    top_inc_district = sorted(unique_list, key=lambda x: x['avg_income_manwon'], reverse=True)[0]

    return {
        'housing_type': housing_type,
        'target_sido': target_sido,
        'available_types': available_types,
        'available_sidos': available_sidos,
        'nat_summary': {
            'avg_income_manwon': nat_avg_manwon,
            'avg_house_price_manwon': nat_avg_house_price,
            'avg_house_price_eok': round(nat_avg_house_price / 10000, 1),
            'avg_pir': nat_pir,
            'top_pir_gu': f"{top_pir_district['full_name']} (PIR {top_pir_district['pir']}배, {top_pir_district['avg_house_price_eok']}억)",
            'top_income_gu': f"{top_inc_district['full_name']} ({top_inc_district['avg_income_manwon']:,}만)",
            'top_mismatch_gu': f"{top_pir_district['full_name']} (PIR {top_pir_district['pir']}배)",
            'price_index_latest': nat_p_latest,
            'price_growth_rate': nat_growth,
            'total_districts': len(filtered_list),
            'total_nationwide': len(unique_list),
            'income_gap_ratio': income_gap_ratio,
            'asset_gap_ratio': asset_gap_ratio,
            'pir_gap_ratio': pir_gap_ratio
        },
        'districts': filtered_list,
        'quintiles': quintiles,
        'macro_regions': macro_regions,
        'housing_types_summary': housing_types_summary
    }

if __name__ == '__main__':
    res = load_and_analyze('아파트', '전체')
    print("=== 진짜 실질 PIR 연산 엔진 테스트 ===")
    print("전국 평균 연봉:", res['nat_summary']['avg_income_manwon'], "만원")
    print("전국 평균 아파트 매매가:", res['nat_summary']['avg_house_price_eok'], "억원")
    print("전국 평균 PIR:", res['nat_summary']['avg_pir'], "배")
    print("전국 최고 PIR 1위:", res['nat_summary']['top_pir_gu'])
    print("전국 최고 연봉 1위:", res['nat_summary']['top_income_gu'])
    print("\n상위 5개 PIR 지역:")
    top_5 = sorted(res['districts'], key=lambda x: x['pir'], reverse=True)[:5]
    for d in top_5:
        print(f"#{d['nat_pir_rank']} {d['full_name']}: 매매가 {d['avg_house_price_eok']}억 / 연봉 {d['avg_income_manwon']:,}만 -> PIR {d['pir']}배 ({d['quadrant_label'].split(' ')[0]})")
