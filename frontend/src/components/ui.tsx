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
import { createPortal } from "react-dom";
import { useTranslation } from "react-i18next";

/* ---------------------------------------------------------------- Info tooltip */
/* Section 9: appears on ~400 ms hover, on focus, and on tapping the ? icon.
   Rendered as a fixed-position portal anchored to the "?" button's own screen
   position (not a shared bar pinned to the header) so it always shows up right
   next to the icon the user is looking at, however far down the page they have
   scrolled, and is never clipped by an overflow:hidden panel either. A
   visually-hidden span keeps aria-describedby working for screen readers. */

export function Info({ tKey }: { tKey: string }) {
  const { t, i18n } = useTranslation();
  const btnRef = useRef<HTMLButtonElement>(null);
  const [pos, setPos] = useState<{ top: number; left: number; above: boolean } | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const id = useId();
  const text = t(tKey);
  // missing key -> render nothing rather than leak the raw key
  if (text === tKey) return null;

  const place = () => {
    const r = btnRef.current?.getBoundingClientRect();
    if (!r) return;
    const above = r.bottom > window.innerHeight - 90; // near the bottom edge -> flip up
    setPos({
      top: above ? r.top - 8 : r.bottom + 8,
      left: Math.min(Math.max(r.left + r.width / 2, 140), window.innerWidth - 140),
      above,
    });
  };
  const show = () => {
    window.clearTimeout(timer.current);
    place();
  };
  const hide = () => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setPos(null), 120);
  };
  const delayed = () => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(show, 400);
  };

  return (
    <span className="relative inline-flex">
      <button
        ref={btnRef}
        type="button"
        aria-label={i18n.language === "tr" ? "Bilgi" : "Info"}
        aria-describedby={id}
        className="ml-1 h-4 w-4 shrink-0 rounded-full border border-border text-[10px]
                   leading-none text-text-secondary hover:bg-primary hover:text-primary-fg
                   focus:outline-none focus:ring-1 focus:ring-primary"
        onMouseEnter={delayed}
        onMouseLeave={hide}
        onFocus={show}
        onBlur={hide}
        onClick={show}
      >
        ?
      </button>
      <span id={id} className="sr-only">
        {text}
      </span>
      {pos &&
        createPortal(
          <p
            role="tooltip"
            style={{
              position: "fixed",
              top: pos.top,
              left: pos.left,
              transform: `translate(-50%, ${pos.above ? "-100%" : "0"})`,
            }}
            className="pointer-events-none z-[200] max-w-xs rounded-md border border-border
                       bg-surface-2 px-3 py-1.5 text-xs leading-snug text-text shadow-lg"
          >
            {text}
          </p>,
          document.body,
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
