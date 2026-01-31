globalThis.dashAgGridFunctions = {
	...globalThis.dashAgGridFunctions,
	nameGetter: parameters => parameters.data.prefix ? parameters.data.prefix.split('/').pop() : '',
};

globalThis.dashAgGridComponentFunctions = {
	// Adapted from: https://www.dash-mantine-components.com/dash-ag-grid#example-2:-buttons
	dmcButton(props) {
		const {setData, data} = props;

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
