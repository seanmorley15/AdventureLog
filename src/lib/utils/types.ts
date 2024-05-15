export interface Adventure {
  id: number;
  type: string;
  name: string;
  location?: string | undefined;
  activityTypes?: string[] | undefined;
  description?: string | undefined;
  rating?: number | undefined;
  link?: string | undefined;
  imageUrl?: string | undefined;
  date?: string | undefined;
  tripId?: number | undefined;
}

export interface Trip {
  id: number;
  name: string;
  description: string;
  startDate: string;
  endDate: string;
  adventures?: Adventure[] | [];
}
