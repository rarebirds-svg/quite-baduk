# Social Login + Nationality Onboarding — Design

> **SUPERSEDED 2026-04-22** — 개인정보 관리 이슈로 폐기. 대체 설계: [`2026-04-22-ephemeral-nickname-auth-design.md`](./2026-04-22-ephemeral-nickname-auth-design.md). 이 문서는 설계 역사 보존 목적으로 유지합니다.

**Date:** 2026-04-21
**Status:** Superseded (was "Approved for planning")
**Scope:** Replace email/password auth with social login across 8 providers; collect nationality during onboarding.

## 1. Problem & Goals

The project currently ships an email + bcrypt password auth with self-signup. To support a public launch across KR / JP / CN / global markets, we are replacing it with social-only login. Self-signup is removed. During a user's first login we require a one-time nationality entry.

**Success criteria:**

- No email/password login paths remain in code or UI.
- 8 providers are architecturally supported: Google, Naver, Kakao, Facebook, LINE, WeChat, LinkedIn, Yahoo! JAPAN.
- Providers activate per-environment by credential presence — missing credentials cause the provider's button to hide and its endpoints to 404.
- Every user has a `country_code` (ISO 3166-1 alpha-2) by the time they land on any feature page.
- Existing session / cookie / WebSocket auth continues to work unchanged (JWT in HttpOnly cookie).

**Non-goals (YAGNI):**

- OAuth refresh tokens and provider API calls after login (we do not store tokens).
- 2FA, passkey, magic link.
- Admin merge tools (dev stage; handle manually via SQL if needed).
- Periodic profile sync from provider after first login.
- Single logout across providers.
- Email re-verification.

## 2. Key Design Decisions

| Decision | Choice |
|----------|--------|
| Provider rollout | Credential-driven: all 8 coded, enabled per-`.env` |
| OAuth orchestration | Backend-driven (FastAPI) — existing JWT cookie session reused |
| Nationality collection | Blocking `/onboarding` page after first login, `country_code` ISO-2 |
| Account linking | `(provider, subject)` unique, no auto-merge; explicit linking from settings |
| Existing email/password users | Wiped (pre-launch dev state); password code path removed entirely |
| Display name / avatar | Auto-populated from provider, editable during onboarding |

## 3. Data Model

Migration `0005_social_auth.py` recreates `users` and introduces `user_identities`. All existing `users`, `games`, `moves`, `analysis_cache` rows are dropped (pre-launch).

### `users` (recreated)

```
id             INTEGER PK
display_name   VARCHAR(64)  NOT NULL        -- seeded from provider
avatar_url     VARCHAR(512) NULL            -- seeded from provider
country_code   CHAR(2)      NULL            -- NULL until onboarding complete
locale         VARCHAR(8)   NOT NULL DEFAULT 'ko'
theme          VARCHAR(8)   NOT NULL DEFAULT 'light'
preferred_rank VARCHAR(8)   NULL
created_at     DATETIME     NOT NULL DEFAULT now()
last_login_at  DATETIME     NULL
```

Removed columns: `email`, `password_hash`. Email now lives on identities because a user may link multiple providers with different emails.

### `user_identities` (new)

```
id              INTEGER PK
user_id         INTEGER      NOT NULL  REFERENCES users(id) ON DELETE CASCADE
provider        VARCHAR(16)  NOT NULL   -- google|naver|kakao|facebook|line|wechat|linkedin|yahoo_jp
subject         VARCHAR(255) NOT NULL   -- provider's user id (sub / id / openid / unionid)
email           VARCHAR(255) NULL
email_verified  BOOLEAN      NOT NULL DEFAULT false
created_at      DATETIME     NOT NULL DEFAULT now()
UNIQUE (provider, subject)
INDEX (user_id)
INDEX (email) WHERE email IS NOT NULL
```

**WeChat detail:** `subject` stores `unionid` when present (stable across apps under the same Open Platform) and falls back to `openid`. This prevents account fragmentation when a mobile client is added later.

