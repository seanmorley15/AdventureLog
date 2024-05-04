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

/**
 * function savePlan(event: { detail: Adventure }) {
    console.log("Event", event.detail);
    let detailAdventure = event.detail;

    // put request to /api/visits with id and adventure data
    fetch("/api/planner", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        detailAdventure,
      }),
    })
      .then((response) => response.json())
      .then((data) => {
        console.log("Success:", data);
        // update local array with new data
        const index = plans.findIndex(
          (adventure) => adventure.id === detailAdventure.id
        );
        if (index !== -1) {
          plans[index] = detailAdventure;
        }
        adventureToEdit = undefined;
        // showToast("Adventure edited successfully!");
      })
      .catch((error) => {
        console.error("Error:", error);
      });
  }
    */
