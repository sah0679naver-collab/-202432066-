let map;
let currentRegion = 'pangyo';
let boundaryLayer = null;
let buildingsLayer = null;
let stationMarkersGroup = L.layerGroup();
let isochroneLayer = null;
let highlightMarker = null;

// Core coordinates
const coords = {
  pangyo: { center: [37.40030, 127.10873], zoom: 15 },
  cheongna: { center: [37.51979, 126.62919], zoom: 14 }
};

// Key buildings for quick navigation
const keyBuildings = {
  pangyo: [
    { id: 'ahnlab', name: '안랩 (AhnLab)', coords: [37.40193, 127.11054], info: { bd_nm: "안랩 판교사옥", mn_use_nm: "업무시설", tot_fl_ar: 49830, fl_ar_ratio: 382.4, gr_fl_num: 10, ugr_fl_num: 4 } },
    { id: 'ncsoft', name: '엔씨소프트 R&D센터', coords: [37.40211, 127.11183], info: { bd_nm: "엔씨소프트 R&D센터", mn_use_nm: "업무시설", tot_fl_ar: 88480, fl_ar_ratio: 395.2, gr_fl_num: 12, ugr_fl_num: 5 } },
    { id: 'kakao', name: '카카오 판교오피스', coords: [37.40052, 127.11155], info: { bd_nm: "카카오 판교오피스", mn_use_nm: "업무시설", tot_fl_ar: 62450, fl_ar_ratio: 385.1, gr_fl_num: 10, ugr_fl_num: 4 } }
  ],
  cheongna: [
    { id: 'citytower', name: '청라시티타워 부지', coords: [37.53361, 126.61517], info: { bd_nm: "청라시티타워 부지", mn_use_nm: "관광휴게시설/업무시설", tot_fl_ar: 110230, fl_ar_ratio: 15.2, gr_fl_num: 2, ugr_fl_num: 1 } },
    { id: 'hana', name: '하나금융타운 통합데이터센터', coords: [37.54582, 126.62021], info: { bd_nm: "하나금융그룹 통합데이터센터", mn_use_nm: "업무시설(전산센터)", tot_fl_ar: 65420, fl_ar_ratio: 120.4, gr_fl_num: 7, ugr_fl_num: 2 } },
    { id: 'robot', name: '인천 로봇랜드 로봇타워', coords: [37.51922, 126.58623], info: { bd_nm: "인천로봇랜드 로봇타워", mn_use_nm: "업무시설/공장(지식산업)", tot_fl_ar: 37540, fl_ar_ratio: 180.2, gr_fl_num: 23, ugr_fl_num: 2 } }
  ]
};

// Colors for building categories
const useColors = {
  "주거용": "#10b981",
  "업무용": "#3b82f6",
  "상업/근생": "#ef4444",
  "연구/교육/의료": "#eab308",
  "공업/지식산업": "#8b5cf6",
  "기타": "#64748b",
  "미개발/공지": "#334155"
};

// Global data stores
let landuseStatsData = null;
let accessStatsData = null;
let currentIsoTime = 0;

// Global chart references
let landuseChart = null;
let curveChart = null;

// Initialize app on load
window.addEventListener('DOMContentLoaded', async () => {
  initMap();
  await loadData();
  switchRegion('pangyo');
  renderCurveChart();
});

function initMap() {
  // Initialize map centered on Pangyo
  map = L.map('map', {
    zoomControl: true,
    attributionControl: false
  }).setView(coords.pangyo.center, coords.pangyo.zoom);

  // Add dark base map layer
  L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    maxZoom: 19
  }).addTo(map);
  
  stationMarkersGroup.addTo(map);
}

async function loadData() {
  // Use inline data (embedded in data.js) — no server required
  try {
    landuseStatsData = INLINE_LANDUSE_STATS;
    accessStatsData  = INLINE_ACCESS_STATS;
  } catch (error) {
    console.error('Error loading inline stats data:', error);
  }
}

