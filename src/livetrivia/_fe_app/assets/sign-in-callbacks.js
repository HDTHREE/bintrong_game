globalThis.dash_clientside = { // eslint-disable-line camelcase
	...globalThis.dash_clientside, clientside: {
		onClickNew: _ => [false, true],
		updateStateLogin: (email, password) => !(email && password),
		onClickCancel: _ => [true, false],
		updateStateCreate(email, password, confirm) {
			if (!email || email.length === 0 || !password || password.length === 0) {
				return true;
			}

			return password !== confirm;
		},
	},
};
