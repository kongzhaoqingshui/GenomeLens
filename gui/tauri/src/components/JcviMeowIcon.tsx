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
        <linearGradient id="jcvi-meow-lens" x1="88" y1="78" x2="138" y2="132" gradientUnits="userSpaceOnUse">
          <stop stopColor="#EFF6FF" />
          <stop offset="1" stopColor="#BAE6FD" />
        </linearGradient>
      </defs>

      <g className="jcvi-icon-cat">
        <path d="M40 54C35 38 39 26 52 20C60 27 66 35 70 44H87C93 34 101 27 111 22C122 31 124 44 119 57C127 68 128 84 121 98C110 120 88 128 62 121C42 116 30 100 29 80C28 69 32 60 40 54Z" fill="url(#jcvi-meow-face-shadow)" opacity="0.42" />
        <path d="M42 50C37 36 41 25 53 19C61 27 67 36 70 45H88C94 35 102 28 112 23C122 32 123 44 117 57C124 67 125 83 118 96C108 116 88 123 64 117C45 112 34 97 33 79C32 67 35 57 42 50Z" fill="url(#jcvi-meow-face)" />
        <path d="M45 31C48 29 51 27 53 26C57 31 61 37 64 45C58 41 52 37 45 31Z" fill="#E0F2FE" opacity="0.45" />
        <path d="M103 46C106 40 110 35 114 31C116 36 116 43 113 51C110 49 107 47 103 46Z" fill="#DBEAFE" opacity="0.34" />
        <path d="M50 62C56 60 62 61 67 65C64 70 58 73 51 73C48 70 48 66 50 62Z" fill="#F8FAFC" opacity="0.96" />
        <path d="M78 64C84 62 90 63 95 67C92 72 86 75 79 75C76 72 76 68 78 64Z" fill="#F8FAFC" opacity="0.96" />
        <circle cx="60" cy="69" r="3.8" fill="#1E3A8A" />
        <circle cx="88" cy="71" r="3.8" fill="#1E3A8A" />
      </g>

      <g className="jcvi-icon-lens">
        <path d="M121 119L143 141" stroke="#2563EB" strokeWidth="13" strokeLinecap="round" />
        <path d="M121 119L143 141" stroke="#DBEAFE" strokeWidth="5" strokeLinecap="round" opacity="0.72" />
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
