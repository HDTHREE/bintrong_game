globalThis.dash_clientside = { // eslint-disable-line camelcase
	...globalThis.dash_clientside, join: {
		updateStateCode: code => !code || code?.length !== 6,
		updateStateHostButton: value => !value,
	},
};
