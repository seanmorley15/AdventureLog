import { db } from '$lib/db/db.server';
import { featuredAdventures } from '$lib/db/schema';
import type { Adventure } from '$lib/utils/types';


export const load = (async () => {
    const result = await db.select().from(featuredAdventures).orderBy(featuredAdventures.id);
    return {
        result : result as Adventure[]
    };
}) 