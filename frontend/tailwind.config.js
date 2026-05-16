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

					'base-100': '#121212',
					'base-200': '#1d1d1d',
					'base-300': '#292929',
					'base-content': '#e9e7e7',

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
					primary: '#479bb3',
					'primary-focus': '#81A1C1',
					'primary-content': '#ECEFF4',

					secondary: '#5E81AC',
					'secondary-focus': '#4C566A',
					'secondary-content': '#ECEFF4',

					accent: '#B48EAD',
					'accent-focus': '#A3BE8C',
					'accent-content': '#ECEFF4',

					neutral: '#4C566A',
					'neutral-focus': '#3B4252',
					'neutral-content': '#D8DEE9',

					'base-100': '#2E3440',
					'base-200': '#3B4252',
					'base-300': '#434C5E',
					'base-content': '#ECEFF4',

					info: '#88C0D0',
					success: '#A3BE8C',
					warning: '#D08770',
					error: '#BF616A'
				},

				light: {
					primary: '#3E6B57',
					'primary-focus': '#315646',
					'primary-content': '#F7F3EC',

					secondary: '#4F7DA3',
					'secondary-focus': '#3C637F',
					'secondary-content': '#F7F3EC',

					accent: '#C89B4B',
					'accent-focus': '#A97F35',
					'accent-content': '#1E1A14',

					neutral: '#4B4A45',
					'neutral-focus': '#363531',
					'neutral-content': '#F7F3EC',

					'base-100': '#F5F1E8',
					'base-200': '#E7E0D2',
					'base-300': '#D5CCBC',
					'base-content': '#1D2320',

					info: '#4F7DA3',
					success: '#4F7D5E',
					warning: '#D6A13C',
					error: '#B85C4A',

					'--rounded-box': '1rem',
					'--rounded-btn': '.5rem',
					'--rounded-badge': '1.9rem',

					'--animation-btn': '.25s',
					'--animation-input': '.2s',

					'--btn-text-case': 'uppercase',
					'--navbar-padding': '.5rem',
					'--border-btn': '1px',

					fontFamily:
						'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
				},

				dark: {
					primary: '#5A8C74',
					'primary-focus': '#466E5A',
					'primary-content': '#F4F0E8',

					secondary: '#5C8FB5',
					'secondary-focus': '#486F8D',
					'secondary-content': '#F4F0E8',

					accent: '#D1A24A',
					'accent-focus': '#B28332',
					'accent-content': '#14120E',

					neutral: '#2C332F',
					'neutral-focus': '#222723',
					'neutral-content': '#F4F0E8',

					'base-100': '#111713',
					'base-200': '#181F1A',
					'base-300': '#202822',
					'base-content': '#F4F0E8',

					info: '#5C8FB5',
					success: '#6AA37D',
					warning: '#D6A13C',
					error: '#C96A57',

					'--rounded-box': '1rem',
					'--rounded-btn': '.5rem',
					'--rounded-badge': '1.9rem',

					'--animation-btn': '.25s',
					'--animation-input': '.2s',

					'--btn-text-case': 'uppercase',
					'--navbar-padding': '.5rem',
					'--border-btn': '1px',

					fontFamily:
						'ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif'
				}
			}
		]
	}
};
