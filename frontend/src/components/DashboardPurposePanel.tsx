import { Link } from "react-router-dom";
import { ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { BRAND_NAME } from "@/lib/brand";

/**
 * The "why this platform exists" panel for the dashboard.
 *
 * Every role sees a version of the same idea — practice, again and
 * again, is the engine — phrased in the language that matters to
 * them. The headline is bold, the philosophy line is quiet under
 * it, and a single primary CTA points each role at the action that
 * keeps their practice loop running:
 *
 *   learner / individual_learner   → Start a quiz
 *   teacher                         → New quiz from bank
 *   school_admin                    → School report
 *   platform_admin                  → Generate content
 *
 * Visually distinct from the operational widgets below (gradient
 * accent strip down the left, display font, larger type) so it
 * reads as a permanent reminder of why the dashboard exists, not
 * just another stat card.
 *
 * Sits ABOVE the existing stat cards on the dashboard. The
 * splash-screen welcome animation is a one-moment ritual; this
 * panel is the durable place where the platform's purpose lives.
 */
export type RoleKey =
  | "learner"
  | "teacher"
  | "school_admin"
  | "platform_admin";

interface RoleContent {
  /** Bold one-line claim that captures the practice ethos for this role. */
  headline: string;
  /** Single sentence explaining what the role does on the platform. */
  lead: string;
  /** Primary CTA label. */
  ctaLabel: string;
  /** Primary CTA target route. */
  ctaHref: string;
}

const ROLE_CONTENT: Record<RoleKey, RoleContent> = {
  learner: {
    headline: "Practice. Again. And again.",
    lead:
      "Each quiz is another arrow drawn toward mastery. Take one, see where you slipped, take another — your mastery map updates with every attempt.",
    ctaLabel: "Start a quiz",
    ctaHref: "/quick-quiz",
  },
  teacher: {
    headline: "Guide every shot.",
    lead:
      "Build quizzes from the approved bank, watch mastery climb in your gradebook, and step in exactly where your students are still getting it wrong.",
    ctaLabel: "New quiz from bank",
    ctaHref: "/assessments/new",
  },
  school_admin: {
    headline: "Build a culture of practice.",
    lead:
      "See weak topics across every class, every teacher, every section. Spot drift early and intervene before the term-end exam makes it expensive.",
    ctaLabel: "School report",
    ctaHref: "/school-report",
  },
  platform_admin: {
    headline: "Curate the practice ground.",
    lead:
      "Every approved question and every published worksheet becomes another arrow in every learner's quiver. Keep the catalog strong; keep the practice flowing.",
    ctaLabel: "Generate content",
    ctaHref: "/generate",
  },
};

export function DashboardPurposePanel({ role }: { role: RoleKey }) {
  const content = ROLE_CONTENT[role];
  return (
    <Card
      // Brand-accented panel: a four-colour stripe down the left
      // edge picks up the logo palette and signals "this is the
      // brand voice, not an operational widget". The stripe is
      // built from a stack of inset shadows so it scales with the
      // card and never needs absolute positioning.
      className="relative mb-6 overflow-hidden"
      style={{
        boxShadow: `inset 6px 0 0 0 #0E2A4D, inset 12px 0 0 0 #3AB54A, inset 18px 0 0 0 #F36C21, inset 24px 0 0 0 #A04CC9`,
      }}
    >
      <CardContent className="pl-10 pr-6 py-6 md:pl-12 md:py-7">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between md:gap-8">
          <div className="space-y-2">
            {/* Tiny eyebrow keeps the brand visible without
                shouting. */}
            <p className="font-display text-[10px] uppercase tracking-[0.22em] text-(--color-primary)">
              {BRAND_NAME} &middot; Practice. Master. Conquer.
            </p>
            <h2 className="font-display text-xl font-semibold tracking-tight text-(--color-foreground) md:text-2xl">
              {content.headline}
            </h2>
            <p className="max-w-2xl text-sm leading-relaxed text-(--color-muted-foreground)">
              {content.lead}
            </p>
          </div>
          <Button asChild size="lg" className="self-start md:self-center">
            <Link to={content.ctaHref}>
              {role === "learner" ? (
                <Sparkles className="h-4 w-4" />
              ) : (
                <ArrowRight className="h-4 w-4" />
              )}
              {content.ctaLabel}
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
