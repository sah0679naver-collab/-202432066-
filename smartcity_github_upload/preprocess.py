import geopandas as gpd
import pandas as pd
import numpy as np
import json
import re
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import dijkstra
from pathlib import Path

# Paths
WORKSPACE = Path(r"c:\Users\ra068\OneDrive\바탕 화면\스시론 기말")
RAW_DATA = WORKSPACE / "raw_data"
SUBWAY_DIR = RAW_DATA / "subway_network"
PANGYO_DIR = WORKSPACE / "Prom_dataset_spatial"
CHEONGNA_DIR = WORKSPACE / "청라 건물"

POPULATION_DIR = WORKSPACE / "인구 및 종사자 수"

DATA_OUT = WORKSPACE / "smartcity_analysis_project" / "data"
DATA_OUT.mkdir(parents=True, exist_ok=True)

# Administrative Dong (HJD) to representative subway station mappings
bundang_hjd_to_stations = {
    '31023510': ['이매', '서현'], # 분당동
    '31023520': ['수내'], # 수내1동
    '31023530': ['수내'], # 수내2동
    '31023540': ['수내'], # 수내3동
    '31023550': ['정자'], # 정자1동
    '31023560': ['정자'], # 정자2동
    '31023570': ['서현'], # 서현1동
    '31023580': ['서현'], # 서현2동
    '31023590': ['이매'], # 이매1동
    '31023600': ['이매'], # 이매2동
    '31023610': ['야탑'], # 야탑1동
    '31023620': ['야탑'], # 야탑2동
    '31023630': ['야탑'], # 야탑3동
    '31023640': ['미금'], # 금곡동
    '31023650': ['오리'], # 구미동
    '31023660': ['판교'], # 판교동
    '31023670': ['판교'], # 삼평동
    '31023680': ['판교'], # 백현동
    '31023690': ['판교'], # 운중동
    '31023700': ['정자'], # 정자3동
    '31023710': ['오리']  # 구미1동
}

seogu_hjd_to_stations = {
    '23080510': ['검암'], # 검암경서동
    '23080520': ['서구청', '아시아드경기장'], # 연희동
    '23080531': ['가정', '가정중앙시장'], # 가정1동
    '23080541': ['가정'], # 가정2동
    '23080550': ['가정'], # 가정3동
    '23080560': ['석남'], # 신현원창동
    '23080580': ['석남'], # 석남1동
    '23080590': ['석남'], # 석남2동
    '23080600': ['석남'], # 석남3동
    '23080610': ['가정'], # 청라1동
    '23080620': ['청라국제도시'], # 청라2동
    '23080630': ['청라국제도시'], # 청라3동
    '23080640': ['청라국제도시', '가정'], # 청라동 (기존 코드)
    '23080650': ['인천가좌'], # 가좌1동
    '23080660': ['인천가좌'], # 가좌2동
    '23080670': ['가재울'], # 가좌3동
    '23080680': ['가재울'], # 가좌4동
    '23080710': ['검단사거리'], # 검단동
    '23080720': ['검단사거리'], # 불로대곡동
    '23080730': ['완정'], # 원당동
    '23080740': ['완정'], # 당하동
    '23080750': ['검단오류', '왕길'], # 오류왕길동
    '23080760': ['마전'], # 마전동
    '23080770': ['독정'], # 아라동 (아라역 인근)
    '23080780': ['아라'], # 아라동
    '23080790': ['완정'], # 원당동
    '23080800': ['독정'], # 당하동
    '23080810': ['마전'], # 마전동
    '23080840': ['검단오류', '왕길'], # 오류왕길동
    '23080850': ['검단사거리'], # 검단동
    '23080860': ['검단사거리'], # 불로대곡동
    '23080870': ['완정'], # 원당동
    '23080880': ['완정'] # 당하동
}

def clean_use_category(use_nm):
    if not isinstance(use_nm, str) or pd.isna(use_nm):
        return "미개발/공지"
    use_nm = use_nm.strip()
    if "공동주택" in use_nm or "단독주택" in use_nm or "주거" in use_nm:
        return "주거용"
    elif "업무시설" in use_nm or "업무" in use_nm:
        return "업무용"
    elif "근린생활시설" in use_nm or "판매시설" in use_nm or "상업" in use_nm or "숙박시설" in use_nm or "위락시설" in use_nm:
        return "상업/근생"
    elif "교육연구시설" in use_nm or "연구소" in use_nm or "문화및집회시설" in use_nm or "의료시설" in use_nm:
        return "연구/교육/의료"
    elif "공장" in use_nm or "창고" in use_nm or "지식산업센터" in use_nm:
        return "공업/지식산업"
    else:
        return "기타"

