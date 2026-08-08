"use client";
// 어드민 화면의 인증 실패(세션 만료·권한 없음)를 운영자에게 알리는 안내 문구.
import Link from "next/link";
import type { AuthFailure } from "@/lib/api";
import { useT } from "@/lib/i18n";

export function AdminAuthNotice({ kind }: { kind: AuthFailure }) {
  const t = useT();
  if (kind === "forbidden") {
    return <p className="text-sm text-oxblood">{t("admin.forbidden")}</p>;
  }
  return (
    <p className="text-sm text-oxblood">
      {t("admin.sessionExpired")}{" "}
      <Link href="/" className="underline">
        {t("admin.relogin")}
      </Link>
    </p>
  );
}
