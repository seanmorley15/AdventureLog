import { pgTable, json, text, serial } from "drizzle-orm/pg-core";

export const featuredAdventures = pgTable("featuredAdventures", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  location: text("location"),
});

export const sharedAdventures = pgTable("sharedAdventures", {
  id: text("id").primaryKey(),
  data: json("data").notNull(),
});