def calculate_entropy(df):
    total_area = df['tot_fl_ar'].sum()
    if total_area == 0:
        return 0
    grouped = df.groupby('use_cat')['tot_fl_ar'].sum()
    proportions = grouped / total_area
    entropy = 0
    N = len(proportions)
    if N <= 1:
        return 0
    for p in proportions:
        if p > 0:
            entropy -= p * np.log(p)
    return entropy / np.log(N)

def save_geojson_safely(gdf, path):
    with open(path, 'w', encoding='utf-8') as f:
        f.write(gdf.to_json())

def process_gis():
    print("Processing GIS boundaries and buildings...")
    
    # 1. Pangyo boundary
    pangyo_b = gpd.read_file(PANGYO_DIR / "01_구역계" / "구역계.shp", encoding='cp949')
    pangyo_b_wgs84 = pangyo_b.to_crs(epsg=4326)
    save_geojson_safely(pangyo_b_wgs84, DATA_OUT / "pangyo_boundary.json")
    
    # 2. Cheongna boundary
    cheongna_b = gpd.read_file(CHEONGNA_DIR / "01_구역계" / "구역계.shp", encoding='cp949')
    cheongna_b_wgs84 = cheongna_b.to_crs(epsg=4326)
    save_geojson_safely(cheongna_b_wgs84, DATA_OUT / "cheongna_boundary.json")
    
    # 3. Pangyo buildings — 건축물대장.shp는 이미 판교 지역으로 추출된 데이터이므로 전체 사용
    p_bld = gpd.read_file(PANGYO_DIR / "03_토지건축물정보" / "건축물대장.shp", encoding='cp949')
    for col in p_bld.columns:
        if isinstance(p_bld[col].dtype, pd.StringDtype):
            p_bld[col] = p_bld[col].astype(object)
    p_bld['use_cat'] = p_bld['mn_use_nm'].apply(clean_use_category)
    p_bld_wgs84 = p_bld.to_crs(epsg=4326)
    # 구역계(점선) 내부의 건물만 남기기 위해 공간 결합(sjoin) 수행
    p_bld_wgs84 = gpd.sjoin(p_bld_wgs84, pangyo_b_wgs84[['geometry']], how='inner', predicate='intersects').drop(columns=['index_right'], errors='ignore')
    
    bld_cols = ['bd_nm', 'mn_use_nm', 'use_cat', 'tot_fl_ar', 'fl_ar_ratio', 'gr_fl_num', 'ugr_fl_num', 'geometry']
    p_bld_wgs84 = p_bld_wgs84[bld_cols]
    save_geojson_safely(p_bld_wgs84, DATA_OUT / "pangyo_buildings.json")
    
    # Update p_bld for stats calculation to match the clipped data
    p_bld = p_bld_wgs84
    
    # 4. Cheongna buildings — 건축물대장.shp는 이미 청라 지역으로 추출된 데이터이므로 전체 사용
    c_bld = gpd.read_file(CHEONGNA_DIR / "03_토지건축물정보" / "건축물대장.shp", encoding='cp949')
    for col in c_bld.columns:
        if isinstance(c_bld[col].dtype, pd.StringDtype):
            c_bld[col] = c_bld[col].astype(object)
    c_bld['use_cat'] = c_bld['mn_use_nm'].apply(clean_use_category)
    c_bld_wgs84 = c_bld.to_crs(epsg=4326)
    
    # 구역계(점선) 내부의 건물만 남기기 위해 공간 결합(sjoin) 수행
    c_bld_wgs84 = gpd.sjoin(c_bld_wgs84, cheongna_b_wgs84[['geometry']], how='inner', predicate='intersects').drop(columns=['index_right'], errors='ignore')
    
    print(f"Cheongna buildings after boundary filter: {len(c_bld_wgs84)}")
    c_bld_wgs84 = c_bld_wgs84[bld_cols]
    save_geojson_safely(c_bld_wgs84, DATA_OUT / "cheongna_buildings.json")
    
    # Update c_bld for stats calculation to match the clipped data
    c_bld = c_bld_wgs84
    
    # 5. Compute Land Use stats from ALL buildings in each dataset
    print("Calculating land use statistics...")
    p_total_floor = float(p_bld['tot_fl_ar'].sum())
    p_ratios = {}
    if p_total_floor > 0:
        p_ratios = {k: float(v) for k, v in (p_bld.groupby('use_cat')['tot_fl_ar'].sum() / p_total_floor).to_dict().items()}
        
    pangyo_stats = {
        'total_buildings': int(len(p_bld)),
        'total_floor_area': p_total_floor,
        'mean_far': float(p_bld['fl_ar_ratio'].mean()),
        'entropy_index': float(calculate_entropy(p_bld)),
        'usage_ratios': p_ratios
    }
    
    c_total_floor = float(c_bld['tot_fl_ar'].sum())
    c_ratios = {}
    if c_total_floor > 0:
        c_ratios = {k: float(v) for k, v in (c_bld.groupby('use_cat')['tot_fl_ar'].sum() / c_total_floor).to_dict().items()}
        
    cheongna_stats = {
        'total_buildings': int(len(c_bld)),
        'total_floor_area': c_total_floor,
        'mean_far': float(c_bld['fl_ar_ratio'].mean()),
        'entropy_index': float(calculate_entropy(c_bld)),
        'usage_ratios': c_ratios
    }
    
    with open(DATA_OUT / "landuse_stats.json", "w", encoding="utf-8") as f:
        json.dump({'pangyo': pangyo_stats, 'cheongna': cheongna_stats}, f, ensure_ascii=False, indent=2)

