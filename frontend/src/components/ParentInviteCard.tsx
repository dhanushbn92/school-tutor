import { useState } from "react";
import { Check, Copy, Loader2, Plus, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  useCreateParentInviteCode,
  useMyActiveInviteCodes,
  useMyParents,
  useRevokeParent,
} from "@/lib/queries";

/**
 * Stage 6 — learner-side "Invite a parent" card.
 *
 * Two stacked sections in one card:
 *   1. Currently-linked parents, with a revoke button each.
 *   2. Active (unused) invite codes the learner has generated, plus
 *      a button to mint a fresh one.
 *
 * Code-generation is invite-only: a fresh code per parent the
 * learner wants to link. Each code is single-use with a 7-day TTL,
 * so generating one and forgetting to share it is harmless — the
 * code just expires.
 *
 * Sits below PracticeCard on the learner dashboard. Mounting it on
 * the dashboard (vs. a dedicated settings page) was the deliberate
 * choice — children won't go looking in a settings menu, so the
 * affordance lives where they'll bump into it.
 */
export function ParentInviteCard() {
  const parentsQ = useMyParents();
  const codesQ = useMyActiveInviteCodes();
  const createCode = useCreateParentInviteCode();
  const revoke = useRevokeParent();
  const [copiedCode, setCopiedCode] = useState<string | null>(null);

  function handleCopy(code: string) {
    navigator.clipboard
      .writeText(code)
      .then(() => {
        setCopiedCode(code);
        // Reset the visual after a beat so a re-copy still flashes.
        setTimeout(() => setCopiedCode(null), 1500);
      })
      .catch(() => {
        toast.error("Couldn't copy. Read the code aloud instead.");
      });
  }

  function handleRevoke(parentUserId: number, parentName: string) {
    if (
      !window.confirm(
        `Stop sharing your practice with ${parentName}? You can re-link later with a fresh code.`,
      )
    ) {
      return;
    }
    revoke.mutate(parentUserId, {
      onSuccess: () =>
        toast.success(`${parentName} no longer sees your practice.`),
      onError: () => toast.error("Couldn't revoke. Try again."),
    });
  }

  function handleGenerate() {
    createCode.mutate(undefined, {
      onSuccess: () =>
        toast.success(
          "New invite code created — share it with a parent or guardian.",
        ),
    });
  }

  const parents = parentsQ.data ?? [];
  const codes = codesQ.data ?? [];

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="text-base">Parents &amp; guardians</CardTitle>
        <CardDescription>
          Share your practice rhythm with a parent — they see your streak,
          stamps, and weekly goal (never your mistakes). Give them an invite
          code to sign up.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Linked parents */}
        {parentsQ.isLoading ? (
          <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
            <Loader2 className="h-4 w-4 animate-spin" /> Loading…
          </div>
        ) : parents.length === 0 ? (
          <div className="text-sm text-(--color-muted-foreground)">
            No parent linked yet. Generate an invite code and share it with
            them — they'll use it during signup.
          </div>
        ) : (
          <ul className="space-y-2">
            {parents.map((p) => (
              <li
                key={p.user_id}
                className="flex items-center justify-between gap-2 rounded-md border border-(--color-border) px-3 py-2 text-sm"
              >
                <div className="min-w-0">
                  <div className="truncate font-medium">{p.full_name}</div>
                  <div className="truncate text-[11px] text-(--color-muted-foreground)">
                    {p.email}
                  </div>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleRevoke(p.user_id, p.full_name)}
                  disabled={revoke.isPending}
                  title="Stop sharing with this parent"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                  Unlink
                </Button>
              </li>
            ))}
          </ul>
        )}

        {/* Active invite codes */}
        <div className="rounded-md border border-dashed border-(--color-border) p-3">
          <div className="mb-2 flex items-center justify-between">
            <div className="text-xs font-medium text-(--color-muted-foreground)">
              Active invite codes
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={handleGenerate}
              disabled={createCode.isPending}
            >
              {createCode.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Plus className="h-3.5 w-3.5" />
              )}
              New code
            </Button>
          </div>
          {codes.length === 0 ? (
            <div className="text-xs text-(--color-muted-foreground)">
              No active codes. Tap "New code" to make one — it lasts 7 days
              and can be used by one parent.
            </div>
          ) : (
            <ul className="space-y-1.5">
              {codes.map((c) => {
                const isCopied = copiedCode === c.code;
                return (
                  <li
                    key={c.code}
                    className="flex items-center justify-between gap-2 text-xs"
                  >
                    <code className="rounded-md bg-(--color-muted) px-2 py-1 font-mono text-sm tracking-widest">
                      {c.code}
                    </code>
                    <div className="flex items-center gap-2 text-[11px] text-(--color-muted-foreground)">
                      <Badge variant="outline" className="text-[10px]">
                        expires {new Date(c.expires_at).toLocaleDateString()}
                      </Badge>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleCopy(c.code)}
                      >
                        {isCopied ? (
                          <>
                            <Check className="h-3.5 w-3.5" />
                            Copied
                          </>
                        ) : (
                          <>
                            <Copy className="h-3.5 w-3.5" />
                            Copy
                          </>
                        )}
                      </Button>
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
