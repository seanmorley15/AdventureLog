CREATE TABLE IF NOT EXISTS "userVisitedAdventures" (
	"user_id" text NOT NULL,
	"adventure_name" text NOT NULL,
	"location" text,
	"adventure_visited" text
);
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "userVisitedAdventures" ADD CONSTRAINT "userVisitedAdventures_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "user"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
