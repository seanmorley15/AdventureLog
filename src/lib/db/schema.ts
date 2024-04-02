import { pgTable,serial,text } from "drizzle-orm/pg-core";

export const featuredAdventures = pgTable("featuredAdventures",{
    id:serial("id").primaryKey(),
    name:text("name").notNull(),
    location:text("location"),
})


