import type {
	CalendarDateProps,
	CalendarMonthProps,
	CalendarRangeProps
} from 'cally';
import type { HTMLAttributes } from 'svelte/elements';

type MapEvents<T> = {
	[K in keyof T as K extends `on${infer E}` ? `on${Lowercase<E>}` : K]: T[K];
};

declare module 'svelte/elements' {
	interface SvelteHTMLElements {
		'calendar-range': MapEvents<CalendarRangeProps> & HTMLAttributes<HTMLElement>;
		'calendar-month': MapEvents<CalendarMonthProps> & HTMLAttributes<HTMLElement>;
		'calendar-date': MapEvents<CalendarDateProps> & HTMLAttributes<HTMLElement>;
	}

	interface SVGAttributes<T> {
		slot?: string;
	}
}

export {};
