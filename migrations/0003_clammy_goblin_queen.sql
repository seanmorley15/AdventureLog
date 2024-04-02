ALTER TABLE "sharedAdventures" ADD COLUMN "data" json NOT NULL;--> statement-breakpoint
ALTER TABLE "sharedAdventures" DROP COLUMN IF EXISTS "name";--> statement-breakpoint
ALTER TABLE "sharedAdventures" DROP COLUMN IF EXISTS "location";--> statement-breakpoint
ALTER TABLE "sharedAdventures" DROP COLUMN IF EXISTS "date";