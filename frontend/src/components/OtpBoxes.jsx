import { useEffect, useRef, useState } from "react";

/**
 * OtpBoxes — 6-cell OTP input with per-cell micro animations.
 *
 * Props:
 *  - length: number (default 6)
 *  - value: string (controlled)
 *  - onChange: (nextValue: string) => void
 *  - onComplete: (value: string) => void — fired once when all cells are filled
 *  - disabled: boolean
 *  - error: boolean — triggers shake + red accents
 *  - autoFocus: boolean (default true)
 *  - testidPrefix: string (default "otp")
 */
const FILL_ANIMS = [
  { name: "otp-pop",    duration: "520ms" },
  { name: "otp-slide",  duration: "540ms" },
  { name: "otp-flip",   duration: "580ms" },
  { name: "otp-blur",   duration: "520ms" },
  { name: "otp-rotate", duration: "600ms" },
  { name: "otp-swing",  duration: "820ms" }, // last cell — extended so it's clearly visible
];

export default function OtpBoxes({
  length = 6,
  value = "",
  onChange,
  onComplete,
  disabled = false,
  error = false,
  autoFocus = true,
  testidPrefix = "otp",
}) {
  const inputsRef = useRef([]);
  const [activeIdx, setActiveIdx] = useState(0);
  const [waveKey, setWaveKey] = useState(0);
  const digits = Array.from({ length }, (_, i) => value[i] || "");
  const filled = value.length >= length;

  useEffect(() => {
    if (autoFocus && !disabled) {
      const target = Math.min(value.length, length - 1);
      inputsRef.current[target]?.focus();
    }
  }, []);

  useEffect(() => {
    if (filled) {
      setWaveKey((k) => k + 1);
      // Delay so the last cell's entrance animation + completion wave
      // are both visible before the parent triggers navigation/verify.
      const t = window.setTimeout(() => onComplete?.(value), 750);
      return () => window.clearTimeout(t);
    }
    return undefined;
  }, [filled]);

  // Refocus the first cell when the parent externally clears the value
  // (e.g. on "Resend OTP" after a partial entry).
  useEffect(() => {
    if (!disabled && value === "" && document.activeElement !== inputsRef.current[0]) {
      inputsRef.current[0]?.focus();
      setActiveIdx(0);
    }
  }, [value, disabled]);

  const setDigit = (idx, ch) => {
    const arr = digits.slice();
    arr[idx] = ch;
    // Trim to length; join preserving leading empties as blank
    let next = arr.join("");
    // Compact: if user typed past a gap, keep as-is; else compact left
    if (next.length > length) next = next.slice(0, length);
    onChange?.(next);
  };

  const handleChange = (idx, e) => {
    const raw = e.target.value.replace(/\D/g, "");
    if (!raw) {
      setDigit(idx, "");
      return;
    }
    // If multiple chars pasted into single field, splay across
    if (raw.length > 1) {
      const chars = raw.slice(0, length - idx).split("");
      const arr = digits.slice();
      chars.forEach((c, k) => (arr[idx + k] = c));
      const next = arr.join("").slice(0, length);
      onChange?.(next);
      const focusTo = Math.min(idx + chars.length, length - 1);
      inputsRef.current[focusTo]?.focus();
      setActiveIdx(focusTo);
      return;
    }
    const ch = raw[0];
    setDigit(idx, ch);
    if (idx < length - 1) {
      inputsRef.current[idx + 1]?.focus();
      setActiveIdx(idx + 1);
    } else {
      setActiveIdx(idx);
    }
  };

  const handleKeyDown = (idx, e) => {
    if (e.key === "Backspace") {
      e.preventDefault();
      if (digits[idx]) {
        setDigit(idx, "");
      } else if (idx > 0) {
        const arr = digits.slice();
        arr[idx - 1] = "";
        onChange?.(arr.join(""));
        inputsRef.current[idx - 1]?.focus();
        setActiveIdx(idx - 1);
      }
    } else if (e.key === "ArrowLeft" && idx > 0) {
      e.preventDefault();
      inputsRef.current[idx - 1]?.focus();
      setActiveIdx(idx - 1);
    } else if (e.key === "ArrowRight" && idx < length - 1) {
      e.preventDefault();
      inputsRef.current[idx + 1]?.focus();
      setActiveIdx(idx + 1);
    }
  };

  const handlePaste = (idx, e) => {
    const pasted = (e.clipboardData || window.clipboardData).getData("text");
    const clean = pasted.replace(/\D/g, "").slice(0, length - idx);
    if (!clean) return;
    e.preventDefault();
    const arr = digits.slice();
    clean.split("").forEach((c, k) => (arr[idx + k] = c));
    const next = arr.join("").slice(0, length);
    onChange?.(next);
    const focusTo = Math.min(idx + clean.length, length - 1);
    inputsRef.current[focusTo]?.focus();
    setActiveIdx(focusTo);
  };

  return (
    <div
      className={`otp-boxes ${error ? "otp-shake" : ""}`}
      data-testid={`${testidPrefix}-boxes`}
      aria-label="One-time password"
    >
      <style>{OTP_CSS}</style>
      {digits.map((d, idx) => {
        const isActive = activeIdx === idx && !disabled;
        const hasVal = Boolean(d);
        const anim = FILL_ANIMS[idx % FILL_ANIMS.length];
        return (
          <label
            key={idx}
            className={`otp-cell ${isActive ? "is-active" : ""} ${hasVal ? "is-filled" : ""} ${error ? "is-error" : ""}`}
            data-testid={`${testidPrefix}-cell-${idx}`}
          >
            <input
              ref={(el) => (inputsRef.current[idx] = el)}
              inputMode="numeric"
              pattern="[0-9]*"
              autoComplete={idx === 0 ? "one-time-code" : "off"}
              maxLength={length}
              value={d}
              disabled={disabled}
              onChange={(e) => handleChange(idx, e)}
              onKeyDown={(e) => handleKeyDown(idx, e)}
              onPaste={(e) => handlePaste(idx, e)}
              onFocus={() => setActiveIdx(idx)}
              data-testid={`${testidPrefix}-input-${idx}`}
              aria-label={`Digit ${idx + 1}`}
            />
            <span
              className="otp-digit"
              key={`${d}-${idx}`}
              style={hasVal ? { animationName: anim.name, animationDuration: anim.duration } : { animationName: "none" }}
            >
              {d}
            </span>
            <span className="otp-caret" aria-hidden />
            <span className="otp-underline" aria-hidden />
            {filled && (
              <span
                className="otp-wave"
                key={`wave-${idx}-${waveKey}`}
                style={{ animationDelay: `${idx * 55}ms` }}
                aria-hidden
              />
            )}
          </label>
        );
      })}
    </div>
  );
}

