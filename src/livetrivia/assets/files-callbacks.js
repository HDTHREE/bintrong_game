globalThis.dash_clientside = { // eslint-disable-line camelcase
	...globalThis.dash_clientside, files: {
		openUpload: _ => document.querySelector('input[type="file"]').click(), // eslint-disable-line no-undef
		updateStateSubmit: value => !value,
		openYouTubeModal: _ => true,
		closeYouTubeModal: _ => false,

	},
};

function goToFileRow(api, fileId) {
	if (!api || !fileId) {
		return;
	}

	let targetNode = null;
	api.forEachNode(node => {
		if (node.data?.id === fileId) {
			targetNode = node;
		}
	});
	if (!targetNode) {
		return;
	}

	const page = Math.floor(targetNode.rowIndex / api.paginationGetPageSize());
	api.paginationGoToPage(page);
	api.deselectAll();
	targetNode.setSelected(true);
	api.ensureIndexVisible(targetNode.rowIndex, 'middle');
	setTimeout(() => {
		targetNode.setSelected(false);
	}, 3000);
}

globalThis.dashAgGridFunctions = {
	...globalThis.dashAgGridFunctions,
	originIdGetter: parameters => parameters?.data?.generated_from_id ?? 'None',
	generateParams(parameters) {
		const prefix = parameters.data?.prefix ?? '';
		const isAnki = prefix.endsWith('.apkg') || prefix.endsWith('.apkg');
		return {
			rightIcon: 'ic:baseline-attach-file',
			value: 'Generate',
			color: 'green',
			disabled: isAnki,
		};
	},
};

globalThis.dashAgGridComponentFunctions = {
	originRenderer(props) {
		console.log(props);
		const {prefix, generated_from_id: generatedFromId, generated_from_prefix: generatedFromPrefix} = props.data ?? {};
		if (generatedFromPrefix?.includes('/scripts/')) {
			return globalThis.dashAgGridComponentFunctions.nameRenderer({
				...props, data: {
					...props.data, prefix: generatedFromPrefix,
				},
			});
		}

		if (generatedFromPrefix) {
			const onClick = () => goToFileRow(props.api, generatedFromId);
			return React.createElement( // eslint-disable-line no-undef
				'span',
				{onClick, style: {cursor: 'pointer', textDecoration: 'underline'}},
				decodeURIComponent(generatedFromPrefix.split('/')?.pop() ?? ''),
			);
		}

		if (prefix?.includes('/scripts/')) {
			return React.createElement('span', null, 'YouTube'); // eslint-disable-line no-undef
		}

		return React.createElement('span', null, 'Upload'); // eslint-disable-line no-undef
	},
	originIdRenderer(props) {
		const {generated_from_id: generatedFromId, generated_from_prefix: generatedFromPrefix} = props.data ?? {};
		if (!generatedFromId) {
			return React.createElement('span', null, 'None'); // eslint-disable-line no-undef
		}

		if (generatedFromPrefix?.includes('/scripts/')) {
			return React.createElement('span', null, generatedFromId); // eslint-disable-line no-undef
		}

		const onClick = () => goToFileRow(props.api, generatedFromId);
		return React.createElement( // eslint-disable-line no-undef
			'span',
			{onClick, style: {cursor: 'pointer', textDecoration: 'underline'}},
			generatedFromId,
		);
	},
	nameRenderer(props) {
		const prefix = props.data?.prefix;
		const isTranscript = Boolean(prefix?.includes('/scripts/'));
		const videoId = isTranscript ? (prefix.split('/scripts/')?.[1]?.split('/')?.[0] ?? '') : '';

		const [title, setTitle] = React.useState(''); // eslint-disable-line no-undef

		React.useEffect(() => { // eslint-disable-line no-undef
			if (!videoId) {
				return;
			}

			const controller = new AbortController();
			fetch(
				`https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v=${videoId}&format=json`,
				{signal: controller.signal},
			).then(r => r.json()).then(data => setTitle(data?.title ?? '')).catch(() => {});
			return () => controller.abort();
		}, [videoId]);

		if (!isTranscript) {
			return React.createElement('span', null, decodeURIComponent(prefix?.split('/')?.pop() ?? '')); // eslint-disable-line no-undef
		}

		return React.createElement( // eslint-disable-line no-undef
			'a',
			{href: `https://www.youtube.com/watch?v=${videoId}`, target: '_blank', rel: 'noreferrer noopener'},
			title,
		);
	},
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
				disabled: props.disabled,
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
