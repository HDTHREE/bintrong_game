let _gamePollInterval = null;

const _isMobile = 'ontouchstart' in window || navigator.maxTouchPoints > 0;

function _hideNavbarForGame() {
	if (!_isMobile) return;
	const header = document.querySelector('.mantine-AppShell-header');
	const main = document.querySelector('.mantine-AppShell-main');
	const iframe = document.querySelector('#game-embed');
	if (header) header.style.display = 'none';
	if (main) main.style.paddingTop = '0';
	if (iframe) iframe.style.height = '100dvh';
}

function _restoreNavbarForGame() {
	if (!_isMobile) return;
	const header = document.querySelector('.mantine-AppShell-header');
	const main = document.querySelector('.mantine-AppShell-main');
	const iframe = document.querySelector('#game-embed');
	if (header) header.style.display = '';
	if (main) main.style.paddingTop = '';
	if (iframe) iframe.style.height = '';
}

window.addEventListener('message', event => {
	if (event.data?.type === 'gameEnded') {
		globalThis._livetrivia_gameEnded = true;
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

			_hideNavbarForGame();

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
			if (globalThis._livetrivia_gameEnded) {
				globalThis._livetrivia_gameEnded = false;
				_restoreNavbarForGame();
				return '/join';
			}

			return globalThis.dash_clientside.no_update;
		},
	},
};
