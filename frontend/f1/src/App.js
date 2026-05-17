import { useState } from "react";

// ════════════════════════════════════════════════════════════
//  DateFlow — 1주차
//  디자인 시스템: FE2 기준 (보라/핑크/하늘 계열)
// ════════════════════════════════════════════════════════════

const PREFERENCE_TAGS = {
  분위기: ["조용한 분위기", "활기찬 분위기", "로맨틱", "캐주얼", "고급스러운"],
  활동:   ["전시·문화", "맛집 탐방", "활동적인 코스", "핫플 방문", "산책·자연"],
  카페:   ["여유로운 카페", "감성 카페", "디저트 맛집", "브런치"],
};

const MOCK_COURSE = {
  commonTags: ["감성적인 공간", "새로운 경험", "함께 즐기는 식사"],
  schedule: [
    { time:"13:00", place:"성수 갤러리 카페",      desc:"전시 + 커피 · 조용하면서도 감성적인 핫플",           scoreA:90, scoreB:70, tag:"전시·문화",    indoor:true  },
    { time:"15:00", place:"성수 팝업 스토어 거리",  desc:"걸으며 구경하는 활동적 코스 · 무료입장",             scoreA:65, scoreB:88, tag:"활동적인 코스", indoor:false },
    { time:"17:30", place:"성수 오마카세 맛집",     desc:"분위기 있는 식사 · B님 맛집 욕구 + A님 고급 분위기", scoreA:85, scoreB:92, tag:"맛집 탐방",    indoor:true  },
  ],
};

// ── 디자인 시스템 (FE2 기준) ─────────────────────────────────
const C = {
  bg:          "#F5F3FB",   // 페이지 배경
  card:        "#FFFFFF",   // 카드 배경
  cardBorder:  "#E8E4F4",   // 테두리
  main:        "#B8A9D9",   // 메인 (보라)
  mainDim:     "#EAE5F5",   // 메인 연하게
  point:       "#E8A0B4",   // 포인트 (핑크)
  pointDim:    "#FCE8EE",   // 핑크 연하게
  sub:         "#D4849A",   // 서브 (로즈)
  sky:         "#A8C4E0",   // 배경/강조 (하늘)
  skyDim:      "#DFF0F9",   // 하늘 연하게
  text:        "#3D3257",   // 텍스트 (짙은 보라)
  textDim:     "#7B6FA0",   // 텍스트 흐리게
  textMuted:   "#B0A8CC",   // 텍스트 더 흐리게
  inputBg:     "#F0EDF9",   // 인풋 배경
  inputBorder: "#D8D0EE",   // 인풋 테두리
  error:       "#E87070",
  errorBg:     "#FDE8E8",
};

const GS = `
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  @keyframes fadeUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:none} }
  @keyframes fadeIn { from{opacity:0} to{opacity:1} }
  @keyframes spin   { to{transform:rotate(360deg)} }
  @keyframes pulse  { 0%,100%{opacity:1} 50%{opacity:0.45} }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#F5F3FB; }
  input:focus { border-color:#B8A9D9 !important; outline:none; box-shadow:0 0 0 3px #B8A9D922; }
`;

// ── 서브 컴포넌트 ─────────────────────────────────────────────
function TagButton({ label, selected, onClick }) {
  return (
    <button onClick={onClick} style={{
      padding: "8px 16px", borderRadius: "999px",
      border: selected ? "none" : `1.5px solid ${C.cardBorder}`,
      background: selected ? C.main : C.card,
      color: selected ? "#FFFFFF" : C.textDim,
      fontSize: 13, fontFamily: "'Noto Sans KR', sans-serif",
      fontWeight: selected ? 700 : 400, cursor: "pointer",
      transition: "all 0.18s", boxShadow: selected ? "0 2px 8px #B8A9D940" : "none",
    }}>{label}</button>
  );
}

function ScoreBar({ label, score, color }) {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:10, marginTop:6 }}>
      <span style={{ fontSize:12, color:C.textMuted, width:30, fontFamily:"'Noto Sans KR',sans-serif" }}>{label}</span>
      <div style={{ flex:1, height:6, background:C.inputBg, borderRadius:"999px", overflow:"hidden" }}>
        <div style={{ width:`${score}%`, height:"100%", background:color, borderRadius:"999px", transition:"width 0.8s cubic-bezier(0.4,0,0.2,1)" }} />
      </div>
      <span style={{ fontSize:12, color:C.textDim, width:32, textAlign:"right", fontFamily:"monospace" }}>{score}%</span>
    </div>
  );
}

