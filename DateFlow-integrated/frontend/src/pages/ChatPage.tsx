import { useState, useEffect, useRef } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8001";

const C = {
  bg: "#F5F3FB", card: "#FFFFFF", border: "#E8E4F4",
  main: "#B8A9D9", mainDim: "#EAE5F5",
  point: "#E8A0B4",
  text: "#3D3257", textDim: "#7B6FA0", textMuted: "#B0A8CC",
  inputBg: "#F0EDF9", inputBorder: "#D8D0EE",
  botBg: "#EAE5F5", userBg: "#B8A9D9",
};

const GS = `
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  @keyframes fadeUp { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:none} }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
  @keyframes spin { to{transform:rotate(360deg)} }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#F5F3FB; }
  ::-webkit-scrollbar { width:4px; }
  ::-webkit-scrollbar-thumb { background:#D8D0EE; border-radius:4px; }
`;

type Role = "bot" | "user";
interface Msg { role: Role; text: string; }

type ChatStep = "region" | "time" | "budget" | "generating" | "done";

const STEP_QUESTIONS: Record<ChatStep, string> = {
  region:     "어느 지역으로 데이트할까요? 🗺️\n(예: 홍대, 강남, 성수동)",
  time:       "몇 시에 시작할 예정인가요? ⏰\n(예: 오후 2시, 저녁 6시)",
  budget:     "예산은 어느 정도 생각하고 계세요? 💰\n(예: 5만원, 10만원)",
  generating: "잠깐만요, 딱 맞는 코스를 찾고 있어요... ✨",
  done:       "",
};

function parseBudget(text: string): number {
  const t = text.replace(/,/g, "").replace(/\s/g, "");
  const m = t.match(/(\d+)(만원?)?/);
  if (!m) return 80000;
  const n = parseInt(m[1]);
  return t.includes("만") ? n * 10000 : n;
}

function parseTime(text: string): string {
  if (text.includes("오전")) return text.replace(/오전\s?/, "0") + ":00";
  if (text.includes("오후")) {
    const h = text.match(/(\d+)시/)?.[1];
    return h ? `${parseInt(h) + 12}:00` : "14:00";
  }
  const m = text.match(/(\d+):(\d+)/);
  if (m) return `${m[1]}:${m[2]}`;
  const h = text.match(/(\d+)시/)?.[1];
  return h ? `${h}:00` : "14:00";
}

