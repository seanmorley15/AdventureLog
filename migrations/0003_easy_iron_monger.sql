ALTER TABLE "user" ADD COLUMN "signup_date" timestamp with time zone NOT NULL;--> statement-breakpoint
ALTER TABLE "user" ADD COLUMN "last_login" timestamp with time zone;--> statement-breakpoint
ALTER TABLE "user" ADD COLUMN "role" text NOT NULL;