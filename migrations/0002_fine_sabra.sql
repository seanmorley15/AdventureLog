DROP TABLE "featuredAdventures";--> statement-breakpoint
ALTER TABLE "adventures" ALTER COLUMN "activityTypes" SET DATA TYPE text[];--> statement-breakpoint
ALTER TABLE "adventures" ALTER COLUMN "activityTypes" SET DEFAULT '{}'::text[];