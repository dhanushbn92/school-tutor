import { useState, type FormEvent } from "react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
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
import { useAuth } from "@/lib/auth";
import { humanError } from "@/lib/api";

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) {
    const redirect = (location.state as { from?: string } | null)?.from ?? "/";
    return <Navigate to={redirect} replace />;
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await login(email.trim().toLowerCase(), password);
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
      <Card className="w-full max-w-sm">
        <CardHeader>
          <CardTitle>Sign in</CardTitle>
          <CardDescription>
            Use your school-issued email and password.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="email">Email</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="teacher@yourschool.edu"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="password">Password</Label>
              <Input
                id="password"
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
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
              {submitting ? "Signing in..." : "Sign in"}
            </Button>
            <div className="space-y-1 text-center text-xs text-(--color-muted-foreground)">
              <p>
                Self-learner?{" "}
                <a
                  href="/signup-individual"
                  className="text-(--color-primary) underline-offset-4 hover:underline"
                >
                  Create a learning account
                </a>
              </p>
              <p>
                New school?{" "}
                <a
                  href="/signup-school"
                  className="text-(--color-primary) underline-offset-4 hover:underline"
                >
                  Onboard your school
                </a>
              </p>
              <p>
                Parent / guardian?{" "}
                <a
                  href="/signup-parent"
                  className="text-(--color-primary) underline-offset-4 hover:underline"
                >
                  Sign up with an invite code
                </a>
              </p>
              <p>Trouble signing in? Contact your school administrator.</p>
            </div>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
}
