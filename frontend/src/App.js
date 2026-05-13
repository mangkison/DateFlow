import { useState } from "react";

// ════════════════════════════════════════════════════════════
//  DateFlow — 1주차
//  React 프로젝트 세팅 / 온보딩·취향 입력 화면 UI (Mock 데이터 기반)
//
//  포함 기능:
//  - 온보딩 화면 (지역 입력)
//  - A님 / B님 취향 태그 입력 (각자)
//  - Mock 코스 결과 화면 (시간대별 카드 + 만족도 바)
//  - 공통 교집합 태그 표시
//
//  미포함 (다음 주차):
//  - 날씨 API, 예산 슬라이더, 백엔드 연결, 예외 UI, 반응형
// ════════════════════════════════════════════════════════════

// ── Mock 데이터 ──────────────────────────────────────────────
const PREFERENCE_TAGS = {
  분위기: ["조용한 분위기", "활기찬 분위기", "로맨틱", "캐주얼", "고급스러운"],
  활동:   ["전시·문화", "맛집 탐방", "활동적인 코스", "핫플 방문", "산책·자연"],
  카페:   ["여유로운 카페", "감성 카페", "디저트 맛집", "브런치"],
};

const MOCK_COURSE = {
  commonTags: ["감성적인 공간", "새로운 경험", "함께 즐기는 식사"],
  schedule: [
    { time: "13:00", place: "성수 갤러리 카페",      desc: "전시 + 커피 · 조용하면서도 감성적인 핫플",           scoreA: 90, scoreB: 70, tag: "전시·문화",    indoor: true  },
    { time: "15:00", place: "성수 팝업 스토어 거리",  desc: "걸으며 구경하는 활동적 코스 · 무료입장",             scoreA: 65, scoreB: 88, tag: "활동적인 코스", indoor: false },
    { time: "17:30", place: "성수 오마카세 맛집",     desc: "분위기 있는 식사 · B님 맛집 욕구 + A님 고급 분위기", scoreA: 85, scoreB: 92, tag: "맛집 탐방",    indoor: true  },
  ],
};

// ── 스타일 상수 ──────────────────────────────────────────────
const C = {
  bg: "#0f1410", card: "#1a2016", cardBorder: "#2e3828",
  green: "#7aaa4a", greenDim: "#2d4a1e", gold: "#b08840", blue: "#6aaad0",
  text: "#d4e8b8", textDim: "#8a9a70", textMuted: "#5a7040",
  inputBg: "#141810", inputBorder: "#2a3020",
};

const GS = `
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
  @keyframes fadeUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:none} }
  @keyframes fadeIn { from{opacity:0} to{opacity:1} }
  @keyframes spin   { to{transform:rotate(360deg)} }
  @keyframes pulse  { 0%,100%{opacity:1} 50%{opacity:0.45} }
  * { box-sizing:border-box; }
  input:focus { border-color:#7aaa4a !important; outline:none; }
`;

const TOTAL_STEPS = 2; // A님 취향, B님 취향

// ── 서브 컴포넌트 ────────────────────────────────────────────
function TagButton({ label, selected, onClick }) {
  return (
    <button onClick={onClick} style={{
      padding: "8px 16px", borderRadius: "999px",
      border: selected ? "none" : "1.5px solid #4a5240",
      background: selected ? C.green : "transparent",
      color: selected ? "#1a1f14" : C.textDim,
      fontSize: 13, fontFamily: "'Noto Sans KR', sans-serif",
      fontWeight: selected ? 700 : 400, cursor: "pointer", transition: "all 0.18s",
    }}>{label}</button>
  );
}

function ScoreBar({ label, score, color }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 6 }}>
      <span style={{ fontSize: 12, color: "#8a9980", width: 30, fontFamily: "'Noto Sans KR', sans-serif" }}>{label}</span>
      <div style={{ flex: 1, height: 6, background: "#2a2f24", borderRadius: "999px", overflow: "hidden" }}>
        <div style={{ width: `${score}%`, height: "100%", background: color, borderRadius: "999px", transition: "width 0.8s cubic-bezier(0.4,0,0.2,1)" }} />
      </div>
      <span style={{ fontSize: 12, color: "#c0d0a8", width: 32, textAlign: "right", fontFamily: "monospace" }}>{score}%</span>
    </div>
  );
}

