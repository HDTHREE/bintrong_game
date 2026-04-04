globalThis.dash_clientside = { // eslint-disable-line camelcase
	...globalThis.dash_clientside, files: {
		openUpload: _ => document.querySelector('input[type="file"]').click(),
		updateStateSubmit: value => !value,
		openYouTubeModal: _ => true,
		closeYouTubeModal: _ => false,

	},
};

globalThis.dashAgGridFunctions = {
	...globalThis.dashAgGridFunctions,
	nameGetter(parameters) {
		// If the video is a transcript we are going to fetch the title of the youtube video.
		const {prefix} = parameters.data;
		const isTranscript = Boolean(prefix?.includes('/scripts/'));
		if (isTranscript) {
			const videoId = prefix.split('/scripts/')?.[1].split('/')?.[0];
			if (!videoId) {
				return '';
			}

			const request = new XMLHttpRequest();
			request.open(
				'GET',
				`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`,
				false,
			);
			request.send(null);

			try {
				const response = JSON.parse(request.responseText);
				return response.title;
			} catch {
				return '';
			}
		}

		return decodeURIComponent(prefix?.split('/')?.pop() ?? '');
	},
	originGetter(parameters) {
		if (parameters.data.generated_from_prefix) {
			return globalThis.dashAgGridComponentFunctions.nameGetter(parameters);
		}

		if (parameters.data.prefix?.includes('/scripts/')) {
			return 'YouTube';
		}

		return 'Upload';
	},
	originIdGetter: parameters => parameters?.data?.generated_from_id ?? 'None',
};

globalThis.dashAgGridComponentFunctions = {
	// Adapted from: https://www.dash-mantine-components.com/dash-ag-grid#example-2:-buttons
	dmcButton(props) {
		const {setData} = props;

		function onClick() {
			setData();
		}

		let leftIcon;
		let rightIcon;
		if (props?.leftIcon) { // eslint-disable-next-line no-undef
			leftIcon = React.createElement(globalThis.dash_iconify.DashIconify, {
				icon: props.leftIcon,
			});
		}

		if (props?.rightIcon) { // eslint-disable-next-line no-undef
			rightIcon = React.createElement(globalThis.dash_iconify.DashIconify, {
				icon: props.rightIcon,
			});
		}

		return React.createElement( // eslint-disable-line no-undef
			globalThis.dash_mantine_components.Button,
			{
				onClick,
				variant: props.variant,
				color: props.color,
				leftSection: leftIcon,
				rightSection: rightIcon,
				radius: props.radius,
				style: {
					margin: props.margin,
					display: 'flex',
					justifyContent: 'center',
					alignItems: 'center',
				},
			},
			props.value,
		);
	},
};