def load_census_population(csv_path):
    df = pd.read_csv(csv_path, header=None, encoding='utf-8-sig')
    df.columns = ['year', 'code', 'var', 'val']
    df_pop = df[df['var'] == 'to_in_001'].copy()
    df_pop['hjd'] = df_pop['code'].astype(str).str[:8]
    df_pop['val'] = pd.to_numeric(df_pop['val'], errors='coerce').fillna(0)
    return df_pop.groupby('hjd')['val'].sum().to_dict()

def load_census_workers(csv_path):
    df = pd.read_csv(csv_path, header=None, encoding='utf-8-sig')
    df.columns = ['year', 'code', 'var', 'val']
    df['hjd'] = df['code'].astype(str).str[:8]
    df['val'] = pd.to_numeric(df['val'], errors='coerce').fillna(0)
    return df.groupby('hjd')['val'].sum().to_dict()

def process_accessibility():
    print("Processing subway networks and travel times...")
    
    nodes = pd.read_csv(SUBWAY_DIR / "network" / "nodes.tsv", sep="\t")
    links = pd.read_csv(SUBWAY_DIR / "network" / "links.tsv", sep="\t")
    
    V = len(nodes)
    u = links['fromNode'].to_numpy()
    v = links['toNode'].to_numpy()
    src = np.concatenate([u, v])
    dst = np.concatenate([v, u])
    cost = np.concatenate([links['timeFT'].to_numpy(), links['timeTF'].to_numpy()]).astype(np.float32)
    A = csr_matrix((cost, (src, dst)), shape=(V, V))
    
    pangyo_nodes = nodes[nodes['statnm'] == '판교']['id'].tolist()
    cheongna_nodes = nodes[nodes['statnm'] == '청라국제도시']['id'].tolist()
    
    print(f"Pangyo station node IDs: {pangyo_nodes}")
    print(f"Cheongna station node IDs: {cheongna_nodes}")
    
    p_start_node = int(pangyo_nodes[0])
    c_start_node = int(cheongna_nodes[0])
    
    p_dist = dijkstra(A, indices=p_start_node)
    c_dist = dijkstra(A, indices=c_start_node)
    
    # --- NEW SPATIAL JOIN LOGIC ---
    import urllib.request
    geojson_path = WORKSPACE / "HangJeongDong_ver20230701.geojson"
    if not geojson_path.exists():
        print("Downloading HJD GeoJSON...")
        url = 'https://raw.githubusercontent.com/vuski/admdongkor/master/ver20230701/HangJeongDong_ver20230701.geojson'
        urllib.request.urlretrieve(url, geojson_path)
    
    print("Loading HJD polygons for Spatial Join...")
    hjd_gdf = gpd.read_file(geojson_path)
    
    # Create GeoDataFrame for stations
    nodes_gdf = gpd.GeoDataFrame(
        nodes, 
        geometry=gpd.points_from_xy(nodes['lng'], nodes['lat']),
        crs="EPSG:4326"
    )
    
    # Reproject to match (if needed)
    if hjd_gdf.crs != "EPSG:4326":
        hjd_gdf = hjd_gdf.to_crs(epsg=4326)
        
    print("Performing Spatial Join: Stations to HJD...")
    joined_nodes = gpd.sjoin(nodes_gdf, hjd_gdf[['adm_cd8', 'geometry']], how='left', predicate='within')
    
    # Map station ID to its matched HJD code
    node_to_hjd = joined_nodes.set_index('id')['adm_cd8'].to_dict()
    
    # Find all nodes that fall into each HJD
    hjd_to_nodes = {}
    for node_id, hjd in node_to_hjd.items():
        if pd.isna(hjd): continue
        hjd_to_nodes.setdefault(str(hjd), []).append(node_id)
        
    print("Loading Census Data (Seoul, Gyeonggi, Seo-gu)...")
    NEW_POP_DIR = WORKSPACE / "서울 경기 인구 및 종사자"
    
    # Population
    pop_bundang = load_census_population(POPULATION_DIR / "31023_2023년_인구총괄(총인구).csv") # Keep for total comparison if needed
    pop_seogu = load_census_population(POPULATION_DIR / "23080_2023년_인구총괄(총인구).csv")
    pop_seoul = load_census_population(NEW_POP_DIR / "11_2023년_인구총괄(총인구).csv")
    pop_gg = load_census_population(NEW_POP_DIR / "31_2023년_인구총괄(총인구).csv")
    
    pop_all = {**pop_seoul, **pop_gg, **pop_seogu}
    
    # Workers
    worker_bundang = load_census_workers(POPULATION_DIR / "31023_2023년_산업분류별(10차_중분류)_종사자수.csv")
    worker_seogu = load_census_workers(POPULATION_DIR / "23080_2023년_산업분류별(10차_중분류)_종사자수.csv")
    worker_seoul = load_census_workers(NEW_POP_DIR / "11_2023년_산업분류별(10차_중분류)_종사자수.csv")
    worker_gg = load_census_workers(NEW_POP_DIR / "31_2023년_산업분류별(10차_중분류)_종사자수.csv")
    
    worker_all = {**worker_seoul, **worker_gg, **worker_seogu}
    
    node_pops = np.zeros(V)
    node_workers = np.zeros(V)
    
    for hjd, pop in pop_all.items():
        node_list = hjd_to_nodes.get(hjd, [])
        if len(node_list) > 0:
            for n in node_list:
                node_pops[n] += pop / len(node_list)
                
    for hjd, worker in worker_all.items():
        node_list = hjd_to_nodes.get(hjd, [])
        if len(node_list) > 0:
            for n in node_list:
                node_workers[n] += worker / len(node_list)
    # --- END NEW SPATIAL JOIN LOGIC ---

    time_thresholds = np.arange(0, 3601, 300) # 0 to 60 mins in 5-min steps
    
    pangyo_curve = []
    cheongna_curve = []
    
    for t in time_thresholds:
        p_reachable = np.where(p_dist <= t)[0]
        c_reachable = np.where(c_dist <= t)[0]
        
        pangyo_curve.append({
            'time_min': int(t / 60),
            'pop': float(node_pops[p_reachable].sum()),
            'worker': float(node_workers[p_reachable].sum()),
            'stations_reached': int(len(set(nodes.iloc[p_reachable]['statnm'])))
        })
        
        cheongna_curve.append({
            'time_min': int(t / 60),
            'pop': float(node_pops[c_reachable].sum()),
            'worker': float(node_workers[c_reachable].sum()),
            'stations_reached': int(len(set(nodes.iloc[c_reachable]['statnm'])))
        })
        
    pangyo_stations_reached = []
    for idx, row in nodes.iterrows():
        d = p_dist[row['id']]
        if d < 7200:
            pangyo_stations_reached.append({
                'statnm': row['statnm'],
                'linenm': row['linenm'],
                'lng': float(row['lng']),
                'lat': float(row['lat']),
                'time_sec': float(d) if d != np.inf else -1
            })
            
    cheongna_stations_reached = []
    for idx, row in nodes.iterrows():
        d = c_dist[row['id']]
        if d < 7200:
            cheongna_stations_reached.append({
                'statnm': row['statnm'],
                'linenm': row['linenm'],
                'lng': float(row['lng']),
                'lat': float(row['lat']),
                'time_sec': float(d) if d != np.inf else -1
            })
            
    with open(DATA_OUT / "access_stats.json", "w", encoding="utf-8") as f:
        json.dump({
            'pangyo': {
                'total_pop': float(sum(pop_bundang.values())),
                'total_worker': float(sum(worker_bundang.values())),
                'curve': pangyo_curve,
                'stations': pangyo_stations_reached
            },
            'cheongna': {
                'total_pop': float(sum(pop_seogu.values())),
                'total_worker': float(sum(worker_seogu.values())),
                'curve': cheongna_curve,
                'stations': cheongna_stations_reached
            }
        }, f, ensure_ascii=False, indent=2)

def main():
    print("Starting preprocessing...")
    process_gis()
    process_accessibility()
    print("Preprocessing completed successfully!")

if __name__ == "__main__":
    main()