function CourseCard({ item, index }) {
  return (
    <div style={{
      background: C.card, border: `1px solid ${C.cardBorder}`,
      borderRadius: 20, padding: 20,
      boxShadow: "0 2px 16px #B8A9D918",
      animation: `fadeUp 0.4s ease ${index * 0.12}s both`,
    }}>
      <div style={{ display:"flex", alignItems:"flex-start", gap:14 }}>
        <div style={{
          background: C.mainDim, color: C.main, fontSize:13, fontWeight:700,
          fontFamily:"monospace", padding:"6px 10px", borderRadius:12,
          whiteSpace:"nowrap", flexShrink:0,
        }}>{item.time}</div>
        <div style={{ flex:1 }}>
          <div style={{ display:"flex", alignItems:"center", gap:8, flexWrap:"wrap", marginBottom:4 }}>
            <span style={{ fontSize:16, fontWeight:700, color:C.text, fontFamily:"'Noto Sans KR',sans-serif" }}>{item.place}</span>
            <span style={{ fontSize:11, background:C.pointDim, color:C.sub, padding:"2px 8px", borderRadius:"999px" }}>{item.tag}</span>
            <span style={{ fontSize:11, background:item.indoor?C.skyDim:"#F0FBF0", color:item.indoor?C.sky:"#6aaa8a", padding:"2px 8px", borderRadius:"999px" }}>
              {item.indoor?"실내":"실외"}
            </span>
          </div>
          <p style={{ margin:"0 0 10px", fontSize:13, color:C.textDim, lineHeight:1.6, fontFamily:"'Noto Sans KR',sans-serif" }}>{item.desc}</p>
          <ScoreBar label="A님" score={item.scoreA} color={C.main} />
          <ScoreBar label="B님" score={item.scoreB} color={C.point} />
        </div>
      </div>
    </div>
  );
}

function ProgressBar({ step, total=2 }) {
  return (
    <div style={{ display:"flex", gap:6, marginBottom:32 }}>
      {Array.from({length:total}, (_,i) => (
        <div key={i} style={{ flex:1, height:4, borderRadius:"999px", background: i<step ? C.main : C.cardBorder, transition:"background 0.3s" }} />
      ))}
    </div>
  );
}

function NavButtons({ onBack, onNext, nextLabel }) {
  return (
    <div style={{ display:"flex", gap:10, marginTop:8 }}>
      <button onClick={onBack} style={{
        flex:1, padding:14, background:C.card,
        border:`1.5px solid ${C.cardBorder}`, borderRadius:14,
        color:C.textDim, fontSize:14, cursor:"pointer",
        fontFamily:"'Noto Sans KR',sans-serif", fontWeight:500,
      }}>← 이전</button>
      <button onClick={onNext} style={{
        flex:2, padding:14, background:C.main,
        border:"none", borderRadius:14,
        color:"#FFFFFF", fontSize:15, fontWeight:700,
        cursor:"pointer", fontFamily:"'Noto Sans KR',sans-serif",
        boxShadow:"0 4px 14px #B8A9D940", transition:"all 0.2s",
      }}>{nextLabel}</button>
    </div>
  );
}

