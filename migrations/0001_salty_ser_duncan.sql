ALTER TABLE "adventures" ADD COLUMN "tripId" integer;--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "adventures" ADD CONSTRAINT "adventures_tripId_userPlannedTrips_id_fk" FOREIGN KEY ("tripId") REFERENCES "userPlannedTrips"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
--> statement-breakpoint
ALTER TABLE "userPlannedTrips" DROP COLUMN IF EXISTS "adventures";