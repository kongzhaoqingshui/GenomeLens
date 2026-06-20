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
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <title>{title}</title>
      <defs>
        <linearGradient id="jcvi-meow-face" x1="36" y1="24" x2="118" y2="120" gradientUnits="userSpaceOnUse">
          <stop stopColor="#F0F9FF" />
          <stop offset="1" stopColor="#BAE6FD" />
        </linearGradient>
        <linearGradient id="jcvi-meow-lens" x1="86" y1="82" x2="146" y2="140" gradientUnits="userSpaceOnUse">
          <stop stopColor="#7DD3FC" />
          <stop offset="1" stopColor="#0EA5E9" />
        </linearGradient>
      </defs>

      <path
        d="M40 44L56 28L70 44M86 44L102 28L116 44"
        stroke="#0F172A"
        strokeWidth="7"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path
        d="M36 52C36 38.745 46.745 28 60 28H96C109.255 28 120 38.745 120 52V88C120 106.778 104.778 122 86 122H70C51.222 122 36 106.778 36 88V52Z"
        fill="url(#jcvi-meow-face)"
        stroke="#0F172A"
        strokeWidth="7"
        strokeLinejoin="round"
      />
      <path d="M61 69V79" stroke="#0F172A" strokeWidth="7" strokeLinecap="round" />
      <path d="M82 69V79" stroke="#0F172A" strokeWidth="7" strokeLinecap="round" />
      <path d="M65 92C71 98 79 98 85 92" stroke="#0F172A" strokeWidth="6" strokeLinecap="round" />
      <path d="M74 85L72 89L76 89" stroke="#0F172A" strokeWidth="5" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M50 92L36 88" stroke="#0F172A" strokeWidth="5" strokeLinecap="round" />
      <path d="M50 100L35 102" stroke="#0F172A" strokeWidth="5" strokeLinecap="round" />

      <circle cx="108" cy="103" r="29" fill="url(#jcvi-meow-lens)" stroke="#0F172A" strokeWidth="7" />
      <circle cx="108" cy="103" r="20" fill="#F0F9FF" fillOpacity="0.72" />
      <path d="M125 121L141 137" stroke="#0F172A" strokeWidth="8" strokeLinecap="round" />
      <circle cx="117" cy="92" r="7" fill="#F0F9FF" fillOpacity="0.88" />

      {showLensText ? (
        <text
          x="108"
          y="108"
          textAnchor="middle"
          fontSize="14"
          fontWeight="800"
          letterSpacing="0"
          fill="#0369A1"
          fontFamily='"Inter","PingFang SC","Microsoft YaHei",sans-serif'
        >
          JCVI
        </text>
      ) : null}
    </svg>
  );
}
