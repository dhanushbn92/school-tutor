import { useMemo, useState } from "react";
import * as Dialog from "@radix-ui/react-dialog";
import { Keyboard, X } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * "How to type in Devanagari" helper. A one-time setup guide that walks a
 * student through enabling a device keyboard on their OS, with the current OS
 * auto-selected. Complements the in-app transliteration toggle (see
 * DevanagariInput) — that needs no setup; this makes real, exact typing faster.
 *
 * Menu paths drift slightly between OS versions, so copy stays intentionally
 * high-level and says so.
 */

type OsKey = "win" | "mac" | "android" | "ios";

const OS_LABEL: Record<OsKey, string> = {
  win: "Windows",
  mac: "macOS",
  android: "Android",
  ios: "iPhone",
};

function detectOs(): OsKey {
  if (typeof navigator === "undefined") return "win";
  const ua = navigator.userAgent || "";
  if (/Android/i.test(ua)) return "android";
  if (/iPhone|iPad|iPod/i.test(ua)) return "ios";
  if (/Macintosh|Mac OS X/i.test(ua)) return "mac";
  return "win";
}

function Kbd({ children }: { children: React.ReactNode }) {
  return (
    <kbd className="rounded border border-b-2 border-(--color-border) bg-(--color-muted) px-1.5 py-0.5 font-mono text-[11px]">
      {children}
    </kbd>
  );
}

function Steps({ os }: { os: OsKey }) {
  if (os === "win") {
    return (
      <>
        <ol className="list-decimal space-y-1.5 pl-5 text-sm">
          <li>
            Open <b>Settings → Time &amp; language → Language &amp; region</b>.
          </li>
          <li>
            Under <b>Preferred languages</b>, click <b>Add a language</b> → choose{" "}
            <b lang="hi">हिन्दी (Hindi)</b> → Install.
          </li>
          <li>
            Switch keyboards anytime with <Kbd>Win</Kbd> + <Kbd>Space</Kbd>.
          </li>
        </ol>
        <p className="mt-3 rounded-md border border-(--color-border) bg-(--color-muted) px-3 py-2 text-[13px]">
          <b>No setup?</b> Use the <span lang="sa">अ</span>/A toggle on the answer
          box — type in English letters, get Devanagari instantly.
        </p>
      </>
    );
  }
  if (os === "mac") {
    return (
      <>
        <ol className="list-decimal space-y-1.5 pl-5 text-sm">
          <li>
            Open{" "}
            <b>System Settings → Keyboard → Text Input → Input Sources → Edit</b>.
          </li>
          <li>
            Click <b>+</b> → <b>Hindi</b> → pick <b>Devanagari</b> (or{" "}
            <b>Devanagari&nbsp;–&nbsp;QWERTY</b> for a phonetic layout) → Add.
          </li>
          <li>
            Switch with the <Kbd>🌐</Kbd> globe key or <Kbd>Ctrl</Kbd> +{" "}
            <Kbd>Space</Kbd>.
          </li>
        </ol>
        <p className="mt-3 rounded-md border border-(--color-border) bg-(--color-muted) px-3 py-2 text-[13px]">
          <b>Tip:</b> the <b>QWERTY</b> layout maps English-like keys to
          Devanagari — easier to learn.
        </p>
      </>
    );
  }
  if (os === "android") {
    return (
      <>
        <ol className="list-decimal space-y-1.5 pl-5 text-sm">
          <li>
            In <b>Gboard</b>: <b>Settings → Languages → Add keyboard</b>.
          </li>
          <li>
            Choose <b lang="hi">हिन्दी (Hindi)</b>. Pick{" "}
            <b>Hindi (Transliteration)</b> to type in English letters and get
            Devanagari.
          </li>
          <li>
            Switch with the <Kbd>🌐</Kbd> globe key on the keyboard.
          </li>
        </ol>
        <p className="mt-3 rounded-md border border-(--color-border) bg-(--color-muted) px-3 py-2 text-[13px]">
          <b>Built in!</b> Android’s <b>Hindi (Transliteration)</b> keyboard is
          the same idea as the in-app toggle, at the system level.
        </p>
      </>
    );
  }
  return (
    <>
      <ol className="list-decimal space-y-1.5 pl-5 text-sm">
        <li>
          Open{" "}
          <b>Settings → General → Keyboard → Keyboards → Add New Keyboard</b>.
        </li>
        <li>
          Choose <b>Hindi (Devanagari)</b> or <b>Hindi (Transliteration)</b>.
        </li>
        <li>
          Switch with the <Kbd>🌐</Kbd> globe key while typing.
        </li>
      </ol>
      <p className="mt-3 rounded-md border border-(--color-border) bg-(--color-muted) px-3 py-2 text-[13px]">
        <b>Built in!</b> iOS’s <b>Hindi (Transliteration)</b> keyboard types
        English letters → Devanagari.
      </p>
    </>
  );
}

export function DevanagariHelp({ className }: { className?: string }) {
  const [active, setActive] = useState<OsKey>(detectOs);
  const detected = useMemo(() => detectOs(), []);
  const tabs: OsKey[] = ["win", "mac", "android", "ios"];

  return (
    <Dialog.Root>
      <Dialog.Trigger asChild>
        <button
          type="button"
          className={cn(
            "inline-flex items-center gap-1 text-xs font-medium text-(--color-primary) underline-offset-2 hover:underline",
            className,
          )}
        >
          <Keyboard className="h-3.5 w-3.5" />
          How to type <span lang="sa">देवनागरी</span>?
        </button>
      </Dialog.Trigger>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-sm data-[state=open]:animate-in data-[state=open]:fade-in-0" />
        <Dialog.Content className="fixed left-1/2 top-1/2 z-50 w-[min(92vw,520px)] -translate-x-1/2 -translate-y-1/2 rounded-xl border border-(--color-border) bg-(--color-card) text-(--color-card-foreground) shadow-xl focus:outline-none">
          <div className="flex items-center gap-2 border-b border-(--color-border) px-5 py-3.5">
            <Keyboard className="h-4 w-4 text-(--color-primary)" />
            <Dialog.Title className="text-sm font-semibold">
              Type in <span lang="sa">देवनागरी</span> on your device
            </Dialog.Title>
            <Dialog.Close asChild>
              <button
                type="button"
                aria-label="Close"
                className="ml-auto rounded-md p-1 text-(--color-muted-foreground) hover:bg-(--color-muted)"
              >
                <X className="h-4 w-4" />
              </button>
            </Dialog.Close>
          </div>

          <Dialog.Description className="px-5 pt-3 text-xs text-(--color-muted-foreground)">
            One-time setup. Detected:{" "}
            <b className="text-(--color-foreground)">{OS_LABEL[detected]}</b> —
            showing your steps first. Menu names may vary slightly by version.
          </Dialog.Description>

          <div className="flex flex-wrap gap-1 px-5 pt-3">
            {tabs.map((t) => (
              <button
                key={t}
                type="button"
                onClick={() => setActive(t)}
                className={cn(
                  "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                  active === t
                    ? "bg-(--color-primary) text-(--color-primary-foreground)"
                    : "bg-(--color-muted) text-(--color-muted-foreground) hover:bg-(--color-accent)",
                )}
              >
                {OS_LABEL[t]}
              </button>
            ))}
          </div>

          <div className="px-5 pb-5 pt-4">
            <Steps os={active} />
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
