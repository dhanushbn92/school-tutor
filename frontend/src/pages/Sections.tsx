import { Link } from "react-router-dom";
import { ArrowRight, Users } from "lucide-react";
import { PageHeader } from "@/components/layout/PageHeader";
import { ThemedPage } from "@/components/themed";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Empty } from "@/components/ui/empty";
import { Skeleton } from "@/components/ui/skeleton";
import { useMySections } from "@/lib/queries";

export function SectionsPage() {
  const { data, isLoading } = useMySections();

  return (
    <ThemedPage>
      <PageHeader
        title="Classes"
        description="Sections you teach or administer. Click into one to see the roster, gradebook, and class-wide mastery."
      />
      {isLoading ? (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : !data || data.length === 0 ? (
        <Empty
          icon={<Users className="h-6 w-6" />}
          title="No classes assigned"
          description="Ask your administrator to assign you as class teacher for a section."
        />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {data.map((s) => (
            <Link key={s.id} to={`/sections/${s.id}`} className="group">
              <Card className="h-full transition-shadow group-hover:shadow-md">
                <CardHeader className="flex-row items-start justify-between space-y-0">
                  <div>
                    <CardTitle>
                      {s.class_display_name} &middot; {s.name}
                    </CardTitle>
                    <CardDescription>
                      Academic year {s.academic_year ?? "—"}
                    </CardDescription>
                  </div>
                  <Badge variant="outline">
                    <Users className="mr-1 h-3 w-3" /> Section
                  </Badge>
                </CardHeader>
                <CardContent className="flex items-center justify-between">
                  <span className="text-sm text-(--color-muted-foreground)">
                    {s.class_teacher_id ? "Class teacher: you" : "No class teacher"}
                  </span>
                  <ArrowRight className="h-4 w-4 text-(--color-muted-foreground) transition-transform group-hover:translate-x-0.5" />
                </CardContent>
              </Card>
            </Link>
          ))}
        </div>
      )}
    </ThemedPage>
  );
}
