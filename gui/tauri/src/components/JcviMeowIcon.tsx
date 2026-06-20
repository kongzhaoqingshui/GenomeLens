interface JcviMeowIconProps {
  className?: string;
  title?: string;
  showLensText?: boolean;
}

export function JcviMeowIcon({
  className = "h-12 w-12",
  title = "JCVI喵",
  showLensText = true,
}: JcviMeowIconProps) {
  return (
    <svg
      viewBox="0 0 160 160"
      role="img"
      aria-label={title}
      className={className}
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>{title}</title>
      <defs>
        <linearGradient id="jcvi-meow-face" x1="36" y1="24" x2="114" y2="120" gradientUnits="userSpaceOnUse">
          <stop stopColor="#A5F3FC" />
          <stop offset="0.58" stopColor="#60A5FA" />
          <stop offset="1" stopColor="#3B82F6" />
        </linearGradient>
        <linearGradient id="jcvi-meow-face-shadow" x1="44" y1="30" x2="112" y2="126" gradientUnits="userSpaceOnUse">
          <stop stopColor="#C4B5FD" />
          <stop offset="1" stopColor="#2563EB" />
        </linearGradient>
        <linearGradient id="jcvi-meow-lens" x1="78" y1="78" x2="128" y2="132" gradientUnits="userSpaceOnUse">
          <stop stopColor="#EFF6FF" />
          <stop offset="1" stopColor="#BAE6FD" />
        </linearGradient>
      </defs>

      <g className="jcvi-icon-cat">
        <path d="M41 54C35 38 39 26 53 20C62 28 68 37 71 46H88C94 36 102 28 113 23C124 33 125 46 118 59C125 70 126 86 119 98C108 118 88 125 64 118C45 113 33 98 32 80C31 69 34 60 41 54Z" fill="url(#jcvi-meow-face-shadow)" opacity="0.4" />
        <path d="M43 50C38 36 42 25 54 19C63 28 68 37 71 45H88C95 35 103 28 113 23C123 33 124 45 117 57C124 68 124 83 117 96C107 116 88 123 64 117C45 112 34 97 33 79C32 67 36 57 43 50Z" fill="url(#jcvi-meow-face)" />
        <path d="M57 46C54 40 50 35 46 31C44 36 44 43 47 51C50 49 53 47 57 46Z" fill="#E0F2FE" opacity="0.44" />
        <path d="M103 46C106 40 110 35 114 31C116 36 116 43 113 51C110 49 107 47 103 46Z" fill="#DBEAFE" opacity="0.34" />
        <path d="M55 66H66" stroke="#0F172A" strokeWidth="7.5" strokeLinecap="round" />
        <path d="M81 68H92" stroke="#0F172A" strokeWidth="7.5" strokeLinecap="round" />
      </g>

      <path
        d="M62 113C75 137 104 132 114 113C119 104 112 96 104 101C97 105 101 116 112 116"
        fill="none"
        stroke="#2563EB"
        strokeWidth="9"
        strokeLinecap="round"
        strokeLinejoin="round"
        opacity="0.88"
      />
      <g className="jcvi-icon-lens">
        <path d="M91 121L72 141" stroke="#2563EB" strokeWidth="13" strokeLinecap="round" />
        <path d="M91 121L72 141" stroke="#DBEAFE" strokeWidth="5" strokeLinecap="round" opacity="0.72" />
        <circle cx="105" cy="102" r="29" fill="#2563EB" opacity="0.2" />
        <circle cx="105" cy="102" r="25" fill="url(#jcvi-meow-lens)" stroke="#2563EB" strokeWidth="7" />
        <circle cx="96" cy="92" r="5" fill="#FFFFFF" opacity="0.82" />
      </g>

      {showLensText ? (
        <text
          className="jcvi-icon-lens-text"
          x="105"
          y="107"
          textAnchor="middle"
          fontSize="13"
          fontWeight="800"
          letterSpacing="0"
          fill="#1D4ED8"
          fontFamily='"Inter","PingFang SC","Microsoft YaHei",sans-serif'
        >
          JCVI
        </text>
      ) : null}
    </svg>
  );
}