**No OAuth tokens stored.** The userinfo exchange happens once per login and is never reused. This eliminates token-refresh plumbing and reduces leak surface.

## 4. Provider Adapter Layer

One `OAuthProvider` protocol with 8 implementations in `backend/app/core/oauth/`:

```python
class OAuthProvider(Protocol):
    name: str
    authorize_url: str
    token_url: str
    userinfo_url: str | None
    scope: str
    email_is_verified_by_default: bool

    def build_authorize_params(
        self, *, client_id: str, redirect_uri: str, state: str,
        code_verifier: str | None = None,
    ) -> dict[str, str]: ...

    async def exchange_code(
        self, *, code: str, redirect_uri: str, code_verifier: str | None,
        http: httpx.AsyncClient,
    ) -> dict[str, Any]: ...

    async def fetch_userinfo(
        self, *, token_response: dict[str, Any], http: httpx.AsyncClient,
    ) -> UserInfo: ...


@dataclass
class UserInfo:
    subject: str
    email: str | None
    email_verified: bool
    name: str | None
    avatar_url: str | None
```

### Per-provider notes

| Provider | Module | Protocol | Key details |
|----------|--------|----------|-------------|
| Google   | `oauth/google.py`   | OIDC     | `id_token` JWKS-verified via authlib; `sub`; verified email guaranteed |
| LinkedIn | `oauth/linkedin.py` | OIDC     | `sub`, `email`, `email_verified`, `name`, `picture` from userinfo |
| Yahoo JP | `oauth/yahoo_jp.py` | OIDC     | Issuer `https://auth.login.yahoo.co.jp`; scope `openid email profile` |
| LINE     | `oauth/line.py`     | OIDC     | Scope `openid profile email`; email requires channel config; not treated as verified |
| Kakao    | `oauth/kakao.py`    | OAuth2   | `GET /v2/user/me`; `kakao_account.is_email_verified` → `email_verified` |
| Naver    | `oauth/naver.py`    | OAuth2   | `GET /v1/nid/me`; Naver guarantees verified email |
| Facebook | `oauth/facebook.py` | OAuth2   | `GET /me?fields=id,email,name,picture`; email may be missing; not treated as verified |
| WeChat   | `oauth/wechat.py`   | OAuth2 (non-standard) | `appid` param (not `client_id`), `#wechat_redirect` fragment, `/sns/oauth2/access_token` returns `openid`/`unionid` in JSON, userinfo at `/sns/userinfo`; no email; subject = unionid fallback openid |

**`email_verified` policy:** Only Google, Naver, Kakao (when `is_email_verified=true`), LinkedIn, Yahoo JP are trusted. Facebook, LINE, WeChat are never treated as verified for conflict-detection purposes.

Each adapter is 60–120 LOC. OIDC providers reuse `authlib`'s OIDC client for token + id_token verification. Non-OIDC providers use raw `httpx`.

### Registry

```python
# backend/app/core/oauth/registry.py
PROVIDERS: dict[str, OAuthProvider] = {
    "google": GoogleProvider(), ...
}

def enabled_providers() -> list[str]:
    return [name for name in PROVIDERS if _get_credentials(name) is not None]
```

A provider is enabled iff both `*_CLIENT_ID` and `*_CLIENT_SECRET` (or `*_APP_ID`/`*_APP_SECRET` for WeChat) are set.

## 5. OAuth Endpoints

```
GET    /api/auth/providers                       -> ["google","kakao",...]
GET    /api/auth/oauth/{provider}/start?next=... -> 302 to authorize URL
GET    /api/auth/oauth/{provider}/callback       -> 302 to next or /onboarding
POST   /api/auth/oauth/{provider}/link           -> { authorize_url } (authenticated)
GET    /api/auth/oauth/{provider}/link/callback  -> 302 to /settings
GET    /api/auth/identities                      -> list current user's identities
DELETE /api/auth/identities/{id}                 -> 204 or 409 oauth_unlink_last
POST   /api/auth/onboarding                      -> set country_code (+ optional display_name)
```