export default function ChatPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: globalThis.MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) setMenuOpen(false);
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);
  const { manTags = [], womanTags = [] } = (location.state as { manTags: string[]; womanTags: string[] }) ?? {};

  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [step, setStep] = useState<ChatStep>("region");
  const [region, setRegion] = useState("");
  const [startTime, setStartTime] = useState("14:00");
  const [, setBudget] = useState(80000);
  const [typing, setTyping] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const addBot = (text: string, delay = 400) => {
    setTyping(true);
    setTimeout(() => {
      setTyping(false);
      setMsgs(p => [...p, { role: "bot", text }]);
    }, delay);
  };

  useEffect(() => {
    const name = user?.nickname ?? "님";
    setTimeout(() => addBot(`안녕하세요, ${name}! 😊\n두 분의 취향을 분석했어요.\n\n${STEP_QUESTIONS.region}`, 300), 100);
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [msgs, typing]);

  const send = async () => {
    const text = input.trim();
    if (!text || step === "generating" || step === "done") return;
    setInput("");
    setMsgs(p => [...p, { role: "user", text }]);

    if (step === "region") {
      setRegion(text);
      setStep("time");
      addBot(STEP_QUESTIONS.time);
    } else if (step === "time") {
      setStartTime(parseTime(text));
      setStep("budget");
      addBot(STEP_QUESTIONS.budget);
    } else if (step === "budget") {
      const b = parseBudget(text);
      setBudget(b);
      setStep("generating");
      addBot(`알겠어요! ${region} 지역 코스를 만들어드릴게요 ✨`, 300);

      // 코스 생성 API 호출
      try {
        setTimeout(async () => {
          const res = await fetch(`${API}/courses/generate`, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              ...(user ? { Authorization: `Bearer ${user.token}` } : {}),
            },
            body: JSON.stringify({
              user_id: user?.user_id ?? "guest",
              region,
              lat: 37.5563,
              lon: 126.9234,
              start_time: startTime,
              end_time: "22:00",
              budget: b,
            }),
          });
          const data = await res.json();
          setStep("done");
          addBot("코스 완성! 결과 페이지로 이동할게요 🎉", 600);
          setTimeout(() => navigate("/result", {
            state: { courseData: data, region, manTags, womanTags }
          }), 1800);
        }, 800);
      } catch {
        setStep("budget");
        addBot("코스 생성 중 오류가 발생했습니다. 다시 시도해주세요.");
      }
    }
  };

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const quickReplies: Record<ChatStep, string[]> = {
    region: ["홍대", "강남", "성수동", "이태원", "인사동"],
    time:   ["오후 1시", "오후 2시", "오후 4시", "저녁 6시", "저녁 7시"],
    budget: ["5만원", "8만원", "10만원", "15만원", "20만원"],
    generating: [],
    done: [],
  };

  return (
    <div style={{ minHeight: "100vh", background: C.bg, display: "flex", flexDirection: "column" }}>
      <style>{GS}</style>

      {/* 헤더 */}
      <div style={{ background: C.card, borderBottom: `1px solid ${C.border}`, padding: "14px 20px", display: "flex", alignItems: "center", gap: 12, position: "sticky", top: 0, zIndex: 10 }}>
        <div style={{ width: 36, height: 36, borderRadius: "50%", background: C.mainDim, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 18 }}>✦</div>
        <div>
          <div style={{ fontSize: 15, fontWeight: 700, color: C.text, fontFamily: "'Noto Sans KR',sans-serif" }}>DateFlow AI</div>
          <div style={{ fontSize: 11, color: C.textMuted, fontFamily: "'Noto Sans KR',sans-serif" }}>데이트 코스 추천 챗봇</div>
        </div>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          {manTags.slice(0, 2).map(t => (
            <span key={t} style={{ fontSize: 11, background: C.mainDim, color: C.main, padding: "3px 8px", borderRadius: 999, fontFamily: "'Noto Sans KR',sans-serif" }}>{t}</span>
          ))}
          {womanTags.slice(0, 2).map(t => (
            <span key={t} style={{ fontSize: 11, background: "#FCE8EE", color: C.point, padding: "3px 8px", borderRadius: 999, fontFamily: "'Noto Sans KR',sans-serif" }}>{t}</span>
          ))}

          {/* 톱니바퀴 메뉴 */}
          <div ref={menuRef} style={{ position: "relative" }}>
            <button
              onClick={() => setMenuOpen(p => !p)}
              style={{ width: 34, height: 34, borderRadius: "50%", border: `1.5px solid ${C.border}`, background: menuOpen ? C.mainDim : C.card, cursor: "pointer", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16, color: C.textDim, transition: "all 0.15s" }}
            >⚙</button>
            {menuOpen && (
              <div style={{ position: "absolute", right: 0, top: 42, background: C.card, border: `1.5px solid ${C.border}`, borderRadius: 12, boxShadow: "0 4px 20px #B8A9D930", minWidth: 150, zIndex: 100, overflow: "hidden" }}>
                <button
                  onClick={() => { setMenuOpen(false); navigate("/onboarding"); }}
                  style={{ width: "100%", padding: "12px 16px", background: "none", border: "none", textAlign: "left", fontSize: 14, color: C.text, cursor: "pointer", fontFamily: "'Noto Sans KR',sans-serif", borderBottom: `1px solid ${C.border}` }}
                >✦ 취향 재설정</button>
                <button
                  onClick={() => { logout(); navigate("/login"); }}
                  style={{ width: "100%", padding: "12px 16px", background: "none", border: "none", textAlign: "left", fontSize: 14, color: "#E87070", cursor: "pointer", fontFamily: "'Noto Sans KR',sans-serif" }}
                >→ 로그아웃</button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 메시지 영역 */}
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 16px", display: "flex", flexDirection: "column", gap: 16 }}>
        {msgs.map((m, i) => (
          <div key={i} style={{ display: "flex", justifyContent: m.role === "user" ? "flex-end" : "flex-start", animation: "fadeUp 0.25s ease" }}>
            {m.role === "bot" && (
              <div style={{ width: 30, height: 30, borderRadius: "50%", background: C.mainDim, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, marginRight: 8, flexShrink: 0, alignSelf: "flex-end" }}>✦</div>
            )}
            <div style={{
              maxWidth: "72%", padding: "12px 16px", borderRadius: m.role === "bot" ? "18px 18px 18px 4px" : "18px 18px 4px 18px",
              background: m.role === "bot" ? C.botBg : C.userBg,
              color: m.role === "bot" ? C.text : "#fff",
              fontSize: 14, lineHeight: 1.65,
              fontFamily: "'Noto Sans KR',sans-serif",
              whiteSpace: "pre-line",
              boxShadow: "0 1px 4px #B8A9D918",
            }}>{m.text}</div>
          </div>
        ))}

        {/* 타이핑 인디케이터 */}
        {typing && (
          <div style={{ display: "flex", alignItems: "flex-end", gap: 8, animation: "fadeUp 0.2s ease" }}>
            <div style={{ width: 30, height: 30, borderRadius: "50%", background: C.mainDim, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>✦</div>
            <div style={{ background: C.botBg, borderRadius: "18px 18px 18px 4px", padding: "13px 18px", display: "flex", gap: 5, alignItems: "center" }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{ width: 7, height: 7, borderRadius: "50%", background: C.main, animation: `blink 1.2s ${i * 0.2}s ease infinite` }} />
              ))}
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 빠른 답장 */}
      {quickReplies[step].length > 0 && !typing && (
        <div style={{ padding: "0 16px 10px", display: "flex", gap: 8, overflowX: "auto", scrollbarWidth: "none" }}>
          {quickReplies[step].map(q => (
            <button key={q} onClick={() => { setInput(q); inputRef.current?.focus(); }} style={{
              padding: "7px 14px", borderRadius: 999, border: `1.5px solid ${C.border}`,
              background: C.card, color: C.main, fontSize: 13, cursor: "pointer",
              fontFamily: "'Noto Sans KR',sans-serif", fontWeight: 500, whiteSpace: "nowrap",
              flexShrink: 0,
            }}>{q}</button>
          ))}
        </div>
      )}

      {/* 입력창 */}
      <div style={{ padding: "12px 16px 20px", background: C.card, borderTop: `1px solid ${C.border}`, display: "flex", gap: 10 }}>
        <input
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder={step === "generating" || step === "done" ? "코스 생성 중..." : "메시지를 입력하세요"}
          disabled={step === "generating" || step === "done"}
          style={{
            flex: 1, padding: "13px 16px",
            background: C.inputBg, border: `1.5px solid ${C.inputBorder}`,
            borderRadius: 24, color: C.text, fontSize: 14,
            fontFamily: "'Noto Sans KR',sans-serif",
            outline: "none",
          }}
        />
        <button
          onClick={send}
          disabled={!input.trim() || step === "generating" || step === "done"}
          style={{
            width: 46, height: 46, borderRadius: "50%", border: "none",
            background: input.trim() ? C.main : C.inputBg,
            color: input.trim() ? "#fff" : C.textMuted,
            fontSize: 20, cursor: input.trim() ? "pointer" : "default",
            display: "flex", alignItems: "center", justifyContent: "center",
            transition: "all 0.2s", flexShrink: 0,
          }}
        >↑</button>
      </div>
    </div>
  );
}
