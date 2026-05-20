// 2자리 ISO 국가 코드를 작은 국기 이미지로 렌더링하는 컴포넌트.
import * as React from "react";

export interface CountryFlagProps {
  /** 2-letter ISO 3166-1 code (대소문자 무관). 없거나 형식이 어긋나면 미표시. */
  code?: string | null;
  className?: string;
}

/**
 * flagcdn.com의 작은 PNG로 국기를 표시한다. 국기 이모지는 Windows에서
 * 글리프가 없어 글자로 깨지므로, 모든 플랫폼에서 일관되게 보이는
 * 이미지 방식을 쓴다. width 16px — 닉네임 옆 인라인 표식 용도.
 */
export function CountryFlag({ code, className }: CountryFlagProps) {
  if (!code || !/^[A-Za-z]{2}$/.test(code)) return null;
  const lc = code.toLowerCase();
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={`https://flagcdn.com/w20/${lc}.png`}
      srcSet={`https://flagcdn.com/w40/${lc}.png 2x`}
      width={16}
      height={12}
      alt={code.toUpperCase()}
      title={code.toUpperCase()}
      loading="lazy"
      className={
        "inline-block shrink-0 align-[-0.1em] " + (className ?? "")
      }
    />
  );
}
