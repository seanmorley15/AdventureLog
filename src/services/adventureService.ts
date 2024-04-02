import type { Adventure } from '$lib/utils/types';

let adventures: Adventure[] = [];

import { visitCount } from '$lib/utils/stores/visitCountStore';

// Check if localStorage is available (browser environment)
const isBrowser = typeof window !== 'undefined';


// Load adventures from localStorage on startup (only in the browser)
if (isBrowser) {
    const storedAdventures = localStorage.getItem('adventures');
    if (storedAdventures) {
        adventures = JSON.parse(storedAdventures);
    }
}

export function getNextId() {
    let nextId = Math.max(0, ...adventures.map(adventure => adventure.id)) + 1;
    return nextId;
}

export function setAdventures(importArray: Adventure[]) {
    adventures = importArray
}

export function addAdventure(adventure: Adventure) {
    adventures = [...adventures, adventure];
    if (isBrowser) {
        localStorage.setItem('adventures', JSON.stringify(adventures));
    }
    console.log(adventures);
    visitCount.update((n) => n + 1);
}

export function getAdventures(): Adventure[] {
    return adventures;
}

export function removeAdventure(event: { detail: number; }) {
    adventures = adventures.filter(adventure => adventure.id !== event.detail);
    if (isBrowser) {
        localStorage.setItem('adventures', JSON.stringify(adventures));
    }
    visitCount.update((n) => n - 1);
}

export function saveEdit(adventure:Adventure) {
    let editId = adventure.id;
    console.log("saving edit")
    let editName = adventure.name;
    let editLocation = adventure.location;
    let editCreated = adventure.created;
    let oldAdventure: Adventure | undefined = adventures.find(adventure => adventure.id === editId);
    console.log("old" + oldAdventure)
    if (oldAdventure) {
        oldAdventure.name = editName;
        oldAdventure.location = editLocation;
        oldAdventure.created = editCreated;
    }
    editId = NaN;
    console.log("done")
    if (isBrowser) {
        localStorage.setItem('adventures', JSON.stringify(adventures));
    }
}

export function clearAdventures() {
    adventures = [];
    if (isBrowser) {
        localStorage.setItem('adventures', JSON.stringify(adventures));
    }
}