function CourseCard({ item, index }) {
  return (
    <div style={{
      background: C.card, border: `1px solid ${C.cardBorder}`,
      borderRadius: 16, padding: 20,
      animation: `fadeUp 0.4s ease ${index * 0.12}s both`,
    }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 14 }}>
        <div style={{
          background: C.greenDim, color: "#a8c87a", fontSize: 13, fontWeight: 700,
          fontFamily: "monospace", padding: "6px 10px", borderRadius: 10,
          whiteSpace: "nowrap", flexShrink: 0,
        }}>{item.time}</div>
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", marginBottom: 4 }}>
            <span style={{ fontSize: 16, fontWeight: 700, color: "#e8f0d8", fontFamily: "'Noto Sans KR', sans-serif" }}>{item.place}</span>
            <span style={{ fontSize: 11, background: "#3a4830", color: "#8aaa60", padding: "2px 8px", borderRadius: "999px" }}>{item.tag}</span>
            <span style={{ fontSize: 11, background: item.indoor ? "#1e2a3a" : "#1a2e1a", color: item.indoor ? "#6ab0d0" : "#7aaa6a", padding: "2px 8px", borderRadius: "999px" }}>
              {item.indoor ? "실내" : "실외"}
            </span>
          </div>
          <p style={{ margin: "0 0 10px", fontSize: 13, color: "#7a8a6a", fontFamily: "'Noto Sans KR', sans-serif", lineHeight: 1.5 }}>{item.desc}</p>
          <ScoreBar label="A님" score={item.scoreA} color={C.green} />
          <ScoreBar label="B님" score={item.scoreB} color={C.gold} />
        </div>
      </div>
    </div>
  );
}

function ProgressBar({ step }) {
  return (
    <div style={{ display: "flex", gap: 6, marginBottom: 32 }}>
      {Array.from({ length: TOTAL_STEPS }, (_, i) => (
        <div key={i} style={{ flex: 1, height: 3, borderRadius: "999px", background: i < step ? C.green : "#2a3020", transition: "background 0.3s" }} />
      ))}
    </div>
  );
}

function NavButtons({ onBack, onNext, nextLabel, nextDisabled }) {
  return (
    <div style={{ display: "flex", gap: 10 }}>
      <button onClick={onBack} style={{
        flex: 1, padding: 14, background: "transparent",
        border: `1.5px solid ${C.cardBorder}`, borderRadius: 12,
        color: C.textMuted, fontSize: 14, cursor: "pointer", fontFamily: "'Noto Sans KR', sans-serif",
      }}>← 이전</button>
      <button onClick={onNext} disabled={nextDisabled} style={{
        flex: 2, padding: 14,
        background: nextDisabled ? "#2a3020" : C.green,
        border: "none", borderRadius: 12,
        color: nextDisabled ? "#3a4830" : "#0f1410",
        fontSize: 15, fontWeight: 700,
        cursor: nextDisabled ? "not-allowed" : "pointer",
        fontFamily: "'Noto Sans KR', sans-serif", transition: "all 0.2s",
      }}>{nextLabel}</button>
    </div>
  );
}

