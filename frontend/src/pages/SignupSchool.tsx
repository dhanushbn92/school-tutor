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
import { VALID_BOARDS } from "@/lib/boards";
import type { LoginResponse, User } from "@/lib/types";

interface SignupResponse {
  user: User;
  school_id: number;
  token: LoginResponse;
}

export function SignupSchoolPage() {
  const { user, refresh } = useAuth();
  const navigate = useNavigate();
  const [school, setSchool] = useState({ name: "", board: "CBSE", contact_email: "" });
  const [admin, setAdmin] = useState({ full_name: "", email: "", password: "" });
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (user) return <Navigate to="/" replace />;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const { data } = await api.post<SignupResponse>("/auth/signup-school", {
        school_name: school.name.trim(),
        board: school.board.trim() || "CBSE",
        contact_email: school.contact_email.trim() || null,
        admin_full_name: admin.full_name.trim(),
        admin_email: admin.email.trim().toLowerCase(),
        admin_password: admin.password,
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
      <Card className="w-full max-w-lg">
        <CardHeader>
          <CardTitle>Onboard your school</CardTitle>
          <CardDescription>
            Create your school's tenant. Your data stays isolated to your school; you'll be the
            first administrator and can invite teachers + add students next.
          </CardDescription>
        </CardHeader>
        <form onSubmit={handleSubmit}>
          <CardContent className="space-y-4">
            <div className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
              School
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="school_name">School name</Label>
              <Input
                id="school_name"
                required
                minLength={3}
                value={school.name}
                onChange={(e) => setSchool({ ...school, name: e.target.value })}
                placeholder="Sunshine Public School"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label htmlFor="board">Board</Label>
                <Select
                  value={school.board}
                  onValueChange={(v) => setSchool({ ...school, board: v })}
                >
                  <SelectTrigger id="board">
                    <SelectValue placeholder="Pick a board..." />
                  </SelectTrigger>
                  <SelectContent>
                    {VALID_BOARDS.map((b) => (
                      <SelectItem key={b} value={b}>
                        {b}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label htmlFor="contact_email">Contact email (optional)</Label>
                <Input
                  id="contact_email"
                  type="email"
                  value={school.contact_email}
                  onChange={(e) =>
                    setSchool({ ...school, contact_email: e.target.value })
                  }
                />
              </div>
            </div>

            <div className="pt-2 text-xs uppercase tracking-wide text-(--color-muted-foreground)">
              First administrator
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="admin_name">Your full name</Label>
              <Input
                id="admin_name"
                required
                minLength={2}
                value={admin.full_name}
                onChange={(e) => setAdmin({ ...admin, full_name: e.target.value })}
                placeholder="Mrs. Anita Verma"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="admin_email">Email</Label>
              <Input
                id="admin_email"
                type="email"
                required
                value={admin.email}
                onChange={(e) => setAdmin({ ...admin, email: e.target.value })}
                placeholder="principal@yourschool.edu"
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="admin_password">Password</Label>
              <Input
                id="admin_password"
                type="password"
                required
                minLength={8}
                value={admin.password}
                onChange={(e) => setAdmin({ ...admin, password: e.target.value })}
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
              {submitting ? "Creating school…" : "Create school"}
            </Button>
            <p className="text-center text-xs text-(--color-muted-foreground)">
              Already have an account?{" "}
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
