/* eslint-disable @typescript-eslint/no-explicit-any */
import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";

declare var kakao: any;

const API_BASE    = import.meta.env.VITE_API_URL           || "http://localhost:8000";
const KAKAO_JS_KEY = import.meta.env.VITE_KAKAO_MAPS_API_KEY || "";

// ── 카카오 Maps SDK ──────────────────────────────────────
let _sdkPromise: Promise<void> | null = null;
function loadKakaoSDK() {
  if (_sdkPromise) return _sdkPromise;
  if (window.kakao?.maps?.services) return (_sdkPromise = Promise.resolve());
  _sdkPromise = new Promise((resolve, reject) => {
    const prev = document.getElementById("kakao-maps-sdk");
    if (prev) { prev.addEventListener("load", () => kakao.maps.load(resolve)); return; }
    const s   = document.createElement("script");
    s.id      = "kakao-maps-sdk";
    s.src     = `//dapi.kakao.com/v2/maps/sdk.js?appkey=${KAKAO_JS_KEY}&libraries=services&autoload=false`;
    s.onload  = () => kakao.maps.load(resolve);
    s.onerror = reject;
    document.head.appendChild(s);
  });
  return _sdkPromise;
}

async function searchKakaoPlaces(query: string) {
  if (!KAKAO_JS_KEY || !query.trim()) return [];
  await loadKakaoSDK();
  return new Promise<{ name: string; address: string; lat: number; lon: number }[]>((resolve) => {
    const ps = new kakao.maps.services.Places();
    ps.keywordSearch(query, (results: any[], status: string) => {
      if (status !== kakao.maps.services.Status.OK) { resolve([]); return; }
      resolve(results.slice(0, 8).map(d => ({
        name:    d.place_name,
        address: d.address_name,
        lat:     parseFloat(d.y),
        lon:     parseFloat(d.x),
      })));
    });
  });
}

// ── 날씨 ─────────────────────────────────────────────────
const weatherCodeToType = (c: number) => {
  if ([0,1].includes(c))                          return "sunny";
  if ([2,3].includes(c))                          return "cloudy";
  if ([51,53,55,61,63,65,80,81,82].includes(c))   return "rainy";
  if ([71,73,75,77,85,86].includes(c))            return "snow";
  return "cloudy";
};
const WEATHER_META: Record<string, { icon: string; label: string; note: string }> = {
  sunny:  { icon:"☀️", label:"맑음",    note:"실외 코스 포함" },
  cloudy: { icon:"⛅",  label:"흐림",    note:"실내·외 혼합 코스" },
  rainy:  { icon:"🌧️", label:"비",      note:"실내 중심 코스" },
  snow:   { icon:"❄️", label:"눈·추위", note:"따뜻한 실내 코스" },
};

async function fetchWeatherWithFallback(lat: number, lon: number, cityName: string, targetDate?: string) {
  try {
    const ctrl  = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 4000);
    const dateParam = targetDate ? `&target_date=${targetDate.replace(/-/g, "")}` : "";
    const res   = await fetch(
      `${API_BASE}/weather/?lat=${lat}&lon=${lon}&region=${encodeURIComponent(cityName || "")}${dateParam}`,
      { signal: ctrl.signal }
    );
    clearTimeout(timer);
    if (res.ok) {
      const d = await res.json();
      if (!d.error && d.pty_code !== null && d.pty_code !== undefined) {
        let type = "cloudy";
        if (d.pty_code > 0) {
          if ([1,2,4].includes(d.pty_code)) type = "rainy";
          else if (d.pty_code === 3)         type = "snow";
        } else {
          if (d.sky_code === 1) type = "sunny";
          else                  type = "cloudy";
        }
        return {
          type,
          temp:        d.temperature !== null ? Math.round(d.temperature) : null,
          cityName:    cityName || d.region || "선택 지역",
          source:      "kma",
          humidity:    d.humidity,
          windSpeed:   d.wind_speed,
          pop:         d.pop,
          skyDesc:     d.sky_desc,
          description: d.description,
          isOutdoorOk: d.is_outdoor_ok,
        };
      }
    }
  } catch { /* 백엔드 미연결 → 폴백 */ }

  const today = new Date(); today.setHours(0, 0, 0, 0);
  const tgt   = targetDate ? new Date(targetDate + "T00:00:00") : null;

  if (tgt && tgt >= today) {
    const days = Math.min(Math.ceil((tgt.getTime() - today.getTime()) / 86400000) + 2, 16);
    const w: any = await fetch(
      `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=Asia%2FSeoul&forecast_days=${days}`
    ).then(r => r.json());
    const idx = (w.daily?.time || []).indexOf(targetDate);
    if (idx >= 0) {
      const avg = Math.round((w.daily.temperature_2m_max[idx] + w.daily.temperature_2m_min[idx]) / 2);
      return { type: weatherCodeToType(w.daily.weathercode[idx]), temp: avg, cityName: cityName || "선택 지역", source: "openmeteo" };
    }
  }

  const w: any = await fetch(
    `https://api.open-meteo.com/v1/forecast?latitude=${lat}&longitude=${lon}&current=weathercode,temperature_2m&timezone=Asia%2FSeoul`
  ).then(r => r.json());
  return {
    type:     weatherCodeToType(w.current.weathercode),
    temp:     Math.round(w.current.temperature_2m),
    cityName: cityName || "선택 지역",
    source:   "openmeteo",
  };
}

async function fetchWeatherByCoords(lat: number, lon: number, cityName: string, targetDate?: string) {
  return fetchWeatherWithFallback(lat, lon, cityName, targetDate);
}

async function fetchWeatherByCity(city: string, targetDate?: string) {
  const g: any = await fetch(
    `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(city)}&count=1&language=ko`
  ).then(r => r.json());
  if (!g.results?.length) throw new Error("지역을 찾을 수 없어요");
  const { latitude, longitude, name } = g.results[0];
  return fetchWeatherWithFallback(latitude, longitude, name, targetDate);
}

// ── 예산 ──────────────────────────────────────────────────
const BUDGET_VALUES = [10000,20000,30000,50000,70000,100000,150000,200000,300000,500000,Infinity];
const BUDGET_LABELS = ["1만","2만","3만","5만","7만","10만","15만","20만","30만","50만","∞"];
const fmtBudget = (v: number) => v === Infinity ? "제한없음" : `${(v/10000)}만원`;

const snapToBudgetIdx = (rawValue: string | number) => {
  const num = parseInt(String(rawValue).replace(/[^0-9]/g, ""), 10);
  if (!num || num <= 0) return 0;
  let bestIdx = 0, bestDiff = Infinity;
  BUDGET_VALUES.forEach((v, i) => {
    const bv   = v === Infinity ? 99999999 : v;
    const diff = Math.abs(bv - num);
    if (diff < bestDiff) { bestDiff = diff; bestIdx = i; }
  });
  return bestIdx;
};