// ── 메인 앱 ──────────────────────────────────────────────────
export default function DateFlow() {
  const [step, setStep]   = useState(0);
  const [area, setArea]   = useState("");
  const [tagsA, setTagsA] = useState([]);
  const [tagsB, setTagsB] = useState([]);
  const [loading, setLoading] = useState(false);

  const toggleTag = (tag, who) => {
    const [get, set] = who==="A" ? [tagsA,setTagsA] : [tagsB,setTagsB];
    set(get.includes(tag) ? get.filter(t=>t!==tag) : [...get,tag]);
  };

  const handleGenerate = () => {
    setLoading(true);
    setTimeout(() => { setLoading(false); setStep(4); }, 1600);
  };

  const reset = () => { setStep(0); setTagsA([]); setTagsB([]); setArea(""); };

  const wrap  = { minHeight:"100vh", background:C.bg, fontFamily:"'Noto Sans KR',sans-serif", display:"flex", flexDirection:"column", alignItems:"center", padding:"0 0 80px" };
  const inner = { maxWidth:"420px", width:"100%", padding:"48px 20px 0" };

  // 로딩
  if (loading) return (
    <div style={{ ...wrap, justifyContent:"center", alignItems:"center" }}>
      <style>{GS}</style>
      <div style={{ textAlign:"center" }}>
        <div style={{ fontSize:40, animation:"spin 1.6s linear infinite", display:"inline-block", marginBottom:20, color:C.main }}>◎</div>
        <p style={{ color:C.main, fontSize:15, animation:"pulse 1.5s ease infinite", fontFamily:"'Noto Sans KR',sans-serif" }}>취향을 분석 중이에요...</p>
      </div>
    </div>
  );

  // STEP 0: 온보딩
  if (step === 0) return (
    <div style={wrap}>
      <style>{GS}</style>
      <div style={{ ...inner, paddingTop:64, animation:"fadeUp 0.5s ease" }}>
        <div style={{ fontSize:11, letterSpacing:"0.2em", color:C.main, marginBottom:16, textTransform:"uppercase", fontWeight:600 }}>Capstone 12조</div>
        <h1 style={{ fontSize:40, fontWeight:900, color:C.text, margin:"0 0 8px", lineHeight:1.15, letterSpacing:"-0.03em" }}>
          Date<span style={{ color:C.main }}>Flow</span>
        </h1>
        <p style={{ fontSize:15, color:C.textDim, margin:"0 0 36px", lineHeight:1.7 }}>
          두 사람의 취향을 분석해<br />딱 맞는 데이트 코스를 만들어드려요
        </p>

        {[
          { icon:"✦", text:"각자의 취향을 따로 입력", color:C.main },
          { icon:"◎", text:"AI가 교집합 장소를 자동 분석", color:C.point },
          { icon:"→", text:"시간표 형태 데이트 코스 생성", color:C.sky },
        ].map((x,i) => (
          <div key={i} style={{ display:"flex", alignItems:"center", gap:14, marginBottom:12, animation:`fadeUp 0.5s ease ${0.08+i*0.08}s both` }}>
            <span style={{ color:x.color, fontSize:16, width:22, textAlign:"center" }}>{x.icon}</span>
            <span style={{ fontSize:14, color:C.textDim }}>{x.text}</span>
          </div>
        ))}

        <div style={{ marginTop:32, marginBottom:20 }}>
          <label style={{ fontSize:12, color:C.textDim, display:"block", marginBottom:8, fontWeight:500 }}>데이트 지역</label>
          <input
            value={area} onChange={e=>setArea(e.target.value)}
            placeholder="예: 성수동, 홍대, 강남"
            style={{ width:"100%", padding:"14px 16px", background:C.card, border:`1.5px solid ${C.inputBorder}`, borderRadius:14, color:C.text, fontSize:15, fontFamily:"'Noto Sans KR',sans-serif" }}
          />
        </div>

        <button onClick={()=>setStep(1)} disabled={!area.trim()} style={{
          width:"100%", padding:16,
          background: area.trim() ? C.main : C.inputBg,
          color: area.trim() ? "#FFFFFF" : C.textMuted,
          border:"none", borderRadius:14, fontSize:16, fontWeight:700,
          cursor: area.trim() ? "pointer" : "not-allowed",
          fontFamily:"'Noto Sans KR',sans-serif",
          boxShadow: area.trim() ? "0 4px 20px #B8A9D950" : "none",
          transition:"all 0.2s",
        }}>시작하기 →</button>
      </div>
    </div>
  );

  // STEP 1, 2: 취향 입력
  if (step === 1 || step === 2) {
    const who      = step === 1 ? "A" : "B";
    const tagColor = step === 1 ? C.main : C.point;
    const selected = step === 1 ? tagsA : tagsB;

    return (
      <div style={wrap}>
        <style>{GS}</style>
        <div style={{ ...inner, animation:"fadeUp 0.35s ease" }}>
          <ProgressBar step={step} total={2} />
          <div style={{ fontSize:11, color:C.main, marginBottom:10, letterSpacing:"0.1em", textTransform:"uppercase", fontWeight:600 }}>Step {step} / 2</div>
          <h2 style={{ fontSize:26, fontWeight:700, color:C.text, margin:"0 0 4px" }}>
            <span style={{ color:tagColor }}>{who}님</span>의 취향을 알려주세요
          </h2>
          <p style={{ fontSize:13, color:C.textMuted, margin:"0 0 28px" }}>여러 개 선택 가능해요</p>

          {Object.entries(PREFERENCE_TAGS).map(([cat, list]) => (
            <div key={cat} style={{ marginBottom:24 }}>
              <div style={{ fontSize:11, color:C.textMuted, marginBottom:10, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:600 }}>{cat}</div>
              <div style={{ display:"flex", flexWrap:"wrap", gap:8 }}>
                {list.map(t => <TagButton key={t} label={t} selected={selected.includes(t)} onClick={()=>toggleTag(t,who)} />)}
              </div>
            </div>
          ))}

          {selected.length > 0 && (
            <div style={{ background:C.mainDim, border:`1px solid ${C.cardBorder}`, borderRadius:14, padding:"12px 16px", marginBottom:20 }}>
              <div style={{ fontSize:11, color:C.main, marginBottom:8, fontWeight:600 }}>선택됨</div>
              <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                {selected.map(t => <span key={t} style={{ fontSize:12, background:C.main, color:"#fff", padding:"3px 10px", borderRadius:"999px" }}>{t}</span>)}
              </div>
            </div>
          )}

          <NavButtons
            onBack={()=>setStep(step-1)}
            onNext={()=>step===1?setStep(2):handleGenerate()}
            nextLabel={step===1?"B님 취향 입력 →":"코스 생성하기 ✦"}
          />
        </div>
      </div>
    );
  }

  // STEP 4: 결과
  return (
    <div style={wrap}>
      <style>{GS}</style>
      <div style={{ ...inner, animation:"fadeUp 0.4s ease" }}>
        <div style={{ fontSize:11, color:C.main, marginBottom:10, letterSpacing:"0.15em", textTransform:"uppercase", fontWeight:600 }}>
          DateFlow · {area}
        </div>
        <h2 style={{ fontSize:24, fontWeight:700, color:C.text, margin:"0 0 20px" }}>절충 데이트 코스 ✦</h2>

        {/* 취향 요약 */}
        <div style={{ background:C.card, border:`1px solid ${C.cardBorder}`, borderRadius:20, padding:18, marginBottom:20, boxShadow:"0 2px 12px #B8A9D912" }}>
          {[
            { label:"A님 선호", tags:tagsA.length?tagsA:["조용한 분위기","전시·문화"], color:C.main, dimColor:C.mainDim },
            { label:"B님 선호", tags:tagsB.length?tagsB:["맛집 탐방","활동적인 코스"], color:C.point, dimColor:C.pointDim },
          ].map(({ label,tags,color,dimColor }) => (
            <div key={label} style={{ marginBottom:14 }}>
              <div style={{ fontSize:11, color:C.textMuted, marginBottom:6, fontWeight:600 }}>{label}</div>
              <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
                {tags.slice(0,4).map(t => <span key={t} style={{ fontSize:12, background:dimColor, color, padding:"3px 10px", borderRadius:"999px", border:`1px solid ${color}44` }}>{t}</span>)}
              </div>
            </div>
          ))}
          <div style={{ borderTop:`1px solid ${C.cardBorder}`, paddingTop:14, marginTop:4 }}>
            <div style={{ fontSize:11, color:C.textMuted, marginBottom:6, fontWeight:600 }}>공통 교집합</div>
            <div style={{ display:"flex", flexWrap:"wrap", gap:6 }}>
              {MOCK_COURSE.commonTags.map(t => <span key={t} style={{ fontSize:12, background:C.skyDim, color:C.sky, padding:"3px 10px", borderRadius:"999px", border:`1px solid ${C.sky}44` }}>{t}</span>)}
            </div>
          </div>
        </div>

        {/* 코스 카드 */}
        <div style={{ display:"flex", flexDirection:"column", gap:12, marginBottom:28 }}>
          {MOCK_COURSE.schedule.map((item,i) => <CourseCard key={i} item={item} index={i} />)}
        </div>

        <div style={{ display:"flex", gap:10 }}>
          <button onClick={reset} style={{ flex:1, padding:14, background:C.card, border:`1.5px solid ${C.cardBorder}`, borderRadius:14, color:C.textDim, fontSize:14, cursor:"pointer", fontFamily:"'Noto Sans KR',sans-serif" }}>
            다시 시작
          </button>
          <button style={{ flex:2, padding:14, background:C.main, border:"none", borderRadius:14, color:"#fff", fontSize:15, fontWeight:700, cursor:"pointer", fontFamily:"'Noto Sans KR',sans-serif", boxShadow:"0 4px 14px #B8A9D940" }}>
            웨이팅 적은 시간대로 ↗
          </button>
        </div>
        <p style={{ textAlign:"center", fontSize:11, color:C.textMuted, marginTop:20 }}>※ Mock 데이터 기반 · 3주차에 실제 API 연결 예정</p>
      </div>
    </div>
  );
}