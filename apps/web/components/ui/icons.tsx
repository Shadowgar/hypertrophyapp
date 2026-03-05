import { cn } from "@/lib/utils";

type IconName =
  | "workout"
  | "plan"
  | "analytics"
  | "body"
  | "settings"
  | "video"
  | "swap"
  | "notes"
  | "play"
  | "save"
  | "login"
  | "reset"
  | "onboarding"
  | "history"
  | "close"
  | "skip"
  | "review";

type Props = Readonly<{
  name: IconName;
  className?: string;
}>;

export function UiIcon({ name, className }: Props) {
  return (
    <svg
      aria-hidden="true"
      className={cn("ui-icon", className)}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.9"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {resolvePaths(name)}
    </svg>
  );
}

function resolvePaths(name: IconName) {
  switch (name) {
    case "workout":
      return <path d="M4 10h3l2-3 6 10 2-3h3" />;
    case "plan":
      return (
        <>
          <rect x="4" y="5" width="16" height="15" rx="2" />
          <path d="M8 3v4M16 3v4M7 11h10M7 15h6" />
        </>
      );
    case "analytics":
      return <path d="M5 19V9M12 19V5M19 19v-7" />;
    case "body":
      return (
        <>
          <circle cx="12" cy="6" r="2" />
          <path d="M12 8v6M8 12l4-2 4 2M9 20l3-4 3 4" />
        </>
      );
    case "settings":
      return (
        <>
          <circle cx="12" cy="12" r="2.5" />
          <path d="M12 3v3M12 18v3M3 12h3M18 12h3M5.6 5.6l2.1 2.1M16.3 16.3l2.1 2.1M18.4 5.6l-2.1 2.1M7.7 16.3l-2.1 2.1" />
        </>
      );
    case "video":
      return (
        <>
          <rect x="3" y="6" width="13" height="12" rx="2" />
          <path d="m11 10 3 2-3 2zM16 10l5-3v10l-5-3" />
        </>
      );
    case "swap":
      return <path d="M7 7h11l-3-3M17 17H6l3 3M18 7l-3-3M6 17l3 3" />;
    case "notes":
      return (
        <>
          <rect x="5" y="4" width="14" height="16" rx="2" />
          <path d="M8 9h8M8 13h8M8 17h5" />
        </>
      );
    case "play":
      return <path d="M8 6v12l10-6z" />;
    case "save":
      return (
        <>
          <path d="M5 4h11l3 3v13H5z" />
          <path d="M8 4v6h8M8 20v-6h8" />
        </>
      );
    case "login":
      return <path d="M10 8V5h9v14h-9v-3M15 12H5M8 9l-3 3 3 3" />;
    case "reset":
      return <path d="M20 7v5h-5M20 12a8 8 0 1 1-2.3-5.7" />;
    case "onboarding":
      return <path d="M4 12h7M15 8h5M15 16h5M12 4v16" />;
    case "history":
      return (
        <>
          <circle cx="12" cy="12" r="8" />
          <path d="M12 8v4l3 2" />
        </>
      );
    case "close":
      return <path d="m6 6 12 12M18 6 6 18" />;
    case "skip":
      return <path d="M5 6v12l8-6-8-6ZM15 6v12" />;
    case "review":
      return (
        <>
          <path d="M5 4h10l4 4v12H5z" />
          <path d="M15 4v4h4M8 13h8M8 17h6" />
        </>
      );
    default:
      return null;
  }
}