// ── 디자인 시스템 ──────────────────────────────────────────
const C = {
  bg:"#F5F3FB", card:"#FFFFFF", cardBorder:"#E8E4F4",
  main:"#B8A9D9", mainDim:"#EAE5F5",
  point:"#E8A0B4", pointDim:"#FCE8EE",
  sub:"#D4849A", sky:"#A8C4E0", skyDim:"#DFF0F9",
  text:"#3D3257", textDim:"#7B6FA0", textMuted:"#B0A8CC",
  inputBg:"#F0EDF9", inputBorder:"#D8D0EE",
  error:"#E87070", errorBg:"#FDE8E8",
  warn:"#D4900A", warnBg:"#FFF6E0",
  green:"#388E3C", greenBg:"#E8F5E9",
};
const GS = `
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  @keyframes fadeUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:none} }
  @keyframes fadeIn { from{opacity:0} to{opacity:1} }
  @keyframes spin   { to{transform:rotate(360deg)} }
  @keyframes pulse  { 0%,100%{opacity:1} 50%{opacity:0.45} }
  @keyframes shake  { 0%,100%{transform:translateX(0)} 25%{transform:translateX(-6px)} 75%{transform:translateX(6px)} }
  * { box-sizing:border-box; }
  input:focus { border-color:#B8A9D9 !important; outline:none; box-shadow:0 0 0 3px #B8A9D922; }
  input[type=range] { -webkit-appearance:none; appearance:none; height:4px; background:transparent; cursor:pointer; }
  input[type=range]::-webkit-slider-thumb { -webkit-appearance:none; width:22px; height:22px; border-radius:50%; background:#B8A9D9; cursor:grab; border:3px solid #F5F3FB; box-shadow:0 2px 8px #B8A9D950; }
  @media (max-width:480px) {
    .df-title     { font-size:30px !important; }
    .df-step-title{ font-size:20px !important; }
    .df-inner     { padding-left:14px !important; padding-right:14px !important; padding-top:28px !important; }
    .df-nav-btn   { padding:12px !important; font-size:13px !important; }
    .df-course-card { padding:14px !important; }
  }
`;

const PREF_TAGS: Record<string, string[]> = {
  분위기: ["조용한 분위기","활기찬 분위기","로맨틱","캐주얼","고급스러운"],
  활동:   ["전시·문화","맛집 탐방","활동적인 코스","핫플 방문","산책·자연"],
  카페:   ["여유로운 카페","감성 카페","디저트 맛집","브런치"],
};

// ── 날짜 헬퍼 ─────────────────────────────────────────────
const KO_DAYS = ["일","월","화","수","목","금","토"];
function todayStr() { return new Date().toISOString().split("T")[0]; }
function formatDateKo(s: string) {
  if (!s) return "";
  const d   = new Date(s + "T00:00:00");
  const now = new Date(); now.setHours(0,0,0,0);
  const diffDays = Math.round((d.getTime() - now.getTime()) / 86400000);
  const suffix = diffDays === 0 ? "(오늘)" : diffDays === 1 ? "(내일)" : `(${KO_DAYS[d.getDay()]}요일)`;
  return `${d.getMonth()+1}월 ${d.getDate()}일 ${suffix}`;
}
function isWeekendDate(s: string) {
  if (!s) return false;
  const dow = new Date(s + "T00:00:00").getDay();
  return dow === 0 || dow === 6;
}

// ── 공통 컴포넌트 ─────────────────────────────────────────
function TagButton({ label, selected, onClick, color=C.main }: { label: string; selected: boolean; onClick: () => void; color?: string }) {
  return (
    <button onClick={onClick} style={{
      padding:"8px 16px", borderRadius:"999px",
      border: selected ? "none" : `1.5px solid ${C.cardBorder}`,
      background: selected ? color : C.card,
      color: selected ? "#fff" : C.textDim,
      fontSize:13, fontFamily:"'Noto Sans KR',sans-serif",
      fontWeight: selected ? 700 : 400, cursor:"pointer",
      transition:"all 0.18s",
      boxShadow: selected ? "0 2px 8px #B8A9D940" : "none",
    }}>{label}</button>
  );
}

function ScoreBar({ label, score, color }: { label: string; score: number; color: string }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:10, marginTop:6 }}>
      <span style={{ fontSize:12, color:C.textMuted, width:30 }}>{label}</span>
      <div style={{ flex:1, height:6, background:C.inputBg, borderRadius:"999px", overflow:"hidden" }}>
        <div style={{ width:`${score}%`, height:"100%", background:color, borderRadius:"999px", transition:"width 0.8s cubic-bezier(0.4,0,0.2,1)" }} />
      </div>
      <span style={{ fontSize:12, color:C.textDim, width:32, textAlign:"right", fontFamily:"monospace" }}>{score}%</span>
    </div>
  );
}

function CourseCard({ item, index }: { item: any; index: number }) {
  return (
    <div className="df-course-card" style={{ background:C.card, border:`1px solid ${C.cardBorder}`, borderRadius:20, padding:20, boxShadow:"0 2px 16px #B8A9D918", animation:`fadeUp 0.4s ease ${index*0.1}s both` }}>
      <div style={{ display:"flex", alignItems:"flex-start", gap:14 }}>
        <div style={{ background:C.mainDim, color:C.main, fontSize:13, fontWeight:700, fontFamily:"monospace", padding:"6px 10px", borderRadius:12, whiteSpace:"nowrap", flexShrink:0 }}>{item.time}</div>
        <div style={{ flex:1, minWidth:0 }}>
          <div style={{ display:"flex", alignItems:"center", gap:8, flexWrap:"wrap", marginBottom:4 }}>
            <span style={{ fontSize:15, fontWeight:700, color:C.text, fontFamily:"'Noto Sans KR',sans-serif" }}>{item.place}</span>
            <span style={{ fontSize:11, background:C.pointDim, color:C.sub, padding:"2px 8px", borderRadius:"999px", flexShrink:0 }}>{item.tag}</span>
            <span style={{ fontSize:11, background:item.indoor?C.skyDim:"#F0FBF0", color:item.indoor?C.sky:"#6aaa8a", padding:"2px 8px", borderRadius:"999px", flexShrink:0 }}>{item.indoor?"실내":"실외"}</span>
          </div>
          <p style={{ margin:"0 0 10px", fontSize:13, color:C.textDim, lineHeight:1.6, fontFamily:"'Noto Sans KR',sans-serif" }}>{item.desc}</p>
          <ScoreBar label="A님" score={item.scoreA} color={C.main} />
          <ScoreBar label="B님" score={item.scoreB} color={C.point} />
        </div>
      </div>
    </div>
  );
}

function ProgressBar({ step, total=4 }: { step: number; total?: number }) {
  return (
    <div style={{ display:"flex", gap:6, marginBottom:32 }}>
      {Array.from({length:total},(_,i)=>(
        <div key={i} style={{ flex:1, height:4, borderRadius:"999px", background:i<step?C.main:C.cardBorder, transition:"background 0.3s" }} />
      ))}
    </div>
  );
}

function NavButtons({ onBack, onNext, nextLabel, nextDisabled }: { onBack: () => void; onNext: () => void; nextLabel: string; nextDisabled?: boolean }) {
  return (
    <div style={{ display:"flex", gap:10 }}>
      <button className="df-nav-btn" onClick={onBack} style={{ flex:1, padding:14, background:C.card, border:`1.5px solid ${C.cardBorder}`, borderRadius:14, color:C.textDim, fontSize:14, cursor:"pointer", fontFamily:"'Noto Sans KR',sans-serif" }}>← 이전</button>
      <button className="df-nav-btn" onClick={onNext} disabled={nextDisabled} style={{ flex:2, padding:14, background:nextDisabled?C.inputBg:C.main, border:"none", borderRadius:14, color:nextDisabled?C.textMuted:"#fff", fontSize:15, fontWeight:700, cursor:nextDisabled?"not-allowed":"pointer", fontFamily:"'Noto Sans KR',sans-serif", boxShadow:nextDisabled?"none":"0 4px 14px #B8A9D940", transition:"all 0.2s" }}>{nextLabel}</button>
    </div>
  );
}

// ── 지역 검색 ─────────────────────────────────────────────
type RegionValue = { name: string; lat: number | null; lon: number | null } | null;

