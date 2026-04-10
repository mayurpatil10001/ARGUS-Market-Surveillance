// src/api/mockData.js — Realistic mock data for all API responses

const now = new Date()
const daysAgo = (n) => new Date(now - n * 86400000).toISOString()
const hoursAgo = (n) => new Date(now - n * 3600000).toISOString()
const minsAgo = (n) => new Date(now - n * 60000).toISOString()

export const mockAlerts = [
  {
    id: 'a1b2c3d4-0001', scrip: 'DEMOBROADCAST', exchange: 'NSE',
    detected_at: minsAgo(3), impossibility_score: 8.9,
    scheme_type: 'pump_and_dump', status: 'open',
    accounts_involved: Array.from({length:23}, (_,i)=>`COLL_${String(i).padStart(3,'0')}`),
    gnn_score: 7.0, dna_score: 10.0, cross_market_score: 6.8, zero_day_score: 7.6,
    estimated_gain: 47500000,
  },
  {
    id: 'a1b2c3d4-0002', scrip: 'DEMOSPOOFCO', exchange: 'NSE',
    detected_at: minsAgo(17), impossibility_score: 8.5,
    scheme_type: 'spoofing', status: 'open',
    accounts_involved: ['SPF_000','SPF_001','SPF_002','SPF_003','SPF_004'],
    gnn_score: 1.0, dna_score: 10.0, cross_market_score: 5.0, zero_day_score: 8.2,
    estimated_gain: 3200000,
  },
  {
    id: 'a1b2c3d4-0003', scrip: 'DEMOCIRCLE', exchange: 'BSE',
    detected_at: minsAgo(42), impossibility_score: 7.9,
    scheme_type: 'circular_trading', status: 'open',
    accounts_involved: ['RING_A','RING_B','RING_C','RING_D','RING_E','RING_F','RING_G','RING_H'],
    gnn_score: 7.0, dna_score: 10.0, cross_market_score: 10.0, zero_day_score: 5.9,
    estimated_gain: 8750000,
  },
  {
    id: 'a1b2c3d4-0004', scrip: 'INFOTECH_X', exchange: 'NSE',
    detected_at: hoursAgo(2), impossibility_score: 9.2,
    scheme_type: 'insider_trading', status: 'under_review',
    accounts_involved: ['INSDR_001','INSDR_002','INSDR_003'],
    gnn_score: 9.1, dna_score: 8.7, cross_market_score: 7.2, zero_day_score: 9.4,
    estimated_gain: 125000000,
  },
  {
    id: 'a1b2c3d4-0005', scrip: 'METALFAB', exchange: 'NSE',
    detected_at: hoursAgo(4), impossibility_score: 8.7,
    scheme_type: 'pump_and_dump', status: 'open',
    accounts_involved: Array.from({length:15}, (_,i)=>`ACC_${String(i+50).padStart(3,'0')}`),
    gnn_score: 8.2, dna_score: 7.9, cross_market_score: 6.1, zero_day_score: 8.9,
    estimated_gain: 22300000,
  },
  {
    id: 'a1b2c3d4-0006', scrip: 'SUGARMILL_B', exchange: 'BSE',
    detected_at: hoursAgo(6), impossibility_score: 7.8,
    scheme_type: 'circular_trading', status: 'open',
    accounts_involved: ['CIR_001','CIR_002','CIR_003','CIR_004','CIR_005','CIR_006'],
    gnn_score: 7.5, dna_score: 7.1, cross_market_score: 8.0, zero_day_score: 7.6,
    estimated_gain: 9100000,
  },
  {
    id: 'a1b2c3d4-0007', scrip: 'PHARMAGEN', exchange: 'NSE',
    detected_at: hoursAgo(8), impossibility_score: 7.6,
    scheme_type: 'spoofing', status: 'open',
    accounts_involved: ['SF_A01','SF_A02','SF_A03'],
    gnn_score: 6.8, dna_score: 8.2, cross_market_score: 4.5, zero_day_score: 7.9,
    estimated_gain: 4500000,
  },
  {
    id: 'a1b2c3d4-0008', scrip: 'DEVINFRA', exchange: 'NSE',
    detected_at: hoursAgo(11), impossibility_score: 7.5,
    scheme_type: 'zero_day', status: 'open',
    accounts_involved: ['ZD_001','ZD_002','ZD_003','ZD_004'],
    gnn_score: 7.2, dna_score: 6.8, cross_market_score: 5.5, zero_day_score: 9.1,
    estimated_gain: 6800000,
  },
  {
    id: 'a1b2c3d4-0009', scrip: 'CERAMICS_CO', exchange: 'BSE',
    detected_at: hoursAgo(15), impossibility_score: 6.8,
    scheme_type: 'pump_and_dump', status: 'resolved',
    accounts_involved: Array.from({length:8}, (_,i)=>`PD_${String(i).padStart(3,'0')}`),
    gnn_score: 6.2, dna_score: 6.5, cross_market_score: 5.0, zero_day_score: 7.2,
    estimated_gain: 3400000,
  },
  {
    id: 'a1b2c3d4-0010', scrip: 'AGRITECH_N', exchange: 'NSE',
    detected_at: hoursAgo(19), impossibility_score: 6.5,
    scheme_type: 'circular_trading', status: 'resolved',
    accounts_involved: ['AGS_001','AGS_002','AGS_003','AGS_004','AGS_005'],
    gnn_score: 6.0, dna_score: 6.1, cross_market_score: 7.5, zero_day_score: 6.3,
    estimated_gain: 5200000,
  },
  {
    id: 'a1b2c3d4-0011', scrip: 'MICROCHIP_Z', exchange: 'NSE',
    detected_at: daysAgo(1), impossibility_score: 6.1,
    scheme_type: 'spoofing', status: 'false_positive',
    accounts_involved: ['MZ_001','MZ_002'],
    gnn_score: 5.5, dna_score: 5.2, cross_market_score: 4.0, zero_day_score: 6.8,
    estimated_gain: 1200000,
  },
  {
    id: 'a1b2c3d4-0012', scrip: 'OILPIPE_LTD', exchange: 'BSE',
    detected_at: daysAgo(1), impossibility_score: 5.8,
    scheme_type: 'zero_day', status: 'false_positive',
    accounts_involved: ['OPL_001','OPL_002','OPL_003'],
    gnn_score: 5.1, dna_score: 5.8, cross_market_score: 3.5, zero_day_score: 6.4,
    estimated_gain: 980000,
  },
  {
    id: 'a1b2c3d4-0013', scrip: 'TEXTILES_RJ', exchange: 'BSE',
    detected_at: daysAgo(2), impossibility_score: 8.1,
    scheme_type: 'pump_and_dump', status: 'case_filed',
    accounts_involved: Array.from({length:11}, (_,i)=>`TRJ_${String(i).padStart(3,'0')}`),
    gnn_score: 7.8, dna_score: 8.1, cross_market_score: 6.5, zero_day_score: 8.4,
    estimated_gain: 31500000,
  },
  {
    id: 'a1b2c3d4-0014', scrip: 'AUTOCOMP_K', exchange: 'NSE',
    detected_at: daysAgo(3), impossibility_score: 9.4,
    scheme_type: 'insider_trading', status: 'case_filed',
    accounts_involved: ['AINS_001','AINS_002','AINS_003','AINS_004'],
    gnn_score: 9.3, dna_score: 9.1, cross_market_score: 8.1, zero_day_score: 9.6,
    estimated_gain: 210000000,
  },
  {
    id: 'a1b2c3d4-0015', scrip: 'BANKFIN_H', exchange: 'NSE',
    detected_at: daysAgo(4), impossibility_score: 7.2,
    scheme_type: 'circular_trading', status: 'under_review',
    accounts_involved: ['BFH_001','BFH_002','BFH_003','BFH_004','BFH_005','BFH_006','BFH_007'],
    gnn_score: 6.9, dna_score: 7.1, cross_market_score: 9.2, zero_day_score: 7.0,
    estimated_gain: 14200000,
  },
]

