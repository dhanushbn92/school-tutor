import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate, useSearchParams } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { BrandLogo } from "@/components/BrandLogo";
import { BRAND_NAME } from "@/lib/brand";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api, humanError, saveToken } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { LoginResponse, User } from "@/lib/types";

interface ParentSignupResponse {
  user: User;
  child_user_id: number;
  token: LoginResponse;
}

/**
 * Stage 6 of the child-centric roadmap — parent / guardian signup.
 *
 * Differs from the individual learner signup in one critical way:
 * the parent must enter a single-use invite code their child
 * generated. The backend `consume_invite_code` validates the code,
 * creates the User row, AND writes the parent ↔ child link in one
 * atomic transaction — so a bad code never leaves an orphan
 * parent account.
 *
 * The page accepts `?code=ABCD1234` as a query param so a learner
 * can share a deep link rather than dictating the code over the
 * phone. The field stays editable so the parent can correct typos.
 */
export function SignupParentPage() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const initialCode = (searchParams.get("code") ?? "").toUpperCase().slice(0, 16);

  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    invite_code: initialCode,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { data } = await api.post<ParentSignupResponse>("/auth/signup-parent", {
        full_name: form.full_name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
        // Server normalises to uppercase + strips whitespace, but
        // doing it client-side too means the input field shows the
        // canonical form as the parent types.
        invite_code: form.invite_code.trim().toUpperCase(),
      });
      saveToken(data.token.access_token);
      await refresh();
      navigate("/", { replace: true });
    } catch (err) {
      setError(humanError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-(--color-muted) p-6">
      <div className="mb-6 flex items-center gap-2.5 text-(--color-foreground)">
        <BrandLogo size={36} />
        <span className="text-lg font-semibold tracking-tight">{BRAND_NAME}</span>
      </div>
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>Create a parent account</CardTitle>
          <CardDescription>
            Stay connected to your child's practice with a gentle, encouraging
            view — no marks, no grading reports. You'll need a short invite
            code from your child to get started.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="invite_code">Invite code from your child</Label>
              <Input
                id="invite_code"
                required
                minLength={8}
                maxLength={16}
                autoComplete="off"
                spellCheck={false}
                value={form.invite_code}
                onChange={(e) =>
                  setForm({
                    ...form,
                    invite_code: e.target.value.toUpperCase().replace(/\s+/g, ""),
                  })
                }
                placeholder="ABCD1234"
                className="font-mono tracking-widest uppercase"
              />
              <p className="text-[11px] text-(--color-muted-foreground)">
                Ask your child to generate one from their dashboard.
              </p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="full_name">Your name</Label>
              <Input
                id="full_name"
                required
                minLength={2}
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="Priya Patel"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                required
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="you@example.com"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                required
                minLength={8}
                value={form.password}
                onChange={(e) => setForm({ ...form, password: e.target.value })}
              />
              <p className="text-[11px] text-(--color-muted-foreground)">
                Minimum 8 characters.
              </p>
            </div>

            {error && (
              <div className="rounded-md border border-(--color-destructive) bg-[color-mix(in_oklab,var(--color-destructive)_10%,transparent)] px-3 py-2 text-sm text-(--color-destructive)">
                {error}
              </div>
            )}
          </CardContent>
          <CardFooter className="flex-col items-stretch gap-3 pt-2">
            <Button type="submit" disabled={submitting} className="w-full">
              {submitting && <Loader2 className="h-4 w-4 animate-spin" />}
              {submitting ? "Creating account…" : "Create parent account"}
            </Button>
            <p className="text-center text-xs text-(--color-muted-foreground)">
              Already a member?{" "}
              <Link to="/login" className="text-(--color-primary) underline-offset-4 hover:underline">
                Sign in
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
