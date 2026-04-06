let _gamePollInterval = null;

window.addEventListener('message', event => {
	if (event.data?.type === 'gameEnded') {
		window._livetrivia_gameEnded = true;
	}
});

globalThis.dash_clientside = {
	...globalThis.dash_clientside,
	game: {
		setGameSrc(pathname, gamePlayerData) {
			if (!pathname) {
				return '';
			}

			if (_gamePollInterval !== null) {
				clearInterval(_gamePollInterval);
				_gamePollInterval = null;
			}

			const parts = pathname.split('/').filter(Boolean);
			const gamePlayerId = gamePlayerData?.id ?? '';
			const src = `/gameserver/${parts.at(-1)}/?gamePlayerId=${encodeURIComponent(gamePlayerId)}`;

			_gamePollInterval = setInterval(() => {
				const iframe = document.querySelector('#game-embed');
				if (!iframe) {
					return;
				}

				try {
					if (iframe.contentDocument?.title === 'Three.js + TypeScript') {
						iframe.style.visibility = 'visible';
						clearInterval(_gamePollInterval);
						_gamePollInterval = null;
					} else {
						iframe.style.visibility = 'hidden';
						iframe.src = src;
					}
				} catch {
					iframe.style.visibility = 'hidden';
					iframe.src = src;
				}
			}, 1000);

			return src;
		},
		pollGameEnded(_n) {
			if (window._livetrivia_gameEnded) {
				window._livetrivia_gameEnded = false;
				return '/join';
			}

			return window.dash_clientside.no_update;
		},
	},
};
