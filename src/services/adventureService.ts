import { visitCount } from "$lib/utils/stores/visitCountStore";
import type { Adventure } from "$lib/utils/types";

/**
 * Object containing the API routes for the different types of adventures.
 */
const apiRoutes: { [key: string]: string } = {
  planner: "/api/planner",
  mylog: "/api/visits",
};

/**
 * Saves an adventure by sending a PUT request to the corresponding API endpoint.
 * If the request is successful, the local adventure array is updated with the new data.
 * If the request fails, an empty array is returned to allow for handling errors.
 * @param adventure - The adventure object to be saved.
 * @param adventureArray - The array of adventures to be updated.
 * @returns A promise that resolves to the updated adventure array.
 */
export async function saveAdventure(
  adventure: Adventure,
  adventureArray: Adventure[]
): Promise<Adventure[]> {
  const detailAdventure = adventure;
  const type = detailAdventure.type;
  const url = apiRoutes[type];

  // put request to /api/visits with id and adventure data
  const response = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      detailAdventure,
    }),
  });

  if (response.ok) {
    // update local array with new data
    const index = adventureArray.findIndex(
      (adventure) => adventure.id === detailAdventure.id
    );
    if (index !== -1) {
      adventureArray[index] = detailAdventure;
    }
    // showToast("Adventure edited successfully!");
  } else {
    console.error("Error:", response.statusText);
    adventureArray = [];
  }

  return adventureArray;
}

/**
 * Removes an adventure from the adventure array and sends a delete request to the server.
 * @param adventure - The adventure to be removed.
 * @param adventureArray - The array of adventures.
 * @returns A promise that resolves to the updated adventure array.
 */
export async function removeAdventure(
  adventure: Adventure,
  adventureArray: Adventure[]
): Promise<Adventure[]> {
  let url = apiRoutes[adventure.type];
  // delete request to /api/visits with id
  const response = await fetch(url, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ id: adventure.id }),
  });

  if (response.ok) {
    // remove adventure from array where id matches
    adventureArray = adventureArray.filter(
      (existingAdventure) => existingAdventure.id !== adventure.id
    );
    // showToast("Adventure removed successfully!");
  } else {
    console.error("Error:", response.statusText);
    adventureArray = [];
  }

  console.log(adventureArray);

  return adventureArray;
}

/**
 * Adds an adventure to the adventure array and sends a POST request to the specified URL.
 * @param {Adventure} adventure - The adventure to be added.
 * @param {Adventure[]} adventureArray - The array of adventures.
 * @returns {Promise<Adventure[]>} - A promise that resolves to the updated adventure array.
 */
export async function addAdventure(
  adventure: Adventure,
  adventureArray: Adventure[]
): Promise<Adventure[]> {
  let url = apiRoutes[adventure.type];
  let detailAdventure = adventure;
  // post request to /api/visits with adventure data
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ detailAdventure }),
  })
    .then((response) => response.json())
    .then((data) => {
      adventureArray.push(data.adventure);
      if (data.adventure.type === "mylog") {
        incrementVisitCount(1);
      }
    })
    .catch((error) => {
      console.error("Error:", error);
      return [];
    });

  return adventureArray;
}

export async function changeType(
  newAdventure: Adventure,
  newType: string,
  adventureArray: Adventure[]
) {
  newAdventure.type = newType;
  let detailAdventure = newAdventure;

  const response = await fetch("/api/visits", {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ detailAdventure }),
  });

  if (response.ok) {
    // remove adventure from array where id matches
    adventureArray = adventureArray.filter(
      (existingAdventure) => existingAdventure.id !== newAdventure.id
    );
    // showToast("Adventure removed successfully!");
  } else {
    console.error("Error:", response.statusText);
    adventureArray = [];
  }

  console.log(adventureArray);

  return adventureArray;
}
/**
 * Increments the visit count by the specified amount.
 * @param {number} amount - The amount to increment the visit count by.
 */
export function incrementVisitCount(amount: number) {
  visitCount.update((n) => n + 1);
}