// ── 메인 앱 ──────────────────────────────────────────────────
export default function DateFlow() {
  // step: 0 온보딩 / 1 A님 취향 / 2 B님 취향 / 3 로딩 / 4 결과
  const [step, setStep]   = useState(0);
  const [area, setArea]   = useState("");
  const [tagsA, setTagsA] = useState([]);
  const [tagsB, setTagsB] = useState([]);
  const [loading, setLoading] = useState(false);

  const toggleTag = (tag, who) => {
    const [get, set] = who === "A" ? [tagsA, setTagsA] : [tagsB, setTagsB];
    set(get.includes(tag) ? get.filter(t => t !== tag) : [...get, tag]);
  };

  // Mock 생성: 실제 API 대신 setTimeout
  const handleGenerate = () => {
    setLoading(true);
    setTimeout(() => { setLoading(false); setStep(4); }, 1600);
  };

  const reset = () => { setStep(0); setTagsA([]); setTagsB([]); setArea(""); };

  const wrap  = { minHeight: "100vh", background: C.bg, color: C.text, fontFamily: "'Noto Sans KR', sans-serif", display: "flex", flexDirection: "column", alignItems: "center", padding: "0 0 80px" };
  const inner = { maxWidth: "420px", width: "100%", padding: "48px 24px 0" };

  // ── 로딩 ─────────────────────────────────────────────────
  if (loading) return (
    <div style={{ ...wrap, justifyContent: "center", alignItems: "center" }}>
      <style>{GS}</style>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 40, animation: "spin 1.6s linear infinite", display: "inline-block", marginBottom: 20 }}>◎</div>
        <p style={{ color: C.green, fontSize: 15, animation: "pulse 1.5s ease infinite", margin: 0, fontFamily: "'Noto Sans KR', sans-serif" }}>
          취향을 분석 중이에요...
        </p>
      </div>
    </div>
  );

  // ── STEP 0: 온보딩 ───────────────────────────────────────
  if (step === 0) return (
    <div style={wrap}>
      <style>{GS}</style>
      <div style={{ ...inner, paddingTop: 64, animation: "fadeUp 0.5s ease" }}>
        <div style={{ fontSize: 11, letterSpacing: "0.2em", color: C.textMuted, marginBottom: 16, textTransform: "uppercase" }}>Capstone 12조</div>
        <h1 style={{ fontSize: 42, fontWeight: 900, color: "#c8e8a0", margin: "0 0 8px", lineHeight: 1.1, letterSpacing: "-0.03em" }}>
          Date<span style={{ color: C.green }}>Flow</span>
        </h1>
        <p style={{ fontSize: 15, color: "#6a8050", margin: "0 0 36px", lineHeight: 1.6 }}>
          두 사람의 취향을 분석해<br />딱 맞는 데이트 코스를 만들어드려요
        </p>

        {[
          { icon: "✦", text: "각자의 취향을 따로 입력" },
          { icon: "◎", text: "AI가 교집합 장소를 자동 분석" },
          { icon: "→", text: "시간표 형태 데이트 코스 생성" },
        ].map((x, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 14, marginBottom: 10, animation: `fadeUp 0.5s ease ${0.08 + i * 0.08}s both` }}>
            <span style={{ color: C.green, fontSize: 16, width: 22, textAlign: "center" }}>{x.icon}</span>
            <span style={{ fontSize: 14, color: "#8aaa70" }}>{x.text}</span>
          </div>
        ))}

        <div style={{ marginTop: 36, marginBottom: 20 }}>
          <label style={{ fontSize: 12, color: C.textMuted, display: "block", marginBottom: 8, letterSpacing: "0.05em" }}>데이트 지역</label>
          <input
            value={area} onChange={e => setArea(e.target.value)}
            placeholder="예: 성수동, 홍대, 강남"
            style={{ width: "100%", padding: "14px 16px", background: C.inputBg, border: `1.5px solid ${C.inputBorder}`, borderRadius: 12, color: C.text, fontSize: 15, fontFamily: "'Noto Sans KR', sans-serif" }}
          />
        </div>

        <button onClick={() => setStep(1)} disabled={!area.trim()} style={{
          width: "100%", padding: 16,
          background: area.trim() ? C.green : "#2a3020",
          color: area.trim() ? "#0f1410" : "#3a4830",
          border: "none", borderRadius: 14, fontSize: 16, fontWeight: 700,
          cursor: area.trim() ? "pointer" : "not-allowed",
          fontFamily: "'Noto Sans KR', sans-serif", transition: "all 0.2s",
        }}>시작하기 →</button>
      </div>
    </div>
  );

  // ── STEP 1, 2: 취향 입력 ────────────────────────────────
  if (step === 1 || step === 2) {
    const who      = step === 1 ? "A" : "B";
    const color    = step === 1 ? C.green : C.gold;
    const selected = step === 1 ? tagsA : tagsB;

    return (
      <div style={wrap}>
        <style>{GS}</style>
        <div style={{ ...inner, animation: "fadeUp 0.35s ease" }}>
          <ProgressBar step={step} />
          <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 10, letterSpacing: "0.1em", textTransform: "uppercase" }}>Step {step} / {TOTAL_STEPS}</div>
          <h2 style={{ fontSize: 26, fontWeight: 700, color: "#c8e8a0", margin: "0 0 4px" }}>
            <span style={{ color }}>{who}님</span>의 취향을 알려주세요
          </h2>
          <p style={{ fontSize: 13, color: C.textMuted, margin: "0 0 24px" }}>여러 개 선택 가능해요</p>

          {Object.entries(PREFERENCE_TAGS).map(([cat, list]) => (
            <div key={cat} style={{ marginBottom: 20 }}>
              <div style={{ fontSize: 11, color: "#4a5a38", marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.1em" }}>{cat}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
                {list.map(t => <TagButton key={t} label={t} selected={selected.includes(t)} onClick={() => toggleTag(t, who)} />)}
              </div>
            </div>
          ))}

          {selected.length > 0 && (
            <div style={{ background: C.inputBg, border: `1px solid ${C.inputBorder}`, borderRadius: 12, padding: "12px 16px", marginBottom: 20 }}>
              <div style={{ fontSize: 11, color: "#4a6030", marginBottom: 6 }}>선택됨</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {selected.map(t => (
                  <span key={t} style={{ fontSize: 12, background: "#2d4020", color: "#9aba70", padding: "3px 10px", borderRadius: "999px" }}>{t}</span>
                ))}
              </div>
            </div>
          )}

          <NavButtons
            onBack={() => setStep(step - 1)}
            onNext={() => step === 1 ? setStep(2) : handleGenerate()}
            nextLabel={step === 1 ? "B님 취향 입력 →" : "코스 생성하기 ✦"}
          />
        </div>
      </div>
    );
  }

  // ── STEP 4: 결과 ────────────────────────────────────────
  return (
    <div style={wrap}>
      <style>{GS}</style>
      <div style={{ ...inner, animation: "fadeUp 0.4s ease" }}>
        <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 10, letterSpacing: "0.15em", textTransform: "uppercase" }}>
          DateFlow · {area}
        </div>
        <h2 style={{ fontSize: 24, fontWeight: 700, color: "#c8e8a0", margin: "0 0 20px" }}>절충 데이트 코스 ✦</h2>

        {/* 취향 요약 */}
        <div style={{ background: C.inputBg, border: `1px solid ${C.inputBorder}`, borderRadius: 14, padding: 18, marginBottom: 20 }}>
          {[
            { label: "A님 선호", tags: tagsA.length ? tagsA : ["조용한 분위기", "전시·문화"], color: C.green },
            { label: "B님 선호", tags: tagsB.length ? tagsB : ["맛집 탐방", "활동적인 코스"], color: C.gold  },
          ].map(({ label, tags, color }) => (
            <div key={label} style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: "#4a5a38", marginBottom: 6 }}>{label}</div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
                {tags.slice(0, 4).map(t => (
                  <span key={t} style={{ fontSize: 12, background: color + "22", color, padding: "3px 10px", borderRadius: "999px", border: `1px solid ${color}44` }}>{t}</span>
                ))}
              </div>
            </div>
          ))}
          <div style={{ borderTop: `1px solid ${C.inputBorder}`, paddingTop: 12, marginTop: 4 }}>
            <div style={{ fontSize: 11, color: "#4a5a38", marginBottom: 6 }}>공통 교집합</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {MOCK_COURSE.commonTags.map(t => (
                <span key={t} style={{ fontSize: 12, background: "#1e2e3a", color: C.blue, padding: "3px 10px", borderRadius: "999px", border: "1px solid #2a4a5a" }}>{t}</span>
              ))}
            </div>
          </div>
        </div>

        {/* 코스 카드 */}
        <div style={{ display: "flex", flexDirection: "column", gap: 12, marginBottom: 28 }}>
          {MOCK_COURSE.schedule.map((item, i) => <CourseCard key={i} item={item} index={i} />)}
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          <button onClick={reset} style={{ flex: 1, padding: 14, background: "transparent", border: `1.5px solid ${C.cardBorder}`, borderRadius: 12, color: C.textMuted, fontSize: 14, cursor: "pointer", fontFamily: "'Noto Sans KR', sans-serif" }}>
            다시 시작
          </button>
          <button style={{ flex: 2, padding: 14, background: C.green, border: "none", borderRadius: 12, color: "#0f1410", fontSize: 15, fontWeight: 700, cursor: "pointer", fontFamily: "'Noto Sans KR', sans-serif" }}>
            웨이팅 적은 시간대로 ↗
          </button>
        </div>

        <p style={{ textAlign: "center", fontSize: 11, color: "#3a4830", marginTop: 20 }}>
          ※ Mock 데이터 기반 · 3주차에 실제 API 연결 예정
        </p>
      </div>
    </div>
  );
}