"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useT } from "@/lib/i18n";

export default function SignupPage() {
  const t = useT();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr(null);
    try {
      await api("/api/auth/signup", {
        method: "POST",
        body: JSON.stringify({ email, password, display_name: displayName })
      });
      router.push("/game/new");
    } catch (e: unknown) {
      setErr(t(`errors.${(e as ApiError).code || "validation"}`));
    }
  }
  return (
    <form onSubmit={submit} className="max-w-sm space-y-3 mt-6">
      <h1 className="text-2xl font-bold">{t("auth.signup")}</h1>
      <input className="border rounded px-2 py-1 w-full dark:bg-gray-900" placeholder={t("auth.email")} type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
      <input className="border rounded px-2 py-1 w-full dark:bg-gray-900" placeholder={t("auth.password")} type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
      <input className="border rounded px-2 py-1 w-full dark:bg-gray-900" placeholder={t("auth.displayName")} value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
      {err && <div className="text-red-600 text-sm">{err}</div>}
      <button className="px-4 py-2 bg-blue-600 text-white rounded">{t("auth.signup")}</button>
    </form>
  );
}