const OTP_CSS = `
.otp-boxes { display: flex; gap: 10px; justify-content: space-between; }
@media (max-width: 380px) { .otp-boxes { gap: 6px; } }
.otp-cell {
  position: relative;
  flex: 1 1 0;
  height: 60px;
  background: #fff;
  border: 1px solid #e7e5e4;
  border-bottom: 2px solid #d6d3d1;
  overflow: hidden;
  cursor: text;
  transition: transform 260ms cubic-bezier(.2,.7,.2,1),
              border-color 220ms ease,
              box-shadow 260ms ease,
              background-color 220ms ease;
}
.otp-cell:hover { border-color: #a8a29e; }
.otp-cell input {
  position: absolute; inset: 0;
  width: 100%; height: 100%;
  opacity: 0; z-index: 3;
  border: 0; outline: none; background: transparent;
  font-size: 16px; /* prevents iOS zoom */
  caret-color: transparent;
  text-align: center;
}
.otp-cell .otp-digit {
  position: absolute; inset: 0;
  display: flex; align-items: center; justify-content: center;
  font-family: 'Cormorant Garamond', 'Playfair Display', serif;
  font-weight: 500;
  font-size: 30px;
  line-height: 1;
  color: #1c1917;
  animation-duration: 560ms;
  animation-timing-function: cubic-bezier(.2,.9,.25,1.15);
  animation-fill-mode: both;
  pointer-events: none;
  will-change: transform, opacity, filter;
}
.otp-cell .otp-caret {
  position: absolute;
  bottom: 12px; left: 50%;
  width: 2px; height: 22px;
  background: #1c1917;
  transform: translateX(-50%) scaleY(0);
  transform-origin: bottom center;
  opacity: 0;
  transition: transform 180ms ease, opacity 180ms ease;
}
.otp-cell .otp-underline {
  position: absolute;
  bottom: -2px; left: 50%;
  width: 0%; height: 2px;
  background: #1c1917;
  transform: translateX(-50%);
  transition: width 320ms cubic-bezier(.2,.7,.2,1);
}
.otp-cell.is-active {
  transform: translateY(-2px);
  border-color: #78716c;
  box-shadow: 0 6px 22px -14px rgba(28,25,23,0.55);
  background: #fdfcfa;
}
.otp-cell.is-active .otp-underline { width: 78%; }
.otp-cell.is-active:not(.is-filled) .otp-caret {
  transform: translateX(-50%) scaleY(1);
  opacity: 1;
  animation: otp-blink 1s steps(2, start) infinite;
}
.otp-cell.is-filled {
  border-color: #1c1917;
  background: #fafaf9;
}
.otp-cell.is-filled .otp-underline { width: 100%; background: #1c1917; }
.otp-cell.is-error {
  border-color: #b91c1c !important;
  background: #fef2f2 !important;
}
.otp-cell.is-error .otp-digit { color: #7f1d1d; }
.otp-cell.is-error .otp-underline { background: #b91c1c; }

.otp-wave {
  position: absolute;
  left: 0; right: 0; bottom: 0;
  height: 2px;
  background: linear-gradient(90deg, transparent, #1c1917, transparent);
  transform: translateY(3px);
  opacity: 0;
  animation: otp-wave-run 700ms ease forwards;
}

.otp-shake { animation: otp-shake 420ms cubic-bezier(.36,.07,.19,.97) both; }

@keyframes otp-blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}
@keyframes otp-shake {
  0%, 100% { transform: translateX(0); }
  15% { transform: translateX(-7px); }
  30% { transform: translateX(6px); }
  45% { transform: translateX(-5px); }
  60% { transform: translateX(4px); }
  75% { transform: translateX(-2px); }
  90% { transform: translateX(1px); }
}
@keyframes otp-wave-run {
  0% { transform: translateY(6px); opacity: 0; }
  40% { opacity: 1; }
  100% { transform: translateY(-40px); opacity: 0; }
}
.otp-wave { animation-duration: 900ms; }

/* Per-cell fill entrance animations */
@keyframes otp-pop {
  0% { transform: scale(0.4); opacity: 0; }
  60% { transform: scale(1.18); opacity: 1; }
  100% { transform: scale(1); opacity: 1; }
}
@keyframes otp-slide {
  0% { transform: translateY(22px); opacity: 0; }
  70% { transform: translateY(-3px); opacity: 1; }
  100% { transform: translateY(0); opacity: 1; }
}
@keyframes otp-flip {
  0% { transform: rotateX(-90deg); opacity: 0; }
  60% { transform: rotateX(15deg); opacity: 1; }
  100% { transform: rotateX(0); opacity: 1; }
}
@keyframes otp-blur {
  0% { filter: blur(10px); transform: scale(1.4); opacity: 0; }
  100% { filter: blur(0); transform: scale(1); opacity: 1; }
}
@keyframes otp-rotate {
  0% { transform: rotate(-90deg) scale(0.6); opacity: 0; }
  70% { transform: rotate(8deg) scale(1.05); opacity: 1; }
  100% { transform: rotate(0) scale(1); opacity: 1; }
}
@keyframes otp-swing {
  0%   { transform: translateY(-26px) rotate(-22deg); opacity: 0; }
  30%  { transform: translateY(4px) rotate(14deg); opacity: 1; }
  55%  { transform: translateY(-3px) rotate(-9deg); }
  75%  { transform: translateY(2px) rotate(5deg); }
  90%  { transform: translateY(-1px) rotate(-2deg); }
  100% { transform: translateY(0) rotate(0); opacity: 1; }
}
`;
