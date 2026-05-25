import { Accessibility, Coffee, Eye, Hand, Type } from "lucide-react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  useBreakNudgeEnabled,
  useContrastPreference,
  useFontPreference,
  useTouchPreference,
} from "@/lib/accessibility";

/**
 * Accessibility card — Stage 10 of the child-centric roadmap.
 *
 * Lives on the learner dashboard alongside Audio settings. Four
 * independent toggles, all per-device (localStorage):
 *   - Dyslexia-friendly font (OpenDyslexic via CDN, MIT-licensed)
 *   - High-contrast mode (bumps borders + text-on-bg)
 *   - Larger touch targets (~44px minimum, WCAG AAA)
 *   - Take-a-break gentle nudge after 20 min continuous use
 *
 * Each toggle is a labelled checkbox row — no fancy controls, no
 * radio groups. Kids find checkbox + label easier to scan than a
 * tabbed segmented control, and screen readers prefer them too.
 */
export function AccessibilityCard() {
  const [font, setFont] = useFontPreference();
  const [contrast, setContrast] = useContrastPreference();
  const [touch, setTouch] = useTouchPreference();
  const [breakNudge, setBreakNudge] = useBreakNudgeEnabled();

  return (
    <Card className="mb-6">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <Accessibility className="h-4 w-4 text-(--color-primary)" />
          Make it easier to use
        </CardTitle>
        <CardDescription>
          Four small switches. Turn on whatever helps you focus.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-3 sm:grid-cols-2">
        <ToggleRow
          icon={<Type className="h-4 w-4" />}
          title="Dyslexia-friendly font"
          description="Switch to OpenDyslexic — characters are weighted at the bottom so they don't flip in your eye."
          checked={font === "dyslexia-friendly"}
          onChange={(c) => setFont(c ? "dyslexia-friendly" : "default")}
        />
        <ToggleRow
          icon={<Eye className="h-4 w-4" />}
          title="High contrast"
          description="Stronger borders + darker text. Helpful in bright sunlight or on small screens."
          checked={contrast === "high"}
          onChange={(c) => setContrast(c ? "high" : "default")}
        />
        <ToggleRow
          icon={<Hand className="h-4 w-4" />}
          title="Larger tap targets"
          description="Bigger buttons + slightly larger fine print. Useful on a small phone."
          checked={touch === "large"}
          onChange={(c) => setTouch(c ? "large" : "default")}
        />
        <ToggleRow
          icon={<Coffee className="h-4 w-4" />}
          title="Take-a-break nudge"
          description={
            "After 20 minutes of continuous practice, we'll gently suggest a break. " +
            "Nothing gets paused — just a friendly check-in."
          }
          checked={breakNudge}
          onChange={setBreakNudge}
        />
      </CardContent>
    </Card>
  );
}

function ToggleRow({
  icon,
  title,
  description,
  checked,
  onChange,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
  checked: boolean;
  onChange: (next: boolean) => void;
}) {
  return (
    <label className="flex items-start gap-3 rounded-md border border-(--color-border) p-3 text-sm">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 h-4 w-4 accent-(--color-primary)"
      />
      <div>
        <div className="flex items-center gap-2 font-medium">
          {icon}
          {title}
        </div>
        <div className="mt-0.5 text-xs text-(--color-muted-foreground)">
          {description}
        </div>
      </div>
    </label>
  );
}
