CREATE TABLE IF NOT EXISTS "adventures" (
	"id" serial PRIMARY KEY NOT NULL,
	"userId" text NOT NULL,
	"adventureName" text NOT NULL,
	"location" text,
	"activityTypes" json,
	"description" text,
	"rating" integer,
	"link" text,
	"imageUrl" text,
	"date" text
);
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "adventures" ADD CONSTRAINT "adventures_userId_user_id_fk" FOREIGN KEY ("userId") REFERENCES "user"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
