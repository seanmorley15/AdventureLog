ALTER TABLE "adventures" ALTER COLUMN "userId" DROP NOT NULL;--> statement-breakpoint
ALTER TABLE "adventures" ADD COLUMN "type" text NOT NULL;