export const mockAccounts = {
  'COLL_000': {
    id: 'COLL_000', broker: 'ICICI Securities', flagged: true,
    dna_updated: minsAgo(5),
    dna_vector: [0.91, 0.85, 0.72, 0.94, 0.68, 0.88, 0.79, 0.93],
    anomaly_score: 8.9,
    fraudster_matches: [
      { name: 'OPERATOR_X_2022', scheme: 'pump_and_dump', similarity: 91.2 },
      { name: 'RING_MASTER_2021', scheme: 'circular_trading', similarity: 76.4 },
      { name: 'SPOOF_KING_2023', scheme: 'spoofing', similarity: 68.1 },
      { name: 'INSDR_GANG_2020', scheme: 'insider_trading', similarity: 55.3 },
      { name: 'PHANTOM_ACC_19', scheme: 'pump_and_dump', similarity: 48.7 },
    ],
  },
  'SPF_000': {
    id: 'SPF_000', broker: 'Zerodha', flagged: true,
    dna_updated: minsAgo(18),
    dna_vector: [0.45, 0.92, 0.88, 0.71, 0.38, 0.95, 0.89, 0.82],
    anomaly_score: 9.1,
    fraudster_matches: [
      { name: 'SPOOF_KING_2023', scheme: 'spoofing', similarity: 94.7 },
      { name: 'LAYER_MASTER_22', scheme: 'spoofing', similarity: 82.3 },
      { name: 'OPERATOR_X_2022', scheme: 'pump_and_dump', similarity: 63.1 },
      { name: 'RING_MASTER_2021', scheme: 'circular_trading', similarity: 41.2 },
      { name: 'PHANTOM_ACC_19', scheme: 'pump_and_dump', similarity: 35.8 },
    ],
  },
}

