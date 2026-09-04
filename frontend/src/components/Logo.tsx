export function Logo({
  size = 40,
  variant = "full",
}: {
  size?: number;
  variant?: "full" | "mark";
}) {
  const showText = variant === "full" && size >= 30;
  return (
    <svg
      viewBox="0 0 240 220"
      width={size}
      height={(size * 220) / 240}
      fill="none"
      stroke="currentColor"
      role="img"
      aria-label="KNSB"
    >
      <polygon points="120,20 220,193.2 20,193.2" strokeWidth="9" strokeLinejoin="round" />
      <circle cx="120" cy="135.5" r="50" strokeWidth="8" />
      {showText && (
        <text
          x="120"
          y="137"
          textAnchor="middle"
          dominantBaseline="central"
          fontFamily="var(--font-sans, system-ui)"
          fontWeight="800"
          fontSize="27"
          letterSpacing="0.5"
          fill="currentColor"
          stroke="none"
        >
          KNSB
        </text>
      )}
    </svg>
  );
}
