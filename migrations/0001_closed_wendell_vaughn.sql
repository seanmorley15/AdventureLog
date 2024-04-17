ALTER TABLE "userVisitedWorldTravel" ADD COLUMN "country_code" text NOT NULL;--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "userVisitedWorldTravel" ADD CONSTRAINT "userVisitedWorldTravel_country_code_worldTravelCountries_country_code_fk" FOREIGN KEY ("country_code") REFERENCES "worldTravelCountries"("country_code") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
