globalThis.dash_clientside = { // eslint-disable-line camelcase
	...globalThis.dash_clientside, join: {
		updateState: code => !code || code?.length !== 6,
	},
};
