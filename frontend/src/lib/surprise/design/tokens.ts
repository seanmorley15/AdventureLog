/**
 * Yvette Surprise Trip - Premium Romance Design Tokens
 */

export const tokens = {
	colors: {
		primary: {
			50: '#fdf2f4',
			100: '#fce7eb',
			200: '#f9d0d9',
			300: '#f4a9bb',
			400: '#ed7a97',
			500: '#e04d75',
			600: '#cc2d5a',
			700: '#ab2049',
			800: '#8f1d40',
			900: '#7a1c3a'
		},
		gold: {
			50: '#fefbe8',
			100: '#fef7c3',
			200: '#feee8a',
			300: '#fde047',
			400: '#facc15',
			500: '#eab308',
			600: '#ca8a04',
			700: '#a16207'
		},
		surface: {
			light: '#fffbf7',
			card: '#ffffff',
			overlay: 'rgba(28, 25, 23, 0.75)'
		}
	},
	gradients: {
		hero: 'linear-gradient(135deg, #fdf2f4 0%, #fef7c3 50%, #fdf2f4 100%)',
		card: 'linear-gradient(180deg, #ffffff 0%, #fffbf7 100%)',
		locked: 'linear-gradient(180deg, rgba(28, 25, 23, 0.6) 0%, rgba(28, 25, 23, 0.85) 100%)'
	},
	spacing: { 1: '0.25rem', 2: '0.5rem', 3: '0.75rem', 4: '1rem', 6: '1.5rem', 8: '2rem' },
	shadows: {
		card: '0 4px 20px rgba(28, 25, 23, 0.08)',
		glow: '0 0 40px rgba(224, 77, 117, 0.15)'
	},
	animation: {
		duration: { fast: '150ms', normal: '200ms', reveal: '500ms' },
		easing: { reveal: 'cubic-bezier(0.16, 1, 0.3, 1)' }
	}
} as const;

export default tokens;
