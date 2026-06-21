import jcviMeowLogo from "../assets/brand/jcvi-meow-logo.svg";

interface JcviMeowIconProps {
  className?: string;
  title?: string;
}

export function JcviMeowIcon({
  className = "h-12 w-12",
  title = "JCVI meow",
}: JcviMeowIconProps) {
  return (
    <img
      src={jcviMeowLogo}
      role="img"
      aria-label={title}
      title={title}
      className={`${className} select-none object-contain`}
      draggable={false}
    />
  );
}
