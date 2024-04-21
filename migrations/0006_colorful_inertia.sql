ALTER TABLE "userPlannedAdventures" RENAME COLUMN "user_id" TO "userId";--> statement-breakpoint
ALTER TABLE "userPlannedAdventures" RENAME COLUMN "adventure_name" TO "adventureName";--> statement-breakpoint
ALTER TABLE "userPlannedAdventures" RENAME COLUMN "activity_types" TO "activityTypes";--> statement-breakpoint
ALTER TABLE "userPlannedAdventures" DROP CONSTRAINT "userPlannedAdventures_user_id_user_id_fk";
--> statement-breakpoint
DO $$ BEGIN
 ALTER TABLE "userPlannedAdventures" ADD CONSTRAINT "userPlannedAdventures_userId_user_id_fk" FOREIGN KEY ("userId") REFERENCES "user"("id") ON DELETE no action ON UPDATE no action;
EXCEPTION
 WHEN duplicate_object THEN null;
END $$;
