import { writable } from 'svelte/store';

export const toasts = writable<{ type: any; message: any; id: number }[]>([]);

export const addToast = (type: any, message: any, duration = 5000) => {
	const id = Date.now();
	toasts.update((currentToasts) => {
		return [...currentToasts, { type, message, id, duration }];
	});
	setTimeout(() => {
		removeToast(id);
	}, duration);
};

export const removeToast = (id: number) => {
	toasts.update((currentToasts) => {
		return currentToasts.filter((toast) => toast.id !== id);
	});
};
