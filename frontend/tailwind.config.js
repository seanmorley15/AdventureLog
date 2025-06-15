/** @type {import('tailwindcss').Config} */
export default {
	content: ['./src/**/*.{html,js,svelte,ts}'],
	theme: {
		extend: {}
	},
	plugins: [require('@tailwindcss/typography'), require('daisyui')],
	daisyui: {
		themes: [
			'light',
			'dark',
			'night',
			'retro',
			'forest',
			'aqua',
			'emerald',
			'dim',
			{
				aestheticDark: {
					primary: '#3e5747',
					'primary-focus': '#2f4236',
					'primary-content': '#e9e7e7',

					secondary: '#547b82',
					'secondary-focus': '#3d5960',
					'secondary-content': '#c1dfe5',

					accent: '#8b6161',
					'accent-focus': '#6e4545',
					'accent-content': '#f2eaea',

					neutral: '#2b2a2a',
					'neutral-focus': '#272525',
					'neutral-content': '#e9e7e7',

					'base-100': '#121212', // Dark background
					'base-200': '#1d1d1d',
					'base-300': '#292929',
					'base-content': '#e9e7e7', // Light content on dark background

					// set bg-primary-content
					'bg-base': '#121212',
					'bg-base-content': '#e9e7e7',

					info: '#3b7ecb',
					success: '#007766',
					warning: '#d4c111',
					error: '#e64a19',

					'--rounded-box': '1rem',
					'--rounded-btn': '.5rem',
					'--rounded-badge': '1.9rem',

					'--animation-btn': '.25s',
					'--animation-input': '.2s',

					'--btn-text-case': 'uppercase',
					'--navbar-padding': '.5rem',
					'--border-btn': '1px',

					fontFamily:
						'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
				},
				aestheticLight: {
					primary: '#5a7c65',
					'primary-focus': '#48604f',
					'primary-content': '#dcd5d5',

					secondary: '#a8cfd7',
					'secondary-focus': '#5585aa',
					'secondary-content': '#177a9b',

					accent: '#c78e8e',
					'accent-focus': '#b25757',
					'accent-content': '#322020',

					neutral: '#5c5757',
					'neutral-focus': '#272525',
					'neutral-content': '#e9e7e7',

					'base-100': '#e9e7e7',
					'base-200': '#d1cccc',
					'base-300': '#b9b1b1',
					'base-content': '#100f0f',

					info: '#1c92f2',
					success: '#009485',
					warning: '#c8c21e',
					error: '#ff5724',

					'--rounded-box': '1rem',
					'--rounded-btn': '.5rem',
					'--rounded-badge': '1.9rem',

					'--animation-btn': '.25s',
					'--animation-input': '.2s',

					'--btn-text-case': 'uppercase',
					'--navbar-padding': '.5rem',
					'--border-btn': '1px',

					fontFamily:
						'ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace'
				},
				northernLights: {
					primary: '#479bb3', // Primary color
					'primary-focus': '#81A1C1', // Primary color - focused
					'primary-content': '#ECEFF4', // Foreground content color to use on primary color

					secondary: '#5E81AC', // Secondary color
					'secondary-focus': '#4C566A', // Secondary color - focused
					'secondary-content': '#ECEFF4', // Foreground content color to use on secondary color

					accent: '#B48EAD', // Accent color
					'accent-focus': '#A3BE8C', // Accent color - focused
					'accent-content': '#ECEFF4', // Foreground content color to use on accent color

					neutral: '#4C566A', // Neutral color
					'neutral-focus': '#3B4252', // Neutral color - focused
					'neutral-content': '#D8DEE9', // Foreground content color to use on neutral color

					'base-100': '#2E3440', // Base color of page, used for blank backgrounds
					'base-200': '#3B4252', // Base color, a little lighter
					'base-300': '#434C5E', // Base color, even more lighter
					'base-content': '#ECEFF4', // Foreground content color to use on base color

					info: '#88C0D0', // Info
					success: '#A3BE8C', // Success
					warning: '#D08770', // Warning
					error: '#BF616A' // Error
				}
			}
		]
	}
};
