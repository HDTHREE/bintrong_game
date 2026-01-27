globalThis.dash_clientside = { // eslint-disable-line camelcase
	...globalThis.dash_clientside, layout: {
		setInitials: user => (user ?? '').trim().slice(0, 2).toUpperCase(),
	},
};
