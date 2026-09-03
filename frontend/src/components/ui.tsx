import clsx from "clsx";
import {
  createContext,
  useContext,
  useEffect,
  useId,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useTranslation } from "react-i18next";

/* ---------------------------------------------------------------- Info tooltip */
/* Section 9: appears on ~400 ms hover, on focus, and on tapping the ? icon.
   Bound with aria-describedby; never blocks typing. */

export function Info({ tKey }: { tKey: string }) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const timer = useRef<number | undefined>(undefined);
  const id = useId();
  const text = t(tKey);
  // missing key -> render nothing rather than leak the raw key
  if (text === tKey) return null;

  const show = () => setOpen(true);
  const hide = () => setOpen(false);
  const delayed = () => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(show, 400);
  };
  const cancel = () => {
    window.clearTimeout(timer.current);
    hide();
  };

  return (
    <span className="relative inline-flex">
      <button
        type="button"
        aria-label={i18n.language === "tr" ? "Bilgi" : "Info"}
        aria-describedby={open ? id : undefined}
        className="ml-1 h-4 w-4 shrink-0 rounded-full border border-border text-[10px]
                   leading-none text-text-secondary hover:bg-surface-2"
        onMouseEnter={delayed}
        onMouseLeave={cancel}
        onFocus={show}
        onBlur={hide}
        onClick={() => setOpen((o) => !o)}
      >
        ?
      </button>
      {open && (
        <span
          role="tooltip"
          id={id}
          className="absolute left-5 top-0 z-50 w-64 rounded-md border border-border
                     bg-surface p-2 text-xs leading-snug text-text shadow-lg"
        >
          {text}
        </span>
      )}
    </span>
  );
}

/* --------------------------------------------------------------------- Card */
export function Card({ className, children }: { className?: string; children: ReactNode }) {
  return <div className={clsx("card", className)}>{children}</div>;
}

/* ------------------------------------------------------------------ Accordion */
interface AccCtx {
  open: Set<string>;
  toggle: (id: string) => void;
}
const AccordionCtx = createContext<AccCtx | null>(null);

export function Accordion({
  defaultOpen = [],
  children,
}: {
  defaultOpen?: string[];
  children: ReactNode;
}) {
  const [open, setOpen] = useState(new Set(defaultOpen));
  const toggle = (id: string) =>
    setOpen((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  return <AccordionCtx.Provider value={{ open, toggle }}>{children}</AccordionCtx.Provider>;
}

export function AccordionItem({
  id,
  title,
  children,
}: {
  id: string;
  title: ReactNode;
  children: ReactNode;
}) {
  const ctx = useContext(AccordionCtx)!;
  const isOpen = ctx.open.has(id);
  return (
    <div className="border-b border-border">
      <button
        type="button"
        aria-expanded={isOpen}
        className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm font-medium"
        onClick={() => ctx.toggle(id)}
      >
        <span className={clsx("transition-transform", isOpen && "rotate-90")}>▸</span>
        {title}
      </button>
      {isOpen && <div className="space-y-2 px-3 pb-3">{children}</div>}
    </div>
  );
}

/* ----------------------------------------------------------------------- Tabs */
export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { id: string; label: string }[];
  active: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex gap-1 border-b border-border" role="tablist">
      {tabs.map((tb) => (
        <button
          key={tb.id}
          role="tab"
          aria-selected={active === tb.id}
          className={clsx(
            "px-3 py-1.5 text-sm font-medium border-b-2 -mb-px",
            active === tb.id
              ? "border-primary text-text"
              : "border-transparent text-text-secondary hover:text-text",
          )}
          onClick={() => onChange(tb.id)}
        >
          {tb.label}
        </button>
      ))}
    </div>
  );
}

/* --------------------------------------------------------------------- Dialog */
export function Dialog({
  open,
  onClose,
  title,
  children,
}: {
  open: boolean;
  onClose: () => void;
  title: ReactNode;
  children: ReactNode;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 p-4"
      onClick={onClose}
    >
      <div
        role="dialog"
        aria-modal="true"
        className="card w-full max-w-md p-4"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 text-base font-semibold">{title}</div>
        {children}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------- warning badge */
export function LevelDot({ level }: { level: "info" | "warning" | "danger" }) {
  const color =
    level === "danger" ? "bg-danger" : level === "warning" ? "bg-warning" : "bg-info";
  const shape = level === "danger" ? "rounded-sm" : level === "warning" ? "rotate-45" : "rounded-full";
  return <span className={clsx("inline-block h-2.5 w-2.5", color, shape)} aria-hidden />;
}
