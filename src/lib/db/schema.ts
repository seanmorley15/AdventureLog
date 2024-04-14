import {
  pgTable,
  text,
  timestamp,
  json,
  serial,
  varchar,
  integer,
} from "drizzle-orm/pg-core";

export const featuredAdventures = pgTable("featuredAdventures", {
  id: serial("id").primaryKey(),
  name: text("name").notNull().unique(),
  location: text("location"),
});

export const sharedAdventures = pgTable("sharedAdventures", {
  id: text("id").primaryKey(),
  data: json("data").notNull(),
  name: text("name").notNull(),
  date: text("date").notNull(),
});

export const userTable = pgTable("user", {
  id: text("id").primaryKey(),
  username: text("username").notNull(),
  first_name: text("first_name").notNull(),
  last_name: text("last_name").notNull(),
  icon: text("icon"),
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
  adventureID: serial("adventure_id").primaryKey(),
  userId: text("user_id")
    .notNull()
    .references(() => userTable.id),
  adventureName: text("adventure_name").notNull(),
  location: text("location"),
  visitedDate: text("visited_date"),
});

export const worldTravelCountries = pgTable("worldTravelCountries", {
  id: serial("id").primaryKey(),
  name: text("name").notNull(),
  country_code: text("country_code").notNull().unique(),
  continent: text("continent").notNull(),
});

export const worldTravelCountryRegions = pgTable("worldTravelCountryRegions", {
  id: varchar("id").primaryKey(),
  name: text("name").notNull(),
  country_code: text("country_code")
    .notNull()
    .references(() => worldTravelCountries.country_code),
  info: json("info"),
});

export const userVisitedWorldTravel = pgTable("userVisitedWorldTravel", {
  id: serial("id").primaryKey(),
  country_code: text("country_code")
    .notNull()
    .references(() => worldTravelCountries.country_code),
  userId: text("user_id")
    .notNull()
    .references(() => userTable.id),
  region_id: varchar("region_id")
    .notNull()
    .references(() => worldTravelCountryRegions.id),
});