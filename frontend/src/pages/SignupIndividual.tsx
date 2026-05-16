import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, humanError, saveToken } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import type { LoginResponse, User } from "@/lib/types";

interface IndividualSignupResponse {
  user: User;
  school_id: number;
  section_id: number;
  student_id: number;
  token: LoginResponse;
}

const CLASS_OPTIONS = [6, 7, 8, 9, 10];

export function SignupIndividualPage() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    class_level: 6,
  });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { data } = await api.post<IndividualSignupResponse>("/auth/signup-individual", {
        full_name: form.full_name.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
        class_level: form.class_level,
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
          <CardTitle>Create your learning account</CardTitle>
          <CardDescription>
            For students learning on their own. You'll get a personal mastery dashboard
            and instant practice quizzes from the curated question bank.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="full_name">Your name</Label>
              <Input
                id="full_name"
                required
                minLength={2}
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                placeholder="Rohan Patel"
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
            <div className="space-y-1.5">
              <Label>Class</Label>
              <Select
                value={String(form.class_level)}
                onValueChange={(v) => setForm({ ...form, class_level: Number(v) })}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CLASS_OPTIONS.map((c) => (
                    <SelectItem key={c} value={String(c)}>
                      Class {c}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-[11px] text-(--color-muted-foreground)">
                Class 6–10 supported in MVP. You can change this later.
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
              {submitting ? "Creating account…" : "Create account"}
            </Button>
            <p className="text-center text-xs text-(--color-muted-foreground)">
              Already a member?{" "}
              <Link to="/login" className="text-(--color-primary) underline-offset-4 hover:underline">
                Sign in
              </Link>
              {" · "}
              Onboarding a school?{" "}
              <Link to="/signup-school" className="text-(--color-primary) underline-offset-4 hover:underline">
                Use the school signup
              </Link>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
