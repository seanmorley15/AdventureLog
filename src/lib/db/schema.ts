import {
  pgTable,
  text,
  timestamp,
  json,
  serial,
  varchar,
} from "drizzle-orm/pg-core";

export const featuredAdventures = pgTable("featuredAdventures", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  location: text("location"),
});

export const sharedAdventures = pgTable("sharedAdventures", {
  id: text("id").primaryKey(),
  data: json("data").notNull(),
});

export const userTable = pgTable("user", {
  id: text("id").primaryKey(),
  username: text("username").notNull(),
  first_name: text("first_name").notNull(),
  last_name: text("last_name").notNull(),
  hashed_password: varchar("hashed_password").notNull(),
});

// export type SelectUser = typeof userTable.$inferSelect;

export const sessionTable = pgTable("session", {
  id: text("id").primaryKey(),
  userId: text("user_id")
    .notNull()
    .references(() => userTable.id),
  expiresAt: timestamp("expires_at", {
    withTimezone: true,
    mode: "date",
  }).notNull(),
});

export const userVisitedAdventures = pgTable("userVisitedAdventures", {
  userId: text("user_id")
    .notNull()
    .references(() => userTable.id),
  adventureName: text("adventure_name").notNull(),
  location: text("location"),
  adventureVistied: text("adventure_visited"),
});
