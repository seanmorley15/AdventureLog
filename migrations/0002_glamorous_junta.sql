CREATE TABLE IF NOT EXISTS "worldTravelRegions" (
	"id" serial PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"country_id" text NOT NULL
);
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "worldTravelRegions" ADD CONSTRAINT "worldTravelRegions_country_id_worldTravelCountries_id_fk" FOREIGN KEY ("country_id") REFERENCES "worldTravelCountries"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