function switchRegion(region) {
  currentRegion = region;
  
  // Update active tab buttons
  document.getElementById('btn-pangyo').classList.toggle('active', region === 'pangyo');
  document.getElementById('btn-cheongna').classList.toggle('active', region === 'cheongna');
  
  // Show/hide the real spatial data source card (Prom_dataset_spatial)
  const dataCard = document.getElementById('cheongna-data-card');
  if (dataCard) {
    dataCard.style.display = region === 'cheongna' ? 'block' : 'none';
  }
  
  // Update building navigation dropdown options
  const select = document.getElementById('select-building');
  select.innerHTML = '<option value="">-- 건물을 선택하세요 --</option>';
  if (keyBuildings[region]) {
    keyBuildings[region].forEach(bld => {
      const opt = document.createElement('option');
      opt.value = bld.id;
      opt.textContent = bld.name;
      select.appendChild(opt);
    });
  }
  
  // Close attribute popup
  closeBuildingCard();
  
  // Load spatial layers and UI updates
  loadMapLayers(region);
  drawAllIsochrones();
  updateStatsPanel(region);
  
  // Fly to region view
  map.flyTo(coords[region].center, coords[region].zoom);
}

function updateStatsPanel(region) {
  if (!landuseStatsData || !accessStatsData) return;
  
  const lu = landuseStatsData[region];
  const ac = accessStatsData[region];
  
  // Landuse stats
  document.getElementById('val-total-area').textContent = lu.total_floor_area.toLocaleString(undefined, {maximumFractionDigits: 0});
  document.getElementById('val-bld-count').textContent = lu.total_buildings.toLocaleString();
  document.getElementById('val-mean-far').textContent = lu.mean_far.toFixed(1);
  document.getElementById('val-lum-index').textContent = lu.entropy_index.toFixed(3);
  
  // Population & Worker Stats
  document.getElementById('val-total-pop').textContent = ac.total_pop ? ac.total_pop.toLocaleString() : '-';
  document.getElementById('val-total-worker').textContent = ac.total_worker ? ac.total_worker.toLocaleString() : '-';

  // Accessibility stats
  const coreStName = region === 'pangyo' ? '판교역 (신분당선/경강선)' : '청라국제도시역 (공항철도)';
  document.getElementById('val-core-station').textContent = coreStName;
  
  const curve30 = ac.curve.find(c => c.time_min === 30);
  const curve60 = ac.curve.find(c => c.time_min === 60);

  if (curve30) {
    document.getElementById('val-reach-stations-30').textContent = curve30.stations_reached + ' 개역';
    document.getElementById('val-reach-pop-30').textContent = curve30.pop.toLocaleString() + ' 명';
    document.getElementById('val-reach-emp-30').textContent = curve30.worker.toLocaleString() + ' 명';
  } else {
    document.getElementById('val-reach-stations-30').textContent = '-';
    document.getElementById('val-reach-pop-30').textContent = '-';
    document.getElementById('val-reach-emp-30').textContent = '-';
  }
  
  if (curve60) {
    document.getElementById('val-reach-stations-60').textContent = curve60.stations_reached + ' 개역';
    document.getElementById('val-reach-pop-60').textContent = curve60.pop.toLocaleString() + ' 명';
    document.getElementById('val-reach-emp-60').textContent = curve60.worker.toLocaleString() + ' 명';
  } else {
    document.getElementById('val-reach-stations-60').textContent = '-';
    document.getElementById('val-reach-pop-60').textContent = '-';
    document.getElementById('val-reach-emp-60').textContent = '-';
  }
  
  // Update Layer Info Card
  const bndDesc = document.getElementById('layer-desc-boundary');
  const bldDesc = document.getElementById('layer-desc-bld');
  const devDesc = document.getElementById('layer-desc-dev');
  const regDesc = document.getElementById('layer-desc-reg');
  
  if (bndDesc) {
    if (region === 'pangyo') {
      bndDesc.textContent = '판교테크노밸리 (1, 2, 3밸리) 외곽 경계 폴리곤';
      bldDesc.textContent = `${lu.total_buildings.toLocaleString()}동 · 평균용적률 ${lu.mean_far.toFixed(1)}%`;
      devDesc.textContent = '판교일반산업단지 · 판교제로시티';
      regDesc.textContent = '일반산업단지 · 연구개발특구 등';
    } else {
      bndDesc.textContent = '청라국제지구 외곽 경계 폴리곤';
      bldDesc.textContent = `${lu.total_buildings.toLocaleString()}동 · 평균용적률 ${lu.mean_far.toFixed(1)}%`;
      devDesc.textContent = '청라지구 + 청라1산단 포함';
      regDesc.textContent = '일반주거·준주거·상업지역 등';
    }
  }

  // Render Pie Chart
  renderPieChart(lu.usage_ratios);
}

