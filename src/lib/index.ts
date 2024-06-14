import inspirationalQuotes from "./json/quotes.json";
import type { Adventure } from "./utils/types";

/**
 * Generates the URL for a flag image based on the specified size and country code.
 * @param size - The desired height of the flag image. Avaliable sizes: 20, 24, 40, 60, 80, 120, 240.
 * @param country - The 2 digit country code representing the desired flag.
 * @returns The URL of the flag image.
 */
export function getFlag(size: number, country: string) {
  return `https://flagcdn.com/h${size}/${country}.png`;
}

/**
 * Generates a random string consisting of alphanumeric characters.
 * @returns {string} The randomly generated string.
 */
export function generateRandomString() {
  let randomString = "";
  const digits =
    "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ";

  for (let i = 0; i < 10; i++) {
    const randomIndex = Math.floor(Math.random() * digits.length);
    randomString += digits[randomIndex];
  }
  return randomString;
}

const quotes = inspirationalQuotes.quotes;
/**
 * Retrieves a random quote from the quotes array.
 * @returns A formatted string containing the random quote and its author.
 */
export function getRandomQuote() {
  const randomIndex = Math.floor(Math.random() * quotes.length);
  let quoteString = quotes[randomIndex].quote;
  let authorString = quotes[randomIndex].author;
  return '"' + quoteString + '" - ' + authorString;
}

/**
 * Adds activity types to the adventure.
 *
 * @param activityInput - The input string containing activity types separated by commas.
 * @param adventureToEdit - The adventure object to which the activity types will be added.
 * @returns The adventure object with the updated activity types.
 */
export function addActivityType(
  activityInput: string,
  adventureToEdit: Adventure
) {
  if (activityInput.trim() !== "") {
    const activities = activityInput
      .split(",")
      .filter((activity) => activity.trim() !== "");
    // trims the whitespace from the activities
    for (let i = 0; i < activities.length; i++) {
      activities[i] = activities[i].trim();
    }
    adventureToEdit.activityTypes = activities;
    activityInput = "";
  }
  return adventureToEdit;
}

/**
 * Generates a description for an adventure using the adventure title.
 * @param adventureTitle - The title of the adventure.
 * @returns A Promise that resolves to the description of the adventure.
 */
export async function generateDescription(adventureTitle: string) {
  const url = `https://en.wikipedia.org/w/api.php?origin=*&action=query&prop=extracts&exintro&explaintext&format=json&titles=${encodeURIComponent(
    adventureTitle
  )}`;

  try {
    const res = await fetch(url);
    const data = await res.json();

    // Check if the query was successful
    if (data.query && data.query.pages) {
      const pageId = Object.keys(data.query.pages)[0];
      const page = data.query.pages[pageId];

      // Check if the page exists
      if (page.extract) {
        return page.extract;
      } else {
        return `No Wikipedia article found for "${adventureTitle}".`;
      }
    } else {
      return `Error: ${data.error.info}`;
    }
  } catch (error) {
    console.error("Error fetching Wikipedia data:", error);
    return `Error fetching Wikipedia data for "${adventureTitle}".`;
  }
}

export async function getImage(adventureTitle: string) {
  const url = `https://en.wikipedia.org/w/api.php?origin=*&action=query&prop=pageimages&format=json&piprop=original&titles=${adventureTitle}`;

  try {
    const res = await fetch(url);
    const data = await res.json();

    // Check if the query was successful
    if (data.query && data.query.pages) {
      const pageId = Object.keys(data.query.pages)[0];
      const page = data.query.pages[pageId];

      // Check if the page has an image
      if (page.original && page.original.source) {
        return page.original.source;
      } else {
        return `No image found for "${adventureTitle}".`;
      }
    } else {
      return `Error: ${data.error.info}`;
    }
  } catch (error) {
    console.error("Error fetching Wikipedia data:", error);
    return `Error fetching Wikipedia data for "${adventureTitle}".`;
  }
}

/**
 * Returns the URL of an object in the specified bucket.
 * @param bucketName - The name of the bucket.
 * @param fileName - The name of the file.
 * @returns The URL of the object.
 */
export const getObjectUrl = (bucketName: string, fileName: string): string => {
  let objectUrl: string;
  let endpoint: string = "";
  if (import.meta.env.VITE_MINIO_CLIENT_OVERRIDE) {
    endpoint = import.meta.env.VITE_MINIO_CLIENT_OVERRIDE as string;
  } else {
    endpoint = import.meta.env.VITE_AWS_S3_ENDPOINT as string;
  }

  // This code is not as clean as it could be, but it works for whats needed. Help is welcome to clean it up!
  // Currently supports Amazon S3, Google Cloud Storage, DigitalOcean Spaces, and Supabase Storage as well as self-hosted MinIO.

  if (endpoint.includes("amazonaws.com")) {
    // Amazon S3
    objectUrl = `https://${bucketName}.s3.${
      import.meta.env.AWS_REGION
    }.amazonaws.com/${fileName}`;
  } else if (endpoint.includes("storage.googleapis.com")) {
    // Google Cloud Storage
    objectUrl = `https://storage.googleapis.com/${bucketName}/${fileName}`;
  } else if (endpoint.includes("digitaloceanspaces.com")) {
    // DigitalOcean Spaces
    objectUrl = `https://${bucketName}.${endpoint}/${fileName}`;
  } else if (endpoint.includes("supabase.co")) {
    // Supabase Storage
    endpoint = endpoint.replace("s3", "object/public"); // Remove the version
    console.log(endpoint);
    objectUrl = `${endpoint}/${bucketName}/${fileName}`;
  } else {
    // Default fallback
    objectUrl = `${endpoint}/${bucketName}/${fileName}`;
  }

  return objectUrl as string;
};
