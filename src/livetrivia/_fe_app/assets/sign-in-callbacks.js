globalThis.dash_clientside = { // eslint-disable-line camelcase
	...globalThis.dash_clientside, login: {
		updateCurrentMenu: (new_, cancel) => {
			if (!new_ && !cancel) return [true, false];
			if (dash_clientside.callback_context.triggered_id === "new-button") return [false, true];
			return [true, false];
		},
		updateStateLogin: (email, password) => !(email && password),
		updateStateCreate(email, password, confirm) {
			if (!email || email.length === 0 || !password || password.length === 0) {
				return true;
			}

			return password !== confirm;
		},
	},
};
