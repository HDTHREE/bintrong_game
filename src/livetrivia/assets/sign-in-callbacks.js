globalThis.dash_clientside = { // eslint-disable-line camelcase
	...globalThis.dash_clientside, login: {
		updateCurrentMenu(_, __) {
			// eslint-disable-next-line no-undef
			if (dash_clientside.callback_context.triggered_id === 'new-button') { // eslint-disable-line camelcase
				return [false, true];
			}

			return [true, false];
		},
		updateStateLogin: (email, password) => !(email && password),
		updateStateCreate(email, password, confirm) {
			if (!email || email.length === 0 || !password || password.length === 0) {
				return true;
			}

			return password !== confirm;
		},
		redirectToAccount(_, __, token, user) {
			if (!token || !user) {
				return;
			}

			setTimeout(() => {
				globalThis.location.href = '/login';
			}, 500);
		},
		updateLoginAlert(user, token) {
			const hidden = {display: 'none'};
			const visible = {display: 'block'};

			if (user && token && token.access_token) {
				return [`Logged in as ${user}.`, visible, 'blue'];
			}

			if (!user && !token) {
				return ['Your session has expired. Please log in again.', visible, 'yellow'];
			}

			return [globalThis.dash_clientside.no_update, hidden, globalThis.dash_clientside.no_update];
		},
	},
};