function RegionInput({ value, onChange }: { value: RegionValue; onChange: (v: RegionValue) => void }) {
  const [query,    setQuery]   = useState(value?.name || "");
  const [results,  setResults] = useState<{ name: string; address: string; lat: number; lon: number }[]>([]);
  const [loading,  setLoading] = useState(false);
  const [open,     setOpen]    = useState(false);
  const ref        = useRef<HTMLDivElement>(null);
  const debRef     = useRef<ReturnType<typeof setTimeout> | null>(null);
  const hasKey     = !!KAKAO_JS_KEY;

  const doSearch = useCallback(async (q: string) => {
    if (!q.trim()) { setResults([]); setOpen(false); return; }
    setLoading(true);
    try {
      const list = await searchKakaoPlaces(q);
      setResults(list);
      setOpen(list.length > 0);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value;
    setQuery(q);
    onChange(null);
    if (hasKey) {
      if (debRef.current) clearTimeout(debRef.current);
      debRef.current = setTimeout(() => doSearch(q), 350);
    }
  };

  const handleFreeForm = () => {
    if (query.trim() && !value?.name) {
      onChange({ name: query.trim(), lat: null, lon: null });
    }
  };

  const handleSelect = (result: { name: string; address: string; lat: number; lon: number }) => {
    setQuery(result.name);
    setOpen(false);
    onChange(result);
  };

  useEffect(() => {
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  return (
    <div ref={ref} style={{ position:"relative", marginBottom:8 }}>
      <div style={{ position:"relative" }}>
        <input
          value={query}
          onChange={handleInput}
          onFocus={() => results.length > 0 && setOpen(true)}
          onBlur={handleFreeForm}
          onKeyDown={e => { if (e.key === "Enter") { e.preventDefault(); handleFreeForm(); setOpen(false); } }}
          placeholder={hasKey ? "지역·장소 검색 (예: 홍대, 해운대, 한옥마을)" : "지역명 직접 입력 후 Enter (예: 성수동)"}
          style={{ width:"100%", padding:"14px 16px", paddingRight:40, background:C.card, border:`1.5px solid ${C.inputBorder}`, borderRadius:14, color:C.text, fontSize:15, fontFamily:"'Noto Sans KR',sans-serif" }}
        />
        {loading && (
          <span style={{ position:"absolute", right:14, top:"50%", transform:"translateY(-50%)", fontSize:11, color:C.textMuted, animation:"pulse 1s ease infinite" }}>검색 중</span>
        )}
      </div>

      {!hasKey && (
        <p style={{ fontSize:11, color:C.textMuted, margin:"6px 0 0 4px", lineHeight:1.5 }}>
          💡 <code style={{ background:C.inputBg, padding:"1px 5px", borderRadius:4, fontSize:10 }}>VITE_KAKAO_MAPS_API_KEY</code> 설정 시 자동완성 활성화
        </p>
      )}

      {open && results.length > 0 && (
        <div style={{ position:"absolute", top:"calc(100% + 4px)", left:0, right:0, background:C.card, border:`1px solid ${C.cardBorder}`, borderRadius:14, zIndex:200, overflow:"hidden", boxShadow:"0 8px 24px #B8A9D930", animation:"fadeIn 0.15s ease" }}>
          {results.map((r, i) => (
            <button
              key={i}
              onClick={() => handleSelect(r)}
              style={{ width:"100%", padding:"11px 16px", background:"transparent", border:"none", borderBottom: i < results.length-1 ? `1px solid ${C.cardBorder}` : "none", color:C.text, fontSize:14, textAlign:"left", cursor:"pointer", fontFamily:"'Noto Sans KR',sans-serif" }}
              onMouseEnter={e => (e.currentTarget.style.background = C.mainDim)}
              onMouseLeave={e => (e.currentTarget.style.background = "transparent")}
            >
              <div style={{ fontWeight:600, marginBottom:2 }}>📍 {r.name}</div>
              <div style={{ fontSize:11, color:C.textMuted }}>{r.address}</div>
            </button>
          ))}
        </div>
      )}

      {value?.name && (
        <p style={{ fontSize:11, color:C.main, margin:"6px 0 0 4px", fontWeight:600 }}>
          ✓ {value.name} 선택됨 {value.lat && <span style={{ color:C.textMuted }}>({value.lat.toFixed(3)}, {value.lon!.toFixed(3)})</span>}
        </p>
      )}
    </div>
  );
}

// ── 날씨 배지 ─────────────────────────────────────────────
function WeatherBadge({ wx, loading }: { wx: any; loading: boolean }) {
  if (loading) return (
    <div style={{ display:"flex", alignItems:"center", gap:8, padding:"10px 14px", background:C.inputBg, borderRadius:12, fontSize:13, color:C.textMuted, animation:"pulse 1.2s ease infinite" }}>
      <span style={{ animation:"spin 1.4s linear infinite", display:"inline-block" }}>◎</span> 날씨 확인 중...
    </div>
  );
  if (!wx) return null;
  const m     = WEATHER_META[wx.type];
  const isKMA = wx.source === "kma";
  const hasExtra = isKMA && (wx.humidity != null || wx.windSpeed != null || wx.pop != null || wx.skyDesc);
  return (
    <div style={{ padding:"12px 14px", background:C.skyDim, border:`1px solid ${C.sky}44`, borderRadius:14, animation:"fadeUp 0.3s ease" }}>
      <div style={{ display:"flex", alignItems:"center", gap:10 }}>
        <span style={{ fontSize:24 }}>{m.icon}</span>
        <div style={{ flex:1 }}>
          <div style={{ display:"flex", alignItems:"center", gap:7, flexWrap:"wrap", marginBottom:2 }}>
            <span style={{ fontSize:13, fontWeight:700, color:C.text }}>
              {wx.cityName} 현재 {wx.skyDesc || m.label}{wx.temp !== null ? ` · ${wx.temp}°C` : ""}
            </span>
            <span style={{ fontSize:10, padding:"1px 6px", borderRadius:4, fontWeight:700,
              background: isKMA ? C.greenBg : C.skyDim,
              color:      isKMA ? C.green   : C.sky }}>
              {isKMA ? "기상청" : "open-meteo"}
            </span>
          </div>
          <div style={{ fontSize:11, color:C.textDim }}>{m.note} · 코스 생성에 반영돼요</div>
        </div>
      </div>
      {hasExtra && (
        <div style={{ display:"flex", gap:14, marginTop:10, paddingTop:8, borderTop:`1px solid ${C.sky}33`, flexWrap:"wrap" }}>
          {wx.humidity != null && <span style={{ fontSize:12, color:C.textDim }}>💧 습도 <strong style={{ color:C.text }}>{wx.humidity}%</strong></span>}
          {wx.windSpeed != null && <span style={{ fontSize:12, color:C.textDim }}>💨 풍속 <strong style={{ color:C.text }}>{wx.windSpeed}m/s</strong></span>}
          {wx.pop != null && <span style={{ fontSize:12, color:C.textDim }}>🌂 강수확률 <strong style={{ color:C.text }}>{wx.pop}%</strong></span>}
          {wx.isOutdoorOk != null && (
            <span style={{ fontSize:12, padding:"1px 8px", borderRadius:"999px", fontWeight:600,
              background: wx.isOutdoorOk ? C.greenBg : C.errorBg,
              color:      wx.isOutdoorOk ? C.green   : C.error }}>
              {wx.isOutdoorOk ? "실외 활동 가능" : "실내 추천"}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ── 예산 슬라이더 ─────────────────────────────────────────
function BudgetSlider({ minIdx, maxIdx, onMinChange, onMaxChange, color, label }: {
  minIdx: number; maxIdx: number; onMinChange: (v: number) => void; onMaxChange: (v: number) => void; color: string; label: string;
}) {
  const [showDirect, setShowDirect] = useState(false);
  const [dMin, setDMin] = useState("");
  const [dMax, setDMax] = useState("");
  const [topSlider, setTopSlider] = useState("max");

  const applyDirect = () => {
    if (dMin.trim()) { const idx = snapToBudgetIdx(dMin); onMinChange(Math.min(idx, maxIdx)); }
    if (dMax.trim()) { const idx = snapToBudgetIdx(dMax); onMaxChange(Math.max(idx, minIdx)); }
    setDMin(""); setDMax("");
  };

  const leftPct  = (minIdx / 10) * 100;
  const rightPct = (maxIdx / 10) * 100;

  return (
    <div style={{ marginBottom:8 }}>
      <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:12 }}>
        <span style={{ fontSize:13, color, fontWeight:700, fontFamily:"'Noto Sans KR',sans-serif" }}>{label}</span>
        <span style={{ fontSize:13, color:C.text, fontFamily:"'Noto Sans KR',sans-serif" }}>
          {fmtBudget(BUDGET_VALUES[minIdx])} ~ {fmtBudget(BUDGET_VALUES[maxIdx])}
        </span>
      </div>
      <div style={{ position:"relative", height:4, background:C.inputBg, borderRadius:2, margin:"14px 0" }}
        onMouseDown={(e) => {
          const rect = e.currentTarget.getBoundingClientRect();
          const pct  = (e.clientX - rect.left) / rect.width;
          const val  = Math.round(pct * 10);
          setTopSlider(Math.abs(val - minIdx) <= Math.abs(val - maxIdx) ? "min" : "max");
        }}>
        <div style={{ position:"absolute", left:`${leftPct}%`, width:`${rightPct-leftPct}%`, height:"100%", background:color, borderRadius:2, opacity:0.7 }} />
        <input type="range" min={0} max={10} value={minIdx}
          onChange={e => { const v=Number(e.target.value); if(v<=maxIdx) onMinChange(v); }}
          style={{ position:"absolute", width:"100%", top:-8, left:0, margin:0, accentColor:color, zIndex: topSlider==="min" ? 3 : 1 }} />
        <input type="range" min={0} max={10} value={maxIdx}
          onChange={e => { const v=Number(e.target.value); if(v>=minIdx) onMaxChange(v); }}
          style={{ position:"absolute", width:"100%", top:-8, left:0, margin:0, accentColor:color, zIndex: topSlider==="max" ? 3 : 1 }} />
      </div>
      <div style={{ display:"flex", justifyContent:"space-between", marginTop:6 }}>
        {BUDGET_LABELS.map((l,i) => (
          <span key={i} style={{ fontSize:9, color:i===minIdx||i===maxIdx?color:C.textMuted, fontFamily:"monospace", transition:"color 0.2s" }}>{l}</span>
        ))}
      </div>
      <button onClick={() => setShowDirect(v => !v)}
        style={{ marginTop:12, padding:"6px 14px", background:"transparent", border:`1px dashed ${C.inputBorder}`, borderRadius:8, color:C.textDim, fontSize:12, cursor:"pointer", fontFamily:"'Noto Sans KR',sans-serif", display:"flex", alignItems:"center", gap:6 }}>
        <span>{showDirect ? "▲" : "⌨️"}</span>
        {showDirect ? "슬라이더로 돌아가기" : "금액 직접 입력"}
      </button>
      {showDirect && (
        <div style={{ marginTop:10, padding:"14px 16px", background:C.inputBg, borderRadius:12, animation:"fadeUp 0.2s ease" }}>
          <p style={{ fontSize:11, color:C.textMuted, margin:"0 0 10px" }}>금액 입력 후 Enter — 가장 가까운 단계로 자동 설정돼요</p>
          <div style={{ display:"flex", gap:8 }}>
            {[
              { label:"최솟값 (원)", val:dMin, set:setDMin, placeholder:BUDGET_VALUES[minIdx] === Infinity ? "∞" : BUDGET_VALUES[minIdx].toLocaleString() },
              { label:"최댓값 (원)", val:dMax, set:setDMax, placeholder:BUDGET_VALUES[maxIdx] === Infinity ? "∞" : BUDGET_VALUES[maxIdx].toLocaleString() },
            ].map(({ label: lbl, val, set, placeholder }) => (
              <div key={lbl} style={{ flex:1 }}>
                <label style={{ fontSize:11, color, fontWeight:600, display:"block", marginBottom:4 }}>{lbl}</label>
                <input type="number" value={val} onChange={e => set(e.target.value)} onBlur={applyDirect}
                  onKeyDown={e => e.key === "Enter" && applyDirect()} placeholder={placeholder}
                  style={{ width:"100%", padding:"10px 12px", background:C.card, border:`1.5px solid ${C.inputBorder}`, borderRadius:10, color:C.text, fontSize:14, fontFamily:"'Noto Sans KR',sans-serif" }} />
              </div>
            ))}
          </div>
          <p style={{ fontSize:11, color:C.textMuted, margin:"8px 0 0" }}>
            → 적용 결과: {fmtBudget(BUDGET_VALUES[minIdx])} ~ {fmtBudget(BUDGET_VALUES[maxIdx])}
          </p>
        </div>
      )}
    </div>
  );
}

// ── 로딩 화면 ─────────────────────────────────────────────
const LOADING_STEPS = [
  "지역 좌표를 확인하는 중...",
  "현재 날씨를 확인하는 중...",
  "취향을 분석하는 중...",
  "데이트 코스를 구성하는 중...",
];
function LoadingScreen({ message }: { message: string }) {
  const stepIdx = LOADING_STEPS.indexOf(message);
  const isDone  = stepIdx < 0;
  const pct     = isDone ? 100 : Math.round(((stepIdx + 1) / LOADING_STEPS.length) * 100);
  return (
    <div style={{ minHeight:"100vh", background:C.bg, display:"flex", flexDirection:"column", alignItems:"center", justifyContent:"center", padding:"0 20px", fontFamily:"'Noto Sans KR',sans-serif" }}>
      <style>{GS}</style>
      <div style={{ textAlign:"center", width:"100%", maxWidth:320 }}>
        <div style={{ fontSize:44, animation:"spin 1.6s linear infinite", display:"inline-block", marginBottom:24, color:C.main }}>◎</div>
        <p style={{ color:C.text, fontSize:16, fontWeight:600, marginBottom:8 }}>{isDone ? "코스 완성! ✦" : "코스 생성 중"}</p>
        <p style={{ color:C.textDim, fontSize:14, animation:"pulse 1.5s ease infinite", marginBottom:28 }}>{message}</p>
        <div style={{ background:C.inputBg, borderRadius:"999px", height:6, overflow:"hidden", marginBottom:14 }}>
          <div style={{ width:`${pct}%`, height:"100%", background:`linear-gradient(90deg,${C.main},${C.point})`, borderRadius:"999px", transition:"width 0.5s ease" }} />
        </div>
        <div style={{ display:"flex", justifyContent:"space-between", padding:"0 4px" }}>
          {LOADING_STEPS.map((_, i) => (
            <div key={i} style={{ width:8, height:8, borderRadius:"50%", background:(isDone||i<=stepIdx)?C.main:C.inputBg, transition:"background 0.3s" }} />
          ))}
        </div>
      </div>
    </div>
  );
}

// ── 달력 ──────────────────────────────────────────────────
function CalendarPicker({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const today = todayStr();
  const [view, setView] = useState(() => {
    const d = new Date((value || today) + "T00:00:00");
    return { year: d.getFullYear(), month: d.getMonth() };
  });

  useEffect(() => {
    if (value) {
      const d = new Date(value + "T00:00:00");
      setView({ year: d.getFullYear(), month: d.getMonth() });
    }
  }, [value]);

  const { year: vy, month: vm } = view;
  const prevMonth = () => setView(v => v.month === 0  ? { year:v.year-1, month:11 } : { ...v, month:v.month-1 });
  const nextMonth = () => setView(v => v.month === 11 ? { year:v.year+1, month:0  } : { ...v, month:v.month+1 });

  const firstDow    = new Date(vy, vm, 1).getDay();
  const daysInMonth = new Date(vy, vm + 1, 0).getDate();
  const cells = [
    ...Array(firstDow).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ];
  while (cells.length % 7 !== 0) cells.push(null);

  const KO_MONTH = ["1월","2월","3월","4월","5월","6월","7월","8월","9월","10월","11월","12월"];

  return (
    <div style={{ marginBottom:16 }}>
      <div style={{ background:C.card, border:`1.5px solid ${C.cardBorder}`, borderRadius:20, padding:"16px 14px 20px", boxShadow:"0 2px 12px #B8A9D910" }}>
        <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
          <button onClick={prevMonth} style={{ width:32, height:32, borderRadius:"50%", border:"none", background:C.inputBg, color:C.textDim, fontSize:16, cursor:"pointer", lineHeight:"1" }}>‹</button>
          <span style={{ fontSize:15, fontWeight:700, color:C.text, fontFamily:"'Noto Sans KR',sans-serif" }}>{vy}년 {KO_MONTH[vm]}</span>
          <button onClick={nextMonth} style={{ width:32, height:32, borderRadius:"50%", border:"none", background:C.inputBg, color:C.textDim, fontSize:16, cursor:"pointer", lineHeight:"1" }}>›</button>
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(7,1fr)", marginBottom:6 }}>
          {["일","월","화","수","목","금","토"].map((d, i) => (
            <div key={d} style={{ textAlign:"center", fontSize:11, fontWeight:700, padding:"4px 0",
              color: i===0 ? "#E07070" : i===6 ? "#6090D0" : C.textMuted }}>{d}</div>
          ))}
        </div>
        <div style={{ display:"grid", gridTemplateColumns:"repeat(7,1fr)", gap:"2px" }}>
          {cells.map((day, idx) => {
            if (!day) return <div key={`e${idx}`} />;
            const ds     = `${vy}-${String(vm+1).padStart(2,"0")}-${String(day).padStart(2,"0")}`;
            const dow    = new Date(vy, vm, day).getDay();
            const isPast = ds < today;
            const isSel  = ds === value;
            const isToday= ds === today;
            return (
              <button key={ds} onClick={() => !isPast && onChange(ds)} style={{
                padding:"8px 2px", borderRadius:10,
                border: isToday && !isSel ? `1.5px solid ${C.main}` : "none",
                background: isSel ? C.main : "transparent",
                color: isPast ? C.textMuted : isSel ? "#fff" : dow===0 ? "#E07070" : dow===6 ? "#6090D0" : C.text,
                fontSize:13, fontWeight: isSel||isToday ? 700 : 400,
                cursor: isPast ? "default" : "pointer", opacity: isPast ? 0.3 : 1,
                fontFamily:"'Noto Sans KR',sans-serif", transition:"background 0.15s, color 0.15s",
              }}>{day}</button>
            );
          })}
        </div>
      </div>
      {value && (
        <div style={{ marginTop:10, display:"flex", alignItems:"center", gap:8 }}>
          <span style={{ fontSize:13, color:C.text, fontWeight:600, fontFamily:"'Noto Sans KR',sans-serif" }}>📅 {formatDateKo(value)}</span>
          <span style={{ fontSize:11, padding:"2px 9px", borderRadius:"999px", fontWeight:600,
            background: isWeekendDate(value) ? C.pointDim : C.mainDim,
            color:      isWeekendDate(value) ? C.point    : C.main }}>
            {isWeekendDate(value) ? "주말" : "평일"}
          </span>
        </div>
      )}
    </div>
  );
}

// ── 태그 유틸 ─────────────────────────────────────────────
const tagToMood = (tags: string[]) => {
  if (tags.includes("로맨틱"))        return "로맨틱";
  if (tags.includes("고급스러운"))    return "고급스러운";
  if (tags.includes("조용한 분위기")) return "조용한";
  if (tags.includes("활기찬 분위기")) return "활기찬";
  return "감성적";
};
const FOOD_TAGS = ["맛집 탐방","여유로운 카페","감성 카페","디저트 맛집","브런치","전시·문화","활동적인 코스","산책·자연","핫플 방문"];
const tagToFoodType = (tags: string[]) => tags.filter(t => FOOD_TAGS.includes(t));

const hashScore = (seed: string, tags: string[], category: string) => {
  let h = 0;
  for (let i = 0; i < seed.length; i++) h = (h * 31 + seed.charCodeAt(i)) & 0xFFFFFF;
  const base  = 68 + (h % 22);
  const bonus = tags.some(t => category?.includes(t.split("·")[0].trim())) ? 11 : 0;
  return Math.min(96, base + bonus);
};

const adaptCourses = (apiCourses: any, tagsA: string[], tagsB: string[]) => {
  const places = apiCourses?.[0]?.places;
  if (!places?.length) return null;
  const INDOOR_CATS = ["카페","식당","레스토랑","바","펍","전시","갤러리","베이커리","디저트"];
  return places.map((p: any) => ({
    time:   p.time || "13:00",
    place:  p.name,
    desc:   `${p.category} · 예상 ${typeof p.price === "number" ? p.price.toLocaleString() : "?"}원`,
    scoreA: hashScore(p.name + "A", tagsA, p.category),
    scoreB: hashScore(p.name + "B", tagsB, p.category),
    tag:    p.category,
    indoor: INDOOR_CATS.some(c => p.category?.includes(c)),
  }));
};

const MOCK_COURSES: Record<string, any[]> = {
  sunny: [
    { time:"13:00", place:"서울숲 피크닉",      desc:"잔디밭 여유로운 오후 · 돗자리 대여 가능", scoreA:88, scoreB:82, tag:"산책·자연",    indoor:false },
    { time:"15:00", place:"성수 갤러리 카페",    desc:"전시 + 커피 · 감성적인 핫플",            scoreA:90, scoreB:70, tag:"전시·문화",    indoor:true  },
    { time:"17:30", place:"성수 오마카세 맛집",  desc:"분위기 있는 식사",                       scoreA:85, scoreB:92, tag:"맛집 탐방",    indoor:true  },
  ],
  cloudy: [
    { time:"13:00", place:"성수 갤러리 카페",      desc:"전시 + 커피 · 감성적인 핫플",           scoreA:90, scoreB:70, tag:"전시·문화",    indoor:true  },
    { time:"15:00", place:"성수 팝업 스토어 거리", desc:"걸으며 구경 · 무료입장",                scoreA:65, scoreB:88, tag:"활동적인 코스", indoor:false },
    { time:"17:30", place:"성수 오마카세 맛집",    desc:"분위기 있는 식사",                      scoreA:85, scoreB:92, tag:"맛집 탐방",    indoor:true  },
  ],
  rainy: [
    { time:"13:00", place:"DDP 전시관",       desc:"비 오는 날 딱인 실내 전시 · 주차 편리",  scoreA:91, scoreB:74, tag:"전시·문화",    indoor:true },
    { time:"15:00", place:"성수 감성 카페",   desc:"빗소리 들으며 디저트 · 창가 자리 추천", scoreA:87, scoreB:80, tag:"여유로운 카페", indoor:true },
    { time:"18:00", place:"이탈리안 레스토랑",desc:"따뜻한 파스타 · 예약 필수",              scoreA:83, scoreB:90, tag:"맛집 탐방",    indoor:true },
  ],
  snow: [
    { time:"13:00", place:"북촌 한옥 카페",   desc:"눈 쌓인 한옥 분위기 · 전통차 코스",     scoreA:92, scoreB:78, tag:"감성 카페",    indoor:true },
    { time:"15:30", place:"인사동 공예 체험", desc:"실내 도예·공예 체험 · 커플 추천",        scoreA:80, scoreB:85, tag:"전시·문화",    indoor:true },
    { time:"18:00", place:"광장시장 먹거리",  desc:"따뜻한 빈대떡·마약김밥 · 겨울 명물",    scoreA:78, scoreB:94, tag:"맛집 탐방",    indoor:false },
  ],
};

// ══════════════════════════════════════════════════════════
//  메인 컴포넌트
// ══════════════════════════════════════════════════════════
export default function OnboardingPage() {
  const navigate = useNavigate();

  const [region,      setRegion]      = useState<RegionValue>(null);
  const [dateStr,     setDateStr]     = useState(todayStr());
  const [tagsA,       setTagsA]       = useState<string[]>([]);
  const [tagsB,       setTagsB]       = useState<string[]>([]);
  const [budgetMinA,  setBudgetMinA]  = useState(2);
  const [budgetMaxA,  setBudgetMaxA]  = useState(5);
  const [budgetMinB,  setBudgetMinB]  = useState(2);
  const [budgetMaxB,  setBudgetMaxB]  = useState(5);

  const [step,        setStep]        = useState(0);
  const [loadingMsg,  setLoadingMsg]  = useState("");
  const [weather,     setWeather]     = useState<any>(null);
  const [wxPreview,   setWxPreview]   = useState<any>(null);
  const [wxLoading,   setWxLoading]   = useState(false);
  const [apiError,    setApiError]    = useState<string | null>(null);
  const [isMobile,    setIsMobile]    = useState(window.innerWidth <= 480);

  const sessionRef = useRef(`df_${Date.now()}`);

  useEffect(() => {
    const h = () => setIsMobile(window.innerWidth <= 480);
    window.addEventListener("resize", h);
    return () => window.removeEventListener("resize", h);
  }, []);

  const toggleTag = (tag: string, who: "A" | "B") => {
    const [get, set] = who === "A" ? [tagsA, setTagsA] : [tagsB, setTagsB];
    set(get.includes(tag) ? get.filter(t => t !== tag) : [...get, tag]);
  };

  const budgetOverlapMin = Math.max(budgetMinA, budgetMinB);
  const budgetOverlapMax = Math.min(budgetMaxA, budgetMaxB);
  const hasBudgetOverlap = budgetOverlapMin <= budgetOverlapMax;

  useEffect(() => {
    if (!region?.name) { setWxPreview(null); setWxLoading(false); return; }
    let cancelled = false;
    setWxPreview(null);
    setWxLoading(true);
    const doFetch = async () => {
      try {
        const wx = region.lat
          ? await fetchWeatherByCoords(region.lat, region.lon!, region.name, dateStr)
          : await fetchWeatherByCity(region.name, dateStr);
        if (!cancelled) setWxPreview(wx);
      } catch {
        if (!cancelled) setWxPreview(null);
      } finally {
        if (!cancelled) setWxLoading(false);
      }
    };
    doFetch();
    return () => { cancelled = true; };
  }, [region, dateStr]);

  const handleGenerate = async () => {
    setApiError(null);

    setLoadingMsg(LOADING_STEPS[0]);
    let lat = region?.lat || 37.5665;
    let lon = region?.lon || 126.9780;
    let cityName = region?.name || "";

    if (!region?.lat) {
      try {
        const g: any = await fetch(
          `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(cityName)}&count=1&language=ko`
        ).then(r => r.json());
        if (g.results?.length) { lat = g.results[0].latitude; lon = g.results[0].longitude; cityName = g.results[0].name; }
      } catch { /* ignore */ }
    }

    setLoadingMsg(LOADING_STEPS[1]);
    let weatherObj = wxPreview || { type:"cloudy", temp:null, cityName };
    if (!wxPreview) {
      try { weatherObj = await fetchWeatherByCoords(lat, lon, cityName); } catch { /* ignore */ }
    }
    setWeather({ ...weatherObj, cityName });

    setLoadingMsg(LOADING_STEPS[2]);
    const sid       = sessionRef.current;
    const rawBudget = hasBudgetOverlap ? BUDGET_VALUES[budgetOverlapMin] : BUDGET_VALUES[budgetMaxA];
    const budget    = rawBudget === Infinity ? 999999 : rawBudget;
    let backendOk   = false;

    try {
      const r = await fetch(`${API_BASE}/user/prefs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id:    `${sid}_A`,
          partner_id: `${sid}_B`,
          mood:       tagToMood(tagsA),
          food_type:  tagToFoodType([...tagsA, ...tagsB]),
          budget,
          age_group: "20대",
        }),
      });
      backendOk = r.ok;
    } catch { /* ignore */ }

    setLoadingMsg(LOADING_STEPS[3]);

    if (backendOk) {
      try {
        const r = await fetch(`${API_BASE}/course/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            user_id: `${sid}_A`, region: cityName, lat, lon,
            start_time: "13:00", end_time: "21:00", budget, weather: weatherObj.type,
          }),
        });
        if (!r.ok && r.status >= 500) setApiError("서버에서 코스를 생성하지 못했어요. 샘플 데이터로 대체합니다.");
      } catch { /* ignore */ }
    }

    // F2 결과 페이지로 이동 (같은 앱 내 라우팅)
    const urlParams = new URLSearchParams({
      session:   sid,
      region:    cityName,
      lat:       String(lat),
      lon:       String(lon),
      date:      dateStr,
      weather:   weatherObj.type,
      temp:      String(weatherObj.temp ?? ""),
      humidity:  String(weatherObj.humidity ?? ""),
      windSpeed: String(weatherObj.windSpeed ?? ""),
      pop:       String(weatherObj.pop ?? ""),
      skyDesc:   weatherObj.skyDesc || "",
      tagsA:     tagsA.join(","),
      tagsB:     tagsB.join(","),
      budget:    String(budget),
    });
    setLoadingMsg("결과 페이지로 이동합니다 ✦");
    await new Promise(r => setTimeout(r, 700));
    navigate('/result?' + urlParams.toString());
  };

  const reset = () => {
    setStep(0); setRegion(null); setDateStr(todayStr()); setTagsA([]); setTagsB([]);
    setWeather(null); setBudgetMinA(2); setBudgetMaxA(5); setBudgetMinB(2); setBudgetMaxB(5);
    setApiError(null); setWxPreview(null);
  };

  const wrap  = { minHeight:"100vh", background:C.bg, fontFamily:"'Noto Sans KR',sans-serif", display:"flex" as const, flexDirection:"column" as const, alignItems:"center" as const, padding:"0 0 80px" };
  const inner = { maxWidth:"420px", width:"100%", padding: isMobile ? "28px 14px 0" : "48px 20px 0" };

  const areaName   = region?.name || "";
  const commonTags = tagsA.filter(t => tagsB.includes(t));

  if (loadingMsg) return <LoadingScreen message={loadingMsg} />;

  // ── STEP 0: 랜딩 ────────────────────────────────────────
  if (step === 0) return (
    <div style={wrap}><style>{GS}</style>
      <div className="df-inner" style={{ ...inner, paddingTop: isMobile ? 40 : 64, animation:"fadeUp 0.5s ease" }}>
        <div style={{ fontSize:11, letterSpacing:"0.2em", color:C.main, marginBottom:16, textTransform:"uppercase", fontWeight:600 }}>Capstone 12조</div>
        <h1 className="df-title" style={{ fontSize:40, fontWeight:900, color:C.text, margin:"0 0 8px", lineHeight:1.15, letterSpacing:"-0.03em" }}>
          Date<span style={{ color:C.main }}>Flow</span>
        </h1>
        <p style={{ fontSize:15, color:C.textDim, margin:"0 0 28px", lineHeight:1.7 }}>두 사람의 취향을 분석해<br />딱 맞는 데이트 코스를 만들어드려요</p>
        {[
          { icon:"📍", text: KAKAO_JS_KEY ? "카카오 API 실시간 지역 검색" : "전국 어디든 지역명 입력" },
          { icon:"🌤", text:"선택 즉시 날씨 자동 확인" },
          { icon:"💰", text:"A/B 각자 예산 · 직접 입력 가능" },
          { icon:"✦",  text:"취향 교집합 코스 자동 생성" },
        ].map((x, i) => (
          <div key={i} style={{ display:"flex", alignItems:"center", gap:14, marginBottom:10, animation:`fadeUp 0.5s ease ${0.06+i*0.07}s both` }}>
            <span style={{ fontSize:16, width:22, textAlign:"center" }}>{x.icon}</span>
            <span style={{ fontSize:14, color:C.textDim }}>{x.text}</span>
          </div>
        ))}
        <div style={{ marginTop:24 }}>
          <label style={{ fontSize:12, color:C.textDim, display:"block", marginBottom:8, fontWeight:500 }}>데이트 날짜</label>
          <CalendarPicker value={dateStr} onChange={setDateStr} />
          <label style={{ fontSize:12, color:C.textDim, display:"block", marginBottom:8, fontWeight:500 }}>데이트 지역</label>
          <RegionInput value={region} onChange={setRegion} />
          <div style={{ marginTop:8, marginBottom:16, minHeight:wxLoading ? 48 : 0 }}>
            <WeatherBadge wx={wxPreview} loading={wxLoading && !wxPreview} />
          </div>
        </div>
        <button onClick={() => setStep(1)} disabled={!areaName}
          style={{ width:"100%", padding:16, background:areaName?C.main:C.inputBg, color:areaName?"#fff":C.textMuted, border:"none", borderRadius:14, fontSize:16, fontWeight:700, cursor:areaName?"pointer":"not-allowed", fontFamily:"'Noto Sans KR',sans-serif", boxShadow:areaName?"0 4px 20px #B8A9D950":"none", transition:"all 0.2s" }}>
          시작하기 →
        </button>
      </div>
    </div>
  );

  // ── STEP 1: A님 취향 ────────────────────────────────────
  if (step === 1) return (
    <div style={wrap}><style>{GS}</style>
      <div className="df-inner" style={{ ...inner, animation:"fadeUp 0.35s ease" }}>
        <ProgressBar step={1} />
        <div style={{ fontSize:11, color:C.main, marginBottom:10, letterSpacing:"0.1em", textTransform:"uppercase", fontWeight:600 }}>Step 1 / 4 · A님</div>
        <h2 className="df-step-title" style={{ fontSize:26, fontWeight:700, color:C.text, margin:"0 0 4px" }}><span style={{ color:C.main }}>A님</span>의 취향을 알려주세요</h2>
        <p style={{ fontSize:13, color:C.textMuted, margin:"0 0 24px" }}>여러 개 선택 가능해요</p>
        {Object.entries(PREF_TAGS).map(([cat, list]) => (
          <div key={cat} style={{ marginBottom:22 }}>
            <div style={{ fontSize:11, color:C.textMuted, marginBottom:8, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:600 }}>{cat}</div>
            <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
              {list.map(t => <TagButton key={t} label={t} selected={tagsA.includes(t)} onClick={() => toggleTag(t,"A")} />)}
            </div>
          </div>
        ))}
        {tagsA.length > 0 && (
          <div style={{ background:C.mainDim, border:`1px solid ${C.cardBorder}`, borderRadius:14, padding:"12px 16px", marginBottom:20 }}>
            <div style={{ fontSize:11, color:C.main, marginBottom:6, fontWeight:600 }}>선택됨</div>
            <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
              {tagsA.map(t => <span key={t} style={{ fontSize:12, background:C.main, color:"#fff", padding:"3px 10px", borderRadius:"999px" }}>{t}</span>)}
            </div>
          </div>
        )}
        <NavButtons onBack={() => setStep(0)} onNext={() => setStep(2)} nextLabel="A님 예산 설정 →" />
      </div>
    </div>
  );

  // ── STEP 2: A님 예산 ────────────────────────────────────
  if (step === 2) return (
    <div style={wrap}><style>{GS}</style>
      <div className="df-inner" style={{ ...inner, animation:"fadeUp 0.35s ease" }}>
        <ProgressBar step={2} />
        <div style={{ fontSize:11, color:C.main, marginBottom:10, letterSpacing:"0.1em", textTransform:"uppercase", fontWeight:600 }}>Step 2 / 4 · A님</div>
        <h2 className="df-step-title" style={{ fontSize:26, fontWeight:700, color:C.text, margin:"0 0 4px" }}><span style={{ color:C.main }}>A님</span>의 1인 예산 범위는요?</h2>
        <p style={{ fontSize:13, color:C.textMuted, margin:"0 0 24px" }}>슬라이더 조정 또는 직접 입력하세요</p>
        <div style={{ background:C.card, border:`1px solid ${C.cardBorder}`, borderRadius:20, padding:"20px 20px 24px", marginBottom:24, boxShadow:"0 2px 12px #B8A9D912" }}>
          <BudgetSlider minIdx={budgetMinA} maxIdx={budgetMaxA} onMinChange={setBudgetMinA} onMaxChange={setBudgetMaxA} color={C.main} label="A님 예산" />
        </div>
        <NavButtons onBack={() => setStep(1)} onNext={() => setStep(3)} nextLabel="B님 취향 입력 →" />
      </div>
    </div>
  );

  // ── STEP 3: B님 취향 ────────────────────────────────────
  if (step === 3) return (
    <div style={wrap}><style>{GS}</style>
      <div className="df-inner" style={{ ...inner, animation:"fadeUp 0.35s ease" }}>
        <ProgressBar step={3} />
        <div style={{ fontSize:11, color:C.point, marginBottom:10, letterSpacing:"0.1em", textTransform:"uppercase", fontWeight:600 }}>Step 3 / 4 · B님</div>
        <h2 className="df-step-title" style={{ fontSize:26, fontWeight:700, color:C.text, margin:"0 0 4px" }}><span style={{ color:C.point }}>B님</span>의 취향을 알려주세요</h2>
        <p style={{ fontSize:13, color:C.textMuted, margin:"0 0 24px" }}>여러 개 선택 가능해요</p>
        {Object.entries(PREF_TAGS).map(([cat, list]) => (
          <div key={cat} style={{ marginBottom:22 }}>
            <div style={{ fontSize:11, color:C.textMuted, marginBottom:8, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:600 }}>{cat}</div>
            <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
              {list.map(t => <TagButton key={t} label={t} selected={tagsB.includes(t)} onClick={() => toggleTag(t,"B")} color={C.point} />)}
            </div>
          </div>
        ))}
        {tagsB.length > 0 && (
          <div style={{ background:C.pointDim, border:`1px solid ${C.cardBorder}`, borderRadius:14, padding:"12px 16px", marginBottom:20 }}>
            <div style={{ fontSize:11, color:C.point, marginBottom:6, fontWeight:600 }}>선택됨</div>
            <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
              {tagsB.map(t => <span key={t} style={{ fontSize:12, background:C.point, color:"#fff", padding:"3px 10px", borderRadius:"999px" }}>{t}</span>)}
            </div>
          </div>
        )}
        <NavButtons onBack={() => setStep(2)} onNext={() => setStep(4)} nextLabel="B님 예산 설정 →" />
      </div>
    </div>
  );

  // ── STEP 4: B님 예산 + 요약 ─────────────────────────────
  if (step === 4) return (
    <div style={wrap}><style>{GS}</style>
      <div className="df-inner" style={{ ...inner, animation:"fadeUp 0.35s ease" }}>
        <ProgressBar step={4} />
        <div style={{ fontSize:11, color:C.point, marginBottom:10, letterSpacing:"0.1em", textTransform:"uppercase", fontWeight:600 }}>Step 4 / 4 · B님</div>
        <h2 className="df-step-title" style={{ fontSize:26, fontWeight:700, color:C.text, margin:"0 0 4px" }}><span style={{ color:C.point }}>B님</span>의 1인 예산 범위는요?</h2>
        <p style={{ fontSize:13, color:C.textMuted, margin:"0 0 24px" }}>슬라이더 조정 또는 직접 입력하세요</p>
        <div style={{ background:C.card, border:`1px solid ${C.cardBorder}`, borderRadius:20, padding:"20px 20px 24px", marginBottom:20, boxShadow:"0 2px 12px #B8A9D912" }}>
          <BudgetSlider minIdx={budgetMinB} maxIdx={budgetMaxB} onMinChange={setBudgetMinB} onMaxChange={setBudgetMaxB} color={C.point} label="B님 예산" />
        </div>
        <div style={{ background:hasBudgetOverlap?C.skyDim:C.errorBg, border:`1px solid ${hasBudgetOverlap?C.sky:C.error}44`, borderRadius:12, padding:"14px 16px", marginBottom:20 }}>
          {hasBudgetOverlap
            ? (<><div style={{ fontSize:13, color:C.sky, fontWeight:700, marginBottom:4 }}>✓ 예산 교집합</div><div style={{ fontSize:13, color:C.text }}>{fmtBudget(BUDGET_VALUES[budgetOverlapMin])} ~ {fmtBudget(BUDGET_VALUES[budgetOverlapMax])}</div><div style={{ fontSize:11, color:C.textMuted, marginTop:4 }}>이 범위 안의 장소로 코스를 구성해요</div></>)
            : (<><div style={{ fontSize:13, color:C.error, fontWeight:700, marginBottom:4 }}>⚠ 예산 범위가 겹치지 않아요</div><div style={{ fontSize:11, color:C.error, marginTop:4 }}>A님 예산 기준으로 코스를 생성해요</div></>)}
        </div>
        <div style={{ background:C.card, border:`1px solid ${C.cardBorder}`, borderRadius:16, padding:16, marginBottom:20 }}>
          <div style={{ fontSize:11, color:C.main, marginBottom:10, fontWeight:600 }}>입력 요약</div>
          {[
            { k:"지역",     v: areaName },
            { k:"날짜",     v: dateStr ? formatDateKo(dateStr) : "미선택" },
            { k:"날씨",     v: wxPreview ? `${WEATHER_META[wxPreview.type].label} · ${wxPreview.temp ?? "?"}°C` : "생성 시 자동 확인" },
            { k:"A님 취향", v: tagsA.length ? tagsA.slice(0,3).join(", ") : "미선택" },
            { k:"A님 예산", v: `${fmtBudget(BUDGET_VALUES[budgetMinA])} ~ ${fmtBudget(BUDGET_VALUES[budgetMaxA])}` },
            { k:"B님 취향", v: tagsB.length ? tagsB.slice(0,3).join(", ") : "미선택" },
            { k:"B님 예산", v: `${fmtBudget(BUDGET_VALUES[budgetMinB])} ~ ${fmtBudget(BUDGET_VALUES[budgetMaxB])}` },
          ].map(({k,v}) => (
            <div key={k} style={{ display:"flex", gap:10, fontSize:12, marginBottom:5 }}>
              <span style={{ color:C.textMuted, width:64, flexShrink:0 }}>{k}</span>
              <span style={{ color:k==="날씨"?C.sky:C.text }}>{v}</span>
            </div>
          ))}
        </div>
        <NavButtons onBack={() => setStep(3)} onNext={handleGenerate} nextLabel="날씨 확인 후 코스 생성 ✦" />
        {apiError && <div style={{ marginTop:12, fontSize:12, color:C.error }}>{apiError}</div>}
      </div>
    </div>
  );

  // ── STEP 5 (fallback): 결과 미리보기 ─────────────────────
  const wxType   = weather?.type || "cloudy";
  const wxMeta   = WEATHER_META[wxType];
  const schedule = adaptCourses(null, tagsA, tagsB) || MOCK_COURSES[wxType];

  return (
    <div style={wrap}><style>{GS}</style>
      <div className="df-inner" style={{ ...inner, animation:"fadeUp 0.4s ease" }}>
        <div style={{ fontSize:11, color:C.main, marginBottom:10, letterSpacing:"0.15em", textTransform:"uppercase", fontWeight:600 }}>
          DateFlow · {weather?.cityName || areaName}
        </div>
        <h2 style={{ fontSize: isMobile?20:24, fontWeight:700, color:C.text, margin:"0 0 6px" }}>절충 데이트 코스 ✦</h2>
        <div style={{ display:"flex", gap:8, marginBottom:16 }}>
          <span style={{ fontSize:12, background:C.skyDim, color:C.sky, padding:"5px 12px", borderRadius:"999px", border:`1px solid ${C.sky}44` }}>
            {wxMeta.icon} {wxMeta.label}{weather?.temp != null && ` · ${weather.temp}°C`}
          </span>
        </div>
        <div style={{ display:"flex", gap:12, marginBottom:20 }}>
          {[
            { label:"A님 선호", tags:tagsA.length?tagsA:["(미선택)"], color:C.main,  dim:C.mainDim  },
            { label:"B님 선호", tags:tagsB.length?tagsB:["(미선택)"], color:C.point, dim:C.pointDim },
          ].map(({ label, tags, color, dim }) => (
            <div key={label} style={{ flex:1 }}>
              <div style={{ fontSize:11, color:C.textMuted, marginBottom:6, fontWeight:600 }}>{label}</div>
              <div style={{ display:"flex", flexWrap:"wrap", gap:4 }}>
                {tags.slice(0,3).map(t => <span key={t} style={{ fontSize:11, background:dim, color, padding:"2px 8px", borderRadius:"999px" }}>{t}</span>)}
              </div>
            </div>
          ))}
        </div>
        {commonTags.length > 0 && (
          <div style={{ marginBottom:16, padding:"10px 14px", background:C.skyDim, borderRadius:12 }}>
            <div style={{ fontSize:11, color:C.textMuted, marginBottom:6, fontWeight:600 }}>공통 취향</div>
            <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
              {commonTags.map(t => <span key={t} style={{ fontSize:12, background:C.card, color:C.sky, padding:"3px 10px", borderRadius:"999px", border:`1px solid ${C.sky}44` }}>{t}</span>)}
            </div>
          </div>
        )}
        <div style={{ display:"flex", flexDirection:"column", gap:12, marginBottom:28 }}>
          {schedule.map((item: any, i: number) => <CourseCard key={i} item={item} index={i} />)}
        </div>
        <div style={{ display:"flex", gap:10 }}>
          <button onClick={reset} style={{ flex:1, padding: isMobile?12:14, background:C.card, border:`1.5px solid ${C.cardBorder}`, borderRadius:14, color:C.textDim, fontSize: isMobile?13:14, cursor:"pointer", fontFamily:"'Noto Sans KR',sans-serif" }}>다시 시작</button>
        </div>
      </div>
    </div>
  );
}
