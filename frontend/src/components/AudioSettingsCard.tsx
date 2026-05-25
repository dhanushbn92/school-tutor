import { useMemo, useState } from "react";
import { Loader2, Volume2 } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useAudioPreferences,
  useUpdateAudioPreferences,
} from "@/lib/queries";
import { isSpeechAvailable, useSpeech, useVoices } from "@/lib/speech";

/**
 * Audio preferences card — Stage 8 of the child-centric roadmap.
 *
 * Lives on the learner dashboard. Two controls:
 *   1. Voice picker — the browser-installed voices, grouped by
 *      language. Saving updates `preferred_voice_uri` server-side
 *      so the same voice follows the learner across surfaces.
 *   2. Autoplay toggle — whether ReadAloudButton starts speaking
 *      on mount for the few surfaces that opt into it (Surprise me
 *      reveal, each Flashcard front). Off by default.
 *
 * A "Test voice" button reads a short sentence aloud so the learner
 * can sanity-check the pick before committing.
 *
 * Renders an explanatory empty-state if the browser doesn't expose
 * SpeechSynthesis (some older Android browsers) — the rest of the
 * dashboard is unaffected.
 */
export function AudioSettingsCard() {
  const prefsQ = useAudioPreferences();
  const updatePrefs = useUpdateAudioPreferences();
  const voices = useVoices();
  const [previewVoice, setPreviewVoice] = useState<string | null>(null);
  const { speak } = useSpeech({ voiceUri: previewVoice });

  // Group voices by language family so the dropdown stays scannable
  // on systems with 30+ installed voices.
  const grouped = useMemo(() => {
    const map = new Map<string, SpeechSynthesisVoice[]>();
    for (const v of voices) {
      const key = v.lang || "other";
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(v);
    }
    // Sort: languages alphabetically, voices within each lang
    // alphabetically by name.
    return [...map.entries()]
      .sort((a, b) => a[0].localeCompare(b[0]))
      .map(
        ([lang, vs]) =>
          [lang, vs.sort((a, b) => a.name.localeCompare(b.name))] as const,
      );
  }, [voices]);

  if (!isSpeechAvailable()) {
    return (
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Volume2 className="h-4 w-4" /> Read-aloud
          </CardTitle>
          <CardDescription>
            Your browser doesn't support read-aloud. Try Chrome, Edge, or
            Safari on a recent device.
          </CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (prefsQ.isLoading || !prefsQ.data) {
    return null; // No layout jump — dashboard loads its other widgets first.
  }
  const prefs = prefsQ.data;
  const selectedVoiceUri = previewVoice ?? prefs.preferred_voice_uri ?? "__default__";

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Volume2 className="h-4 w-4 text-(--color-primary)" /> Read-aloud
        </CardTitle>
        <CardDescription>
          Have any question, answer, or explanation read out loud. Pick a
          voice and we'll use it everywhere.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-3 sm:grid-cols-[1fr,auto]">
          <Select
            value={selectedVoiceUri}
            onValueChange={(v) => {
              const next = v === "__default__" ? null : v;
              setPreviewVoice(next);
              updatePrefs.mutate({ preferred_voice_uri: next ?? "" });
            }}
          >
            <SelectTrigger>
              <SelectValue placeholder="Pick a voice" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__default__">Browser default</SelectItem>
              {grouped.map(([lang, vs]) => (
                <div key={lang}>
                  <div className="px-2 py-1 text-[10px] uppercase tracking-wider text-(--color-muted-foreground)">
                    {lang}
                  </div>
                  {vs.map((v) => (
                    <SelectItem key={v.voiceURI} value={v.voiceURI}>
                      {v.name}
                      {v.default ? " · default" : ""}
                    </SelectItem>
                  ))}
                </div>
              ))}
            </SelectContent>
          </Select>
          <Button
            variant="outline"
            onClick={() =>
              speak(
                "Hello! I'm ready to read questions and answers out loud for you.",
              )
            }
          >
            <Volume2 className="h-4 w-4" /> Test voice
          </Button>
        </div>

        <label className="flex items-start gap-3 rounded-md border border-(--color-border) p-3 text-sm">
          <input
            type="checkbox"
            checked={prefs.autoplay_questions}
            onChange={(e) =>
              updatePrefs.mutate({ autoplay_questions: e.target.checked })
            }
            disabled={updatePrefs.isPending}
            className="mt-1 h-4 w-4 accent-(--color-primary)"
          />
          <div>
            <div className="font-medium">Autoplay when a new question appears</div>
            <div className="mt-0.5 text-xs text-(--color-muted-foreground)">
              Each flashcard or "Surprise me" question starts reading
              automatically. Tap the 🔊 button anywhere to stop or restart.
            </div>
          </div>
        </label>

        {updatePrefs.isPending && (
          <div className="flex items-center gap-2 text-xs text-(--color-muted-foreground)">
            <Loader2 className="h-3 w-3 animate-spin" /> Saving…
          </div>
        )}
      </CardContent>
    </Card>
  );
}