function renderPieChart(ratios) {
  const ctx = document.getElementById('landuse-chart').getContext('2d');
  
  if (landuseChart) {
    landuseChart.destroy();
  }
  
  const labels = Object.keys(ratios);
  const data = Object.values(ratios).map(v => v * 100);
  const colors = labels.map(l => useColors[l] || "#999");
  
  landuseChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: labels,
      datasets: [{
        data: data,
        backgroundColor: colors,
        borderWidth: 1,
        borderColor: '#1e293b'
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return ` ${context.label}: ${context.raw.toFixed(1)}%`;
            }
          }
        }
      },
      cutout: '65%'
    }
  });
}

function renderCurveChart() {
  if (!accessStatsData) {
    setTimeout(renderCurveChart, 200);
    return;
  }
  
  const ctx = document.getElementById('accessibility-curve-chart').getContext('2d');
  const labels = accessStatsData.pangyo.curve.map(c => `${c.time_min}분`);
  
  const pangyoPop = accessStatsData.pangyo.curve.map(c => c.pop);
  const cheongnaPop = accessStatsData.cheongna.curve.map(c => c.pop);
  const pangyoWorker = accessStatsData.pangyo.curve.map(c => c.worker);
  const cheongnaWorker = accessStatsData.cheongna.curve.map(c => c.worker);
  
  curveChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: '판교역 출발 (도달 종사자수)',
          data: pangyoWorker,
          borderColor: varColor('--accent-blue'),
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          fill: false,
          tension: 0.3,
          borderWidth: 2
        },
        {
          label: '청라국제도시역 출발 (도달 종사자수)',
          data: cheongnaWorker,
          borderColor: varColor('--accent-purple'),
          backgroundColor: 'rgba(139, 92, 246, 0.1)',
          fill: false,
          tension: 0.3,
          borderWidth: 2
        },
        {
          label: '판교역 출발 (도달 인구수)',
          data: pangyoPop,
          borderColor: '#10b981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          fill: false,
          borderDash: [5, 5],
          tension: 0.3,
          borderWidth: 1.5
        },
        {
          label: '청라국제도시역 출발 (도달 인구수)',
          data: cheongnaPop,
          borderColor: '#eab308',
          backgroundColor: 'rgba(234, 179, 8, 0.1)',
          fill: false,
          borderDash: [5, 5],
          tension: 0.3,
          borderWidth: 1.5
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: {
            color: '#94a3b8',
            font: { size: 10 }
          }
        }
      },
      scales: {
        x: {
          grid: { color: '#232c43' },
          ticks: { color: '#94a3b8', font: { size: 10 } }
        },
        y: {
          title: {
            display: true,
            text: '누적 인구/종사자 수 (명)',
            color: '#94a3b8',
            font: { size: 10 }
          },
          grid: { color: '#232c43' },
          ticks: { color: '#94a3b8', font: { size: 10 } }
        }
      }
    }
  });
}

function varColor(varName) {
  return getComputedStyle(document.documentElement).getPropertyValue(varName).trim() || varName;
}

async function loadMapLayers(region) {
  // Clear previous layers
  if (boundaryLayer) map.removeLayer(boundaryLayer);
  if (buildingsLayer) map.removeLayer(buildingsLayer);
  
  try {
    // 1. Use inline boundary GeoJSON
    const boundaryGeo = window.data.boundaries[region];
    
    boundaryLayer = L.geoJSON(boundaryGeo, {
      style: {
        color: region === 'pangyo' ? '#3b82f6' : '#8b5cf6',
        weight: 3,
        fillColor: region === 'pangyo' ? '#3b82f6' : '#8b5cf6',
        fillOpacity: 0.05,
        dashArray: '5, 5'
      }
    }).addTo(map);
    
    // 2. Use inline buildings GeoJSON
    if (document.getElementById('toggle-buildings').checked) {
      const buildingsGeo = window.data.buildings[region];
      
      buildingsLayer = L.geoJSON(buildingsGeo, {
        style: function (feature) {
          const cat = feature.properties.use_cat || "기타";
          return {
            color: useColors[cat] || "#64748b",
            weight: 0.8,
            fillColor: useColors[cat] || "#64748b",
            fillOpacity: 0.5
          };
        },
        onEachFeature: function (feature, layer) {
          layer.on('click', function (e) {
            L.DomEvent.stopPropagation(e);
            showBuildingAttributes(feature.properties);
          });
        }
      }).addTo(map);
    }
  } catch (error) {
    console.error('Error loading map layers:', error);
  }
}

