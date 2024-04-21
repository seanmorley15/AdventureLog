CREATE TABLE IF NOT EXISTS "userPlannedAdventures" (
	"id" serial PRIMARY KEY NOT NULL,
	"user_id" text NOT NULL,
	"adventure_name" text NOT NULL,
	"location" text,
	"activity_types" text
);
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "userPlannedAdventures" ADD CONSTRAINT "userPlannedAdventures_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "user"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
