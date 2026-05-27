import { useState } from "react";
import type { FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8001";

const C = {
  bg: "#F5F3FB", card: "#FFFFFF", border: "#E8E4F4",
  main: "#B8A9D9", mainDim: "#EAE5F5",
  point: "#E8A0B4", pointDim: "#FCE8EE",
  text: "#3D3257", textDim: "#7B6FA0", textMuted: "#B0A8CC",
  inputBg: "#F0EDF9", inputBorder: "#D8D0EE",
  error: "#E87070", errorBg: "#FDE8E8",
};

const GS = `
  @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;700&display=swap');
  @keyframes fadeUp { from{opacity:0;transform:translateY(16px)} to{opacity:1;transform:none} }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { background:#F5F3FB; }
  input:focus { border-color:#B8A9D9 !important; outline:none; box-shadow:0 0 0 3px #B8A9D922; }
`;

const inputStyle = {
  width: "100%", padding: "13px 16px",
  background: C.inputBg, border: `1.5px solid ${C.inputBorder}`,
  borderRadius: 12, color: C.text, fontSize: 15,
  fontFamily: "'Noto Sans KR',sans-serif",
};

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [gender, setGender] = useState<"M" | "F" | "N">("N");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const validateUsername = (v: string) => {
    if (!v) return "";
    if (!/^[a-z0-9_]{4,20}$/.test(v)) return "4~20자의 영문 소문자, 숫자, 언더스코어(_)만 사용 가능합니다.";
    if (/^\d/.test(v)) return "숫자로 시작할 수 없습니다.";
    return "";
  };

  const validatePassword = (v: string) => {
    if (!v) return "";
    if (v.length < 8) return "8자 이상이어야 합니다.";
    if (!/[a-zA-Z]/.test(v)) return "영문자를 포함해야 합니다.";
    if (!/[0-9]/.test(v)) return "숫자를 포함해야 합니다.";
    return "";
  };

  const usernameErr = mode === "register" ? validateUsername(username) : "";
  const passwordErr = mode === "register" ? validatePassword(password) : "";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    if (!username.trim() || !password.trim()) { setError("아이디와 비밀번호를 입력하세요."); return; }
    if (mode === "register" && !nickname.trim()) { setError("닉네임을 입력하세요."); return; }
    if (mode === "register" && usernameErr) { setError(usernameErr); return; }
    if (mode === "register" && passwordErr) { setError(passwordErr); return; }

    setLoading(true);
    try {
      const endpoint = mode === "login" ? "/auth/login" : "/auth/register";
      const body = mode === "login"
        ? { username, password }
        : { username, password, nickname, gender };

      const res = await fetch(`${API}${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();
      if (!res.ok) {
        const d = data.detail;
        setError(Array.isArray(d) ? d.map((e: { msg: string }) => e.msg.replace("Value error, ", "")).join(" / ") : (d ?? "오류가 발생했습니다."));
        return;
      }

      login({ ...data, token: data.access_token });
      if (mode === "register") {
        navigate("/onboarding");
      } else {
        navigate("/");  // SmartHome이 취향 유무 판단
      }
    } catch {
      setError("서버에 연결할 수 없습니다.");
    } finally {
      setLoading(false);
    }
  };

  const GenderBtn = ({ val, label }: { val: "M" | "F" | "N"; label: string }) => (
    <button type="button" onClick={() => setGender(val)} style={{
      flex: 1, padding: "10px 0", borderRadius: 10,
      border: gender === val ? "none" : `1.5px solid ${C.border}`,
      background: gender === val ? C.main : C.card,
      color: gender === val ? "#fff" : C.textDim,
      fontSize: 14, fontWeight: gender === val ? 700 : 400,
      cursor: "pointer", fontFamily: "'Noto Sans KR',sans-serif",
      transition: "all 0.18s",
    }}>{label}</button>
  );

  return (
    <div style={{ minHeight: "100vh", background: C.bg, display: "flex", alignItems: "center", justifyContent: "center", padding: "24px 20px" }}>
      <style>{GS}</style>
      <div style={{ width: "100%", maxWidth: 400, animation: "fadeUp 0.45s ease" }}>

        {/* 로고 */}
        <div style={{ textAlign: "center", marginBottom: 36 }}>
          <h1 style={{ fontSize: 36, fontWeight: 900, color: C.text, letterSpacing: "-0.03em" }}>
            Date<span style={{ color: C.main }}>Flow</span>
          </h1>
          <p style={{ fontSize: 13, color: C.textMuted, marginTop: 6, fontFamily: "'Noto Sans KR',sans-serif" }}>
            두 사람의 취향으로 만드는 데이트 코스
          </p>
        </div>

        {/* 탭 */}
        <div style={{ display: "flex", background: C.inputBg, borderRadius: 12, padding: 4, marginBottom: 24 }}>
          {(["login", "register"] as const).map(m => (
            <button key={m} type="button" onClick={() => { setMode(m); setError(""); }} style={{
              flex: 1, padding: "9px 0", borderRadius: 9, border: "none",
              background: mode === m ? C.card : "transparent",
              color: mode === m ? C.main : C.textMuted,
              fontWeight: mode === m ? 700 : 400, fontSize: 14, cursor: "pointer",
              fontFamily: "'Noto Sans KR',sans-serif",
              boxShadow: mode === m ? "0 1px 6px #B8A9D922" : "none",
              transition: "all 0.2s",
            }}>{m === "login" ? "로그인" : "회원가입"}</button>
          ))}
        </div>

        {/* 폼 */}
        <form onSubmit={submit} style={{ display: "flex", flexDirection: "column", gap: 12 }}>
          <div>
            <label style={{ fontSize: 12, color: C.textDim, display: "block", marginBottom: 6, fontWeight: 500 }}>아이디</label>
            <input value={username} onChange={e => setUsername(e.target.value)} placeholder="아이디 입력" style={inputStyle} />
            {mode === "register" && username && usernameErr && (
              <div style={{ fontSize: 11, color: C.error, marginTop: 4 }}>⚠ {usernameErr}</div>
            )}
            {mode === "register" && !usernameErr && (
              <div style={{ fontSize: 11, color: C.textMuted, marginTop: 4 }}>영문 소문자·숫자·언더스코어, 4~20자 (숫자 시작 불가)</div>
            )}
          </div>

          <div>
            <label style={{ fontSize: 12, color: C.textDim, display: "block", marginBottom: 6, fontWeight: 500 }}>비밀번호</label>
            <input type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="비밀번호 입력" style={inputStyle} />
            {mode === "register" && password && passwordErr && (
              <div style={{ fontSize: 11, color: C.error, marginTop: 4 }}>⚠ {passwordErr}</div>
            )}
            {mode === "register" && !passwordErr && (
              <div style={{ fontSize: 11, color: C.textMuted, marginTop: 4 }}>8자 이상, 영문+숫자 조합 필수</div>
            )}
          </div>

          {mode === "register" && (
            <>
              <div>
                <label style={{ fontSize: 12, color: C.textDim, display: "block", marginBottom: 6, fontWeight: 500 }}>닉네임</label>
                <input value={nickname} onChange={e => setNickname(e.target.value)} placeholder="닉네임 입력" style={inputStyle} />
              </div>
              <div>
                <label style={{ fontSize: 12, color: C.textDim, display: "block", marginBottom: 6, fontWeight: 500 }}>성별</label>
                <div style={{ display: "flex", gap: 8 }}>
                  <GenderBtn val="M" label="남자" />
                  <GenderBtn val="F" label="여자" />
                  <GenderBtn val="N" label="선택 안 함" />
                </div>
              </div>
            </>
          )}

          {error && (
            <div style={{ background: C.errorBg, border: `1px solid ${C.error}44`, borderRadius: 10, padding: "10px 14px", color: C.error, fontSize: 13, fontFamily: "'Noto Sans KR',sans-serif" }}>
              {error}
            </div>
          )}

          <button type="submit" disabled={loading} style={{
            width: "100%", padding: 15, marginTop: 4,
            background: loading ? C.inputBg : C.main,
            color: loading ? C.textMuted : "#fff",
            border: "none", borderRadius: 13, fontSize: 15, fontWeight: 700,
            cursor: loading ? "not-allowed" : "pointer",
            fontFamily: "'Noto Sans KR',sans-serif",
            boxShadow: loading ? "none" : "0 4px 16px #B8A9D940",
            transition: "all 0.2s",
          }}>
            {loading ? "처리 중..." : mode === "login" ? "로그인" : "가입하기"}
          </button>
        </form>
      </div>
    </div>
  );
}
