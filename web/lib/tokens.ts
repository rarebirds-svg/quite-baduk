/**
 * Programmatic access to design tokens for places where Tailwind utilities
 * are not reachable (e.g. SVG inline attributes in Board, image generation).
 *
 * UI should prefer Tailwind classes; only use these constants when necessary.
 */

export const tokens = {
  light: {
    paper: "rgb(245 239 230)",
    "paper-deep": "rgb(233 223 201)",
    ink: "rgb(26 23 21)",
    "ink-mute": "rgb(107 99 90)",
    "ink-faint": "rgb(184 175 163)",
    oxblood: "rgb(123 30 36)",
    gold: "rgb(163 123 30)",
    moss: "rgb(46 74 58)",
    "stone-black": "rgb(15 13 12)",
    "stone-white": "rgb(250 245 236)",
  },
  dark: {
    paper: "rgb(28 25 23)",
    "paper-deep": "rgb(38 34 31)",
    ink: "rgb(242 235 223)",
    "ink-mute": "rgb(155 146 136)",
    "ink-faint": "rgb(92 84 77)",
    oxblood: "rgb(200 80 88)",
    gold: "rgb(217 166 72)",
    moss: "rgb(106 148 120)",
    "stone-black": "rgb(15 13 12)",
    "stone-white": "rgb(250 245 236)",
  },
} as const;

export const motion = {
  base: "150ms ease-out",
  stone: "300ms cubic-bezier(.2,.7,.2,1)",
  page: "200ms ease-out",
} as const;

export type TokenName = keyof typeof tokens.light;
