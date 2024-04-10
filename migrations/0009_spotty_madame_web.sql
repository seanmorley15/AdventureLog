ALTER TABLE "userVisitedAdventures" RENAME COLUMN "adventure_visited" TO "adventure_id";--> statement-breakpoint
ALTER TABLE "userVisitedAdventures" ADD PRIMARY KEY ("adventure_id");--> statement-breakpoint
ALTER TABLE "userVisitedAdventures" ALTER COLUMN "adventure_id" SET DATA TYPE serial;--> statement-breakpoint
ALTER TABLE "userVisitedAdventures" ALTER COLUMN "adventure_id" SET NOT NULL;--> statement-breakpoint
ALTER TABLE "userVisitedAdventures" ADD COLUMN "visited_date" text;