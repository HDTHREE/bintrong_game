globalThis.dashAgGridFunctions = { // eslint-disable-line camelcase
	...globalThis.dashAgGridFunctions ,
    nameGetter: params => params.data.prefix ? params.data.prefix.split('/').pop() : ''
};
