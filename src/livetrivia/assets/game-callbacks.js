globalThis.dash_clientside = {
	...globalThis.dash_clientside,
	game: {
		setGameSrc(pathname) {
			if (!pathname) {
				return '';
			}

			const parts = pathname.split('/').filter(Boolean);
			return `/gameserver/${parts.at(-1)}/`;
		},
	},
};
