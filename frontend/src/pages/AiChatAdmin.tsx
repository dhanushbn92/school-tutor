import { useMemo, useState } from "react";
import { Loader2, Search } from "lucide-react";
import { toast } from "sonner";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Empty } from "@/components/ui/empty";
import { api, humanError } from "@/lib/api";

interface AdminUser {
  id: number;
  email: string;
  full_name: string;
  role: string;
  school_id: number | null;
  ai_chat_enabled: boolean;
}

export function AiChatAdminPage() {
  const qc = useQueryClient();
  const usersQ = useQuery({
    queryKey: ["admin", "users"],
    queryFn: async () => {
      const { data } = await api.get<AdminUser[]>("/admin/users");
      return data;
    },
  });
  const toggle = useMutation({
    mutationFn: async ({ userId, enabled }: { userId: number; enabled: boolean }) => {
      const { data } = await api.post<{ user_id: number; ai_chat_enabled: boolean }>(
        `/admin/users/${userId}/ai-chat-enabled`,
        { enabled },
      );
      return data;
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["admin", "users"] }),
    onError: (err) => toast.error(humanError(err)),
  });

  const [filter, setFilter] = useState("");
  const filtered = useMemo(() => {
    const all = usersQ.data ?? [];
    const q = filter.trim().toLowerCase();
    if (!q) return all;
    return all.filter(
      (u) =>
        u.email.toLowerCase().includes(q) ||
        u.full_name.toLowerCase().includes(q) ||
        u.role.toLowerCase().includes(q),
    );
  }, [usersQ.data, filter]);

  const enabledCount = (usersQ.data ?? []).filter((u) => u.ai_chat_enabled).length;
  const learnerCount = (usersQ.data ?? []).filter(
    (u) => u.role === "student" || u.role === "individual_learner",
  ).length;

  return (
    <ThemedPage>
      <PageHeader
        title="AI tutor entitlements"
        description="Toggle the premium AI tutor on or off per user. Once payment lands this will be automated."
      />

      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-wide text-(--color-muted-foreground)">
              Total users
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{usersQ.data?.length ?? "—"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-wide text-(--color-muted-foreground)">
              Learners
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold">{learnerCount}</div>
            <div className="text-xs text-(--color-muted-foreground)">
              students + individual learners
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-sm uppercase tracking-wide text-(--color-muted-foreground)">
              AI chat enabled
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-semibold text-(--color-success)">
              {enabledCount}
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Users</CardTitle>
          <CardDescription>
            Click the toggle to grant or revoke AI tutor access. Effective
            immediately on the user's next page load.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="mb-3 flex items-center gap-2">
            <Search className="h-4 w-4 text-(--color-muted-foreground)" />
            <Input
              placeholder="Search by email, name, or role…"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              className="max-w-sm"
            />
          </div>

          {usersQ.isLoading ? (
            <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
              <Loader2 className="h-4 w-4 animate-spin" /> Loading users…
            </div>
          ) : filtered.length === 0 ? (
            <Empty title="No users match your filter" />
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-xs uppercase tracking-wide text-(--color-muted-foreground)">
                  <tr className="border-b border-(--color-border)">
                    <th className="py-2 text-left font-medium">User</th>
                    <th className="py-2 text-left font-medium">Email</th>
                    <th className="py-2 text-left font-medium">Role</th>
                    <th className="py-2 text-right font-medium">AI tutor</th>
                  </tr>
                </thead>
                <tbody>
                  {filtered.map((u) => (
                    <tr key={u.id} className="border-b border-(--color-border)/60">
                      <td className="py-2">{u.full_name}</td>
                      <td className="py-2 text-(--color-muted-foreground)">{u.email}</td>
                      <td className="py-2">
                        <Badge variant="outline">{u.role}</Badge>
                      </td>
                      <td className="py-2 text-right">
                        <button
                          type="button"
                          onClick={() =>
                            toggle.mutate({ userId: u.id, enabled: !u.ai_chat_enabled })
                          }
                          disabled={toggle.isPending}
                          className={`relative inline-flex h-5 w-10 items-center rounded-full transition-colors ${
                            u.ai_chat_enabled
                              ? "bg-(--color-success)"
                              : "bg-(--color-muted)"
                          }`}
                          title={
                            u.ai_chat_enabled
                              ? "Disable AI tutor for this user"
                              : "Enable AI tutor for this user"
                          }
                        >
                          <span
                            className={`inline-block h-4 w-4 transform rounded-full bg-white shadow transition-transform ${
                              u.ai_chat_enabled ? "translate-x-5" : "translate-x-0.5"
                            }`}
                          />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </ThemedPage>
  );
}
