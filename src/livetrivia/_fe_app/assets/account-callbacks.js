globalThis.dash_clientside = { // eslint-disable-line camelcase
	...globalThis.dash_clientside, accounts: {
		updateDisplay: value => value ?? '',
		updateStateSignout: value => !value,
	},
};
