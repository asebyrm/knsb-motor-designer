export function Logo({
  size = 28,
  variant = "full",
}: {
  size?: number;
  variant?: "full" | "mark";
}) {
  const showText = variant === "full" && size >= 24;
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
      <polygon points="120,20 220,193.2 20,193.2" strokeWidth="4" strokeLinejoin="round" />
      <circle cx="120" cy="135.5" r="50" strokeWidth="3.5" />
      {showText && (
        <text
          x="120"
          y="135.5"
          textAnchor="middle"
          dominantBaseline="central"
          fontFamily="var(--font-sans, system-ui)"
          fontWeight="700"
          fontSize="28"
          fill="currentColor"
          stroke="none"
        >
          KNSB
        </text>
      )}
    </svg>
  );
}
