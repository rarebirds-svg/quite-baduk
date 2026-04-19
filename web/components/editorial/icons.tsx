import * as React from "react";

type IconProps = React.SVGAttributes<SVGSVGElement> & { size?: number };

const svgBase = (size: number): React.SVGAttributes<SVGSVGElement> => ({
  width: size,
  height: size,
  viewBox: "0 0 24 24",
  fill: "none",
  stroke: "currentColor",
  strokeWidth: 1.5,
  strokeLinecap: "round" as const,
  strokeLinejoin: "round" as const,
});

export const IconPass = ({ size = 16, ...props }: IconProps) => (
  <svg {...svgBase(size)} aria-hidden="true" {...props}>
    <line x1="5" y1="19" x2="19" y2="5" />
    <circle cx="8" cy="16" r="1.5" fill="currentColor" />
  </svg>
);

export const IconResign = ({ size = 16, ...props }: IconProps) => (
  <svg {...svgBase(size)} aria-hidden="true" {...props}>
    <circle cx="12" cy="12" r="9" />
    <line x1="12" y1="3" x2="12" y2="21" />
  </svg>
);

export const IconUndo = ({ size = 16, ...props }: IconProps) => (
  <svg {...svgBase(size)} aria-hidden="true" {...props}>
    <path d="M9 14L4 9l5-5" />
    <path d="M4 9h10a6 6 0 010 12h-3" />
  </svg>
);

export const IconHint = ({ size = 16, ...props }: IconProps) => (
  <svg {...svgBase(size)} aria-hidden="true" {...props}>
    <circle cx="12" cy="12" r="9" />
    <circle cx="12" cy="12" r="3" fill="currentColor" />
  </svg>
);

export const IconHandicap = ({ size = 16, ...props }: IconProps) => (
  <svg {...svgBase(size)} aria-hidden="true" {...props}>
    <circle cx="7" cy="7" r="1.5" fill="currentColor" />
    <circle cx="17" cy="7" r="1.5" fill="currentColor" />
    <circle cx="7" cy="17" r="1.5" fill="currentColor" />
    <circle cx="17" cy="17" r="1.5" fill="currentColor" />
    <circle cx="12" cy="12" r="1.5" fill="currentColor" />
  </svg>
);
