import type { Adventure } from '$lib/utils/types';

let adventures: Adventure[] = [];

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
}

export function getAdventures(): Adventure[] {
    return adventures;
}

export function removeAdventure(event: { detail: number; }) {
    adventures = adventures.filter(adventure => adventure.id !== event.detail);
    if (isBrowser) {
        localStorage.setItem('adventures', JSON.stringify(adventures));
    }
}

export function saveEdit(editId:number, editName:string, editLocation:string, editCreated:string) {
    const adventure = adventures.find(adventure => adventure.id === editId);
    if (adventure) {
        adventure.name = editName;
        adventure.location = editLocation;
        adventure.created = editCreated;
    }
    editId = NaN;
    console.log("done")
    if (isBrowser) {
        localStorage.setItem('adventures', JSON.stringify(adventures));
    }
}

export function getNumberOfAdventures() {
    return adventures.length;
}


