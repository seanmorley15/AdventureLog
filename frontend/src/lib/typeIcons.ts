import type { Component } from 'svelte';

import OfficeBuilding from '~icons/mdi/office-building';
import BunkBed from '~icons/mdi/bunk-bed';
import Island from '~icons/mdi/island';
import Coffee from '~icons/mdi/coffee';
import Tent from '~icons/mdi/tent';
import PineTree from '~icons/mdi/pine-tree';
import Domain from '~icons/mdi/domain';
import Home from '~icons/mdi/home';
import HomeModern from '~icons/mdi/home-modern';
import Bed from '~icons/mdi/bed';
import BedOutline from '~icons/mdi/bed-outline';

import Car from '~icons/mdi/car';
import Airplane from '~icons/mdi/airplane';
import Train from '~icons/mdi/train';
import Bus from '~icons/mdi/bus';
import SailBoat from '~icons/mdi/sail-boat';
import Bike from '~icons/mdi/bike';
import Walk from '~icons/mdi/walk';
import MapMarkerPath from '~icons/mdi/map-marker-path';

type IconComponent = Component<any>;

const lodgingIcons: Record<string, IconComponent> = {
	hotel: OfficeBuilding,
	hostel: BunkBed,
	resort: Island,
	bnb: Coffee,
	campground: Tent,
	cabin: PineTree,
	apartment: Domain,
	house: Home,
	villa: HomeModern,
	motel: Bed,
	other: BedOutline
};

const transportationIcons: Record<string, IconComponent> = {
	car: Car,
	plane: Airplane,
	train: Train,
	bus: Bus,
	boat: SailBoat,
	bike: Bike,
	walking: Walk,
	other: MapMarkerPath
};

export function getLodgingTypeIcon(type: string | null | undefined): IconComponent {
	return (type && lodgingIcons[type]) || BedOutline;
}

export function getTransportationTypeIcon(type: string | null | undefined): IconComponent {
	return (type && transportationIcons[type]) || MapMarkerPath;
}
