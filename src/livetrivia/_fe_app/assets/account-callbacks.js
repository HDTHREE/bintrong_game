globalThis.dash_clientside = { // eslint-disable-line camelcase
	...globalThis.dash_clientside, accounts: {
		updateDisplay: value => value ?? '',
		updateStateSignout: value => !value,
		redirectToLogin: (_, __) => setTimeout(() => globalThis.location.href = '/login', 500),
	},
};
