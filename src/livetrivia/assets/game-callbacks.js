let _gamePollInterval = null;

globalThis.dash_clientside = {
	...globalThis.dash_clientside,
	game: {
		setGameSrc(pathname) {
			if (!pathname) {
				return '';
			}

			if (_gamePollInterval !== null) {
				clearInterval(_gamePollInterval);
				_gamePollInterval = null;
			}

			const parts = pathname.split('/').filter(Boolean);
			const src = `/gameserver/${parts.at(-1)}/`;

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
	},
};
