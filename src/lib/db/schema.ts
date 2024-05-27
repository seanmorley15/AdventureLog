import { desc } from "drizzle-orm";
import {
  pgTable,
  text,
  timestamp,
  json,
  serial,
  varchar,
  integer,
} from "drizzle-orm/pg-core";

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
  signup_date: timestamp("signup_date", {
    withTimezone: true,
    mode: "date",
  }).notNull(),
  last_login: timestamp("last_login", {
    withTimezone: true,
    mode: "date",
  }),
  role: text("role").notNull(),
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

export const userPlannedTrips = pgTable("userPlannedTrips", {
  id: serial("id").primaryKey(),
  userId: text("userId")
    .notNull()
    .references(() => userTable.id),
  name: text("adventureName").notNull(),
  description: text("description"),
  startDate: text("startDate"),
  endDate: text("endDate"),
});

export const adventureTable = pgTable("adventures", {
  id: serial("id").primaryKey(),
  type: text("type").notNull(),
  userId: text("userId").references(() => userTable.id),
  name: text("name").notNull(),
  location: text("location"),
  activityTypes: json("activityTypes"),
  description: text("description"),
  rating: integer("rating"),
  link: text("link"),
  imageUrl: text("imageUrl"),
  date: text("date"),
  tripId: integer("tripId").references(() => userPlannedTrips.id),
});