const generateTrades = (accountId, n = 30) =>
  Array.from({ length: n }, (_, i) => ({
    id: `tr_${i}`,
    timestamp: hoursAgo(i * 0.8),
    scrip: ['DEMOBROADCAST','METALFAB','NSE_IDX'][i % 3],
    side: i % 3 === 0 ? 'SELL' : 'BUY',
    price: (150 + Math.sin(i) * 12).toFixed(2),
    volume: Math.floor(800 + Math.random() * 2000),
    exchange: 'NSE',
    suspicious: i % 5 === 0,
  }))

export const mockTrades = Object.fromEntries(
  Object.keys(mockAccounts).map(id => [id, generateTrades(id)])
)

export const mockNetwork23 = {
  nodes: [
    ...Array.from({length:8}, (_,i) => ({
      id: `RING_${String.fromCharCode(65+i)}`,
      score: 8.5 + Math.random() * 1.4,
      flagged: true,
      x: 350 + Math.cos(i * Math.PI / 4) * 120,
      y: 250 + Math.sin(i * Math.PI / 4) * 120,
    })),
    ...Array.from({length:15}, (_,i) => ({
      id: `INNO_${String(i).padStart(3,'0')}`,
      score: 1 + Math.random() * 3,
      flagged: false,
      x: Math.random() * 700,
      y: Math.random() * 450,
    })),
  ],
  edges: [
    // Ring edges
    ...Array.from({length:8}, (_,i) => ({
      source: `RING_${String.fromCharCode(65+i)}`,
      target: `RING_${String.fromCharCode(65+(i+1)%8)}`,
      coincidence_count: 22,
    })),
    // Some innocent connections
    {source:'INNO_000', target:'INNO_001', coincidence_count:2},
    {source:'INNO_003', target:'INNO_007', coincidence_count:1},
    {source:'INNO_009', target:'INNO_012', coincidence_count:3},
  ],
}

const lastWeek = Array.from({length:7}, (_,i) => {
  const d = new Date(now - (6-i)*86400000)
  return d.toLocaleDateString('en-IN',{weekday:'short'})
})

export const mockWeeklySummary = {
  total_alerts: 47,
  resolved_alerts: 31,
  false_positive_rate: 12.8,
  cases_filed: 6,
  daily_alerts: lastWeek.map((day,i) => ({
    day, count: [4,7,5,9,8,6,8][i],
    avg_score: [7.1,7.8,6.9,8.2,7.5,7.0,7.9][i],
  })),
  scheme_distribution: [
    { name: 'Pump & Dump', value: 18, color: '#ff3355' },
    { name: 'Circular', value: 13, color: '#7c3aed' },
    { name: 'Spoofing', value: 9, color: '#ffb300' },
    { name: 'Zero-Day', value: 7, color: '#00ff88' },
  ],
  top_scrips: [
    { scrip:'DEMOBROADCAST', alerts:5, avg_score:8.6, peak_score:8.9, scheme_type:'pump_and_dump' },
    { scrip:'AUTOCOMP_K',   alerts:3, avg_score:9.1, peak_score:9.4, scheme_type:'insider_trading' },
    { scrip:'TEXTILES_RJ',  alerts:4, avg_score:7.9, peak_score:8.1, scheme_type:'pump_and_dump' },
    { scrip:'DEMOCIRCLE',   alerts:2, avg_score:7.4, peak_score:7.9, scheme_type:'circular_trading' },
    { scrip:'DEMOSPOOFCO',  alerts:2, avg_score:8.0, peak_score:8.5, scheme_type:'spoofing' },
  ],
  detection_metrics: {
    avg_detection_time_mins: 4.2,
    cases_sent_to_enforcement: 4,
    alert_resolution_rate: 66,
  },
}

export const mockHealth = {
  status: 'ok',
  database: { status: 'ok' },
  redis: { status: 'not_configured' },
  models: {
    gnn: { loaded: true },
    dna: { loaded: true },
    zero_day: { loaded: true },
    cross_market: { loaded: true },
  },
}
