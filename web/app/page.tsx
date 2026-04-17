"use client";
import Link from "next/link";
import { useT } from "@/lib/i18n";

export default function Home() {
  const t = useT();
  return (
    <div className="space-y-6 mt-6">
      <h1 className="text-3xl font-bold">{t("home.heading")}</h1>
      <p className="text-gray-600 dark:text-gray-400">{t("home.sub")}</p>
      <Link href="/game/new" className="inline-block px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700">
        {t("home.startButton")}
      </Link>
    </div>
  );
}
