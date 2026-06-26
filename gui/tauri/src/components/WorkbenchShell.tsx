import { useCallback, useEffect, useRef, useState, type PointerEvent as ReactPointerEvent, type ReactNode } from "react";

interface WorkbenchShellProps {
  children: ReactNode; // canvas area
  leftPanel?: ReactNode;
  rightPanel?: ReactNode;
  topBar?: ReactNode;
  leftWidth?: number;
  rightWidth?: number;
  onLeftResize?: (width: number) => void;
  onRightResize?: (width: number) => void;
}

const MIN_SIDEBAR_WIDTH = 200;
const MAX_SIDEBAR_WIDTH = 520;
const DEFAULT_LEFT_WIDTH = 288;
const DEFAULT_RIGHT_WIDTH = 368;

function clampSidebarWidth(value: number): number {
  return Math.min(Math.max(value, MIN_SIDEBAR_WIDTH), MAX_SIDEBAR_WIDTH);
}

export function WorkbenchShell({
  children,
  leftPanel,
  rightPanel,
  topBar,
  leftWidth = DEFAULT_LEFT_WIDTH,
  rightWidth = DEFAULT_RIGHT_WIDTH,
  onLeftResize,
  onRightResize,
}: WorkbenchShellProps) {
  const [dragging, setDragging] = useState<"left" | "right" | null>(null);
  const dragStart = useRef<{ startX: number; startWidth: number } | null>(null);

  const handlePointerDown = useCallback(
    (side: "left" | "right", event: ReactPointerEvent<HTMLDivElement>) => {
      event.preventDefault();
      event.currentTarget.setPointerCapture(event.pointerId);
      setDragging(side);
      dragStart.current = {
        startX: event.clientX,
        startWidth: side === "left" ? leftWidth : rightWidth,
      };
    },
    [leftWidth, rightWidth],
  );

  const handlePointerMove = useCallback(
    (event: PointerEvent) => {
      if (!dragStart.current || !dragging) return;
      const delta = event.clientX - dragStart.current.startX;
      if (dragging === "left") {
        onLeftResize?.(clampSidebarWidth(dragStart.current.startWidth + delta));
      } else {
        onRightResize?.(clampSidebarWidth(dragStart.current.startWidth - delta));
      }
    },
    [dragging, onLeftResize, onRightResize],
  );

  const handlePointerUp = useCallback(() => {
    setDragging(null);
    dragStart.current = null;
  }, []);

  useIsDragging(dragging !== null, handlePointerMove, handlePointerUp);

  return (
    <div className="relative h-screen w-full overflow-hidden">
      {/* Canvas area — always full-size behind sidebars */}
      <div className="absolute inset-0 z-0">{children}</div>

      {/* Top bar */}
      {topBar ? (
        <div className="absolute top-0 inset-x-0 z-20 h-14">{topBar}</div>
      ) : null}

      {/* Left sidebar */}
      {leftPanel ? (
        <>
          <div
            className="absolute top-14 left-0 bottom-0 z-10 border-r border-border/90 bg-surface shadow-xl"
            style={{ width: leftWidth }}
          >
            {leftPanel}
          </div>
          <div
            role="separator"
            aria-label="Resize left sidebar"
            aria-orientation="vertical"
            aria-valuemin={MIN_SIDEBAR_WIDTH}
            aria-valuemax={MAX_SIDEBAR_WIDTH}
            aria-valuenow={Math.round(leftWidth)}
            tabIndex={0}
            className={[
              "absolute top-14 bottom-0 z-30 flex cursor-col-resize items-center justify-center outline-none transition-colors",
              dragging === "left" ? "bg-ice-100" : "bg-transparent hover:bg-ice-50 focus-visible:bg-ice-50",
            ].join(" ")}
            style={{ left: leftWidth, width: 6 }}
            onPointerDown={(e) => handlePointerDown("left", e)}
          >
            <span
              className={[
                "h-12 w-px rounded-full transition-colors",
                dragging === "left" ? "bg-ice-500" : "bg-border group-hover:bg-ice-300 group-focus-visible:bg-ice-400",
              ].join(" ")}
            />
          </div>
        </>
      ) : null}

      {/* Right sidebar */}
      {rightPanel ? (
        <>
          <div
            className="absolute top-14 right-0 bottom-0 z-10 border-l border-border/90 bg-surface shadow-xl"
            style={{ width: rightWidth }}
          >
            {rightPanel}
          </div>
          <div
            role="separator"
            aria-label="Resize right sidebar"
            aria-orientation="vertical"
            aria-valuemin={MIN_SIDEBAR_WIDTH}
            aria-valuemax={MAX_SIDEBAR_WIDTH}
            aria-valuenow={Math.round(rightWidth)}
            tabIndex={0}
            className={[
              "absolute top-14 bottom-0 z-30 flex cursor-col-resize items-center justify-center outline-none transition-colors",
              dragging === "right" ? "bg-ice-100" : "bg-transparent hover:bg-ice-50 focus-visible:bg-ice-50",
            ].join(" ")}
            style={{ right: rightWidth, width: 6 }}
            onPointerDown={(e) => handlePointerDown("right", e)}
          >
            <span
              className={[
                "h-12 w-px rounded-full transition-colors",
                dragging === "right" ? "bg-ice-500" : "bg-border group-hover:bg-ice-300 group-focus-visible:bg-ice-400",
              ].join(" ")}
            />
          </div>
        </>
      ) : null}
    </div>
  );
}

function useIsDragging(
  isDragging: boolean,
  onMove: (event: PointerEvent) => void,
  onUp: () => void,
) {
  const moveRef = useRef(onMove);
  const upRef = useRef(onUp);
  moveRef.current = onMove;
  upRef.current = onUp;

  useEffect(() => {
    if (!isDragging) return;
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const handleMove = (e: PointerEvent) => moveRef.current(e);
    const handleUp = () => upRef.current();

    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", handleUp);
    window.addEventListener("pointercancel", handleUp);
    window.addEventListener("lostpointercapture", handleUp);

    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", handleUp);
      window.removeEventListener("pointercancel", handleUp);
      window.removeEventListener("lostpointercapture", handleUp);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
    };
  });
}
