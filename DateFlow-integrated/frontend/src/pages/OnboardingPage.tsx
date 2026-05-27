import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8001";

const TAGS: Record<string, string[]> = {
  분위기: ["조용한 분위기", "활기찬 분위기", "로맨틱", "캐주얼", "고급스러운"],
  활동:   ["전시·문화", "맛집 탐방", "활동적인 코스", "핫플 방문", "산책·자연"],
  카페:   ["여유로운 카페", "감성 카페", "디저트 맛집", "브런치"],
};

const C = {
  bg: "#F5F3FB", card: "#FFFFFF", border: "#E8E4F4",
  main: "#B8A9D9", mainDim: "#EAE5F5",
  point: "#E8A0B4", pointDim: "#FCE8EE",
  text: "#3D3257", textDim: "#7B6FA0", textMuted: "#B0A8CC",
  inputBg: "#F0EDF9", inputBorder: "#D8D0EE",
};

const GS = `
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  @keyframes fadeUp { from{opacity:0;transform:translateY(14px)} to{opacity:1;transform:none} }
  @keyframes spin { to{transform:rotate(360deg)} }
  @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.45} }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#F5F3FB; }
`;

function TagBtn({ label, selected, color, onClick }: { label: string; selected: boolean; color: string; onClick: () => void }) {
  return (
    <button onClick={onClick} style={{
      padding: "8px 16px", borderRadius: "999px",
      border: selected ? "none" : `1.5px solid ${C.border}`,
      background: selected ? color : C.card,
      color: selected ? "#fff" : C.textDim,
      fontSize: 13, cursor: "pointer",
      fontFamily: "'Noto Sans KR',sans-serif",
      fontWeight: selected ? 700 : 400,
      transition: "all 0.16s",
      boxShadow: selected ? `0 2px 8px ${color}40` : "none",
    }}>{label}</button>
  );
}

function ProgressBar({ step }: { step: number }) {
  return (
    <div style={{ display: "flex", gap: 6, marginBottom: 28 }}>
      {[0, 1].map(i => (
        <div key={i} style={{ flex: 1, height: 4, borderRadius: 999, background: i < step ? C.main : C.border, transition: "background 0.3s" }} />
      ))}
    </div>
  );
}

export default function OnboardingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [step, setStep] = useState(0); // 0=남자, 1=여자
  const [manTags, setManTags] = useState<string[]>([]);
  const [womanTags, setWomanTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const toggle = (tag: string, step: number) => {
    if (step === 0) setManTags(p => p.includes(tag) ? p.filter(t => t !== tag) : [...p, tag]);
    else setWomanTags(p => p.includes(tag) ? p.filter(t => t !== tag) : [...p, tag]);
  };

  const current = step === 0 ? manTags : womanTags;
  const color = step === 0 ? C.main : C.point;
  const label = step === 0 ? "남자친구" : "여자친구";

  const handleNext = async () => {
    if (step === 0) { setStep(1); return; }

    // 취향 저장 후 채팅 페이지로
    setLoading(true);
    setError("");
    try {
      if (user) {
        await fetch(`${API}/prefs`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${user.token}`,
          },
          body: JSON.stringify({
            user_id: user.user_id,
            mood: manTags[0] ?? womanTags[0] ?? "",
            food_type: [...manTags, ...womanTags],
            budget: 80000,
            age_group: "20대",
            person1: { tags: manTags, gender: "M" },
            person2: { tags: womanTags, gender: "F" },
          }),
        });
      }
      navigate("/chat", { state: { manTags, womanTags } });
    } catch {
      setError("저장에 실패했습니다. 다시 시도해주세요.");
    } finally {
      setLoading(false);
    }
  };

  if (loading) return (
    <div style={{ minHeight: "100vh", background: C.bg, display: "flex", alignItems: "center", justifyContent: "center" }}>
      <style>{GS}</style>
      <div style={{ textAlign: "center" }}>
        <div style={{ fontSize: 38, animation: "spin 1.4s linear infinite", display: "inline-block", marginBottom: 16, color: C.main }}>◎</div>
        <p style={{ color: C.main, fontSize: 14, animation: "pulse 1.4s ease infinite", fontFamily: "'Noto Sans KR',sans-serif" }}>취향을 저장하는 중...</p>
      </div>
    </div>
  );

  return (
    <div style={{ minHeight: "100vh", background: C.bg, display: "flex", flexDirection: "column", alignItems: "center", paddingBottom: 80 }}>
      <style>{GS}</style>
      <div style={{ maxWidth: 420, width: "100%", padding: "48px 20px 0", animation: "fadeUp 0.35s ease" }}>

        <ProgressBar step={step + 1} />

        <div style={{ fontSize: 11, color, marginBottom: 8, letterSpacing: "0.1em", textTransform: "uppercase", fontWeight: 600 }}>
          Step {step + 1} / 2
        </div>
        <h2 style={{ fontSize: 26, fontWeight: 700, color: C.text, margin: "0 0 4px", fontFamily: "'Noto Sans KR',sans-serif" }}>
          <span style={{ color }}>{label}</span>의 취향을 알려주세요
        </h2>
        <p style={{ fontSize: 13, color: C.textMuted, margin: "0 0 28px", fontFamily: "'Noto Sans KR',sans-serif" }}>여러 개 선택 가능해요</p>

        {Object.entries(TAGS).map(([cat, list]) => (
          <div key={cat} style={{ marginBottom: 24 }}>
            <div style={{ fontSize: 11, color: C.textMuted, marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.08em", fontWeight: 600 }}>{cat}</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
              {list.map(t => (
                <TagBtn key={t} label={t} selected={current.includes(t)} color={color} onClick={() => toggle(t, step)} />
              ))}
            </div>
          </div>
        ))}

        {current.length > 0 && (
          <div style={{ background: C.mainDim, border: `1px solid ${C.border}`, borderRadius: 12, padding: "10px 14px", marginBottom: 20 }}>
            <div style={{ fontSize: 11, color, marginBottom: 6, fontWeight: 600 }}>선택됨</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {current.map(t => (
                <span key={t} style={{ fontSize: 12, background: color, color: "#fff", padding: "3px 10px", borderRadius: 999 }}>{t}</span>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div style={{ background: "#FDE8E8", border: "1px solid #f5c0c0", borderRadius: 10, padding: "10px 14px", color: "#c0392b", fontSize: 13, marginBottom: 12, fontFamily: "'Noto Sans KR',sans-serif" }}>
            {error}
          </div>
        )}

        <div style={{ display: "flex", gap: 10, marginTop: 8 }}>
          {step === 1 && (
            <button onClick={() => setStep(0)} style={{
              flex: 1, padding: 14, background: C.card, border: `1.5px solid ${C.border}`,
              borderRadius: 13, color: C.textDim, fontSize: 14, cursor: "pointer",
              fontFamily: "'Noto Sans KR',sans-serif",
            }}>← 이전</button>
          )}
          <button onClick={handleNext} style={{
            flex: 2, padding: 14, background: color, border: "none", borderRadius: 13,
            color: "#fff", fontSize: 15, fontWeight: 700, cursor: "pointer",
            fontFamily: "'Noto Sans KR',sans-serif",
            boxShadow: `0 4px 14px ${color}40`, transition: "all 0.2s",
          }}>
            {step === 0 ? "여자친구 취향 입력 →" : "채팅으로 코스 만들기 →"}
          </button>
        </div>
      </div>
    </div>
  );
}
