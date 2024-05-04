import type { Adventure } from "$lib/utils/types";

// json that maps the type to api routes
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
 * function removeAdventure(event: { detail: number }) {
    console.log("Event ID " + event.detail);
    // send delete request to server at /api/visits
    fetch("/api/visits", {
      method: "DELETE",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ id: event.detail }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Success:", data);
        // remove adventure from array where id matches
        plans = plans.filter((adventure) => adventure.id !== event.detail);
        // showToast("Adventure removed successfully!");
        // visitCount.update((n) => n - 1);
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }
 * 
 * 
    */
