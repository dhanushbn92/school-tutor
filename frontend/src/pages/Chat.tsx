import { useEffect, useRef, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowUp,
  Bot,
  Loader2,
  Sparkles,
  User as UserIcon,
} from "lucide-react";
import { toast } from "sonner";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { humanError } from "@/lib/api";
import {
  useChatSession,
  useSendChatMessage,
} from "@/lib/queries";
import type { ChatMessageRead } from "@/lib/types";

const DIFFICULTY_HINTS: Record<"easier" | "harder", string> = {
  easier:
    "Please explain this in simpler words, with a short everyday example I can picture.",
  harder:
    "Please go a level deeper — add the precise term and one extra detail or example from the chapter.",
};

export function ChatPage() {
  const { sessionId: idParam } = useParams();
  const sessionId = idParam ? Number(idParam) : undefined;
  const sessionQ = useChatSession(sessionId);
  const sendMut = useSendChatMessage(sessionId);
  const [draft, setDraft] = useState("");
  const [hint, setHint] = useState<"easier" | "harder" | null>(null);
  const scrollRef = useRef<HTMLDivElement | null>(null);

  // Scroll to bottom on new messages.
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [sessionQ.data?.messages.length, sendMut.isPending]);

  if (sessionQ.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-(--color-muted-foreground)">
        <Loader2 className="h-4 w-4 animate-spin" /> Loading chat…
      </div>
    );
  }
  if (!sessionQ.data) {
    return (
      <Empty
        icon={<Bot className="h-6 w-6" />}
        title="Chat not found"
        description="The session you tried to open doesn't exist or isn't yours."
        action={
          <Button asChild variant="outline">
            <Link to="/learn">
              <ArrowLeft className="h-4 w-4" /> Back to Learn
            </Link>
          </Button>
        }
      />
    );
  }

  const session = sessionQ.data;
  const messages = session.messages;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const content = draft.trim();
    if (!content) return;
    const finalContent = hint ? `${DIFFICULTY_HINTS[hint]}\n\n${content}` : content;
    setDraft("");
    setHint(null);
    try {
      await sendMut.mutateAsync({ content: finalContent });
    } catch (err) {
      toast.error(humanError(err));
    }
  }

  return (
    <ThemedPage>
      <PageHeader
        title={session.title}
        description={
          <>
            <Badge variant="secondary" className="mr-2">
              {session.scope === "TOPIC" ? "Topic-scoped" : "Whole-chapter"}
            </Badge>
            <span className="text-xs text-(--color-muted-foreground)">
              The AI tutor only answers from this chapter / topic. Off-topic
              questions get a polite redirect.
            </span>
          </>
        }
        actions={
          <Button asChild variant="outline">
            <Link to="/learn">
              <ArrowLeft className="h-4 w-4" /> Back to Learn
            </Link>
          </Button>
        }
      />

      <Card>
        <CardContent className="pt-4">
          <div
            ref={scrollRef}
            className="h-[55vh] overflow-y-auto rounded-md border border-(--color-border) bg-(--color-muted)/30 p-4 space-y-3"
          >
            {messages.length === 0 ? (
              <Empty
                icon={<Sparkles className="h-6 w-6" />}
                title="Ask me anything from this chapter"
                description="Try: 'Can you explain in simpler words?', 'What is the main idea here?', or 'Give me a real-life example.'"
                className="border-0"
              />
            ) : (
              messages.map((m) => <Bubble key={m.id} message={m} />)
            )}
            {sendMut.isPending && (
              <div className="flex items-center gap-2 text-xs text-(--color-muted-foreground)">
                <Loader2 className="h-3 w-3 animate-spin" /> Tutor is typing…
              </div>
            )}
          </div>

          <form onSubmit={handleSubmit} className="mt-3 space-y-2">
            <div className="flex gap-2">
              <textarea
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    handleSubmit(e as unknown as FormEvent);
                  }
                }}
                rows={2}
                placeholder="Type a question about this chapter…  (Enter to send · Shift+Enter for newline)"
                className="flex-1 rounded-md border border-(--color-input) bg-transparent px-3 py-2 text-sm shadow-sm placeholder:text-(--color-muted-foreground) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-(--color-ring)"
                disabled={sendMut.isPending}
              />
              <Button type="submit" size="icon" disabled={sendMut.isPending || !draft.trim()}>
                {sendMut.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <ArrowUp className="h-4 w-4" />
                )}
              </Button>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="text-(--color-muted-foreground)">Optional nudge:</span>
              <button
                type="button"
                onClick={() => setHint(hint === "easier" ? null : "easier")}
                className={`rounded-full border px-3 py-1 transition-colors ${
                  hint === "easier"
                    ? "border-(--color-primary) bg-(--color-primary) text-(--color-primary-foreground)"
                    : "border-(--color-border) hover:bg-(--color-muted)"
                }`}
              >
                Easier please
              </button>
              <button
                type="button"
                onClick={() => setHint(hint === "harder" ? null : "harder")}
                className={`rounded-full border px-3 py-1 transition-colors ${
                  hint === "harder"
                    ? "border-(--color-primary) bg-(--color-primary) text-(--color-primary-foreground)"
                    : "border-(--color-border) hover:bg-(--color-muted)"
                }`}
              >
                Go deeper
              </button>
            </div>
          </form>
        </CardContent>
      </Card>

      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">How the AI tutor works</CardTitle>
          <CardDescription>
            Quick reminders so you get the most out of each chat.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-(--color-muted-foreground)">
          <p>
            Each chat is scoped to a single chapter or topic — the tutor is
            given just that text and is told to refuse off-topic questions.
          </p>
          <p>
            Tap <strong>Easier please</strong> for a simpler explanation, or{" "}
            <strong>Go deeper</strong> for the full term and an extra detail.
          </p>
          <p>
            The tutor can answer in English or Hinglish — write in whichever
            feels natural for you.
          </p>
        </CardContent>
      </Card>
    </ThemedPage>
  );
}

function Bubble({ message }: { message: ChatMessageRead }) {
  const isUser = message.role === "USER";
  return (
    <div className={`flex gap-2 ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-(--color-primary) text-(--color-primary-foreground)">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div
        className={`max-w-[75%] rounded-lg px-3 py-2 text-sm leading-relaxed whitespace-pre-wrap ${
          isUser
            ? "bg-(--color-primary) text-(--color-primary-foreground)"
            : "bg-(--color-card) border border-(--color-border) text-(--color-foreground)"
        }`}
      >
        {message.content}
      </div>
      {isUser && (
        <div className="mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-(--color-secondary) text-(--color-secondary-foreground)">
          <UserIcon className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}
