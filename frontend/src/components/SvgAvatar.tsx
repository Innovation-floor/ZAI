export function SvgAvatar() {
  return (
    <svg viewBox="0 0 200 260" className="avatar-media" preserveAspectRatio="xMidYMid slice">
      <rect width="200" height="260" fill="#12243A" />
      <g opacity=".2" fill="none" stroke="#B08A3E" strokeWidth=".7">
        <circle cx="100" cy="120" r="86" />
        <circle cx="100" cy="120" r="62" />
        <path d="M14 120h172M100 30v190M42 62l116 116M158 62L42 178" />
      </g>
      <g>
        <path
          d="M100 62c-32 0-52 22-52 55 0 36 22 66 52 83 30-17 52-47 52-83 0-33-20-55-52-55z"
          fill="#0D1928" stroke="#C69A50" strokeWidth="1.6"
        />
        <ellipse cx="100" cy="126" rx="31" ry="37" fill="#C99C6E" />
        <path d="M69 114c0-23 14-35 31-35s31 12 31 35" fill="#0D1928" />
        <g>
          <ellipse cx="88" cy="122" rx="5.6" ry="3.4" fill="#F3EDE4" />
          <ellipse cx="112" cy="122" rx="5.6" ry="3.4" fill="#F3EDE4" />
          <circle cx="88" cy="122" r="2.6" fill="#22160C" />
          <circle cx="112" cy="122" r="2.6" fill="#22160C" />
        </g>
        <path d="M82 114q6-3.4 12 0M106 114q6-3.4 12 0"
          stroke="#3A2716" strokeWidth="1.7" fill="none" strokeLinecap="round" />
        <path d="M100 128v6" stroke="#A87B52" strokeWidth="1.3" fill="none" strokeLinecap="round" />
        <ellipse cx="100" cy="146" rx="9" ry="1.6" fill="#5C2E2A" />
      </g>
    </svg>
  );
}