function showBuildingAttributes(props) {
  document.getElementById('pop-bld-name').textContent = props.bd_nm || "이름 없음";
  document.getElementById('pop-bld-use').textContent = props.mn_use_nm || "기타";
  document.getElementById('pop-bld-area').textContent = props.tot_fl_ar ? `${props.tot_fl_ar.toLocaleString()} ㎡` : "-";
  document.getElementById('pop-bld-far').textContent = props.fl_ar_ratio ? `${props.fl_ar_ratio.toFixed(1)} %` : "-";
  
  const floors = (props.gr_fl_num || 0) + " / " + (props.ugr_fl_num || 0);
  document.getElementById('pop-bld-floors').textContent = floors + " 층";
  
  const card = document.getElementById('building-info-card');
  card.classList.remove('hidden');
}

function closeBuildingCard() {
  document.getElementById('building-info-card').classList.add('hidden');
}

function toggleLayer(layerType) {
  if (layerType === 'buildings') {
    loadMapLayers(currentRegion);
  } else if (layerType === 'iso30' || layerType === 'iso60') {
    drawAllIsochrones();
  }
}

let isochroneLayer30 = null;
let isochroneLayer60 = null;

function drawAllIsochrones() {
  if (isochroneLayer30) {
    map.removeLayer(isochroneLayer30);
    isochroneLayer30 = null;
  }
  if (isochroneLayer60) {
    map.removeLayer(isochroneLayer60);
    isochroneLayer60 = null;
  }
  stationMarkersGroup.clearLayers();
  
  if (!accessStatsData) return;
  const ac = accessStatsData[currentRegion];
  
  const drawSingle = (timeMin, color, layerVarName) => {
    let pts = [];
    ac.stations.forEach(st => {
      const stTime = st.time_sec / 60;
      if (stTime <= timeMin) {
        pts.push([st.lng, st.lat]);
        const marker = L.circleMarker([st.lat, st.lng], {
          radius: 3,
          fillColor: color,
          color: '#000',
          weight: 1,
          fillOpacity: 0.8
        });
        marker.bindTooltip(`<strong>${st.statnm}역</strong><br>${Math.round(stTime)}분`, { direction: 'top', className: 'custom-tooltip' });
        stationMarkersGroup.addLayer(marker);
      }
    });
    
    if (pts.length > 2) {
      const multiPoint = turf.multiPoint(pts);
      const hull = turf.convex(multiPoint);
      const layer = L.geoJSON(hull, {
        style: {
          color: color,
          weight: 2,
          fillColor: color,
          fillOpacity: 0.2
        }
      }).addTo(map);
      
      if (layerVarName === 30) isochroneLayer30 = layer;
      if (layerVarName === 60) isochroneLayer60 = layer;
      
      map.fitBounds(layer.getBounds(), { padding: [50, 50] });
    }
  };

  if (document.getElementById('toggle-iso60') && document.getElementById('toggle-iso60').checked) {
    drawSingle(60, '#eab308', 60);
  }
  if (document.getElementById('toggle-iso30') && document.getElementById('toggle-iso30').checked) {
    drawSingle(30, '#10b981', 30);
  }
}

function flyToKeyBuilding(bldId) {
  if (!bldId) {
    if (highlightMarker) map.removeLayer(highlightMarker);
    closeBuildingCard();
    return;
  }
  
  const bld = keyBuildings[currentRegion].find(b => b.id === bldId);
  if (!bld) return;
  
  // Fly to building coords with high zoom level
  map.flyTo(bld.coords, 18);
  
  // Draw highlighting circle marker
  if (highlightMarker) map.removeLayer(highlightMarker);
  
  highlightMarker = L.circle(bld.coords, {
    radius: 40,
    color: '#f59e0b',
    fillColor: '#f59e0b',
    fillOpacity: 0.2,
    weight: 2
  }).addTo(map);
  
  // Trigger attribute card show
  showBuildingAttributes(bld.info);
}
