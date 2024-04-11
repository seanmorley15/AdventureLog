CREATE TABLE IF NOT EXISTS "featuredAdventures" (
	"id" serial PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"location" text
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "session" (
	"id" text PRIMARY KEY NOT NULL,
	"user_id" text NOT NULL,
	"expires_at" timestamp with time zone NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "sharedAdventures" (
	"id" text PRIMARY KEY NOT NULL,
	"data" json NOT NULL,
	"name" text NOT NULL,
	"date" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "user" (
	"id" text PRIMARY KEY NOT NULL,
	"username" text NOT NULL,
	"first_name" text NOT NULL,
	"last_name" text NOT NULL,
	"icon" text,
	"hashed_password" varchar NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "userVisitedAdventures" (
	"adventure_id" serial PRIMARY KEY NOT NULL,
	"user_id" text NOT NULL,
	"adventure_name" text NOT NULL,
	"location" text,
	"visited_date" text
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "worldTravelCountries" (
	"id" serial PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"country_code" text NOT NULL,
	"continent" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "worldTravelRegions" (
	"id" serial PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"country_id" text NOT NULL
);
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "session" ADD CONSTRAINT "session_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "user"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "userVisitedAdventures" ADD CONSTRAINT "userVisitedAdventures_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "user"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "worldTravelRegions" ADD CONSTRAINT "worldTravelRegions_country_id_worldTravelCountries_id_fk" FOREIGN KEY ("country_id") REFERENCES "worldTravelCountries"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
