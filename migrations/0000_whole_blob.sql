CREATE TABLE IF NOT EXISTS "adventures" (
	"id" serial PRIMARY KEY NOT NULL,
	"type" text NOT NULL,
	"userId" text,
	"name" text NOT NULL,
	"location" text,
	"activityTypes" text[] DEFAULT ARRAY[]::text[],
	"description" text,
	"rating" integer,
	"link" text,
	"imageUrl" text,
	"date" text,
	"tripId" integer
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
CREATE TABLE IF NOT EXISTS "userPlannedTrips" (
	"id" serial PRIMARY KEY NOT NULL,
	"userId" text NOT NULL,
	"adventureName" text NOT NULL,
	"description" text,
	"startDate" text,
	"endDate" text
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "user" (
	"id" text PRIMARY KEY NOT NULL,
	"username" text NOT NULL,
	"first_name" text NOT NULL,
	"last_name" text NOT NULL,
	"icon" text,
	"hashed_password" varchar NOT NULL,
	"signup_date" timestamp with time zone NOT NULL,
	"last_login" timestamp with time zone,
	"role" text NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "userVisitedWorldTravel" (
	"id" serial PRIMARY KEY NOT NULL,
	"country_code" text NOT NULL,
	"user_id" text NOT NULL,
	"region_id" varchar NOT NULL
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "worldTravelCountries" (
	"id" serial PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"country_code" text NOT NULL,
	"continent" text NOT NULL,
	CONSTRAINT "worldTravelCountries_country_code_unique" UNIQUE("country_code")
);
--> statement-breakpoint
CREATE TABLE IF NOT EXISTS "worldTravelCountryRegions" (
	"id" varchar PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"country_code" text NOT NULL,
	"info" json
);
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "adventures" ADD CONSTRAINT "adventures_userId_user_id_fk" FOREIGN KEY ("userId") REFERENCES "user"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "adventures" ADD CONSTRAINT "adventures_tripId_userPlannedTrips_id_fk" FOREIGN KEY ("tripId") REFERENCES "userPlannedTrips"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "session" ADD CONSTRAINT "session_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "user"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "userPlannedTrips" ADD CONSTRAINT "userPlannedTrips_userId_user_id_fk" FOREIGN KEY ("userId") REFERENCES "user"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "userVisitedWorldTravel" ADD CONSTRAINT "userVisitedWorldTravel_country_code_worldTravelCountries_country_code_fk" FOREIGN KEY ("country_code") REFERENCES "worldTravelCountries"("country_code") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "userVisitedWorldTravel" ADD CONSTRAINT "userVisitedWorldTravel_user_id_user_id_fk" FOREIGN KEY ("user_id") REFERENCES "user"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "userVisitedWorldTravel" ADD CONSTRAINT "userVisitedWorldTravel_region_id_worldTravelCountryRegions_id_fk" FOREIGN KEY ("region_id") REFERENCES "worldTravelCountryRegions"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "worldTravelCountryRegions" ADD CONSTRAINT "worldTravelCountryRegions_country_code_worldTravelCountries_country_code_fk" FOREIGN KEY ("country_code") REFERENCES "worldTravelCountries"("country_code") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
