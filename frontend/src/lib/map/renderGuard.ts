/**
 * MapLibre GL JS throws "Attempting to run(), but is already running" when
 * ResizeObserver (or an app-level resize) calls redraw() while _render() is
 * already on the stack. If that throw happens inside the task queue, the queue
 * stays marked as running and the map never paints again.
 *
 * Markers/layers often mount in the `load` handler, which MapLibre fires
 * *during* _render(), so this race shows up after the first successful paint
 * (cold start) and then on every later visit (warm JS).
 *
 * Patch the prototype (not only the possibly-proxied instance) so MapLibre's
 * own `this.redraw()` from ResizeObserver is guarded.
 */

type MapLibreTaskQueue = {
	_currentlyRunning?: unknown;
};

type GuardedMap = {
	_removed?: boolean;
	_styleDirty?: boolean;
	_sourcesDirty?: boolean;
	_renderTaskQueue?: MapLibreTaskQueue;
	__adventurelogRenderGuard?: boolean;
	resize?: (...args: unknown[]) => unknown;
	redraw?: (...args: unknown[]) => unknown;
	triggerRepaint?: () => void;
	on?: (type: string, listener: (...args: unknown[]) => void) => void;
};

type GuardedMapProto = GuardedMap & { __adventurelogRedrawPatched?: boolean };

function isAlreadyRunningError(err: unknown): boolean {
	return err instanceof Error && err.message.includes('already running');
}

export function recoverMapRenderQueue(map: GuardedMap | null | undefined): void {
	if (!map?._renderTaskQueue) return;
	if (map._renderTaskQueue._currentlyRunning) {
		map._renderTaskQueue._currentlyRunning = false;
	}
}

export function isMapRenderRunning(map: GuardedMap | null | undefined): boolean {
	if (!map || map._removed) return true;
	return Boolean(map._renderTaskQueue?._currentlyRunning);
}

export function safeMapResize(map: GuardedMap | null | undefined, attempt = 0): void {
	if (!map || map._removed || typeof map.resize !== 'function') return;

	if (isMapRenderRunning(map)) {
		if (attempt > 10) {
			recoverMapRenderQueue(map);
		} else {
			requestAnimationFrame(() => safeMapResize(map, attempt + 1));
			return;
		}
	}

	try {
		map.resize();
	} catch (err) {
		recoverMapRenderQueue(map);
		if (isAlreadyRunningError(err) && attempt <= 10) {
			requestAnimationFrame(() => safeMapResize(map, attempt + 1));
			return;
		}
		if (!isAlreadyRunningError(err)) throw err;
	}
}

function guardedRedraw(
	originalRedraw: (...args: unknown[]) => unknown,
	map: GuardedMap,
	args: unknown[]
): unknown {
	if (map._removed) return map;
	if (map._renderTaskQueue?._currentlyRunning) {
		map._styleDirty = true;
		map._sourcesDirty = true;
		return map;
	}
	try {
		return originalRedraw.apply(map, args);
	} catch (err) {
		recoverMapRenderQueue(map);
		if (isAlreadyRunningError(err)) {
			map._styleDirty = true;
			map._sourcesDirty = true;
			map.triggerRepaint?.();
			return map;
		}
		throw err;
	}
}

function patchRedrawPrototype(map: GuardedMap): void {
	let proto = Object.getPrototypeOf(map) as GuardedMapProto | null;
	while (proto && proto !== Object.prototype) {
		if (typeof proto.redraw === 'function') {
			if (proto.__adventurelogRedrawPatched) return;
			proto.__adventurelogRedrawPatched = true;
			const originalRedraw = proto.redraw;
			proto.redraw = function (this: GuardedMap, ...args: unknown[]) {
				return guardedRedraw(originalRedraw, this, args);
			};
			return;
		}
		proto = Object.getPrototypeOf(proto) as GuardedMapProto | null;
	}
}

/** Patch redraw so nested ResizeObserver callbacks cannot kill the map. */
export function guardMapRenderQueue(map: GuardedMap | null | undefined): void {
	if (!map) return;

	patchRedrawPrototype(map);

	if (map.__adventurelogRenderGuard) return;
	map.__adventurelogRenderGuard = true;
	map.on?.('error', () => recoverMapRenderQueue(map));
}
