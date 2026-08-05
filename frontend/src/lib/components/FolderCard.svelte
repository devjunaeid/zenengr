<script>
	/**
	 * Folder card in the files gallery grid. Whole card is a navigation
	 * trigger (drills into the folder); hover reveals rename/delete actions.
	 * @type {{
	 *   folder: import('$lib/api/files.js').FolderTreeNode,
	 *   canAct: boolean,
	 *   busy?: boolean,
	 *   onopen: () => void,
	 *   onrename: () => void,
	 *   ondelete: () => void
	 * }}
	 */
	let { folder, canAct, busy = false, onopen, onrename, ondelete } = $props();

	/** @param {MouseEvent} e */
	function onClick(e) {
		if (e.target instanceof Element && e.target.closest('button, a')) return;
		onopen();
	}

	/** @param {KeyboardEvent} e */
	function onKeydown(e) {
		if (e.key !== 'Enter' && e.key !== ' ') return;
		if (e.target instanceof Element && e.target.closest('button, a')) return;
		e.preventDefault();
		onopen();
	}

	const overlayBtn =
		'flex h-7 w-7 items-center justify-center rounded text-white hover:bg-white/20 disabled:cursor-not-allowed disabled:opacity-40';
</script>

<div
	class="group relative flex cursor-pointer flex-col rounded-lg border border-slate-200 bg-white p-2 shadow-sm transition focus-within:ring-2 focus-within:ring-indigo-500 focus-within:outline-none hover:border-slate-300 hover:shadow-md"
	role="button"
	tabindex="0"
	aria-label={`Open folder ${folder.name}`}
	onclick={onClick}
	onkeydown={onKeydown}
>
	<div class="relative">
		<div class="flex h-24 items-center justify-center rounded-md bg-amber-50">
			<svg
				xmlns="http://www.w3.org/2000/svg"
				viewBox="0 0 20 20"
				fill="currentColor"
				class="h-10 w-10 text-amber-500"
				aria-hidden="true"
			>
				<path
					fill-rule="evenodd"
					d="M3.75 3A1.75 1.75 0 002 4.75v10.5c0 .966.784 1.75 1.75 1.75h12.5A1.75 1.75 0 0018 15.25v-8.5A1.75 1.75 0 0016.25 5h-4.836a.25.25 0 01-.177-.073L9.823 3.513A1.75 1.75 0 008.586 3H3.75zM6.5 7.75a.75.75 0 01.75-.75h5.5a.75.75 0 010 1.5h-5.5a.75.75 0 01-.75-.75z"
					clip-rule="evenodd"
				/>
			</svg>
		</div>
		<div
			class="absolute inset-x-0 bottom-0 flex items-center justify-center gap-1 rounded-b-md bg-slate-900/70 p-2 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100 max-sm:opacity-100"
		>
			<button
				type="button"
				title="Rename"
				aria-label="Rename"
				disabled={!canAct || busy}
				onclick={onrename}
				class={overlayBtn}
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4"
					aria-hidden="true"
				>
					<path
						fill-rule="evenodd"
						d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
			<button
				type="button"
				title="Delete"
				aria-label="Delete"
				disabled={!canAct || busy}
				onclick={ondelete}
				class="{overlayBtn} hover:bg-red-500/30 hover:text-red-200"
			>
				<svg
					xmlns="http://www.w3.org/2000/svg"
					viewBox="0 0 20 20"
					fill="currentColor"
					class="h-4 w-4"
					aria-hidden="true"
				>
					<path
						fill-rule="evenodd"
						d="M9 2a1 1 0 00-.894.553L7.382 4H4a1 1 0 000 2v10a2 2 0 002 2h8a2 2 0 002-2V6a1 1 0 100-2h-3.382l-.724-1.447A1 1 0 0011 2H9zM7 8a1 1 0 012 0v6a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v6a1 1 0 102 0V8a1 1 0 00-1-1z"
						clip-rule="evenodd"
					/>
				</svg>
			</button>
		</div>
	</div>
	<div class="mt-2 min-w-0 px-1">
		<p class="truncate text-sm font-medium text-slate-900" title={folder.name}>{folder.name}</p>
		<p class="truncate text-xs text-slate-500">Folder</p>
	</div>
</div>