`POST /api/auth/logout` and `GET /api/auth/me` remain unchanged in contract; `/me` gains `needs_onboarding: bool`.

### State / PKCE / Nonce

`state` is a random opaque 32-byte token (short enough for WeChat's 32-char limit). Its payload — `{nonce, provider, flow: "login"|"link", next_url, user_id?}` — is stored in a separate HMAC-signed HttpOnly `oauth_state` cookie (SameSite=Lax, 10-minute TTL). The callback verifies signature, TTL, provider match, and (for link flow) matches `user_id` against `get_current_user()`.

PKCE is used for every provider that supports it (Google, Kakao, LinkedIn, Yahoo JP, LINE). WeChat, Facebook, Naver do not support PKCE and are skipped.

`nonce` is used for OIDC providers and compared to the `id_token` nonce claim.

`next` values are rejected unless they are path-only and start with `/` (no `//` to block open redirects).

### Login flow

```
1. GET /api/auth/oauth/google/start?next=/game/new
   - generate state + pkce + nonce; write oauth_state / oauth_pkce cookies
   - 302 to https://accounts.google.com/o/oauth2/v2/auth?...

2. User consents at Google.

3. GET /api/auth/oauth/google/callback?code=...&state=...
   - validate state cookie (sig, TTL, provider match)
   - exchange code -> token response -> userinfo (UserInfo)
   - branch:
     (a) (google, subject) exists -> login that user
     (b) does not exist AND userinfo.email present AND verified
         AND another user has a verified identity with the same email
         -> 302 /login?error=email_conflict&with=<existing_provider>
     (c) otherwise -> create new user (display_name=name, avatar_url=picture),
         insert user_identities row, country_code = NULL
   - issue access_token + refresh_token cookies
   - 302 to next_url, unless country_code IS NULL in which case 302 /onboarding
```

### Link flow

```
1. POST /api/auth/oauth/kakao/link   (authenticated)
   - state payload includes current user_id
   - 200 { authorize_url }

2. Frontend navigates to authorize_url.

3. GET /api/auth/oauth/kakao/link/callback?code=...
   - state.user_id must equal current user
   - exchange + userinfo
   - if (kakao, subject) already exists -> 302 /settings?error=already_linked
   - else insert user_identities row for current user
   - 302 /settings?linked=kakao
```

### Unlink

`DELETE /api/auth/identities/{id}` refuses if the user has only 1 identity remaining (`oauth_unlink_last`), preventing lockout.

### Rate limiting

Existing `rate_limiter`:
- `/start`, `/link`: 10 / minute / IP
- `/callback`, `/link/callback`: 20 / minute / IP
- `/onboarding`: 5 / minute / IP

### Error codes (i18n keys under `errors.`)

```
oauth_state_invalid     -> "보안 검증에 실패했습니다. 다시 시도해주세요"
oauth_provider_error    -> "소셜 로그인 중 오류가 발생했습니다"
oauth_email_conflict    -> "이미 {existing}(으)로 가입된 이메일입니다. {existing}(으)로 로그인 후 설정에서 연결해주세요"
oauth_already_linked    -> "이 계정은 이미 다른 사용자에 연결되어 있습니다"
oauth_unlink_last       -> "마지막 로그인 수단은 해제할 수 없습니다"
invalid_country         -> "국가를 선택해주세요"
already_onboarded       -> "이미 가입이 완료된 계정입니다"
```

## 6. Password Auth Removal

Removed entirely (no backwards-compat shims per project convention):

- Endpoints: `POST /api/auth/signup`, `POST /api/auth/login`
- Schemas: `SignupRequest`, `LoginRequest` in `schemas/auth.py`
- Services: `create_user`, `authenticate`, `AuthError` in `services/user_service.py`
- Security helpers: `hash_password`, `verify_password` in `security.py`
- Dependency: `bcrypt` removed from `pyproject.toml`
- Frontend page: `web/app/signup/page.tsx` deleted; `web/app/login/page.tsx` rewritten
- Nav: signup link removed from `TopNav`; `home.guestSignup` link now points to `/login`
- i18n keys removed: `auth.email`, `auth.password`, `auth.displayName`, `auth.signup`, `auth.mustBeLongerPassword`, `errors.invalid_credentials`, `errors.email_already_registered`

## 7. Onboarding (Nationality) Flow

### Backend

- `UserPublic` gains `needs_onboarding: bool` (true iff `country_code IS NULL`).
- `POST /api/auth/onboarding`:
  ```
  body: { country_code: "KR", display_name?: "홍길동" }
  - authenticated
  - country_code: must match ISO 3166-1 alpha-2 against a bundled static allowlist at `backend/app/core/countries.py` (no new backend dependency)
  - display_name: 1..64 chars if provided
  - 409 if already onboarded
  - 200 -> UserPublic
  ```
- Other endpoints (games, analysis, settings) are unchanged and continue to work with `country_code IS NULL`. Only the frontend guard enforces onboarding.

### Frontend guard (AuthGate)

Client-side guard inside the top-level layout (Next.js App Router) — not middleware, to keep cookie handling simple:

- Fetch `/api/auth/me` on mount.
- 401 → redirect to `/login?next=<current>`.
- 200 with `needs_onboarding=true` and path not in `{/onboarding}` → `router.replace("/onboarding")`.
- 200 with `needs_onboarding=false` and path `/onboarding` → `router.replace("/")`.

Public routes bypassing AuthGate: `/login`, `/onboarding`, `/api/auth/oauth/**`.

### Onboarding UI (`web/app/onboarding/page.tsx`)

Editorial layout: Hero with localized welcome, rule divider, two form fields (display name, country combobox), submit.

- **Display name**: pre-filled from provider value, editable.
- **Country**: searchable combobox over 249 ISO regions.
  - Labels from browser `Intl.DisplayNames([locale], { type: "region" })` — "대한민국" in ko, "South Korea" in en.
  - Right-aligned ISO-2 mono chip (`KR`, `JP`, `US`) instead of flag emoji (project forbids emoji).
  - Default selection guessed from `navigator.language` region, falling back to locale mapping (`ko`→`KR`, `ja`→`JP`, `zh`→`CN`, `en`→`US`).
  - Sorted by localized name (hangul order in ko locale, alphabetical in en).
- **Submit** → `POST /api/auth/onboarding` → on success `router.replace("/")` (or the stored `next`).

### Combobox component

New `web/components/ui/combobox.tsx` — Radix `Popover` + a custom Command-like pattern:

- 249 options rendered directly (no virtualization needed).
- Keyboard: ArrowUp/ArrowDown, Enter, Escape.
- ARIA: `role="combobox"`, `aria-expanded`, `aria-activedescendant`.
- Styling: Editorial tokens only — `rounded-sm`, no shadow, `bg-paper`.

### i18n keys (ko / en)

```
onboarding: {
  welcome: "환영합니다, {name}님",
  subtitle: "대국을 시작하기 전에 몇 가지만 확인할게요",
  displayName: "표시 이름",
  country: "국적",
  countrySearchPlaceholder: "국가 검색…",
  submit: "시작하기"
}
```

## 8. Settings — Linked Accounts

`/settings` gains a "연결된 로그인" section showing current identities and allowing link / unlink.

### Backend contract

- `GET /api/auth/identities` returns `[{ id, provider, email, created_at }, ...]`.
- `POST /api/auth/oauth/{provider}/link` returns `{ authorize_url }`.
- `DELETE /api/auth/identities/{id}` with last-identity guard.

### UI

- One row per linked provider with logo, email (or `—`), unlink button.
- "Link more" chips for providers the user has NOT linked yet (only among enabled ones).
- Clicking a chip calls `/link`, then `window.location.assign(authorize_url)`.
- Callback returns to `/settings?linked=<provider>` with a toast (via `sonner`).
- Unlink button disabled with tooltip when only one identity remains.

### Provider logos

`web/components/editorial/icons/oauth/{provider}.tsx` — one SVG per provider, sized 24×24, honoring each provider's brand guideline.

- Google, Naver, Kakao, Facebook, LINE, WeChat, LinkedIn, Yahoo! JAPAN (distinct from Yahoo US).
- Asset provenance is recorded in `docs/oauth-brand-assets.md` (official source links).
- Any missing asset lands as a labeled placeholder with a TODO and is replaced before launch — tracked in the plan.

### i18n keys

```
settings: {
  linkedAccounts: "연결된 로그인",
  linkMore: "다른 방법으로도 로그인하기",
  unlink: "해제",
  unlinkLastTooltip: "마지막 로그인 수단은 해제할 수 없습니다",
  linkedSuccess: "{provider}가 연결되었습니다",
  unlinkedSuccess: "{provider} 연결이 해제되었습니다"
}
```

## 9. Login Page

`/login` fully replaces the old email/password form:

- Brand heading + "로그인 / 가입".
- One button per enabled provider, fetched via `/api/auth/providers` on page load.
- Button order is fixed: `google, naver, kakao, facebook, line, wechat, linkedin, yahoo_jp` — disabled ones are omitted.
- Editorial styling: neutral `bg-paper` background, `border-ink/10`, `rounded-sm`, no shadow. Provider color is restricted to the logo.
- Query param handling: `?error=<code>` displays the mapped i18n message above the buttons.
- Footer line explains onboarding: "소셜 로그인 후 국적을 한 번만 선택하면 가입이 완료됩니다."

### i18n keys

```
auth: {
  signInHeading: "로그인 / 가입",
  continueWith: "{provider}로 계속하기",
  onboardingHint: "소셜 로그인 후 국적을 한 번만 선택하면 가입이 완료됩니다.",
  providerName: {
    google: "Google", naver: "Naver", kakao: "Kakao", facebook: "Facebook",
    line: "LINE", wechat: "WeChat", linkedin: "LinkedIn", yahoo_jp: "Yahoo! JAPAN"
  }
}
```

## 10. Security Checklist

- All cookies (`access_token`, `refresh_token`, `oauth_state`, `oauth_pkce`) are HttpOnly + SameSite=Lax.
- `secure` flag is `true` in prod via `settings.cookie_secure`.
- `state` cookie is HMAC-signed using `JWT_SECRET`, 10-minute TTL.
- PKCE enforced on every provider that supports it.
- OIDC `id_token` signature (JWKS), `iss`, `aud`, `exp`, `nonce` verified via authlib.
- Open-redirect protection on the `next` param: path-only, starts with `/`, no `//`.
- Email-based auto-merge is disallowed. Conflicts produce a user-visible error, never a silent link.
- WeChat-specific: opaque short state in cookie, unionid preferred as subject.
- Rate limiting on every OAuth endpoint and `/onboarding`.
- Bandit / ruff `S1xx` rules pass; no hardcoded secrets.
- Structured logs include `provider`, `user_id`, `flow`, `outcome` only — never tokens, codes, or state.

## 11. Testing

### Unit

- `backend/tests/oauth/test_providers.py` — per-provider adapter: authorize URL shape, token exchange, userinfo parsing with recorded fixtures at `tests/oauth/fixtures/{provider}_userinfo.json`. Includes Kakao verified-email, LINE email-scope, Facebook missing email, WeChat unionid/openid fallback.
- `backend/tests/oauth/test_state.py` — HMAC sign/verify, TTL, provider mismatch, tampering.

### Integration

- `backend/tests/api/test_oauth_flow.py` — registers a `MockProvider` via conftest and walks:
  - new user → `needs_onboarding=true`
  - returning user with existing `(mock, subject)` → same `user_id`
  - verified-email conflict → 302 `/login?error=email_conflict`
  - tampered state → 400
  - PKCE mismatch → 400
  - link flow: link → 2 identities; unlink last → 409 `oauth_unlink_last`
  - `/onboarding`: valid country → 200; invalid ISO → 422; re-onboard → 409

### Frontend

- Combobox filtering and keyboard behavior (vitest + Testing Library).
- AuthGate redirect logic for all three branches.
- Login page renders only enabled providers.

### E2E

- `e2e/tests/auth.spec.ts` — Docker stack with `MOCK_OAUTH_ENABLED=true`:
  1. Click "Mock로 계속하기" → callback auto-handled → `/onboarding`.
  2. Pick country → `/game/new`.
  3. Logout → re-login → onboarding skipped.
- Real providers are **not** in E2E. A manual QA checklist in `docs/oauth-setup.md` covers each production provider.

## 12. Configuration

`.env.example` additions (all blank by default):

```
OAUTH_REDIRECT_BASE_URL=http://localhost:8000
OAUTH_GOOGLE_CLIENT_ID=
OAUTH_GOOGLE_CLIENT_SECRET=
OAUTH_NAVER_CLIENT_ID=
OAUTH_NAVER_CLIENT_SECRET=
OAUTH_KAKAO_CLIENT_ID=
OAUTH_KAKAO_CLIENT_SECRET=
OAUTH_FACEBOOK_CLIENT_ID=
OAUTH_FACEBOOK_CLIENT_SECRET=
OAUTH_LINE_CLIENT_ID=
OAUTH_LINE_CLIENT_SECRET=
OAUTH_WECHAT_APP_ID=
OAUTH_WECHAT_APP_SECRET=
OAUTH_LINKEDIN_CLIENT_ID=
OAUTH_LINKEDIN_CLIENT_SECRET=
OAUTH_YAHOO_JP_CLIENT_ID=
OAUTH_YAHOO_JP_CLIENT_SECRET=
COOKIE_SECURE=false
MOCK_OAUTH_ENABLED=false
```

`backend/pyproject.toml` changes: add `authlib>=1.3`, remove `bcrypt`.

`docs/oauth-setup.md` (new) documents each provider dev-console setup: redirect URI (`{OAUTH_REDIRECT_BASE_URL}/api/auth/oauth/{provider}/callback`), scopes requested, and any review/verification steps (WeChat Open Platform, Facebook App Review for `email`, LINE channel email permission).

## 13. Agent-based Quality Review (mandatory post-implementation)

After implementation completes, the following agents run in parallel and their outputs are summarized in the PR description:

| Agent | Review surface | Pass criterion |
|-------|----------------|----------------|
| `design-token-guardian` | `/login`, `/onboarding`, `/settings`, provider logo SVGs — hardcoded hex, emoji, `framer-motion`, inline `fontFamily` | Zero violations |
| `visual-qa` | Light + dark screenshots of login, onboarding, settings; conformance to Editorial spec | No visual regressions |
| `korean-copy-qa` | New ko/en i18n keys (onboarding.*, auth.providerName, oauth error codes, settings.linkedAccounts) — naturalness + consistency | Suggestions applied |
| `a11y-auditor` | Combobox keyboard flow, provider button focus order, ARIA labeling, error live regions | No critical issues |
| `superpowers:code-reviewer` | Backend OAuth layer vs plan and security checklist | Approved |

## 14. Open Questions (resolved during brainstorming)

All resolved — no open questions remain. Summary of choices in §2.

## 15. Glossary

- **subject** — provider-issued stable user id. Google: `sub`, Kakao: `id`, WeChat: `unionid`/`openid`.
- **identity** — a row in `user_identities`; a single (provider, subject) binding to a `user_id`.
- **onboarding** — the one-time step after first login where a user supplies `country_code`.
- **link** — adding an additional identity to an existing authenticated user.
